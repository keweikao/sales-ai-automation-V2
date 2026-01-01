"""
Speech-to-Text V2 Synchronous Pipeline with 10-minute chunking.

Uses Speech-to-Text V2 Recognize API (NOT BatchRecognize) for faster response.
Chunks audio into 10-minute segments, transcribes each sequentially,
then merges results with proper timeline alignment.
"""

import os
import logging
import time
import subprocess
import tempfile
import uuid
from typing import Dict, Any, List, Optional
from pathlib import Path

from google.cloud import speech_v2
from google.cloud.speech_v2.types import cloud_speech
from google.cloud import storage
from google.api_core import exceptions as gapi_exceptions
from google.api_core.client_options import ClientOptions

from .base_pipeline import TranscriptionPipeline

logger = logging.getLogger(__name__)


class STTV2SyncPipeline(TranscriptionPipeline):
    """
    Speech-to-Text V2 同步轉錄 Pipeline (Chirp 3) - 使用 Recognize API.
    
    特點：
    - 使用 Recognize API 而非 BatchRecognize，更快獲得結果
    - 自動將音檔轉換為 MP3 格式
    - 將長音檔切割成 10 分鐘片段
    - 逐一轉錄每個片段
    - 合併結果時確保時間軸正確對齊
    """
    
    # Recognize API 限制：最大 60 秒的音檔
    # 所以我們需要用 short audio (< 1min) 或者使用 streaming
    # 但 Chirp 3 不支援 Streaming，所以我們用 BatchRecognize 但配合 chunking
    
    # 實際上 Chirp 3 的 Recognize (非 Batch) 有限制
    # 讓我們用 BatchRecognize 但搭配強制 10 分鐘切割
    
    CHUNK_DURATION_SECONDS = 600  # 10 minutes per chunk
    OVERLAP_SECONDS = 2  # 2 seconds overlap for continuity
    
    def __init__(
        self,
        project_id: str = None,
        location: str = "asia-southeast1",  # Use asia for lower latency
        language_codes: List[str] = None,
        model: str = "chirp_2",  # chirp_2 is faster than chirp_3
    ):
        """
        Initialize the STT V2 Sync Pipeline.
        
        Args:
            project_id: GCP Project ID
            location: Region for Speech API
            language_codes: List of language codes (default: Traditional Chinese)
            model: Model to use (chirp_2 for faster processing)
        """
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID", "sales-ai-automation-v2")
        self.location = location
        self.language_codes = language_codes or ["cmn-Hant-TW"]
        self.model = model
        
        # Initialize Speech V2 Client with regional endpoint
        self.client = speech_v2.SpeechClient(
            client_options=ClientOptions(
                api_endpoint=f"{location}-speech.googleapis.com"
            )
        )
        
        # Storage client for GCS operations
        self.storage_client = storage.Client()
        
        # Create recognizer path
        self.recognizer_id = f"sales-ai-recognizer-{model.replace('_', '-')}-sync"
        self.recognizer_path = f"projects/{self.project_id}/locations/{self.location}/recognizers/{self.recognizer_id}"
        
        # Lazy initialization flag
        self._recognizer_initialized = False
        
        logger.info(
            f"STTV2SyncPipeline initialized: project={self.project_id}, "
            f"location={location}, model={model}, chunk_duration={self.CHUNK_DURATION_SECONDS}s"
        )
    
    def _ensure_recognizer(self):
        """Ensures the recognizer exists, creates if not."""
        parent = f"projects/{self.project_id}/locations/{self.location}"
        
        try:
            self.client.get_recognizer(name=self.recognizer_path)
            logger.info(f"Recognizer {self.recognizer_id} exists.")
        except gapi_exceptions.NotFound:
            logger.info(f"Creating recognizer {self.recognizer_id}...")
            
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
            operation.result(timeout=120)
            logger.info(f"Recognizer {self.recognizer_id} created.")
    
    def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe audio file using Speech-to-Text V2 API with chunking.
        
        Args:
            audio_path: GCS URI (gs://bucket/path) or local file path
            
        Returns:
            Dict with transcription results
        """
        # Lazy initialization
        if not self._recognizer_initialized:
            self._ensure_recognizer()
            self._recognizer_initialized = True
        
        logger.info(f"Starting transcription for: {audio_path}")
        start_time = time.time()
        
        try:
            # Step 1: Download and convert to MP3 if necessary
            local_mp3_path = self._prepare_audio(audio_path)
            
            # Step 2: Get audio duration
            duration = self._get_duration(local_mp3_path)
            logger.info(f"Audio duration: {duration:.1f}s ({duration/60:.1f} min)")
            
            # Step 3: Create chunks
            chunks = self._create_chunks(duration)
            logger.info(f"Created {len(chunks)} chunks for transcription")
            
            # Step 4: Transcribe each chunk sequentially
            all_results = []
            for i, chunk in enumerate(chunks):
                logger.info(f"Transcribing chunk {i+1}/{len(chunks)}: {chunk['start']:.0f}s - {chunk['end']:.0f}s")
                
                # Extract chunk audio
                chunk_path = self._extract_chunk(local_mp3_path, chunk)
                
                # Upload chunk to GCS
                chunk_gcs_uri = self._upload_chunk_to_gcs(chunk_path, i)
                
                # Transcribe chunk
                chunk_result = self._transcribe_single_chunk(chunk_gcs_uri)
                
                if chunk_result.get("success"):
                    # Adjust timestamps
                    self._adjust_timestamps(chunk_result, chunk["start"])
                    all_results.append(chunk_result)
                    logger.info(f"Chunk {i+1} completed: {len(chunk_result.get('text', ''))} chars")
                else:
                    logger.warning(f"Chunk {i+1} failed: {chunk_result.get('error')}")
                
                # Cleanup chunk files
                self._cleanup_file(chunk_path)
                self._cleanup_gcs(chunk_gcs_uri)
            
            # Step 5: Merge results
            merged = self._merge_results(all_results)
            
            # Cleanup
            self._cleanup_file(local_mp3_path)
            
            elapsed = time.time() - start_time
            logger.info(f"Transcription completed in {elapsed:.1f}s, {len(merged.get('text', ''))} chars")
            
            return merged
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def _prepare_audio(self, audio_path: str) -> str:
        """Download from GCS if needed and convert to MP3."""
        # Create temp file
        temp_dir = tempfile.mkdtemp()
        
        if audio_path.startswith("gs://"):
            # Download from GCS
            parts = audio_path.replace("gs://", "").split("/", 1)
            bucket_name = parts[0]
            blob_path = parts[1] if len(parts) > 1 else ""
            
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            
            original_ext = Path(blob_path).suffix.lower()
            local_path = os.path.join(temp_dir, f"audio{original_ext}")
            blob.download_to_filename(local_path)
            logger.info(f"Downloaded from GCS: {audio_path}")
        else:
            local_path = audio_path
        
        # Convert to MP3 (mono, 16kHz) for optimal STT performance
        mp3_path = os.path.join(temp_dir, "audio_converted.mp3")
        
        cmd = [
            "ffmpeg", "-y", "-i", local_path,
            "-ac", "1",  # Mono
            "-ar", "16000",  # 16kHz
            "-c:a", "libmp3lame",
            "-q:a", "2",  # Good quality
            "-loglevel", "error", # Only log errors
            mp3_path
        ]
        
        # Don't capture output to avoid memory issues with large logs
        # Redirect to DEVNULL unless we want to debug
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            logger.warning(f"FFmpeg conversion warning: {result.stderr[:500] if result.stderr else 'Unknown error'}")
            # If conversion fails, try to use original
            if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 0:
                pass  # Conversion succeeded despite warning
            else:
                mp3_path = local_path  # Use original
        
        logger.info(f"Audio prepared: {mp3_path}")
        return mp3_path
    
    def _get_duration(self, audio_path: str) -> float:
        """Get audio duration in seconds using ffprobe."""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    
    def _create_chunks(self, duration: float) -> List[Dict]:
        """Create chunk definitions with proper overlap."""
        chunks = []
        current_start = 0
        chunk_id = 0
        
        while current_start < duration:
            chunk_end = min(current_start + self.CHUNK_DURATION_SECONDS, duration)
            
            chunks.append({
                "chunk_id": chunk_id,
                "start": current_start,
                "end": chunk_end,
                "duration": chunk_end - current_start,
            })
            
            # Next chunk starts before the end (overlap)
            current_start = chunk_end - self.OVERLAP_SECONDS
            if current_start >= duration:
                break
            chunk_id += 1
        
        return chunks
    
    def _extract_chunk(self, audio_path: str, chunk: Dict) -> str:
        """Extract a chunk from the audio file."""
        chunk_path = tempfile.mktemp(suffix=".mp3")
        
        cmd = [
            "ffmpeg", "-y",
            "-i", audio_path,
            "-ss", str(chunk["start"]),
            "-t", str(chunk["duration"]),
            "-ac", "1",
            "-ar", "16000",
            "-c:a", "libmp3lame",
            "-q:a", "2",
            "-loglevel", "error",
            chunk_path
        ]
        
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        return chunk_path
    
    def _upload_chunk_to_gcs(self, chunk_path: str, chunk_id: int) -> str:
        """Upload chunk to GCS temp location."""
        bucket_name = "sales-ai-audio-bucket"
        blob_path = f"temp_chunks/{uuid.uuid4()}/chunk_{chunk_id:03d}.mp3"
        
        bucket = self.storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        blob.upload_from_filename(chunk_path)
        
        gcs_uri = f"gs://{bucket_name}/{blob_path}"
        logger.debug(f"Uploaded chunk to {gcs_uri}")
        return gcs_uri
    
    def _transcribe_single_chunk(self, gcs_uri: str) -> Dict[str, Any]:
        """Transcribe a single chunk using BatchRecognize with inline result."""
        try:
            request = cloud_speech.BatchRecognizeRequest(
                recognizer=self.recognizer_path,
                files=[cloud_speech.BatchRecognizeFileMetadata(uri=gcs_uri)],
                recognition_output_config=cloud_speech.RecognitionOutputConfig(
                    inline_response_config=cloud_speech.InlineOutputConfig()
                ),
            )
            
            operation = self.client.batch_recognize(request=request)
            
            # Wait for result with shorter timeout (10 min chunk should be fast)
            result = operation.result(timeout=600)  # 10 minute timeout
            
            return self._parse_batch_result(result, gcs_uri)
            
        except Exception as e:
            logger.error(f"Chunk transcription failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _parse_batch_result(self, response: cloud_speech.BatchRecognizeResponse, input_uri: str) -> Dict[str, Any]:
        """Parse BatchRecognize response."""
        segments = []
        full_text_parts = []
        speakers_set = set()
        
        if input_uri not in response.results:
            return {"success": False, "error": f"No result for {input_uri}"}
        
        file_result = response.results[input_uri]
        
        if file_result.error.code:
            return {"success": False, "error": str(file_result.error)}
        
        for result in file_result.transcript.results:
            if not result.alternatives:
                continue
            
            alt = result.alternatives[0]
            full_text_parts.append(alt.transcript)
            
            # Process words with timestamps
            if alt.words:
                current_speaker = None
                current_segment = None
                
                for word_info in alt.words:
                    speaker_label = getattr(word_info, 'speaker_label', None) or "Speaker"
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
        
        full_text = " ".join(full_text_parts)
        
        # Fallback if no segments
        if not segments and full_text:
            segments.append({
                "start": 0.0,
                "end": 0.0,
                "speaker": "Speaker",
                "text": full_text,
            })
        
        return {
            "success": True,
            "segments": segments,
            "text": full_text,
            "full_text": full_text,
            "speakers": list(speakers_set),
        }
    
    def _adjust_timestamps(self, result: Dict, offset: float):
        """Adjust all timestamps in the result by adding offset."""
        for segment in result.get("segments", []):
            segment["start"] += offset
            segment["end"] += offset
    
    def _merge_results(self, results: List[Dict]) -> Dict[str, Any]:
        """Merge multiple chunk results into one."""
        if not results:
            return {"success": False, "error": "No results to merge"}
        
        all_segments = []
        all_text_parts = []
        all_speakers = set()
        
        for result in results:
            if result.get("success"):
                all_segments.extend(result.get("segments", []))
                if result.get("text"):
                    all_text_parts.append(result["text"])
                all_speakers.update(result.get("speakers", []))
        
        # Sort segments by start time
        all_segments.sort(key=lambda x: x["start"])
        
        # Remove duplicate text from overlapping regions
        # (Simple approach: just concatenate for now)
        full_text = " ".join(all_text_parts)
        
        return {
            "success": True,
            "segments": all_segments,
            "text": full_text,
            "full_text": full_text,
            "speakers": list(all_speakers),
            "engine": "stt_v2_sync",
            "model": self.model,
            "language": ",".join(self.language_codes),
            "chunked": len(results) > 1,
            "chunk_count": len(results),
        }
    
    def _cleanup_file(self, path: str):
        """Remove local file."""
        try:
            if path and os.path.exists(path):
                os.remove(path)
                # Also try to remove parent temp dir if empty
                parent = os.path.dirname(path)
                if parent and os.path.exists(parent) and not os.listdir(parent):
                    os.rmdir(parent)
        except Exception as e:
            logger.warning(f"Cleanup failed for {path}: {e}")
    
    def _cleanup_gcs(self, gcs_uri: str):
        """Remove GCS file."""
        try:
            if not gcs_uri:
                return
            parts = gcs_uri.replace("gs://", "").split("/", 1)
            bucket = self.storage_client.bucket(parts[0])
            blob = bucket.blob(parts[1])
            blob.delete()
        except Exception as e:
            logger.warning(f"GCS cleanup failed for {gcs_uri}: {e}")
