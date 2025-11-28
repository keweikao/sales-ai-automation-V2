"""
Parallel Transcription Module

使用 ThreadPoolExecutor 並行處理多個音檔片段的轉錄
"""

import logging
import subprocess
import threading
from typing import Callable, Dict, List, Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..gemini_transcriber import transcribe as gemini_transcribe
import time

logger = logging.getLogger(__name__)

# Patch tqdm compatibility regression (tqdm>=4.67)
# Removed fw_utils tqdm compatibility block (no longer needed)


class ParallelTranscriber:
    """並行轉錄處理器"""

    def __init__(
        self,
        model_size: str = "medium",
        device: str = "cpu",
        compute_type: str = "int8",
        max_workers: int = 6,
        vad_parameters: Optional[Dict] = None,
        language: str = "zh",
        beam_size: int = 5
    ):
        """
        初始化並行轉錄器

        Args:
            model_size: Whisper 模型大小 (tiny, base, small, medium, large-v3)
            device: 設備類型 (cpu, cuda)
            compute_type: 計算精度 (int8, float16, float32)
            max_workers: 最大並行工作數
            vad_parameters: VAD 參數字典
            language: 語言代碼
            beam_size: Beam search 大小
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.max_workers = max_workers
        self.vad_parameters = vad_parameters or {}
        self.language = language
        self.beam_size = beam_size
        self._thread_local = threading.local()

        logger.info(
            f"Parallel Transcriber initialized - "
            f"model: {model_size}, device: {device}, "
            f"workers: {max_workers}, VAD enabled: {bool(vad_parameters)}"
        )

    # Removed WhisperModel creation – not needed for Gemini transcriber

    # Removed worker model getter – Gemini transcriber is stateless

    def _extract_audio_chunk(
        self,
        audio_path: str,
        chunk: Dict,
        output_dir: Path
    ) -> Optional[str]:
        """
        使用 ffmpeg 提取音檔片段

        Args:
            audio_path: 原始音檔路徑
            chunk: 片段資訊
            output_dir: 輸出目錄

        Returns:
            Optional[str]: 提取的音檔路徑，失敗返回 None
        """
        chunk_id = chunk["chunk_id"]
        start = chunk["start"]
        duration = chunk["duration"]

        # 生成輸出檔名
        input_path = Path(audio_path)
        output_filename = f"{input_path.stem}_chunk_{chunk_id:03d}.wav"
        output_path = output_dir / output_filename

        # 構建 ffmpeg 命令
        ffmpeg_cmd = [
            "ffmpeg",
            "-i", str(audio_path),
            "-ss", str(start),
            "-t", str(duration),
            "-ar", "16000",  # 16kHz 採樣率
            "-ac", "1",      # 單聲道
            "-c:a", "pcm_s16le",  # WAV 格式
            "-y",  # 覆蓋已存在檔案
            str(output_path)
        ]

        try:
            logger.debug(f"Extracting chunk {chunk_id}: {start:.1f}s - {start+duration:.1f}s")

            result = subprocess.run(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )

            logger.debug(f"Chunk {chunk_id} extracted successfully: {output_path}")
            return str(output_path)

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to extract chunk {chunk_id}: {e.stderr.decode()}")
            return None

    def _transcribe_single_chunk(
        self,
        chunk_info: Dict
    ) -> Dict:
        """
        轉錄單個音檔片段（在工作線程中執行）

        Args:
            chunk_info: 包含音檔路徑和片段資訊的字典
                {
                    "chunk_path": "path/to/chunk.wav",
                    "chunk": {"chunk_id": 0, "start": 0.0, ...},
                    "original_audio_path": "path/to/original.m4a"
                }

        Returns:
            Dict: 轉錄結果
        """
        chunk_path = chunk_info["chunk_path"]
        chunk = chunk_info["chunk"]
        chunk_id = chunk["chunk_id"]

        try:
            start_time = time.time()

            # 創建模型實例（每個工作線程獨立且重用）
            # 使用 Gemini 轉錄
            segments = gemini_transcribe(
                chunk_path,
                language=self.language,
                beam_size=self.beam_size
            )
            info = None  # Gemini wrapper does not provide additional info

            # 收集所有 segments
            all_segments = []
            # Gemini returns segments already in the expected dict format
            all_segments.extend(segments)

            processing_time = time.time() - start_time

            result = {
                "chunk_id": chunk_id,
                "chunk": chunk,
                "chunk_path": chunk_path,
                "success": True,
                "segments": all_segments,
                "language": None,
                "language_probability": None,
                "duration": None,
                "processing_time": processing_time,
                "vad_enabled": bool(self.vad_parameters)
            }

            logger.info(
                f"[Chunk {chunk_id}] Completed - "
                f"{len(all_segments)} segments, "
                f"{processing_time:.1f}s processing time"
            )

            return result

        except Exception as e:
            logger.error(f"[Chunk {chunk_id}] Transcription failed: {str(e)}")
            return {
                "chunk_id": chunk_id,
                "chunk": chunk,
                "chunk_path": chunk_path,
                "success": False,
                "error": str(e),
                "segments": []
            }

    def transcribe_chunks(
        self,
        audio_path: str,
        chunks: List[Dict],
        output_dir: Optional[str] = None,
        progress_callback: Optional[Callable[[Dict], None]] = None,
    ) -> List[Dict]:
        """
        並行轉錄所有音檔片段

        Args:
            audio_path: 原始音檔路徑
            chunks: 片段列表（由 AudioChunker 生成）
            output_dir: 臨時檔案輸出目錄

        Returns:
            List[Dict]: 所有片段的轉錄結果列表
        """
        logger.info(f"Starting parallel transcription of {len(chunks)} chunks")
        logger.info(f"Max workers: {self.max_workers}")

        # 設定輸出目錄
        if output_dir is None:
            output_dir = Path(audio_path).parent / "chunks"
        else:
            output_dir = Path(output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Chunk output directory: {output_dir}")

        # Step 1: 提取所有音檔片段
        logger.info("Step 1: Extracting audio chunks...")
        chunk_paths = []

        extracted = 0

        def _notify(**payload):
            if not progress_callback:
                return
            try:
                progress_callback(payload)
            except Exception as exc:  # pylint: disable=broad-except
                logger.debug("Progress callback failed: %s", exc)

        total_chunks = len(chunks)

        for chunk in chunks:
            chunk_path = self._extract_audio_chunk(audio_path, chunk, output_dir)
            if chunk_path:
                chunk_paths.append({
                    "chunk_path": chunk_path,
                    "chunk": chunk,
                    "original_audio_path": audio_path
                })
                extracted += 1
                _notify(
                    step="chunking",
                    total_chunks=total_chunks,
                    completed_chunks=extracted,
                    chunk_id=chunk["chunk_id"],
                    chunk_status="extracted",
                    chunk_duration=chunk.get("duration"),
                )
            else:
                logger.error(f"Failed to extract chunk {chunk['chunk_id']}")

        logger.info(f"Successfully extracted {len(chunk_paths)}/{len(chunks)} chunks")
        _notify(
            step="transcribing",
            total_chunks=len(chunk_paths),
            completed_chunks=0,
            detail="開始並行轉錄",
        )

        # Step 2: 並行轉錄
        logger.info("Step 2: Parallel transcription...")
        start_time = time.time()
        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任務
            future_to_chunk = {
                executor.submit(self._transcribe_single_chunk, chunk_info): chunk_info
                for chunk_info in chunk_paths
            }

            # 收集結果
            processed = 0
            for future in as_completed(future_to_chunk):
                chunk_info = future_to_chunk[future]
                try:
                    result = future.result()
                    results.append(result)
                    chunk_status = "completed" if result["success"] else "failed"
                    processed += 1
                    _notify(
                        step="transcribing",
                        total_chunks=len(chunk_paths),
                        completed_chunks=processed,
                        chunk_id=result["chunk_id"],
                        chunk_status=chunk_status,
                        chunk_duration=result.get("duration"),
                    )
                except Exception as e:
                    logger.error(f"Chunk transcription exception: {str(e)}")
                    results.append({
                        "chunk_id": chunk_info["chunk"]["chunk_id"],
                        "chunk": chunk_info["chunk"],
                        "success": False,
                        "error": str(e),
                        "segments": []
                    })
                    processed += 1
                    _notify(
                        step="transcribing",
                        total_chunks=len(chunk_paths),
                        completed_chunks=processed,
                        chunk_id=chunk_info["chunk"]["chunk_id"],
                        chunk_status="failed",
                    )

        total_time = time.time() - start_time

        # 按 chunk_id 排序
        results.sort(key=lambda x: x["chunk_id"])

        # 統計資訊
        successful = sum(1 for r in results if r["success"])
        total_segments = sum(len(r["segments"]) for r in results)
        total_audio_duration = sum(r.get("duration", 0) for r in results if r["success"])

        logger.info("="*60)
        logger.info("Parallel Transcription Summary:")
        logger.info(f"  Total chunks: {len(chunks)}")
        logger.info(f"  Successful: {successful}/{len(results)}")
        logger.info(f"  Total segments: {total_segments}")
        logger.info(f"  Total audio duration: {total_audio_duration:.1f}s ({total_audio_duration/60:.1f} min)")
        logger.info(f"  Total processing time: {total_time:.1f}s ({total_time/60:.1f} min)")
        if total_audio_duration > 0:
            speed_ratio = total_time / total_audio_duration
            logger.info(f"  Speed ratio: {speed_ratio:.2f}x")
        logger.info("="*60)

        return results


# 使用範例
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 模擬測試
    from src.transcription.chunking.chunker import AudioChunker
    from src.transcription.vad.processor import VADProcessor

    # 1. 創建分段
    chunker = AudioChunker(
        target_chunk_duration=600,  # 10分鐘
        overlap_duration=2
    )

    # 假設音檔為 30 分鐘
    chunks = chunker.create_chunks(total_duration=1800)

    # 2. 獲取 VAD 參數
    vad = VADProcessor()
    vad_params = vad.get_vad_parameters()

    # 3. 並行轉錄
    transcriber = ParallelTranscriber(
        model_size="medium",
        device="cpu",
        compute_type="int8",
        max_workers=6,
        vad_parameters=vad_params,
        language="zh"
    )

    # 注意：這裡需要實際音檔路徑
    # results = transcriber.transcribe_chunks(
    #     audio_path="/path/to/audio.m4a",
    #     chunks=chunks
    # )

    print("Parallel transcriber initialized successfully")
