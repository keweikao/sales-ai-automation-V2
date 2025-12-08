"""
Optimized Transcription Pipeline

完整的音檔轉錄處理流程，整合 VAD、分段、並行轉錄和結果合併
"""

import logging
import subprocess
from typing import Callable, Dict, Optional
from pathlib import Path
import time

from .vad.processor import VADProcessor
from .chunking.chunker import AudioChunker
from .parallel.transcriber import ParallelTranscriber
from .merging.merger import TranscriptionMerger
from .diarization import create_diarizer
from .quality import calculate_transcription_quality
from .gemini_pipeline import GeminiTranscriptionPipeline
from .stt_batch_pipeline import STTBatchTranscriptionPipeline
import os

logger = logging.getLogger(__name__)

# --- Configuration ---
MODEL_SIZE = os.environ.get("MODEL_SIZE", "medium")
DEVICE = os.environ.get("DEVICE", "cpu")
COMPUTE_TYPE = os.environ.get("COMPUTE_TYPE", "int8")
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "3"))
TARGET_CHUNK_DURATION = int(os.environ.get("TARGET_CHUNK_DURATION", "600"))
OVERLAP_DURATION = float(os.environ.get("OVERLAP_DURATION", "2"))
VAD_PRESET = os.environ.get("VAD_PRESET", "meeting")
TRANSCRIPTION_LANGUAGE = os.environ.get("TRANSCRIPTION_LANGUAGE", "zh")
TRANSCRIPTION_ENGINE = os.getenv("TRANSCRIPTION_ENGINE", "whisper").strip().lower()
ENABLE_DIARIZATION = os.getenv("ENABLE_DIARIZATION", "false").lower() == "true"
DIARIZATION_MODEL = os.environ.get("DIARIZATION_MODEL", "pyannote/speaker-diarization")
DIARIZATION_ALLOW_OVERLAP = os.environ.get("DIARIZATION_ALLOW_OVERLAP", "false").lower() == "true"
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")

# Global pipeline instance
pipeline = None


class OptimizedTranscriptionPipeline:
    """優化的音檔轉錄流程"""

    def __init__(
        self,
        model_size: str = "medium",
        device: str = "cpu",
        compute_type: str = "int8",
        max_workers: int = 6,
        target_chunk_duration: int = 600,
        overlap_duration: int = 2,
        vad_preset: str = "meeting",
        language: str = "zh",
        output_dir: Optional[str] = None,
        enable_diarization: bool = False,
        diarization_model: str = "pyannote/speaker-diarization",
        diarization_auth_token: Optional[str] = None,
        diarization_allow_overlap: bool = False,
    ):
        """
        初始化轉錄流程

        Args:
            model_size: Whisper 模型大小
            device: 設備類型 (cpu, cuda)
            compute_type: 計算精度 (int8, float16)
            max_workers: 最大並行工作數
            target_chunk_duration: 目標片段長度（秒）
            overlap_duration: 片段重疊時間（秒）
            vad_preset: VAD 預設配置 (meeting, presentation, noisy)
            language: 語言代碼
            output_dir: 輸出目錄
        """
        self.model_size = model_size
        self.device = device
        self.language = language
        self.output_dir = output_dir
        self.enable_diarization = enable_diarization
        self.diarization_error: Optional[str] = None
        self.diarizer = None
        self._diarization_config = {
            "model_name": diarization_model,
            "auth_token": diarization_auth_token,
            "allow_overlap": diarization_allow_overlap,
        }

        # 初始化各個模組
        self.vad_processor = VADProcessor(
            **VADProcessor.get_preset_parameters(vad_preset)
        )

        self.chunker = AudioChunker(
            target_chunk_duration=target_chunk_duration,
            overlap_duration=overlap_duration
        )

        vad_params = self.vad_processor.get_vad_parameters()

        self.transcriber = ParallelTranscriber(
            model_size=model_size,
            device=device,
            compute_type=compute_type,
            max_workers=max_workers,
            vad_parameters=vad_params,
            language=language
        )

        self.merger = TranscriptionMerger(
            overlap_duration=overlap_duration
        )

        logger.info("="*60)
        logger.info("Optimized Transcription Pipeline Initialized")
        logger.info(f"  Model: {model_size}")
        logger.info(f"  Device: {device}")
        logger.info(f"  Workers: {max_workers}")
        logger.info(f"  VAD Preset: {vad_preset}")
        logger.info(f"  Chunk Duration: {target_chunk_duration}s")
        logger.info(f"  Overlap: {overlap_duration}s")
        logger.info("="*60)

    def process_audio(
        self,
        audio_path: str,
        save_transcription: bool = True,
        output_formats: list = None,
        progress_callback: Optional[Callable[[Dict], None]] = None,
    ) -> Dict:
        """
        處理音檔的完整流程

        Args:
            audio_path: 音檔路徑
            save_transcription: 是否儲存轉錄結果
            output_formats: 輸出格式列表 (txt, srt, vtt, json)

        Returns:
            Dict: 完整的轉錄結果
        """
        if output_formats is None:
            output_formats = ["txt", "json"]

        logger.info("="*60)
        logger.info(f"Processing audio file: {audio_path}")
        logger.info("="*60)

        pipeline_start_time = time.time()

        # Step 1: 取得音檔資訊
        logger.info("\n[Step 1/4] Getting audio information...")
        audio_info = self._get_audio_info(audio_path)

        if not audio_info["success"]:
            return {
                "success": False,
                "error": audio_info.get("error", "Failed to get audio info"),
                "audio_path": audio_path
            }

        total_duration = audio_info["duration"]
        logger.info(f"Audio duration: {total_duration:.1f}s ({total_duration/60:.1f} min)")

        # Step 2: 創建音檔分段
        logger.info("\n[Step 2/4] Creating audio chunks...")
        chunks = self.chunker.create_chunks(total_duration)
        self._notify_progress(
            progress_callback,
            step="chunking",
            total_chunks=len(chunks),
            completed_chunks=0,
            detail=f"已規劃 {len(chunks)} 個片段",
        )

        # Step 3: 並行轉錄所有片段
        logger.info("\n[Step 3/4] Parallel transcription...")

        # 設定輸出目錄
        chunks_output_dir = self._get_chunks_output_dir(audio_path)

        chunk_results = self.transcriber.transcribe_chunks(
            audio_path=audio_path,
            chunks=chunks,
            output_dir=chunks_output_dir,
            progress_callback=progress_callback,
        )

        # Step 4: 合併結果
        logger.info("\n[Step 4/4] Merging results...")
        self._notify_progress(progress_callback, step="merging", detail="合併片段中")
        merged_result = self.merger.merge_chunks(chunk_results)

        # 加入音檔資訊
        merged_result["audio_info"] = audio_info
        merged_result["audio_path"] = audio_path
        merged_result["pipeline_config"] = {
            "model_size": self.model_size,
            "device": self.device,
            "language": self.language,
            "max_workers": self.transcriber.max_workers,
            "vad_enabled": bool(self.vad_processor.vad_parameters),
            "chunk_count": len(chunks),
            "diarization_enabled": self.enable_diarization,
        }

        # 計算總處理時間
        pipeline_total_time = time.time() - pipeline_start_time
        merged_result["pipeline_total_time"] = pipeline_total_time

        # 套用說話者區分
        diarizer = self._get_diarizer()
        if merged_result["success"] and diarizer:
            diarization_segments = diarizer.diarize(
                audio_path, merged_result.get("segments")
            )
            merged_result["speaker_segments"] = [
                {
                    "start": segment.start,
                    "end": segment.end,
                    "speaker": segment.speaker,
                }
                for segment in diarization_segments
            ]

            merged_result["segments"] = self._assign_speakers_to_segments(
                merged_result["segments"], diarization_segments
            )

            # 再次檢查 diarizer 是否有效（防禦性編程）
            if diarizer is not None:
                merged_result["speakers"] = diarizer.summarize(diarization_segments)

            # 立即釋放 diarizer 記憶體
            self._cleanup_diarizer()
        elif self.enable_diarization and not diarizer:
            merged_result["diarization_error"] = self.diarization_error

        # 計算品質評分（FR-010）
        quality = calculate_transcription_quality(
            merged_result=merged_result,
            chunk_results=chunk_results,
            audio_info=audio_info,
            diarization_enabled=self.enable_diarization,
        )
        merged_result["quality"] = quality

        stats = merged_result.setdefault("statistics", {})
        stats.update(
            {
                "characters": quality["diagnostics"]["characters"],
                "char_per_second": quality["components"]["char_time_ratio"]["value"],
                "unique_segment_ratio": quality["components"]["repetition"].get(
                    "unique_segment_ratio"
                ),
            }
        )

        # 儲存結果
        if save_transcription and merged_result["success"]:
            self._save_results(audio_path, merged_result, output_formats)

        # 清理臨時檔案
        self._cleanup_temp_files(chunks_output_dir)

        # 最終摘要
        self._print_final_summary(merged_result, pipeline_total_time)

        return merged_result

    @staticmethod
    def _notify_progress(callback: Optional[Callable[[Dict], None]], **payload) -> None:
        if not callback:
            return
        try:
            callback(payload)
        except Exception as exc:  # pylint: disable=broad-except
            logger.debug("Progress callback failed: %s", exc)

    @staticmethod
    def _assign_speakers_to_segments(segments, diarization_segments):
        """
        將說話者標籤對應到轉錄片段
        """

        def find_speaker(start: float, end: float):
            overlaps = []
            for segment in diarization_segments:
                overlap = min(end, segment.end) - max(start, segment.start)
                if overlap > 0:
                    overlaps.append((overlap, segment.speaker))

            if not overlaps:
                return None

            overlaps.sort(reverse=True)
            return overlaps[0][1]

        for segment in segments:
            speaker = find_speaker(segment["start"], segment["end"])
            segment["speaker"] = speaker or "Speaker-Unknown"

        return segments

    def _get_diarizer(self):
        """Lazily instantiate the diarizer to reduce peak memory usage."""
        if not self.enable_diarization:
            return None

        # 如果 diarizer 不存在，嘗試創建（即使之前失敗過也可能重試成功）
        if self.diarizer is None:
            try:
                logger.info("Loading diarization model...")
                self._log_memory_usage("Before diarization model load")

                self.diarizer = create_diarizer(
                    model_name=self._diarization_config["model_name"],
                    use_auth_token=self._diarization_config["auth_token"],
                    allow_overlap=self._diarization_config["allow_overlap"],
                )

                # 成功創建後清除之前的錯誤標記
                self.diarization_error = None
                self._log_memory_usage("After diarization model load")
            except RuntimeError as exc:
                self.diarization_error = str(exc)
                logger.warning(
                    "Speaker diarization disabled: %s", self.diarization_error
                )
                return None

        return self.diarizer

    def _cleanup_diarizer(self):
        """釋放 diarizer 記憶體"""
        if self.diarizer is not None:
            logger.info("Releasing diarization model from memory...")
            self._log_memory_usage("Before diarizer cleanup")

            # 明確刪除 diarizer 物件
            del self.diarizer
            self.diarizer = None

            # 強制垃圾回收
            import gc
            gc.collect()

            self._log_memory_usage("After diarizer cleanup")
            logger.info("Diarization model memory released")

    def _log_memory_usage(self, context: str = ""):
        """記錄記憶體使用情況"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            process = psutil.Process()
            process_memory = process.memory_info().rss / 1024 / 1024 / 1024  # GB

            logger.info(
                f"Memory usage [{context}]: "
                f"System={memory.percent:.1f}%, "
                f"Process={process_memory:.2f}GB"
            )
        except ImportError:
            # psutil not available, skip logging
            pass
        except Exception as e:
            logger.debug(f"Failed to log memory usage: {e}")

    def _get_audio_info(self, audio_path: str) -> Dict:
        """
        使用 ffprobe 取得音檔資訊

        Args:
            audio_path: 音檔路徑

        Returns:
            Dict: 音檔資訊
        """
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration,size",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )

            output = result.stdout.decode().strip().split("\n")
            duration = float(output[0])
            size = int(output[1])

            return {
                "success": True,
                "duration": duration,
                "size": size,
                "path": audio_path
            }

        except Exception as e:
            logger.error(f"Failed to get audio info: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def _get_chunks_output_dir(self, audio_path: str) -> str:
        """取得片段輸出目錄"""
        if self.output_dir:
            base_dir = Path(self.output_dir)
        else:
            base_dir = Path(audio_path).parent

        audio_name = Path(audio_path).stem
        chunks_dir = base_dir / f"{audio_name}_chunks"

        return str(chunks_dir)

    def _save_results(
        self,
        audio_path: str,
        result: Dict,
        formats: list
    ) -> None:
        """儲存轉錄結果"""
        logger.info("\nSaving transcription results...")

        audio_name = Path(audio_path).stem

        if self.output_dir:
            output_base = Path(self.output_dir) / audio_name
        else:
            output_base = Path(audio_path).parent / audio_name

        for fmt in formats:
            output_file = f"{output_base}_transcription.{fmt}"
            self.merger.save_to_file(result, output_file, format=fmt)

    def _cleanup_temp_files(self, chunks_dir: str) -> None:
        """清理臨時片段檔案"""
        logger.info("\nCleaning up temporary files...")

        chunks_path = Path(chunks_dir)

        if chunks_path.exists():
            import shutil
            try:
                shutil.rmtree(chunks_path)
                logger.info(f"Removed temporary directory: {chunks_path}")
            except Exception as e:
                logger.warning(f"Failed to remove temp directory: {str(e)}")

    def _print_final_summary(self, result: Dict, pipeline_time: float) -> None:
        """列印最終摘要"""
        logger.info("\n" + "="*60)
        logger.info("PIPELINE COMPLETION SUMMARY")
        logger.info("="*60)

        if result["success"]:
            stats = result["statistics"]
            audio_duration = stats["total_duration"]

            logger.info(f"Status: SUCCESS")
            logger.info(f"Audio Duration: {audio_duration:.1f}s ({audio_duration/60:.1f} min)")
            logger.info(f"Processing Time: {pipeline_time:.1f}s ({pipeline_time/60:.1f} min)")
            logger.info(f"Speed Ratio: {pipeline_time/audio_duration:.2f}x")
            logger.info(f"Total Segments: {stats['total_segments']}")
            logger.info(f"Text Length: {len(result['full_text'])} characters")
            logger.info(f"VAD Enabled: {stats['vad_enabled']}")
            if result.get("quality"):
                quality = result["quality"]
                logger.info(f"Quality Score: {quality['score']:.1f}/100")
                language_component = quality["components"].get("language_confidence", {})
                char_component = quality["components"].get("char_time_ratio", {})
                logger.info(
                    "  ├─ Language confidence: %.1f%% (detected=%s)",
                    language_component.get("score", 0.0),
                    language_component.get("detected_language"),
                )
                logger.info(
                    "  ├─ Characters/sec: %.2f",
                    char_component.get("value", 0.0),
                )
                repetition_component = quality["components"].get("repetition", {})
                logger.info(
                    "  └─ Unique segment ratio: %.2f",
                    repetition_component.get("unique_segment_ratio", 0.0),
                )

            # 計算節省的時間
            if pipeline_time < audio_duration:
                time_saved = audio_duration - pipeline_time
                logger.info(f"Time Saved: {time_saved:.1f}s ({time_saved/60:.1f} min)")

        else:
            logger.error(f"Status: FAILED")
            logger.error(f"Error: {result.get('error', 'Unknown error')}")

        logger.info("="*60)


# 使用範例
if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(description="Optimized Audio Transcription Pipeline")
    parser.add_argument("--audio", required=True, help="Path to audio file")
    parser.add_argument("--model", default="medium", help="Whisper model size")
    parser.add_argument("--device", default="cpu", help="Device (cpu/cuda)")
    parser.add_argument("--workers", type=int, default=6, help="Number of parallel workers")
    parser.add_argument("--vad-preset", default="meeting", help="VAD preset (meeting/presentation/noisy)")
    parser.add_argument("--output-dir", help="Output directory")
    parser.add_argument("--formats", nargs="+", default=["txt", "json"], help="Output formats")

    args = parser.parse_args()

    # 創建 pipeline
    pipeline = OptimizedTranscriptionPipeline(
        model_size=args.model,
        device=args.device,
        max_workers=args.workers,
        vad_preset=args.vad_preset,
        output_dir=args.output_dir
    )

    # 處理音檔
    result = pipeline.process_audio(
        audio_path=args.audio,
        save_transcription=True,
        output_formats=args.formats
    )

    # 顯示結果預覽
    if result["success"]:
        print("\n" + "="*60)
        print("TRANSCRIPTION PREVIEW (first 500 characters):")
        print("="*60)
        print(result["full_text"][:500])
        if len(result["full_text"]) > 500:
            print("...")
        print("="*60)

def get_pipeline(engine: str = None, **kwargs):
    global pipeline
    
    # If engine is explicitly provided, return a new instance (factory mode)
    if engine:
        if engine == "stt_batch":
            return STTBatchTranscriptionPipeline(**kwargs)
        elif engine == "gemini":
            return GeminiTranscriptionPipeline(**kwargs)
        else:
            raise ValueError(f"Unknown transcription engine: {engine}")

    # Singleton mode (for main service)
    if pipeline is None:
        engine = TRANSCRIPTION_ENGINE
        logger.info(f"Initializing Global Pipeline. Engine: '{engine}'")
        
        if engine == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY is required for Gemini engine")
            pipeline = GeminiTranscriptionPipeline(api_key=api_key)
            
        elif engine == "stt_batch":
            project_id = os.getenv("GCP_PROJECT_ID", "sales-ai-automation-v2")
            location = os.getenv("GCP_LOCATION", "asia-southeast1")
            pipeline = STTBatchTranscriptionPipeline(project_id=project_id, location=location)
            
        else:
            # Fallback or Error. For now, let's error if not one of the supported ones to avoid confusion
            # unless we want to keep Whisper? The previous code had Whisper.
            # Let's assume we only support stt_batch and gemini for this deployment.
            raise ValueError(f"Unsupported TRANSCRIPTION_ENGINE: {engine}")
            
    return pipeline

