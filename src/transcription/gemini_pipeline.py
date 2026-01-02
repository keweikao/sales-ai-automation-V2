import os
import json
import logging
import time
import re
import subprocess
from typing import Dict, Any, Optional, List
from pathlib import Path
import google.generativeai as genai

from .chunking.chunker import AudioChunker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("DEBUG: VERSION 2025-12-01 CHUNKING & PLAIN TEXT FIX")
logger.info("DEBUG: VERSION 2025-12-01 CHUNKING & PLAIN TEXT FIX")


from .base_pipeline import TranscriptionPipeline

class GeminiTranscriptionPipeline(TranscriptionPipeline):
    """
    Transcription pipeline using Google AI Gemini API.
    Supports direct audio transcription with speaker diarization.
    Now supports CHUNKING for long audio files.
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
        
        # Load model - Using Gemini 1.5 Flash for reliable and cost-effective transcription
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        self.model = genai.GenerativeModel(self.model_name)
        
        # Initialize chunker (10 min chunks, 2s overlap)
        self.chunker = AudioChunker(
            target_chunk_duration=600,
            overlap_duration=2
        )
        
        logger.info(f"GeminiTranscriptionPipeline initialized with model: {self.model_name}")

    def _parse_plain_text_response(self, response_text: str, time_offset: float = 0.0) -> Dict[str, Any]:
        """
        Parse Gemini Plain Text response (e.g., "[00:12] Speaker 1: Hello").
        
        Args:
            response_text: Raw response text
            time_offset: Offset to add to timestamps (for chunking)
            
        Returns:
            Dict with segments, speakers, and full text
        """
        segments = []
        speakers = set()
        full_text_parts = []
        
        # Regex to match: [MM:SS] Content (Speaker optional)
        # Supports [MM:SS], [H:MM:SS], [MM:SS.ms], [MM:SS] Speaker: Content
        pattern = re.compile(r'\[(\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)\]\s*(.*)')
        
        lines = response_text.strip().split('\n')
        
        # Filter out lines that don't match the pattern to avoid garbage
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            match = pattern.match(line)
            if match:
                time_str, content_raw = match.groups()
                
                # Try to extract speaker if present (Speaker: Content)
                speaker_match = re.match(r'^([^:]+):\s*(.+)', content_raw)
                if speaker_match:
                    speaker = speaker_match.group(1)
                    content = speaker_match.group(2)
                else:
                    speaker = "Speaker"
                    content = content_raw
                
                # Parse timestamp to seconds
                try:
                    parts = time_str.split(':')
                    if len(parts) == 2: # MM:SS
                        seconds = float(parts[0]) * 60 + float(parts[1])
                    elif len(parts) == 3: # H:MM:SS
                        seconds = float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
                    else:
                        continue 
                        
                    # Add offset
                    abs_start = seconds + time_offset
                    
                    # Format new timestamp
                    if abs_start >= 3600:
                        hours = int(abs_start // 3600)
                        minutes = int((abs_start % 3600) // 60)
                        secs = int(abs_start % 60)
                        new_time_str = f"{hours:02d}:{minutes:02d}:{secs:02d}"
                    else:
                        minutes = int(abs_start // 60)
                        secs = int(abs_start % 60)
                        new_time_str = f"{minutes:02d}:{secs:02d}"
                    
                    # Store segment
                    segments.append({
                        "start": round(abs_start, 2),
                        "end": round(abs_start + 5.0, 2), # Default duration
                        "speaker": speaker.strip(),
                        "text": content.strip()
                    })
                    
                    speakers.add(speaker.strip())
                    full_text_parts.append(f"[{new_time_str}] {speaker.strip()}: {content.strip()}")
                    
                except ValueError:
                    continue
        
        # Adjust end times based on next segment start
        for i in range(len(segments) - 1):
            segments[i]["end"] = segments[i+1]["start"]
        
        return {
            "success": True,
            "segments": segments,
            "speakers": list(speakers),
            "text": "\n".join(full_text_parts)
        }

    def _split_audio(self, audio_path: str, chunk: Dict) -> str:
        """Split audio file using ffmpeg."""
        chunk_id = chunk["chunk_id"]
        start = chunk["start"]
        duration = chunk["duration"]
        
        input_path = Path(audio_path)
        output_filename = f"{input_path.stem}_chunk_{chunk_id:03d}.m4a"
        output_path = input_path.parent / output_filename
        
        cmd = [
            "ffmpeg", "-y",
            "-i", str(audio_path),
            "-ss", str(start),
            "-t", str(duration),
            "-c:a", "aac",
            "-b:a", "64k",
            str(output_path)
        ]
        
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return str(output_path)

    def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe audio file using Gemini 1.5 Flash.
        """
        try:
            logger.info(f"Starting Gemini transcription (verbatim) for: {audio_path}")
            start_time = time.time()
            
            # 1. Get Audio Duration
            cmd = [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", audio_path
            ]
            duration_str = subprocess.check_output(cmd).decode().strip()
            total_duration = float(duration_str)
            
            # 2. Create Chunks (Gemini 1.5 Flash can handle 1HR, but chunking helps with reliability and long context)
            # Actually, for verbatim, chunking is BETTER because LLMs lose focus on long inputs.
            chunks = self.chunker.create_chunks(total_duration)
            
            all_segments = []
            all_speakers = set()
            full_formatted_text = []
            
            # 3. Process Chunks
            for chunk in chunks:
                chunk_path = self._split_audio(audio_path, chunk)
                
                try:
                    # Upload chunk
                    audio_file = genai.upload_file(path=chunk_path, mime_type="audio/mp4")
                    
                    # Wait for processing
                    while audio_file.state.name == "PROCESSING":
                        time.sleep(2)
                        audio_file = genai.get_file(audio_file.name)
                    
                    # Detailed Prompt for Verbatim Transcription
                    prompt = """
你是一位專業的逐字稿轉錄員。請將音頻檔案「逐字」轉錄成繁體中文。

【任務：逐字稿轉錄】
1. 輸出格式：[MM:SS] 說話者: 內容
2. 規則：
   - 務必包含時間戳，每段交談或長句都要有 [MM:SS]。
   - 務必標註說話者，若無法區分可使用「說話者1」、「說話者2」。
   - 絕對禁止任何摘要、潤飾或刪減。
   - 保留所有贅字，如「然後」、「那」、「就」、「嗯」、「啊」。
   - 不要添加任何標題、前言或後記，只輸出轉錄內容。
                    """
                    
                    # Generate content with Retries
                    max_retries = 3
                    response = None
                    last_error = None
                    
                    for attempt in range(max_retries):
                        try:
                            response = self.model.generate_content(
                                [audio_file, prompt],
                                generation_config={
                                    "temperature": 0.2,
                                    "max_output_tokens": 8192,
                                    "response_mime_type": "text/plain" # Plain text!
                                }
                            )
                            break # Success
                        except Exception as e:
                            last_error = e
                            logger.warning(f"Chunk {chunk['chunk_id']} attempt {attempt+1} failed: {e}. Retrying...")
                            time.sleep(2 * (attempt + 1)) # Exponential backoff
                    
                    if not response:
                        logger.error(f"Failed to process chunk {chunk['chunk_id']} after {max_retries} attempts.")
                        # Instead of failing the whole job, we might want to skip or insert a placeholder
                        # But for now, let's raise to ensure we know it failed
                        raise last_error or ValueError("Unknown error during generation")
                    
                    # Parse response
                    chunk_result = self._parse_plain_text_response(response.text, time_offset=chunk["start"])
                    
                    # Merge results
                    all_segments.extend(chunk_result["segments"])
                    all_speakers.update(chunk_result["speakers"])
                    full_formatted_text.append(chunk_result["text"])
                    
                    # Cleanup chunk file
                    genai.delete_file(audio_file.name)
                    os.remove(chunk_path)
                    
                except Exception as e:
                    logger.error(f"Error processing chunk {chunk['chunk_id']}: {e}")
                    # Continue to next chunk? Or fail? 
                    # For now, let's continue but log error
                    full_formatted_text.append(f"\n[ERROR: Chunk {chunk['chunk_id']} failed: {e}]\n")
            
            # 4. Finalize Result
            processing_time = time.time() - start_time
            
            standard_result = {
                "success": True,
                "full_text": "\n\n".join(full_formatted_text), # Join chunks with newlines
                "segments": all_segments,
                "speakers": list(all_speakers),
                "audio_info": {
                    "duration": total_duration,
                    "processing_time": processing_time
                }
            }
            
            logger.info(f"Gemini transcription completed in {processing_time:.2f}s")
            logger.info(f"Transcribed {len(all_segments)} segments total")
            
            return standard_result
                
        except Exception as e:
            logger.error(f"Gemini transcription failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "full_text": "",
                "segments": [],
                "speakers": []
            }
