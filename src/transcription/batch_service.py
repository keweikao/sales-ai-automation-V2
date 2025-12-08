import os
import json
import logging
import time
import re
import tempfile
import uuid
from typing import Dict, Any, Optional, List
from pathlib import Path

import google.generativeai as genai
from google.cloud import storage, firestore, tasks_v2

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BatchTranscriptionService:
    """
    Service to handle Gemini Batch API interactions.
    """
    
    def __init__(self, api_key: str, project_id: str):
        self.api_key = api_key
        self.project_id = project_id
        
        # Initialize Gemini
        genai.configure(api_key=api_key)
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        
        logger.info(f"BatchTranscriptionService: google-generativeai version: {genai.__version__}")
        logger.info(f"BatchTranscriptionService: genai attributes: {dir(genai)}")
        
        # Initialize Google Cloud Clients
        self.storage_client = storage.Client()
        self.db = firestore.Client()
        self.tasks_client = tasks_v2.CloudTasksClient()
        
        # Buckets
        self.requests_bucket = "sales-ai-batch-requests" # Needs to be created
        self.results_bucket = "sales-ai-batch-results"   # Needs to be created

    def _parse_plain_text_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse Gemini Plain Text response (e.g., "[00:12] Speaker 1: Hello").
        Reused logic from GeminiTranscriptionPipeline.
        """
        segments = []
        speakers = set()
        
        # Regex to match: [MM:SS] Speaker: Content
        pattern = re.compile(r'\[(\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)\]\s*([^:]+):\s*(.+)')
        
        lines = response_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            match = pattern.match(line)
            if match:
                time_str, speaker, content = match.groups()
                
                try:
                    parts = time_str.split(':')
                    if len(parts) == 2: # MM:SS
                        seconds = int(parts[0]) * 60 + float(parts[1])
                    elif len(parts) == 3: # H:MM:SS
                        seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                    else:
                        continue
                        
                    abs_start = seconds
                    duration_est = max(1.0, len(content) / 3.0)
                    abs_end = abs_start + duration_est
                    
                    segments.append({
                        "start": round(abs_start, 2),
                        "end": round(abs_end, 2),
                        "speaker": speaker.strip(),
                        "text": content.strip()
                    })
                    
                    speakers.add(speaker.strip())
                except ValueError:
                    continue
            else:
                if segments:
                    segments[-1]["text"] += " " + line
        
        # Adjust end times
        for i in range(len(segments) - 1):
            if segments[i]["end"] > segments[i+1]["start"]:
                segments[i]["end"] = segments[i+1]["start"]
        
        return {
            "segments": segments,
            "speakers": list(speakers),
            "text": "\n".join(lines)
        }

    def submit_job(self, audio_gcs_uri: str, case_id: str) -> Dict[str, Any]:
        """
        Submit a batch transcription job.
        1. Download audio from GCS.
        2. Upload to Gemini File API.
        3. Create JSONL request.
        4. Upload JSONL to GCS.
        5. Submit Batch Job.
        """
        logger.info(f"Submitting batch job for Case {case_id}, Audio: {audio_gcs_uri}")
        
        # 1. Download Audio
        bucket_name, blob_name = audio_gcs_uri.replace("gs://", "").split("/", 1)
        bucket = self.storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        with tempfile.NamedTemporaryFile(suffix=os.path.splitext(blob_name)[1], delete=False) as temp_audio:
            logger.info(f"Downloading audio to {temp_audio.name}")
            blob.download_to_filename(temp_audio.name)
            temp_audio_path = temp_audio.name

        try:
            # 2. Upload to Gemini File API
            logger.info("Uploading to Gemini File API...")
            mime_type = "audio/mp4" # Defaulting to mp4/m4a as per use case
            if temp_audio_path.endswith(".mp3"): mime_type = "audio/mp3"
            if temp_audio_path.endswith(".wav"): mime_type = "audio/wav"
            
            gemini_file = genai.upload_file(temp_audio_path, mime_type=mime_type)
            
            # Wait for processing
            while gemini_file.state.name == "PROCESSING":
                time.sleep(2)
                gemini_file = genai.get_file(gemini_file.name)
                
            if gemini_file.state.name == "FAILED":
                raise ValueError(f"Gemini File Processing Failed: {gemini_file.state}")
            
            logger.info(f"Gemini File Ready: {gemini_file.uri}")

            # 3. Create JSONL Request
            prompt = """
            You are a professional transcriber. 
            Transcribe the following audio file into Traditional Chinese (繁體中文).
            
            Output Format:
            [MM:SS] Speaker: Content
            
            Example:
            [00:10] Speaker 1: 你好
            [00:15] Speaker 2: 早安
            
            Strictly follow this format. Do not include any other text.
            """
            
            request_id = f"req-{case_id}-{uuid.uuid4().hex[:8]}"
            batch_request = {
                "custom_id": request_id,
                "request": {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [
                                {"file_data": {"mime_type": mime_type, "file_uri": gemini_file.uri}},
                                {"text": prompt}
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.2,
                        "maxOutputTokens": 8192,
                        "responseMimeType": "text/plain"
                    }
                }
            }
            
            # 4. Upload JSONL to GCS
            jsonl_filename = f"batch-req-{case_id}.jsonl"
            jsonl_content = json.dumps(batch_request)
            
            req_bucket = self.storage_client.bucket(self.requests_bucket)
            if not req_bucket.exists():
                self.storage_client.create_bucket(self.requests_bucket, location="asia-east1")
                
            req_blob = req_bucket.blob(jsonl_filename)
            req_blob.upload_from_string(jsonl_content)
            gcs_input_uri = f"gs://{self.requests_bucket}/{jsonl_filename}"
            logger.info(f"Uploaded JSONL to {gcs_input_uri}")

            # 5. Submit Batch Job
            # Output URI prefix
            res_bucket = self.storage_client.bucket(self.results_bucket)
            if not res_bucket.exists():
                self.storage_client.create_bucket(self.results_bucket, location="asia-east1")
            
            gcs_output_uri = f"gs://{self.results_bucket}/"
            
            logger.info("Creating Batch Job...")
            batch_job = genai.create_batch_job(
                display_name=f"transcription-{case_id}",
                source=gcs_input_uri,
                destination=gcs_output_uri
            )
            
            logger.info(f"Batch Job Submitted: {batch_job.name}")
            
            # Save Job ID to Firestore
            self.db.collection("cases").document(case_id).update({
                "transcriptionJobId": batch_job.name,
                "transcriptionStatus": "batch_processing",
                "updatedAt": firestore.SERVER_TIMESTAMP
            })
            
            return {
                "success": True,
                "job_id": batch_job.name,
                "status": batch_job.state.name
            }

        finally:
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)

    def handle_batch_completion(self, result_gcs_uri: str) -> Dict[str, Any]:
        """
        Handle completion notification.
        1. Download result JSONL.
        2. Parse content.
        3. Update Firestore.
        4. Trigger Analysis.
        """
        logger.info(f"Handling batch completion: {result_gcs_uri}")
        
        # 1. Download Result
        bucket_name, blob_name = result_gcs_uri.replace("gs://", "").split("/", 1)
        bucket = self.storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        content = blob.download_as_text()
        
        # Parse JSONL (assuming one request per file for now)
        try:
            result_data = json.loads(content)
        except json.JSONDecodeError:
            # Handle multiple lines if needed, but we expect one
            lines = content.strip().split('\n')
            result_data = json.loads(lines[0])
            
        custom_id = result_data.get("custom_id")
        # Extract case_id from custom_id (req-{case_id}-{uuid})
        # Assuming case_id doesn't have hyphens? Or we parse carefully.
        # Format: req-202512-IC001-12345678
        # Split by '-'
        parts = custom_id.split('-')
        # req, 202512, IC001, uuid -> Case ID is parts[1]-parts[2]
        if len(parts) >= 4:
            case_id = f"{parts[1]}-{parts[2]}"
        else:
            logger.error(f"Could not extract Case ID from custom_id: {custom_id}")
            return {"success": False, "error": "Invalid custom_id"}
            
        logger.info(f"Processing result for Case: {case_id}")
        
        # Check for errors
        response = result_data.get("response", {})
        if "error" in response:
            error_msg = response["error"].get("message", "Unknown Batch Error")
            logger.error(f"Batch Job Failed for {case_id}: {error_msg}")
            self.db.collection("cases").document(case_id).update({
                "transcriptionStatus": "failed",
                "error": error_msg
            })
            return {"success": False, "error": error_msg}
            
        # Get generated text
        try:
            candidates = response.get("candidates", [])
            if not candidates:
                raise ValueError("No candidates in response")
            
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                raise ValueError("No parts in content")
                
            text_output = parts[0].get("text", "")
            
            # 2. Parse Text
            parsed_result = self._parse_plain_text_response(text_output)
            
            # 3. Update Firestore
            transcription_data = {
                "text": parsed_result["text"],
                "segments": parsed_result["segments"],
                "speakers": parsed_result["speakers"],
                "duration": 0, # Batch result doesn't give duration easily, maybe update later or keep from audio info
                "language": "zh",
            }
            
            self.db.collection("cases").document(case_id).update({
                "transcription": transcription_data,
                "status": "transcribed",
                "transcriptionStatus": "completed",
                "updatedAt": firestore.SERVER_TIMESTAMP
            })
            
            logger.info(f"Transcription saved to Firestore for {case_id}")
            
            # 4. Trigger Analysis
            self._trigger_analysis(case_id)
            
            return {"success": True, "case_id": case_id}
            
        except Exception as e:
            logger.error(f"Failed to process batch result: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _trigger_analysis(self, case_id: str):
        """Trigger Analysis Service via Cloud Tasks"""
        ANALYSIS_QUEUE = "analysis-queue"
        ANALYSIS_LOCATION = "asia-east1"
        ANALYSIS_SERVICE_URL = os.environ.get(
            "ANALYSIS_SERVICE_URL",
            "https://analysis-service-497329205771.asia-east1.run.app/analyze"
        )
        SERVICE_ACCOUNT_EMAIL = os.environ.get(
            "SERVICE_ACCOUNT_EMAIL",
            "497329205771-compute@developer.gserviceaccount.com"
        )
        
        try:
            queue_path = self.tasks_client.queue_path(
                self.project_id, ANALYSIS_LOCATION, ANALYSIS_QUEUE
            )
            
            task_payload = {"caseId": case_id}
            
            task = {
                "http_request": {
                    "http_method": tasks_v2.HttpMethod.POST,
                    "url": ANALYSIS_SERVICE_URL,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps(task_payload).encode(),
                    "oidc_token": {"service_account_email": SERVICE_ACCOUNT_EMAIL}
                }
            }
            
            response = self.tasks_client.create_task(request={"parent": queue_path, "task": task})
            logger.info(f"Analysis task created: {response.name}")
            
        except Exception as e:
            logger.error(f"Failed to trigger analysis: {e}")
