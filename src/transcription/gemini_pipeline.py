import os
import json
import logging
import time
import re
import subprocess
import tempfile
from typing import Dict, Any, Optional, List
from pathlib import Path
from google.cloud import storage
import google.generativeai as genai

from .chunking.chunker import AudioChunker
from .base_pipeline import TranscriptionPipeline

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiTranscriptionPipeline(TranscriptionPipeline):
    """
    Transcription pipeline using Google AI Gemini API.
    Supports direct audio transcription with verbatim output.
    Supports CHUNKING for long audio files and robust GCS handling.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize the Gemini pipeline with Google AI API.
        """
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required for Google AI Gemini")
        
        # Initialize storage client for downloading GCS files
        self.storage_client = storage.Client()
        
        # Configure Google AI
        genai.configure(api_key=api_key)
        
        # Load model - Using Gemini 1.5 Flash
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        
        try:
            available_models = [m.name for m in genai.list_models()]
            logger.info(f"Available Gemini models: {available_models}")
        except Exception as e:
            logger.warning(f"Could not list models: {e}")
        
        system_instruction = """
你是一位專業的逐字稿轉錄專家。你的唯一職責是將音頻內容「完全準確」且「逐字逐句」地轉錄為繁體中文。

【行為準則】
1. 嚴格逐字：音頻中說了什麼，你就轉錄什麼。不可優化語句、不可節省字數、不可修改病句。
2. 零幻覺：絕對禁止添加音頻中不存在的任何內容。如果你不確定某個字詞，請標註 [聽不清]，絕對不可猜測。
3. 保留口語特徵：必須保留所有語音特徵，包括贅字（例如：那個、然後、就是、嗯、啊、喔、喔對）、重複的詞彙、以及說話者中途停頓或修正的話語。
4. 禁止摘要或解釋：你的輸出只能包含轉錄內容與時間戳記。禁止提供任何背景說明、語意分析、或心得總結。
5. 時間戳記格式：每段話的開頭必須使用 [MM:SS] 格式標註。
"""
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_instruction
        )
        
        # Initialize chunker (10 min chunks, 2s overlap)
        self.chunker = AudioChunker(
            target_chunk_duration=600,
            overlap_duration=2
        )
        
        logger.info(f"GeminiTranscriptionPipeline initialized with model: {self.model_name}")

    def _parse_plain_text_response(self, response_text: str, time_offset: float = 0.0) -> Dict[str, Any]:
        """Parse Gemini Plain Text response."""
        segments = []
        speakers = set()
        full_text_parts = []
        
        pattern = re.compile(r'\[(\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)\]\s*(.*)')
        lines = response_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line: continue
            match = pattern.match(line)
            if match:
                time_str, content_raw = match.groups()
                speaker_match = re.match(r'^([^:]+):\s*(.+)', content_raw)
                if speaker_match:
                    speaker = speaker_match.group(1)
                    content = speaker_match.group(2)
                else:
                    speaker = "Speaker"
                    content = content_raw
                
                try:
                    parts = time_str.split(':')
                    if len(parts) == 2:
                        seconds = float(parts[0]) * 60 + float(parts[1])
                    elif len(parts) == 3:
                        seconds = float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
                    else: continue
                        
                    abs_start = seconds + time_offset
                    if abs_start >= 3600:
                        h, m, s = int(abs_start // 3600), int((abs_start % 3600) // 60), int(abs_start % 60)
                        new_time_str = f"{h:02d}:{m:02d}:{s:02d}"
                    else:
                        m, s = int(abs_start // 60), int(abs_start % 60)
                        new_time_str = f"{m:02d}:{s:02d}"
                    
                    segments.append({
                        "start": round(abs_start, 2),
                        "end": round(abs_start + 5.0, 2),
                        "speaker": speaker.strip(),
                        "text": content.strip()
                    })
                    speakers.add(speaker.strip())
                    full_text_parts.append(f"[{new_time_str}] {speaker.strip()}: {content.strip()}")
                except ValueError: continue
        
        for i in range(len(segments) - 1):
            segments[i]["end"] = segments[i+1]["start"]
            
        return {
            "success": True,
            "segments": segments,
            "speakers": list(speakers),
            "text": "\n".join(full_text_parts)
        }

    def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """Transcribe audio file using Gemini."""
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                logger.info(f"Starting Gemini transcription for: {audio_path}")
                start_time = time.time()
                
                # Download audio
                local_original = audio_path
                if audio_path.startswith("gs://"):
                    parts = audio_path.replace("gs://", "").split("/", 1)
                    blob = self.storage_client.bucket(parts[0]).blob(parts[1])
                    local_original = os.path.join(temp_dir, f"original_audio{Path(parts[1]).suffix.lower() or '.mp3'}")
                    blob.download_to_filename(local_original)
                    logger.info(f"Downloaded GCS file to: {local_original}")

                # Get duration
                cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", local_original]
                total_duration = float(subprocess.check_output(cmd).decode().strip())
                
                # Process chunks
                chunks = self.chunker.create_chunks(total_duration)
                all_segments, all_speakers, full_formatted_text = [], set(), []
                
                for chunk in chunks:
                    chunk_path = os.path.join(temp_dir, f"chunk_{chunk['chunk_id']:03d}.m4a")
                    subprocess.run(["ffmpeg", "-y", "-i", local_original, "-ss", str(chunk["start"]), "-t", str(chunk["duration"]), "-c:a", "aac", "-b:a", "64k", chunk_path], check=True, capture_output=True)
                    
                    try:
                        audio_file = genai.upload_file(path=chunk_path, mime_type="audio/mp4")
                        while audio_file.state.name == "PROCESSING":
                            time.sleep(2)
                            audio_file = genai.get_file(audio_file.name)
                        
                        prompt = "請將音頻檔案逐字轉錄成繁體中文。輸出格式為：[MM:SS] 說話者: 內容。絕對禁止摘要或刪減。"
                        
                        max_retries = 3
                        response = None
                        for attempt in range(max_retries):
                            try:
                                response = self.model.generate_content([audio_file, prompt], generation_config={"temperature": 0.1, "max_output_tokens": 8192, "response_mime_type": "text/plain"})
                                break
                            except Exception as e:
                                logger.warning(f"Chunk retry {attempt+1}: {e}")
                                time.sleep(2 * (attempt + 1))
                                
                        if not response: raise ValueError("Failed after retries")
                        
                        chunk_result = self._parse_plain_text_response(response.text, time_offset=chunk["start"])
                        all_segments.extend(chunk_result["segments"])
                        all_speakers.update(chunk_result["speakers"])
                        full_formatted_text.append(chunk_result["text"])
                        
                        genai.delete_file(audio_file.name)
                    except Exception as e:
                        logger.error(f"Error in chunk {chunk['chunk_id']}: {str(e)}", exc_info=True)
                        full_formatted_text.append(f"\n[ERROR: Chunk {chunk['chunk_id']} failed: {e}]\n")

                return {
                    "success": True,
                    "full_text": "\n\n".join(full_formatted_text),
                    "segments": all_segments,
                    "speakers": list(all_speakers),
                    "audio_info": {"duration": total_duration, "processing_time": time.time() - start_time}
                }
            except Exception as e:
                logger.error(f"Gemini transcription failed: {e}", exc_info=True)
                return {"success": False, "error": str(e), "full_text": "", "segments": [], "speakers": []}
