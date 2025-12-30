"""
Speech-to-Text V2 Pipeline for synchronous transcription with Chirp 3.

Uses Speech-to-Text V2 API with streaming/batch approach but waits for result.
Supports speaker diarization with Chirp 3 model.
"""

import os
import logging
import time
import subprocess
import tempfile
from typing import Dict, Any, List, Optional

from google.cloud import speech_v2
from google.cloud.speech_v2.types import cloud_speech
from google.cloud import storage
from google.api_core import exceptions as gapi_exceptions
from google.api_core.client_options import ClientOptions
from pathlib import Path

from .base_pipeline import TranscriptionPipeline
from .chunking.chunker import AudioChunker

logger = logging.getLogger(__name__)


class STTV2Pipeline(TranscriptionPipeline):
    """
    Speech-to-Text V2 同步轉錄 Pipeline (Chirp 3).
    
    使用 Speech V2 API 的 Recognize 或 BatchRecognize，
    內部等待結果，對外表現為同步行為。
    精準度比 V1 更高，支援說話者分離。
    """
    
    def __init__(
        self,
        project_id: str = None,
        location: str = "us",  # us multi-region for Chirp 3 GA availability
        language_codes: List[str] = None,
        model: str = "chirp_3",
        enable_diarization: bool = False,
        min_speakers: int = 2,
        max_speakers: int = 4,
    ):
        """
        Initialize the STT V2 Pipeline.
        
        Args:
            project_id: GCP Project ID
            location: Region for Speech API (us-central1 recommended for Chirp)
            language_codes: List of language codes (default: Traditional Chinese + English)
            model: Model to use (chirp_3 recommended)
            enable_diarization: Enable speaker diarization
            min_speakers: Minimum number of speakers
            max_speakers: Maximum number of speakers
        """
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID", "sales-ai-automation-v2")
        self.location = location
        self.language_codes = language_codes or ["cmn-Hant-TW", "en-US"]
        self.model = model
        self.enable_diarization = enable_diarization
        self.min_speakers = min_speakers
        self.max_speakers = max_speakers
        
        # Initialize Speech V2 Client with regional endpoint
        self.client = speech_v2.SpeechClient(
            client_options=ClientOptions(
                api_endpoint=f"{location}-speech.googleapis.com"
            )
        )
        
        # Create recognizer path
        self.recognizer_id = "sales-ai-recognizer-chirp3"
        self.recognizer_path = f"projects/{self.project_id}/locations/{self.location}/recognizers/{self.recognizer_id}"
        
        # Lazy initialization flag - defer recognizer check to first transcription
        self._recognizer_initialized = False
        
        # Initialize AudioChunker for long audio files (>55 min)
        # Chirp 3 BatchRecognize has a 60-minute limit
        self.max_duration_seconds = 55 * 60  # 55 minutes (leave buffer)
        self.chunker = AudioChunker(
            target_chunk_duration=600,  # 10 minutes per chunk
            overlap_duration=2  # 2 seconds overlap
        )
        
        logger.info(
            f"STTV2Pipeline initialized: project={project_id}, location={location}, "
            f"model={model}, langs={language_codes}, diarization={enable_diarization}"
        )
    
    def _ensure_recognizer(self):
        """Ensures the recognizer exists, creates if not."""
        parent = f"projects/{self.project_id}/locations/{self.location}"
        
        try:
            self.client.get_recognizer(name=self.recognizer_path)
            logger.info(f"Recognizer {self.recognizer_id} exists.")
        except gapi_exceptions.NotFound:
            logger.info(f"Creating recognizer {self.recognizer_id}...")
            
            # Build recognition features
            features = cloud_speech.RecognitionFeatures(
                enable_word_time_offsets=True,
                enable_automatic_punctuation=True,
            )
            
            request = cloud_speech.CreateRecognizerRequest(
                parent=parent,
                recognizer_id=self.recognizer_id,
                recognizer=cloud_speech.Recognizer(
                    default_recognition_config=cloud_speech.RecognitionConfig(
                        auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
                        language_codes=self.language_codes,
                        model=self.model,
                        features=features,
                    )
                ),
            )
            
            operation = self.client.create_recognizer(request=request)
            operation.result(timeout=60)
            logger.info(f"Recognizer {self.recognizer_id} created.")
    
    def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe audio file using Speech-to-Text V2 API.
        
        Args:
            audio_path: GCS URI (gs://bucket/path) or local file path
            
        Returns:
            Dict with keys:
                - success: bool
                - segments: List of transcript segments with speaker info
                - text: Full transcript text
                - full_text: Alias for text
                - speakers: List of unique speaker labels
        """
        if audio_path.startswith("gs://"):
            return self._transcribe_gcs(audio_path)
        else:
            return self._transcribe_local(audio_path)
    
    def _convert_to_supported_format(self, gcs_uri: str) -> str:
        """
        Convert unsupported audio formats (M4A, CAF) to MP3.
        
        Args:
            gcs_uri: Original GCS URI
            
        Returns:
            New GCS URI with converted file
        """
        lower_uri = gcs_uri.lower()
        if not (lower_uri.endswith(".m4a") or lower_uri.endswith(".caf")):
            return gcs_uri
        
        format_name = "M4A" if lower_uri.endswith(".m4a") else "CAF"
        logger.info(f"Converting {format_name} to MP3: {gcs_uri}")
        
        # Parse GCS URI
        parts = gcs_uri.replace("gs://", "").split("/", 1)
        bucket_name = parts[0]
        blob_path = parts[1] if len(parts) > 1 else ""
        
        # Create temp files
        suffix = ".m4a" if lower_uri.endswith(".m4a") else ".caf"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as src_file:
            src_path = src_file.name
        
        mp3_path = src_path.rsplit(".", 1)[0] + ".mp3"
        
        try:
            # Download from GCS
            storage_client = storage.Client()
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            blob.download_to_filename(src_path)
            logger.info(f"Downloaded to {src_path}")
            
            # Convert to MP3 using ffmpeg
            cmd = [
                "ffmpeg", "-y", "-i", src_path,
                "-acodec", "libmp3lame",
                "-ar", "16000",
                "-ac", "1",
                "-q:a", "2",
                mp3_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg conversion failed: {result.stderr}")
            
            logger.info(f"Converted to MP3: {mp3_path}")
            
            # Upload MP3 to GCS
            mp3_blob_path = blob_path.rsplit(".", 1)[0] + "_converted.mp3"
            mp3_blob = bucket.blob(mp3_blob_path)
            mp3_blob.upload_from_filename(mp3_path)
            
            new_gcs_uri = f"gs://{bucket_name}/{mp3_blob_path}"
            logger.info(f"Uploaded MP3 to {new_gcs_uri}")
            
            return new_gcs_uri
            
        finally:
            for path in [src_path, mp3_path]:
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file {path}: {e}")
    
    def _get_audio_duration(self, gcs_uri: str) -> float:
        """Get audio duration in seconds using ffprobe."""
        # Download to temp file
        parts = gcs_uri.replace("gs://", "").split("/", 1)
        bucket_name = parts[0]
        blob_path = parts[1] if len(parts) > 1 else ""
        
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        
        with tempfile.NamedTemporaryFile(suffix=Path(blob_path).suffix, delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            blob.download_to_filename(tmp_path)
            
            cmd = [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", tmp_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            duration = float(result.stdout.strip())
            logger.info(f"Audio duration: {duration:.1f}s ({duration/60:.1f} min)")
            return duration
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    def _split_audio_chunk(self, gcs_uri: str, chunk: Dict) -> str:
        """Split audio file into a chunk and upload to GCS."""
        chunk_id = chunk["chunk_id"]
        start = chunk["start"]
        duration = chunk["duration"]
        
        # Download original file
        parts = gcs_uri.replace("gs://", "").split("/", 1)
        bucket_name = parts[0]
        blob_path = parts[1] if len(parts) > 1 else ""
        
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        
        suffix = Path(blob_path).suffix
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            src_path = tmp.name
        
        # Output chunk path
        chunk_suffix = ".mp3"  # Convert to MP3 for reliability
        with tempfile.NamedTemporaryFile(suffix=chunk_suffix, delete=False) as tmp:
            chunk_path = tmp.name
        
        try:
            blob.download_to_filename(src_path)
            
            # Use ffmpeg to extract chunk
            cmd = [
                "ffmpeg", "-y",
                "-i", src_path,
                "-ss", str(start),
                "-t", str(duration),
                "-ac", "1",  # Mono
                "-ar", "16000",  # 16kHz
                "-c:a", "libmp3lame",  # MP3 codec
                "-q:a", "2",  # Good quality
                chunk_path
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Upload chunk to GCS
            chunk_blob_path = f"temp_chunks/{Path(blob_path).stem}_chunk_{chunk_id:03d}.mp3"
            chunk_blob = bucket.blob(chunk_blob_path)
            chunk_blob.upload_from_filename(chunk_path)
            
            chunk_gcs_uri = f"gs://{bucket_name}/{chunk_blob_path}"
            logger.info(f"Uploaded chunk {chunk_id} to {chunk_gcs_uri}")
            
            return chunk_gcs_uri
            
        finally:
            for path in [src_path, chunk_path]:
                if os.path.exists(path):
                    os.remove(path)
    
    def _merge_results(self, results: List[Dict], chunks: List[Dict]) -> Dict[str, Any]:
        """Merge transcription results from multiple chunks."""
        all_segments = []
        all_text_parts = []
        all_speakers = set()
        
        for i, (result, chunk) in enumerate(zip(results, chunks)):
            if not result.get("success"):
                logger.warning(f"Chunk {i} failed: {result.get('error')}")
                continue
            
            time_offset = chunk["start"]
            
            # Adjust segment timestamps
            for segment in result.get("segments", []):
                adjusted_segment = segment.copy()
                adjusted_segment["start"] = segment["start"] + time_offset
                adjusted_segment["end"] = segment["end"] + time_offset
                all_segments.append(adjusted_segment)
                
                if segment.get("speaker"):
                    all_speakers.add(segment["speaker"])
            
            # Collect text
            if result.get("text"):
                all_text_parts.append(result["text"])
        
        full_text = " ".join(all_text_parts)
        
        return {
            "success": True,
            "segments": all_segments,
            "text": full_text,
            "full_text": full_text,
            "speakers": list(all_speakers),
            "engine": "stt_v2",
            "model": self.model,
            "language": ",".join(self.language_codes),
            "chunked": True,
            "chunk_count": len(results),
        }

    
    def _transcribe_gcs(self, gcs_uri: str) -> Dict[str, Any]:
        """Transcribe audio from GCS URI using BatchRecognize with inline result."""
        
        # Lazy initialization of recognizer on first transcription
        if not self._recognizer_initialized:
            self._ensure_recognizer()
            self._recognizer_initialized = True
        
        logger.info(f"Starting transcription for: {gcs_uri}")
        start_time = time.time()
        
        # Convert unsupported formats
        gcs_uri = self._convert_to_supported_format(gcs_uri)
        
        try:
            # Check audio duration for chunking
            duration = self._get_audio_duration(gcs_uri)
            
            if duration > self.max_duration_seconds:
                logger.info(f"Audio is {duration/60:.1f} min, exceeds {self.max_duration_seconds/60:.0f} min limit. Using chunking.")
                return self._transcribe_gcs_chunked(gcs_uri, duration)
            
            # Standard path for short audio
            return self._transcribe_gcs_single(gcs_uri, start_time)
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def _transcribe_gcs_single(self, gcs_uri: str, start_time: float) -> Dict[str, Any]:
        """Transcribe a single audio file (no chunking)."""
        try:
            # Use BatchRecognize for long audio, wait for result synchronously
            request = cloud_speech.BatchRecognizeRequest(
                recognizer=self.recognizer_path,
                files=[cloud_speech.BatchRecognizeFileMetadata(uri=gcs_uri)],
                recognition_output_config=cloud_speech.RecognitionOutputConfig(
                    inline_response_config=cloud_speech.InlineOutputConfig()
                ),
            )
            
            operation = self.client.batch_recognize(request=request)
            logger.info(f"Operation started: {operation.operation.name}")
            
            # Wait for result (timeout: 60 minutes for long audio ~50 min)
            result = operation.result(timeout=3600)
            
            elapsed = time.time() - start_time
            logger.info(f"Transcription completed in {elapsed:.1f}s")
            
            return self._parse_result(result, gcs_uri)
            
        except gapi_exceptions.InvalidArgument as e:
            logger.error(f"Invalid argument error: {e}")
            return {"success": False, "error": str(e)}
        except gapi_exceptions.DeadlineExceeded as e:
            logger.error(f"Transcription timeout: {e}")
            return {"success": False, "error": f"Timeout: {e}"}
        except Exception as e:
            logger.error(f"Transcription failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def _transcribe_gcs_chunked(self, gcs_uri: str, duration: float) -> Dict[str, Any]:
        """Transcribe long audio by splitting into chunks."""
        start_time = time.time()
        
        # Create chunks
        chunks = self.chunker.create_chunks(duration)
        logger.info(f"Created {len(chunks)} chunks for {duration/60:.1f} min audio")
        
        # Process each chunk
        results = []
        chunk_uris = []
        
        try:
            for chunk in chunks:
                logger.info(f"Processing chunk {chunk['chunk_id']}: {chunk['start']:.0f}s - {chunk['end']:.0f}s")
                
                # Split and upload chunk
                chunk_uri = self._split_audio_chunk(gcs_uri, chunk)
                chunk_uris.append(chunk_uri)
                
                # Transcribe chunk
                chunk_start = time.time()
                chunk_result = self._transcribe_gcs_single(chunk_uri, chunk_start)
                results.append(chunk_result)
                
                if chunk_result.get("success"):
                    logger.info(f"Chunk {chunk['chunk_id']} transcribed successfully")
                else:
                    logger.warning(f"Chunk {chunk['chunk_id']} failed: {chunk_result.get('error')}")
            
            # Merge results
            merged = self._merge_results(results, chunks)
            
            elapsed = time.time() - start_time
            logger.info(f"Chunked transcription completed in {elapsed:.1f}s for {len(chunks)} chunks")
            
            return merged
            
        finally:
            # Cleanup chunk files from GCS
            storage_client = storage.Client()
            for uri in chunk_uris:
                try:
                    parts = uri.replace("gs://", "").split("/", 1)
                    bucket = storage_client.bucket(parts[0])
                    blob = bucket.blob(parts[1])
                    blob.delete()
                    logger.debug(f"Cleaned up chunk: {uri}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup chunk {uri}: {e}")
    
    def _transcribe_local(self, file_path: str) -> Dict[str, Any]:
        """Transcribe local audio file (upload to GCS first for long audio)."""
        
        logger.info(f"Transcribing local file: {file_path}")
        
        # For V2, we need to upload to GCS for long audio
        # Upload to temp location
        storage_client = storage.Client()
        bucket_name = "sales-ai-audio-bucket"
        bucket = storage_client.bucket(bucket_name)
        
        import uuid
        blob_path = f"temp_uploads/{uuid.uuid4()}/{os.path.basename(file_path)}"
        blob = bucket.blob(blob_path)
        blob.upload_from_filename(file_path)
        
        gcs_uri = f"gs://{bucket_name}/{blob_path}"
        logger.info(f"Uploaded to {gcs_uri}")
        
        try:
            result = self._transcribe_gcs(gcs_uri)
            return result
        finally:
            # Cleanup temp upload
            try:
                blob.delete()
            except Exception as e:
                logger.warning(f"Failed to cleanup temp upload: {e}")
    
    def _parse_result(self, response: cloud_speech.BatchRecognizeResponse, input_uri: str) -> Dict[str, Any]:
        """
        Parse BatchRecognize response into standardized format.
        
        Returns:
            Dict with segments, text, and speakers
        """
        segments = []
        full_text_parts = []
        speakers_set = set()
        
        # Get result for the input URI
        if input_uri not in response.results:
            logger.error(f"No result found for {input_uri}")
            return {
                "success": False,
                "error": f"No result found for {input_uri}",
                "segments": [],
                "text": "",
                "full_text": "",
                "speakers": [],
            }
        
        file_result = response.results[input_uri]
        
        if file_result.error.code:
            logger.error(f"Error in result: {file_result.error}")
            return {
                "success": False,
                "error": str(file_result.error),
                "segments": [],
                "text": "",
                "full_text": "",
                "speakers": [],
            }
        
        # Parse inline result
        for result in file_result.transcript.results:
            if not result.alternatives:
                continue
            
            alt = result.alternatives[0]
            full_text_parts.append(alt.transcript)
            
            # Process words with speaker labels
            if alt.words:
                current_speaker = None
                current_segment = None
                
                for word_info in alt.words:
                    # Get speaker tag (Chirp 3 uses speaker_label)
                    speaker_label = getattr(word_info, 'speaker_label', None) or "Unknown"
                    if speaker_label:
                        speakers_set.add(speaker_label)
                    
                    word = word_info.word
                    start_time = word_info.start_offset.total_seconds() if word_info.start_offset else 0.0
                    end_time = word_info.end_offset.total_seconds() if word_info.end_offset else 0.0
                    
                    if speaker_label != current_speaker:
                        if current_segment:
                            segments.append(current_segment)
                        
                        current_speaker = speaker_label
                        current_segment = {
                            "start": start_time,
                            "end": end_time,
                            "speaker": speaker_label,
                            "text": word,
                        }
                    else:
                        if current_segment:
                            current_segment["text"] += " " + word
                            current_segment["end"] = end_time
                
                if current_segment:
                    segments.append(current_segment)
        
        # Fallback if no segments created
        if not segments and full_text_parts:
            segments.append({
                "start": 0.0,
                "end": 0.0,
                "speaker": "Unknown",
                "text": " ".join(full_text_parts),
            })
        
        full_text = " ".join(full_text_parts)
        
        return {
            "success": True,
            "segments": segments,
            "text": full_text,
            "full_text": full_text,
            "speakers": list(speakers_set),
            "engine": "stt_v2",
            "model": self.model,
            "language": ",".join(self.language_codes),
        }
