import os
import json
import logging
import time
import subprocess
import tempfile
from typing import Dict, Any, Optional, List
from pathlib import Path
from google.cloud import storage
from groq import Groq

from .base_pipeline import TranscriptionPipeline

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GroqWhisperPipeline(TranscriptionPipeline):
    """
    Transcription pipeline using Groq Whisper API.

    Features:
    - Whisper Large v3 Turbo (228x realtime speed)
    - $0.04/hour pricing
    - No speaker diarization (agents infer from context)
    - Robust GCS handling with chunking for long files
    """

    def __init__(self, api_key: str):
        """
        Initialize the Groq Whisper pipeline.

        Args:
            api_key: Groq API key
        """
        if not api_key:
            raise ValueError("GROQ_API_KEY is required for Groq Whisper")

        # Initialize Groq client
        self.client = Groq(api_key=api_key)

        # Initialize storage client for downloading GCS files
        self.storage_client = storage.Client()

        # Model configuration
        self.model_name = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo")

        # Chunking configuration (Groq has 25MB file size limit)
        self.max_file_size_mb = 24  # Leave 1MB buffer
        self.chunk_duration = 600  # 10 minutes per chunk

        logger.info(f"GroqWhisperPipeline initialized with model: {self.model_name}")

    def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration using ffprobe."""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path
        ]
        duration = float(subprocess.check_output(cmd).decode().strip())
        return duration

    def _get_file_size_mb(self, file_path: str) -> float:
        """Get file size in MB."""
        return os.path.getsize(file_path) / (1024 * 1024)

    def _chunk_audio(self, audio_path: str, output_dir: str) -> List[Dict[str, Any]]:
        """
        Split audio into chunks if needed (> 24MB or > 10 min).

        Returns:
            List of chunk info dicts with keys: path, start, duration
        """
        duration = self._get_audio_duration(audio_path)
        file_size_mb = self._get_file_size_mb(audio_path)

        # If small enough, no chunking needed
        if file_size_mb < self.max_file_size_mb and duration < self.chunk_duration:
            return [{
                "path": audio_path,
                "start": 0.0,
                "duration": duration
            }]

        # Calculate number of chunks needed
        num_chunks = max(
            int(file_size_mb / self.max_file_size_mb) + 1,
            int(duration / self.chunk_duration) + 1
        )
        chunk_duration = duration / num_chunks

        chunks = []
        for i in range(num_chunks):
            start_time = i * chunk_duration
            chunk_path = os.path.join(output_dir, f"chunk_{i:03d}.m4a")

            # Extract chunk using ffmpeg
            cmd = [
                "ffmpeg", "-y", "-i", audio_path,
                "-ss", str(start_time),
                "-t", str(chunk_duration),
                "-c:a", "aac",
                "-b:a", "64k",
                chunk_path
            ]
            subprocess.run(cmd, check=True, capture_output=True)

            chunks.append({
                "path": chunk_path,
                "start": start_time,
                "duration": chunk_duration
            })

        logger.info(f"Split audio into {num_chunks} chunks (avg {chunk_duration:.1f}s each)")
        return chunks

    def _transcribe_chunk(self, audio_path: str, language: str = "zh") -> Dict[str, Any]:
        """
        Transcribe a single audio chunk using Groq Whisper API.

        Args:
            audio_path: Path to audio file (must be < 25MB)
            language: Language code (default: "zh" for Chinese)

        Returns:
            Dict with text and segments
        """
        max_retries = 3

        for attempt in range(max_retries):
            try:
                with open(audio_path, "rb") as audio_file:
                    transcription = self.client.audio.transcriptions.create(
                        file=audio_file,
                        model=self.model_name,
                        language=language,
                        response_format="verbose_json",
                        temperature=0.0
                    )

                # Groq returns verbose_json with text and segments
                # Extract segments with timestamps
                segments = []
                if hasattr(transcription, 'segments') and transcription.segments:
                    for seg in transcription.segments:
                        segments.append({
                            "start": seg.get("start", 0) if isinstance(seg, dict) else getattr(seg, "start", 0),
                            "end": seg.get("end", 0) if isinstance(seg, dict) else getattr(seg, "end", 0),
                            "text": seg.get("text", "") if isinstance(seg, dict) else getattr(seg, "text", ""),
                            "speaker": "Speaker"  # Groq doesn't provide speaker info
                        })

                return {
                    "text": transcription.text,
                    "segments": segments
                }

            except Exception as e:
                logger.warning(f"Groq API attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))
                else:
                    raise

        raise ValueError(f"Failed to transcribe after {max_retries} attempts")

    def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe audio file using Groq Whisper API.

        Args:
            audio_path: GCS path (gs://...) or local file path

        Returns:
            Dict with keys: success, full_text, segments, speakers, audio_info
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                logger.info(f"Starting Groq Whisper transcription for: {audio_path}")
                start_time = time.time()

                # Download audio if from GCS
                local_audio = audio_path
                if audio_path.startswith("gs://"):
                    parts = audio_path.replace("gs://", "").split("/", 1)
                    blob = self.storage_client.bucket(parts[0]).blob(parts[1])
                    local_audio = os.path.join(
                        temp_dir,
                        f"original_audio{Path(parts[1]).suffix.lower() or '.mp3'}"
                    )
                    blob.download_to_filename(local_audio)
                    logger.info(f"Downloaded GCS file to: {local_audio}")

                # Get total duration
                total_duration = self._get_audio_duration(local_audio)

                # Chunk audio if needed
                chunks = self._chunk_audio(local_audio, temp_dir)

                # Transcribe each chunk
                full_text_parts = []
                all_segments = []

                for i, chunk in enumerate(chunks):
                    logger.info(f"Transcribing chunk {i+1}/{len(chunks)}...")

                    try:
                        chunk_result = self._transcribe_chunk(chunk["path"])
                        chunk_text = chunk_result["text"]
                        chunk_segments = chunk_result["segments"]

                        # Adjust segment timestamps for chunk offset
                        chunk_offset = chunk["start"]
                        for seg in chunk_segments:
                            seg["start"] += chunk_offset
                            seg["end"] += chunk_offset
                            all_segments.append(seg)

                        # Add time context for multi-chunk files
                        if len(chunks) > 1:
                            minutes = int(chunk["start"] // 60)
                            seconds = int(chunk["start"] % 60)
                            time_marker = f"\n[{minutes:02d}:{seconds:02d}] "
                            full_text_parts.append(time_marker + chunk_text)
                        else:
                            full_text_parts.append(chunk_text)

                    except Exception as e:
                        logger.error(f"Chunk {i} failed: {e}", exc_info=True)
                        full_text_parts.append(f"\n[ERROR: Chunk {i} failed: {e}]\n")

                # Combine all chunks
                full_text = "\n".join(full_text_parts)

                processing_time = time.time() - start_time

                logger.info(
                    f"Transcription complete: {total_duration:.1f}s audio "
                    f"processed in {processing_time:.1f}s "
                    f"({total_duration/processing_time:.1f}x realtime), "
                    f"{len(all_segments)} segments"
                )

                return {
                    "success": True,
                    "full_text": full_text,
                    "segments": all_segments,
                    "speakers": ["Speaker"],  # Single speaker placeholder
                    "audio_info": {
                        "duration": total_duration,
                        "processing_time": processing_time,
                        "num_chunks": len(chunks),
                        "model": self.model_name
                    }
                }

            except Exception as e:
                logger.error(f"Groq Whisper transcription failed: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e),
                    "full_text": "",
                    "segments": [],
                    "speakers": []
                }
