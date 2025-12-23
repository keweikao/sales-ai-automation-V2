"""
Speech-to-Text V1 Pipeline for synchronous transcription.

Uses LongRunningRecognize API with polling for long audio files.
Supports speaker diarization and Traditional Chinese (Taiwan).
"""

import os
import logging
import time
from typing import Dict, Any, List, Optional

from google.cloud import speech_v1 as speech
from google.api_core import exceptions as gapi_exceptions

from .base_pipeline import TranscriptionPipeline

logger = logging.getLogger(__name__)


class STTV1Pipeline(TranscriptionPipeline):
    """
    Speech-to-Text V1 同步轉錄 Pipeline.
    
    使用 LongRunningRecognize API 處理長音檔，
    內部輪詢等待結果，對外表現為同步行為。
    """
    
    def __init__(
        self,
        language_code: str = "cmn-Hant-TW",
        enable_diarization: bool = True,
        min_speakers: int = 2,
        max_speakers: int = 4,
        sample_rate_hertz: int = 16000,
    ):
        """
        Initialize the STT V1 Pipeline.
        
        Args:
            language_code: Language code for transcription (default: Traditional Chinese Taiwan)
            enable_diarization: Enable speaker diarization
            min_speakers: Minimum number of speakers
            max_speakers: Maximum number of speakers
            sample_rate_hertz: Audio sample rate (16000 for our converted MP3s)
        """
        self.client = speech.SpeechClient()
        self.language_code = language_code
        self.enable_diarization = enable_diarization
        self.min_speakers = min_speakers
        self.max_speakers = max_speakers
        self.sample_rate_hertz = sample_rate_hertz
        
        logger.info(
            f"STTV1Pipeline initialized: lang={language_code}, "
            f"diarization={enable_diarization}, speakers={min_speakers}-{max_speakers}"
        )
    
    def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe audio file using Speech-to-Text V1 API.
        
        Args:
            audio_path: GCS URI (gs://bucket/path) or local file path
            
        Returns:
            Dict with keys:
                - segments: List of transcript segments with speaker info
                - text: Full transcript text
                - speakers: List of unique speaker labels
        """
        # Determine if GCS URI or local file
        if audio_path.startswith("gs://"):
            return self._transcribe_gcs(audio_path)
        else:
            return self._transcribe_local(audio_path)
    
    def _build_config(self, encoding: speech.RecognitionConfig.AudioEncoding) -> speech.RecognitionConfig:
        """Build recognition config with diarization settings."""
        
        config_dict = {
            "encoding": encoding,
            "sample_rate_hertz": self.sample_rate_hertz,
            "language_code": self.language_code,
            "enable_automatic_punctuation": True,
            "enable_word_time_offsets": True,
            "audio_channel_count": 1,
            "model": "default",  # or "telephony" for phone calls
        }
        
        # Add diarization config if enabled
        if self.enable_diarization:
            config_dict["diarization_config"] = speech.SpeakerDiarizationConfig(
                enable_speaker_diarization=True,
                min_speaker_count=self.min_speakers,
                max_speaker_count=self.max_speakers,
            )
        
        return speech.RecognitionConfig(**config_dict)
    
    def _transcribe_gcs(self, gcs_uri: str) -> Dict[str, Any]:
        """Transcribe audio from GCS URI using LongRunningRecognize."""
        
        logger.info(f"Starting transcription for: {gcs_uri}")
        start_time = time.time()
        
        # Detect encoding from file extension
        encoding = self._detect_encoding(gcs_uri)
        config = self._build_config(encoding)
        
        audio = speech.RecognitionAudio(uri=gcs_uri)
        
        try:
            # Start long-running operation
            operation = self.client.long_running_recognize(
                config=config,
                audio=audio,
            )
            
            logger.info(f"Operation started: {operation.operation.name}")
            
            # Poll for result with timeout (10 minutes)
            result = operation.result(timeout=600)
            
            elapsed = time.time() - start_time
            logger.info(f"Transcription completed in {elapsed:.1f}s")
            
            return self._parse_result(result)
            
        except gapi_exceptions.InvalidArgument as e:
            logger.error(f"Invalid argument error: {e}")
            raise
        except gapi_exceptions.DeadlineExceeded as e:
            logger.error(f"Transcription timeout: {e}")
            raise
        except Exception as e:
            logger.error(f"Transcription failed: {e}", exc_info=True)
            raise
    
    def _transcribe_local(self, file_path: str) -> Dict[str, Any]:
        """Transcribe local audio file (< 1 minute or will be rejected)."""
        
        logger.info(f"Transcribing local file: {file_path}")
        
        with open(file_path, "rb") as audio_file:
            content = audio_file.read()
        
        encoding = self._detect_encoding(file_path)
        config = self._build_config(encoding)
        audio = speech.RecognitionAudio(content=content)
        
        # For local files, use synchronous recognize (limited to ~1 min)
        response = self.client.recognize(config=config, audio=audio)
        
        return self._parse_result(response)
    
    def _detect_encoding(self, file_path: str) -> speech.RecognitionConfig.AudioEncoding:
        """Detect audio encoding from file extension."""
        
        lower_path = file_path.lower()
        
        if lower_path.endswith(".mp3"):
            return speech.RecognitionConfig.AudioEncoding.MP3
        elif lower_path.endswith(".flac"):
            return speech.RecognitionConfig.AudioEncoding.FLAC
        elif lower_path.endswith(".wav"):
            return speech.RecognitionConfig.AudioEncoding.LINEAR16
        elif lower_path.endswith(".ogg") or lower_path.endswith(".opus"):
            return speech.RecognitionConfig.AudioEncoding.OGG_OPUS
        elif lower_path.endswith(".m4a"):
            # M4A needs to be converted, but we'll try MP3 encoding
            return speech.RecognitionConfig.AudioEncoding.MP3
        else:
            # Default: let API auto-detect
            return speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED
    
    def _parse_result(self, response) -> Dict[str, Any]:
        """
        Parse Speech-to-Text response into standardized format.
        
        Returns:
            Dict with segments, text, and speakers
        """
        segments = []
        full_text_parts = []
        speakers_set = set()
        
        for result in response.results:
            if not result.alternatives:
                continue
            
            alternative = result.alternatives[0]
            transcript = alternative.transcript
            full_text_parts.append(transcript)
            
            # If diarization is enabled, extract speaker info from words
            if self.enable_diarization and alternative.words:
                # Group words by speaker
                current_speaker = None
                current_segment = None
                
                for word_info in alternative.words:
                    speaker_tag = getattr(word_info, 'speaker_tag', 0)
                    speaker_label = f"Speaker {speaker_tag}" if speaker_tag > 0 else "Unknown"
                    speakers_set.add(speaker_label)
                    
                    word = word_info.word
                    start_time = word_info.start_time.total_seconds()
                    end_time = word_info.end_time.total_seconds()
                    
                    if speaker_label != current_speaker:
                        # Save previous segment
                        if current_segment:
                            segments.append(current_segment)
                        
                        # Start new segment
                        current_speaker = speaker_label
                        current_segment = {
                            "start": start_time,
                            "end": end_time,
                            "speaker": speaker_label,
                            "text": word,
                        }
                    else:
                        # Continue current segment
                        if current_segment:
                            current_segment["text"] += " " + word
                            current_segment["end"] = end_time
                
                # Don't forget last segment
                if current_segment:
                    segments.append(current_segment)
            else:
                # No diarization, just create one segment per result
                segments.append({
                    "start": 0.0,
                    "end": 0.0,
                    "speaker": "Unknown",
                    "text": transcript,
                })
        
        # Format segments with timestamps for output
        formatted_segments = []
        for seg in segments:
            formatted_segments.append({
                "start": seg["start"],
                "end": seg["end"],
                "speaker": seg["speaker"],
                "text": seg["text"].strip(),
            })
        
        full_text = " ".join(full_text_parts)
        
        return {
            "segments": formatted_segments,
            "text": full_text,
            "speakers": list(speakers_set),
            "engine": "stt_v1",
            "language": self.language_code,
        }
