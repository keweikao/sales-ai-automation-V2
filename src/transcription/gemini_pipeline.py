import os
import json
import logging
import time
from typing import Dict, Any, Optional, List
import google.generativeai as genai

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiTranscriptionPipeline:
    """
    Transcription pipeline using Google AI Gemini API.
    Supports direct audio transcription with speaker diarization.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize the Gemini pipeline with Google AI API.
        
        Args:
            api_key: Google AI API Key (GEMINI_API_KEY)
        """
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required for Google AI Gemini")
        
        # Configure Google AI
        genai.configure(api_key=api_key)
        
        # Load model
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.model = genai.GenerativeModel(self.model_name)
        
        logger.info(f"GeminiTranscriptionPipeline initialized with model: {self.model_name}")

    def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe audio file using Gemini.
        
        Args:
            audio_path: Path to the local audio file
            
        Returns:
            Dictionary containing transcription results in the standard format:
            {
                "success": True,
                "full_text": "Full text...",
                "segments": [...],
                "speakers": [...],
                "audio_info": {"duration": ...}
            }
        """
        try:
            logger.info(f"Starting Gemini transcription for: {audio_path}")
            start_time = time.time()
            
            # Read audio file
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
            
            # Detect MIME type based on file extension
            ext = os.path.splitext(audio_path)[1].lower()
            mime_type_map = {
                '.mp3': 'audio/mp3',
                '.m4a': 'audio/mp4',
                '.wav': 'audio/wav',
                '.flac': 'audio/flac',
                '.ogg': 'audio/ogg',
            }
            mime_type = mime_type_map.get(ext, 'audio/mp3')
            
            # Upload file to Gemini
            logger.info(f"Uploading audio file ({len(audio_bytes)} bytes, {mime_type})")
            audio_file = genai.upload_file(path=audio_path, mime_type=mime_type)
            
            # Wait for file to be processed
            while audio_file.state.name == "PROCESSING":
                logger.info("Waiting for file processing...")
                time.sleep(2)
                audio_file = genai.get_file(audio_file.name)
            
            if audio_file.state.name == "FAILED":
                raise ValueError(f"File processing failed: {audio_file.state}")
            
            logger.info("File uploaded and processed successfully")
            
            # Prompt for structured output
            prompt = """
            You are a professional transcriber. 
            Transcribe the following audio file into a structured JSON format.
            
            Requirements:
            1. Identify different speakers (Speaker 1, Speaker 2, etc.).
            2. Provide a list of segments with 'start' (seconds), 'end' (seconds), 'speaker', and 'text'.
            3. Provide a list of unique speakers identified.
            4. Provide the full combined text.
            5. The output MUST be valid JSON. Do not include markdown formatting like ```json ... ```.
            
            Output Format:
            {
                "segments": [
                    {"start": 0.0, "end": 5.5, "speaker": "Speaker 1", "text": "Hello..."},
                    ...
                ],
                "speakers": ["Speaker 1", "Speaker 2"],
                "text": "Full transcript text..."
            }
            """
            
            # Generate content
            logger.info("Generating transcription...")
            response = self.model.generate_content(
                [audio_file, prompt],
                generation_config={
                    "temperature": 0.2,
                    "max_output_tokens": 8192,
                    "response_mime_type": "application/json"
                }
            )
            
            # Parse response
            try:
                result_json = json.loads(response.text)
                
                # Validate structure
                if "segments" not in result_json:
                    result_json["segments"] = []
                if "speakers" not in result_json:
                    result_json["speakers"] = []
                if "text" not in result_json:
                    # Reconstruct text if missing
                    result_json["text"] = " ".join([s.get("text", "") for s in result_json["segments"]])
                
                # Convert to standard format
                processing_time = time.time() - start_time
                
                # Calculate audio duration from segments
                audio_duration = 0
                if result_json["segments"]:
                    audio_duration = max(s.get("end", 0) for s in result_json["segments"])
                
                # Build speaker statistics
                speakers_list = []
                if result_json["speakers"]:
                    for speaker in result_json["speakers"]:
                        speakers_list.append({
                            "speakerId": speaker,
                            "speakingTime": 0,  # Gemini doesn't provide this
                            "percentage": 0
                        })
                
                standard_result = {
                    "success": True,
                    "full_text": result_json["text"],
                    "segments": result_json["segments"],
                    "speakers": speakers_list,
                    "audio_info": {
                        "duration": audio_duration,
                        "processing_time": processing_time
                    }
                }
                
                logger.info(f"Gemini transcription completed in {processing_time:.2f}s")
                logger.info(f"Transcribed {len(result_json['segments'])} segments, {len(result_json['speakers'])} speakers")
                
                # Clean up uploaded file
                try:
                    genai.delete_file(audio_file.name)
                    logger.info("Cleaned up uploaded file")
                except Exception as e:
                    logger.warning(f"Failed to delete uploaded file: {e}")
                
                return standard_result
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini response as JSON: {response.text}")
                raise ValueError(f"Invalid JSON response from Gemini: {e}")
                
        except Exception as e:
            logger.error(f"Gemini transcription failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "full_text": "",
                "segments": [],
                "speakers": []
            }
