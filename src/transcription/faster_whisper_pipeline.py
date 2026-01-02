"""
Faster-Whisper Transcription Pipeline

使用 CTranslate2 優化的 Whisper 模型進行轉錄，支援：
- large-v3-turbo 模型（準確度高、速度快）
- 自動分段處理長音檔
- 說話者辨識整合
- 完整時間戳對齊
"""

import os
import gc
import logging
import tempfile
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from google.cloud import storage

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionSegment:
    """轉錄片段"""
    start: float
    end: float
    text: str
    speaker: Optional[str] = None


class FasterWhisperPipeline:
    """
    Faster-Whisper 轉錄 Pipeline
    
    特點：
    - 使用 CTranslate2 優化推理（CPU 上速度快 4x）
    - 支援 large-v3-turbo 模型
    - 自動分段處理長音檔（每段 10 分鐘）
    - 可選說話者辨識
    - 完整時間戳對齊
    """
    
    CHUNK_DURATION = 600  # 10 分鐘分段
    OVERLAP_SECONDS = 2   # 2 秒重疊
    
    def __init__(
        self,
        model_size: str = "large-v3-turbo",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "zh",
        enable_diarization: bool = True,
        diarization_model: str = "pyannote/speaker-diarization-3.1",
    ):
        """
        初始化 Faster-Whisper Pipeline
        
        Args:
            model_size: 模型大小 (tiny, base, small, medium, large-v3, large-v3-turbo)
            device: 設備類型 (cpu, cuda)
            compute_type: 計算精度 (int8, float16, float32)
            language: 語言代碼
            enable_diarization: 是否啟用說話者辨識
            diarization_model: 說話者辨識模型
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.enable_diarization = enable_diarization
        self.diarization_model = diarization_model
        
        # Lazy load models to reduce memory footprint
        self._whisper_model = None
        self._diarizer = None
        
        # Storage client for GCS operations
        self.storage_client = storage.Client()
        
        logger.info(
            f"FasterWhisperPipeline initialized: "
            f"model={model_size}, device={device}, compute_type={compute_type}, "
            f"diarization={enable_diarization}"
        )
    
    def _get_whisper_model(self):
        """延遲載入 Whisper 模型"""
        if self._whisper_model is None:
            logger.info(f"載入 Whisper 模型: {self.model_size}...")
            start_time = time.time()
            
            from faster_whisper import WhisperModel
            
            self._whisper_model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=4,  # 限制執行緒以節省記憶體
                num_workers=1
            )
            
            elapsed = time.time() - start_time
            logger.info(f"Whisper 模型載入完成 ({elapsed:.1f}s)")
        
        return self._whisper_model
    
    def _get_diarizer(self):
        """延遲載入說話者辨識模型"""
        if not self.enable_diarization:
            return None
        
        if self._diarizer is None:
            logger.info(f"載入說話者辨識模型: {self.diarization_model}...")
            start_time = time.time()
            
            try:
                from pyannote.audio import Pipeline
                
                token = os.getenv("HUGGINGFACE_TOKEN")
                if not token:
                    logger.warning("HUGGINGFACE_TOKEN 未設定，停用說話者辨識")
                    self.enable_diarization = False
                    return None
                
                self._diarizer = Pipeline.from_pretrained(
                    self.diarization_model,
                    use_auth_token=token
                )
                
                elapsed = time.time() - start_time
                logger.info(f"說話者辨識模型載入完成 ({elapsed:.1f}s)")
                
            except Exception as e:
                logger.warning(f"說話者辨識載入失敗: {e}")
                self.enable_diarization = False
                return None
        
        return self._diarizer
    
    def _cleanup_models(self):
        """釋放所有模型記憶體"""
        self._cleanup_diarizer()
        self._cleanup_whisper_model()
        gc.collect()

    def _cleanup_whisper_model(self):
        """單獨釋放 Whisper 模型"""
        if self._whisper_model is not None:
            logger.info("釋放 Whisper 模型記憶體...")
            del self._whisper_model
            self._whisper_model = None
            gc.collect()

    def _cleanup_diarizer(self):
        """單獨釋放說話者辨識模型"""
        if self._diarizer is not None:
            logger.info("釋放說話者辨識模型...")
            del self._diarizer
            self._diarizer = None
            gc.collect()
    
    def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """
        轉錄音檔
        
        Args:
            audio_path: GCS URI (gs://bucket/path) 或本地檔案路徑
            
        Returns:
            Dict 包含:
            - success: bool
            - text: 完整文字
            - full_text: 完整文字
            - segments: List[Dict] 帶時間戳的片段
            - speakers: List[str] 說話者列表
        """
        logger.info(f"開始轉錄: {audio_path}")
        start_time = time.time()
        
        # 使用 TemporaryDirectory 確保所有暫存檔（包括原始下載、轉換後、片段）都會被清理
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Step 1: 準備音檔（下載 + 轉換）
                local_audio = self._prepare_audio_in_dir(audio_path, temp_dir)
            
                # Step 2: 取得音檔長度
                duration = self._get_duration(local_audio)
                logger.info(f"音檔長度: {duration:.1f}s ({duration/60:.1f} min)")
                
                # Step 3: 決定是否需要分段
                if duration > self.CHUNK_DURATION:
                    result = self._transcribe_chunked(local_audio, duration)
                else:
                    result = self._transcribe_single(local_audio)
                
                # Step 4: 取得轉錄結果後，先釋放 Whisper 模型以騰出記憶體給 Diarization
                if self.enable_diarization:
                    self._cleanup_whisper_model()
                    result = self._apply_diarization(local_audio, result, duration)
                
                elapsed = time.time() - start_time
                if result.get("success"):
                    result["processing_time"] = elapsed
                    result["speed_ratio"] = elapsed / duration if duration > 0 else 0
                    logger.info(
                        f"轉錄完成: {len(result.get('text', ''))} 字, "
                        f"耗時 {elapsed:.1f}s (x{result['speed_ratio']:.2f})"
                    )
                return result
                
            except Exception as e:
                logger.error(f"轉錄失敗: {e}", exc_info=True)
                return {"success": False, "error": str(e)}
            finally:
                # 確保模型在不需要時釋放
                self._cleanup_models()
    
    def _prepare_audio_in_dir(self, audio_path: str, temp_dir: str) -> str:
        """下載並轉換音檔，指定暫存目錄"""
        # Download from GCS if needed
        if audio_path.startswith("gs://"):
            parts = audio_path.replace("gs://", "").split("/", 1)
            bucket_name = parts[0]
            blob_path = parts[1] if len(parts) > 1 else ""
            
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            
            original_ext = Path(blob_path).suffix.lower()
            local_path = os.path.join(temp_dir, f"audio_original{original_ext}")
            blob.download_to_filename(local_path)
            logger.info(f"從 GCS 下載至暫存: {audio_path}")
        else:
            local_path = audio_path
        
        # Convert to mono MP3 16kHz
        output_path = os.path.join(temp_dir, "audio_converted.mp3")
        
        cmd = [
            "ffmpeg", "-y", "-i", local_path,
            "-ac", "1",       # Mono
            "-ar", "16000",   # 16kHz
            "-c:a", "libmp3lame",
            "-b:a", "64k",
            "-loglevel", "error",
            output_path
        ]
        
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        logger.info(f"全音軌轉換完成: {output_path}")
        return output_path
    
    def _get_duration(self, audio_path: str) -> float:
        """取得音檔長度"""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    
    def _transcribe_single(self, audio_path: str) -> Dict[str, Any]:
        """轉錄單一音檔（不分段）"""
        model = self._get_whisper_model()
        
        segments_iter, info = model.transcribe(
            audio_path,
            language=self.language,
            beam_size=2,        # 降低 beam size 以節省記憶體
            word_timestamps=False, # 停用單詞級時間戳以節省記憶體
            vad_filter=True,
            vad_parameters=dict(
                min_speech_duration_ms=250,
                max_speech_duration_s=float("inf"),
                min_silence_duration_ms=500,
                speech_pad_ms=200,
            ),
        )
        
        segments = []
        full_text_parts = []
        
        for segment in segments_iter:
            segments.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
                "speaker": "Speaker",
            })
            full_text_parts.append(segment.text.strip())
        
        return {
            "success": True,
            "text": " ".join(full_text_parts),
            "full_text": " ".join(full_text_parts),
            "segments": segments,
            "speakers": ["Speaker"],
            "language": info.language,
            "language_probability": info.language_probability,
            "engine": "faster_whisper",
            "model": self.model_size,
        }
    
    def _transcribe_chunked(self, audio_path: str, duration: float) -> Dict[str, Any]:
        """分段轉錄長音檔"""
        chunks = self._create_chunks(duration)
        logger.info(f"分割為 {len(chunks)} 個片段")
        
        all_results = []
        
        for i, chunk in enumerate(chunks):
            logger.info(
                f"轉錄片段 {i+1}/{len(chunks)}: "
                f"{chunk['start']:.0f}s - {chunk['end']:.0f}s"
            )
            
            # Extract chunk
            chunk_path = self._extract_chunk(audio_path, chunk)
            
            # Transcribe chunk
            chunk_result = self._transcribe_single(chunk_path)
            
            if chunk_result.get("success"):
                # Adjust timestamps
                self._adjust_timestamps(chunk_result, chunk["start"])
                all_results.append(chunk_result)
            else:
                logger.warning(f"片段 {i+1} 轉錄失敗")
            
            # Cleanup
            self._cleanup_file(chunk_path)
        
        # Merge results
        return self._merge_results(all_results)
    
    def _create_chunks(self, duration: float) -> List[Dict]:
        """建立分段定義"""
        chunks = []
        current_start = 0
        chunk_id = 0
        
        while current_start < duration:
            chunk_end = min(current_start + self.CHUNK_DURATION, duration)
            
            chunks.append({
                "chunk_id": chunk_id,
                "start": current_start,
                "end": chunk_end,
                "duration": chunk_end - current_start,
            })
            
            current_start = chunk_end - self.OVERLAP_SECONDS
            if current_start >= duration:
                break
            chunk_id += 1
        
        return chunks
    
    def _extract_chunk(self, audio_path: str, chunk: Dict) -> str:
        """擷取音檔片段"""
        # 片段存在與 audio_path 相同的目錄中
        temp_dir = os.path.dirname(audio_path)
        chunk_path = os.path.join(temp_dir, f"chunk_{chunk['chunk_id']}.mp3")
        
        cmd = [
            "ffmpeg", "-y",
            "-i", audio_path,
            "-ss", str(chunk["start"]),
            "-t", str(chunk["duration"]),
            "-ac", "1",
            "-ar", "16000",
            "-c:a", "libmp3lame",
            "-b:a", "64k",
            "-loglevel", "error",
            chunk_path
        ]
        
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return chunk_path
    
    def _adjust_timestamps(self, result: Dict, offset: float):
        """調整時間戳（加上偏移量）"""
        for segment in result.get("segments", []):
            segment["start"] += offset
            segment["end"] += offset
    
    def _merge_results(self, results: List[Dict]) -> Dict[str, Any]:
        """合併多個片段結果"""
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
        
        # Sort by start time
        all_segments.sort(key=lambda x: x["start"])
        
        # Remove duplicates from overlap regions (simple approach)
        # TODO: More sophisticated deduplication
        
        return {
            "success": True,
            "text": " ".join(all_text_parts),
            "full_text": " ".join(all_text_parts),
            "segments": all_segments,
            "speakers": list(all_speakers),
            "engine": "faster_whisper",
            "model": self.model_size,
            "chunked": len(results) > 1,
            "chunk_count": len(results),
        }
    
    def _apply_diarization(self, audio_path: str, result: Dict, duration: float) -> Dict:
        """
        套用說話者辨識（根據長度決定是否分段）
        """
        diarizer = self._get_diarizer()
        if not diarizer:
            return result
        
        # 如果音檔超過 20 分鐘 (1200s)，使用分段 Diarization 以節省記憶體
        if duration > 1200:
            logger.info(f"偵測到長音檔 ({duration:.1f}s)，啟動分段說話者辨識模式...")
            return self._apply_diarization_chunked(audio_path, result, duration)
        else:
            # 只有在需要時才載入單一 Diarizer
            diarizer = self._get_diarizer()
            return self._apply_diarization_single(audio_path, result, diarizer)

    def _apply_diarization_single(self, audio_path: str, result: Dict, diarizer) -> Dict:
        """對完整音檔執行說話者辨識"""
        if not diarizer:
            return result
        logger.info("執行單一階段說話者辨識...")
        
        try:
            diarization = diarizer(audio_path, num_speakers=None, min_speakers=1, max_speakers=5)
            
            # Build speaker timeline
            speaker_timeline = []
            speakers = set()
            
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                speaker_timeline.append({
                    "start": float(turn.start),
                    "end": float(turn.end),
                    "speaker": str(speaker),
                })
                speakers.add(str(speaker))
            
            # Assign speakers to segments
            for segment in result.get("segments", []):
                segment["speaker"] = self._find_speaker(
                    segment["start"], 
                    segment["end"], 
                    speaker_timeline
                )
            
            result["speakers"] = list(speakers)
            result["speaker_segments"] = speaker_timeline
            
            logger.info(f"說話者辨識完成: {len(speakers)} 位說話者")
            
        except Exception as e:
            logger.warning(f"說話者辨識失敗: {e}")
            result["diarization_error"] = str(e)
        
        return result
    
    def _apply_diarization_chunked(self, audio_path: str, result: Dict, duration: float) -> Dict:
        """
        分段執行說話者辨識並對齊說話者標籤
        
        策略：
        1. 切割成 15 分鐘片段，中間有 2 分鐘重疊
        2. 每個片段獨立 Diarize
        3. 利用重疊區域的說話者分佈進行標籤對齊
        """
        # 定義分段（縮小至 10 分鐘以極限節省記憶體）
        CHUNK_SIZE = 600  # 10 mins
        OVERLAP = 60      # 1 min
        
        current_start = 0
        all_speaker_segments = []
        global_speaker_map = {} # 從「片段本地標籤」映射到「全域標籤」
        global_speakers_count = 0
        
        while current_start < duration:
            chunk_end = min(current_start + CHUNK_SIZE, duration)
            logger.info(f"Diarize 片段: {current_start:.0f}s - {chunk_end:.0f}s")
            
            # 擷取片段
            chunk_path = self._extract_chunk(audio_path, {"start": current_start, "duration": chunk_end - current_start})
            
            try:
                diarizer = self._get_diarizer()
                chunk_diarization = diarizer(chunk_path)
                
                # 取得當前片段的說話者片段
                current_chunk_segments = []
                current_chunk_speakers = set()
                for turn, _, speaker in chunk_diarization.itertracks(yield_label=True):
                    current_chunk_segments.append({
                        "start": float(turn.start) + current_start,
                        "end": float(turn.end) + current_start,
                        "speaker": str(speaker)
                    })
                    current_chunk_speakers.add(str(speaker))
                
                # 對齊標籤
                # 對於每個當前片段的說話者，看他在重疊區域是否與之前的某個說話者重合
                for local_speaker in current_chunk_speakers:
                    matched_global_speaker = None
                    
                    if current_start > 0: # 不是第一段，嘗試對齊
                        # 找尋在 (current_start, current_start + OVERLAP) 範圍內的重合度
                        max_overlap_duration = 0
                        
                        # 比較此 local_speaker 在重疊區的分佈
                        local_speaker_intervals = [
                            (s["start"], s["end"]) for s in current_chunk_segments 
                            if s["speaker"] == local_speaker and s["start"] < current_start + OVERLAP
                        ]
                        
                        # 與已存的全域片段比較
                        for prev_seg in all_speaker_segments:
                            if prev_seg["end"] > current_start: # 在重疊區內
                                for l_start, l_end in local_speaker_intervals:
                                    overlap = min(l_end, prev_seg["end"]) - max(l_start, prev_seg["start"])
                                    if overlap > 0.5: # 超過 0.5s 重合則考慮
                                        # 計算累積重合量
                                        # 這邊簡化邏輯：直接取重合最多的那個全域說話者
                                        matched_global_speaker = prev_seg["speaker"]
                    
                    if not matched_global_speaker:
                        # 建立新的全域說話者標籤
                        global_speakers_count += 1
                        matched_global_speaker = f"Speaker_{global_speakers_count - 1}"
                    
                    # 儲存映射
                    # 注意：這裡加上 chunk index 避免不同片段的本地標籤衝突
                    global_speaker_map[f"{current_start}_{local_speaker}"] = matched_global_speaker
                
                # 將結果轉換為全域標籤並存入
                for seg in current_chunk_segments:
                    seg["speaker"] = global_speaker_map[f"{current_start}_{seg['speaker']}"]
                    # 避免在重疊區重複添加同一個全域說話者的片段（簡化：只添加超過重疊區的部分或在第一段）
                    if current_start == 0 or seg["start"] > current_start + (OVERLAP / 2):
                        all_speaker_segments.append(seg)
                
            finally:
                self._cleanup_file(chunk_path)
                gc.collect() # 每次片段完畢強制回收
            
            if chunk_end >= duration:
                break
            current_start = chunk_end - OVERLAP

        # 將對齊後的結果套用到轉錄段落
        speakers_found = set()
        for segment in result.get("segments", []):
            segment["speaker"] = self._find_speaker(
                segment["start"], 
                segment["end"], 
                all_speaker_segments
            )
            speakers_found.add(segment["speaker"])
        
        result["speakers"] = list(speakers_found)
        result["speaker_segments"] = all_speaker_segments
        return result

    def _find_speaker(self, start: float, end: float, timeline: List[Dict]) -> str:
        """根據時間範圍找出對應的說話者"""
        overlaps = []
        
        for item in timeline:
            overlap = min(end, item["end"]) - max(start, item["start"])
            if overlap > 0:
                overlaps.append((overlap, item["speaker"]))
        
        if not overlaps:
            return "Speaker-Unknown"
        
        overlaps.sort(reverse=True)
        return overlaps[0][1]
    
    def _cleanup_file(self, path: str):
        """清理暫存檔案"""
        try:
            if path and os.path.exists(path):
                os.remove(path)
                parent = os.path.dirname(path)
                if parent and os.path.exists(parent) and not os.listdir(parent):
                    os.rmdir(parent)
        except Exception as e:
            logger.warning(f"清理失敗 {path}: {e}")
