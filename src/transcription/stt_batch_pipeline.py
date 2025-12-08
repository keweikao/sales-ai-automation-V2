import os
import time
import json
import re
import logging
from typing import List, Dict, Any, Optional
from google.cloud import speech_v2
from google.cloud.speech_v2.types import cloud_speech
from google.api_core.client_options import ClientOptions

from .base_pipeline import TranscriptionPipeline

logger = logging.getLogger(__name__)

class STTBatchTranscriptionPipeline(TranscriptionPipeline):
    def __init__(self, project_id: str, location: str = "us-central1", bucket_name: str = None):
        self.project_id = project_id
        self.location = location
        self.bucket_name = bucket_name
        
        # Initialize Speech V2 Client
        self.client = speech_v2.SpeechClient(
            client_options=ClientOptions(
                api_endpoint=f"{location}-speech.googleapis.com"
            )
        )
        self.recognizer_id = "sales-ai-recognizer" # Persistent recognizer ID
        self.recognizer_path = f"projects/{project_id}/locations/{location}/recognizers/{self.recognizer_id}"

    def _ensure_recognizer(self):
        """Ensures a standard recognizer exists."""
        parent = f"projects/{self.project_id}/locations/{self.location}"
        try:
            self.client.get_recognizer(name=self.recognizer_path)
            logger.info(f"Recognizer {self.recognizer_id} exists.")
        except Exception:
            logger.info(f"Creating recognizer {self.recognizer_id}...")
            request = cloud_speech.CreateRecognizerRequest(
                parent=parent,
                recognizer_id=self.recognizer_id,
                recognizer=cloud_speech.Recognizer(
                    default_recognition_config=cloud_speech.RecognitionConfig(
                        auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
                        language_codes=["cmn-Hant-TW", "en-US"], # Support Mixed
                        model="latest_long", # Optimized for long audio
                        features=cloud_speech.RecognitionFeatures(
                            enable_word_time_offsets=True,
                            enable_automatic_punctuation=True,
                            # Diarization not supported for latest_long model
                            # diarization_config=cloud_speech.SpeakerDiarizationConfig(
                            #     min_speaker_count=2,
                            #     max_speaker_count=2
                            # )
                        ),
                    )
                ),
            )
            operation = self.client.create_recognizer(request=request)
            operation.result()
            logger.info(f"Recognizer {self.recognizer_id} created.")

    def submit_batch(self, audio_uris: List[str]) -> str:
        """
        Submits a batch job for multiple files.
        Returns the Operation Name.
        """
        self._ensure_recognizer()
        
        # Infer bucket from the first URI for output
        if not self.bucket_name and audio_uris:
             match = re.match(r"gs://([^/]+)/", audio_uris[0])
             if match:
                 self.bucket_name = match.group(1)
        
        if not self.bucket_name:
            raise ValueError("Bucket name required for output storage.")

        # Create a unique batch ID for output folder
        batch_id = f"batch_{int(time.time())}"
        output_uri = f"gs://{self.bucket_name}/transcripts_stt_batch/{batch_id}/"
        
        logger.info(f"Submitting Batch Job for {len(audio_uris)} files to {output_uri}...")
        
        files_metadata = [cloud_speech.BatchRecognizeFileMetadata(uri=uri) for uri in audio_uris]
        
        batch_config = cloud_speech.BatchRecognizeRequest(
            recognizer=self.recognizer_path,
            files=files_metadata,
            recognition_output_config=cloud_speech.RecognitionOutputConfig(
                gcs_output_config=cloud_speech.GcsOutputConfig(
                    uri=output_uri
                )
            ),
            processing_strategy=cloud_speech.BatchRecognizeRequest.ProcessingStrategy.DYNAMIC_BATCHING
        )

        operation = self.client.batch_recognize(request=batch_config)
        logger.info(f"Batch Operation started: {operation.operation.name}")
        return operation.operation.name

    def check_batch_status(self, operation_name: str) -> bool:
        """Checks if a batch operation is done."""
        operation = self.client.transport.operations_client.get_operation(name=operation_name)
        return operation.done

    def get_results(self, operation_name: str) -> Dict[str, Any]:
        """
        Retrieves results for a completed operation.
        Returns a dictionary mapping input_uri -> transcript_result (List[Dict])
        """
        # We need to get the operation result to find the output GCS path
        # Since get_operation doesn't return the full response object easily deserialized,
        # we rely on the fact that we know the output structure or we can list the output bucket.
        # However, the proper way is to get the result from the operation.
        
        # Re-wrap operation
        from google.api_core import operation as ga_operation
        op = ga_operation.from_gapic(
            self.client.transport.operations_client.get_operation(name=operation_name),
            self.client.transport.operations_client,
            cloud_speech.BatchRecognizeResponse,
            metadata_type=cloud_speech.BatchRecognizeMetadata
        )
        
        if not op.done():
            raise ValueError(f"Operation {operation_name} is not done yet.")
            
        result = op.result()
        
        results_map = {}
        
        for uri, file_result in result.results.items():
            # Match input URI to result
            # The response map key is the input URI
            
            if file_result.error.code:
                logger.error(f"Error in file result for {uri}: {file_result.error}")
                continue
                
            gcs_uri = file_result.cloud_storage_result.json_result_uri
            
            # Download JSON
            from google.cloud import storage
            storage_client = storage.Client()
            bucket_name = gcs_uri.replace("gs://", "").split("/")[0]
            blob_name = "/".join(gcs_uri.replace("gs://", "").split("/")[1:])
            
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            json_content = blob.download_as_text()
            data = json.loads(json_content)
            
            # The JSON contains 'metadata': {'inputUri': '...'}
            input_uri = data.get("metadata", {}).get("inputUri")
            if not input_uri:
                # Fallback: try to match by filename if possible, or skip
                logger.warning(f"Could not find inputUri in result JSON: {gcs_uri}")
                continue

            transcripts = []
            for result_item in data.get("results", []):
                alternatives = result_item.get("alternatives", [])
                if not alternatives:
                    continue
                
                alt = alternatives[0]
                transcript_text = alt.get("transcript", "")
                
                words = alt.get("words", [])
                if words:
                    current_speaker = None
                    current_segment = None
                    
                    for word in words:
                        speaker = word.get("speakerLabel", "Unknown")
                        start_time = float(word.get("startOffset", "0s")[:-1])
                        end_time = float(word.get("endOffset", "0s")[:-1])
                        word_text = word.get("word", "")
                        
                        if speaker != current_speaker:
                            if current_segment:
                                transcripts.append(current_segment)
                            current_speaker = speaker
                            current_segment = {
                                "start": start_time,
                                "end": end_time,
                                "speaker": speaker,
                                "text": word_text
                            }
                        else:
                            if current_segment:
                                current_segment["text"] += " " + word_text
                                current_segment["end"] = end_time
                    
                    if current_segment:
                        transcripts.append(current_segment)
                else:
                    transcripts.append({
                        "start": 0.0,
                        "end": 0.0,
                        "speaker": "Unknown",
                        "text": transcript_text
                    })
            
            results_map[input_uri] = {
                "segments": transcripts,
                "full_text": " ".join([t["text"] for t in transcripts]),
                "language": "zh-TW" # Default/Inferred
            }
            
        return results_map

    def transcribe(self, audio_path: str) -> List[Dict[str, Any]]:
        """
        Legacy single-file transcribe method. 
        Wraps submit_batch for a single file and waits.
        """
        op_name = self.submit_batch([audio_path])
        
        # Poll
        while not self.check_batch_status(op_name):
            time.sleep(10)
            
        results = self.get_results(op_name)
        return results.get(audio_path, {}).get("segments", [])
