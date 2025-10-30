"""
Optimized Transcription Pipeline

完整的音檔轉錄處理流程，整合 VAD、分段、並行轉錄和結果合併
"""

import logging
import subprocess
from typing import Dict, Optional
from pathlib import Path
import time

from .vad.processor import VADProcessor
from .chunking.chunker import AudioChunker
from .parallel.transcriber import ParallelTranscriber
from .merging.merger import TranscriptionMerger
from .diarization import create_diarizer

logger = logging.getLogger(__name__)


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
        output_formats: list = None
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

        # Step 3: 並行轉錄所有片段
        logger.info("\n[Step 3/4] Parallel transcription...")

        # 設定輸出目錄
        chunks_output_dir = self._get_chunks_output_dir(audio_path)

        chunk_results = self.transcriber.transcribe_chunks(
            audio_path=audio_path,
            chunks=chunks,
            output_dir=chunks_output_dir
        )

        # Step 4: 合併結果
        logger.info("\n[Step 4/4] Merging results...")
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
            merged_result["speakers"] = diarizer.summarize(diarization_segments)
        elif self.enable_diarization and not diarizer:
            merged_result["diarization_error"] = self.diarization_error

        # 儲存結果
        if save_transcription and merged_result["success"]:
            self._save_results(audio_path, merged_result, output_formats)

        # 清理臨時檔案
        self._cleanup_temp_files(chunks_output_dir)

        # 最終摘要
        self._print_final_summary(merged_result, pipeline_total_time)

        return merged_result

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

        if self.diarizer is None and not self.diarization_error:
            try:
                self.diarizer = create_diarizer(
                    model_name=self._diarization_config["model_name"],
                    use_auth_token=self._diarization_config["auth_token"],
                    allow_overlap=self._diarization_config["allow_overlap"],
                )
            except RuntimeError as exc:
                self.diarization_error = str(exc)
                logger.warning(
                    "Speaker diarization disabled: %s", self.diarization_error
                )

        return self.diarizer

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
