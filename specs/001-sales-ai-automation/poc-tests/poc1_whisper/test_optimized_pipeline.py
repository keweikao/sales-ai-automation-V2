#!/usr/bin/env python3
"""
POC 1 - Optimized Whisper Transcription Pipeline Test

測試完整的 VAD + 智能分段 + 並行轉錄優化流程
"""

import sys
import logging
import argparse
import json
import time
from pathlib import Path

# 加入 src 路徑
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from transcription.pipeline import OptimizedTranscriptionPipeline


def setup_logging(verbose: bool = False):
    """設定日誌"""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('optimized_pipeline_test.log'),
            logging.StreamHandler()
        ]
    )


def test_optimized_pipeline(
    audio_path: str,
    model_size: str = "medium",
    device: str = "cpu",
    workers: int = 6,
    vad_preset: str = "meeting",
    output_dir: str = None,
    enable_diarization: bool = False,
    diarization_token: str = None,
    diarization_model: str = "pyannote/speaker-diarization",
    diarization_allow_overlap: bool = False,
) -> dict:
    """
    測試優化的轉錄流程

    Args:
        audio_path: 音檔路徑
        model_size: 模型大小
        device: 設備
        workers: 並行工作數
        vad_preset: VAD 預設配置
        output_dir: 輸出目錄

    Returns:
        dict: 測試結果
    """
    logger = logging.getLogger(__name__)

    logger.info("="*80)
    logger.info("POC 1 - OPTIMIZED WHISPER TRANSCRIPTION PIPELINE TEST")
    logger.info("="*80)

    # 建立 pipeline
    logger.info("\nInitializing pipeline...")
    pipeline = OptimizedTranscriptionPipeline(
        model_size=model_size,
        device=device,
        max_workers=workers,
        vad_preset=vad_preset,
        output_dir=output_dir,
        target_chunk_duration=600,  # 10分鐘片段
        overlap_duration=2,
        language="zh",
        enable_diarization=enable_diarization,
        diarization_auth_token=diarization_token,
        diarization_model=diarization_model,
        diarization_allow_overlap=diarization_allow_overlap,
    )

    # 執行轉錄
    logger.info("\nStarting transcription...")
    start_time = time.time()

    result = pipeline.process_audio(
        audio_path=audio_path,
        save_transcription=True,
        output_formats=["txt", "json", "srt"]
    )

    total_time = time.time() - start_time

    # 生成測試報告
    test_result = generate_test_report(result, total_time, audio_path, model_size)

    return test_result


def generate_test_report(
    result: dict,
    total_time: float,
    audio_path: str,
    model_size: str
) -> dict:
    """生成測試報告"""
    logger = logging.getLogger(__name__)

    logger.info("\n" + "="*80)
    logger.info("TEST REPORT")
    logger.info("="*80)

    if not result["success"]:
        logger.error(f"Transcription FAILED: {result.get('error', 'Unknown error')}")
        return {
            "success": False,
            "error": result.get("error"),
            "audio_path": audio_path
        }

    # 提取統計資訊
    stats = result["statistics"]
    audio_info = result["audio_info"]
    config = result["pipeline_config"]

    diarization_enabled = config.get("diarization_enabled", False)
    diarization_error = result.get("diarization_error")

    audio_duration = audio_info["duration"]
    audio_size_mb = audio_info["size"] / (1024 * 1024)
    processing_time = result["pipeline_total_time"]
    speed_ratio = processing_time / audio_duration

    # 計算品質指標（基於 segment 數量和文字長度的啟發式評估）
    expected_segments = int(audio_duration / 5)  # 假設平均每 5 秒一個 segment
    segment_ratio = stats["total_segments"] / expected_segments if expected_segments > 0 else 0
    quality_score = min(100, segment_ratio * 100)  # 簡化的品質評分

    # 判斷是否通過
    target_speed_ratio = 0.5  # 目標是處理時間 < 音檔時長的 50%
    passed = speed_ratio < target_speed_ratio and quality_score > 70

    # 列印報告
    logger.info(f"\n📁 Audio File:")
    logger.info(f"   Path: {audio_path}")
    logger.info(f"   Duration: {audio_duration:.1f}s ({audio_duration/60:.1f} min)")
    logger.info(f"   Size: {audio_size_mb:.2f} MB")

    logger.info(f"\n⚙️  Configuration:")
    logger.info(f"   Model: {model_size}")
    logger.info(f"   Device: {config['device']}")
    logger.info(f"   Workers: {config['max_workers']}")
    logger.info(f"   VAD Enabled: {config['vad_enabled']}")
    logger.info(f"   Chunks: {config['chunk_count']}")

    logger.info(f"\n⏱️  Performance:")
    logger.info(f"   Processing Time: {processing_time:.1f}s ({processing_time/60:.1f} min)")
    logger.info(f"   Speed Ratio: {speed_ratio:.3f}x")

    if speed_ratio < 1.0:
        speedup = 1.0 / speed_ratio
        logger.info(f"   Speedup: {speedup:.2f}x faster than real-time")
    else:
        logger.info(f"   Speedup: {speed_ratio:.2f}x slower than real-time")

    time_saved = audio_duration - processing_time
    logger.info(f"   Time Saved: {time_saved:.1f}s ({time_saved/60:.1f} min)")

    logger.info(f"\n📊 Output:")
    logger.info(f"   Total Segments: {stats['total_segments']}")
    logger.info(f"   Text Length: {len(result['full_text'])} characters")
    logger.info(f"   Quality Score: {quality_score:.1f}%")

    logger.info(f"\n📝 Text Preview (first 200 chars):")
    logger.info(f"   {result['full_text'][:200]}...")

    speaker_summary = result.get("speakers", [])
    if diarization_error:
        logger.warning("Speaker diarization disabled: %s", diarization_error)
    elif diarization_enabled and speaker_summary:
        logger.info(f"\n🗣️  Speakers Detected: {len(speaker_summary)}")
        for speaker in speaker_summary:
            speaker_time = speaker["duration"]
            logger.info(
                "   - %s: segments=%d, duration=%.1fs (%.1f min)",
                speaker["speaker"],
                int(speaker["segment_count"]),
                speaker_time,
                speaker_time / 60.0,
            )

    logger.info(f"\n✅ Test Result:")
    if passed:
        logger.info(f"   Status: PASSED ✓")
        logger.info(f"   Speed ratio {speed_ratio:.3f}x < target {target_speed_ratio}x")
        logger.info(f"   Quality score {quality_score:.1f}% > 70%")
    else:
        logger.warning(f"   Status: FAILED ✗")
        if speed_ratio >= target_speed_ratio:
            logger.warning(f"   Speed ratio {speed_ratio:.3f}x >= target {target_speed_ratio}x")
        if quality_score <= 70:
            logger.warning(f"   Quality score {quality_score:.1f}% <= 70%")

    logger.info("="*80)

    # 比較與原始方案的差異
    logger.info(f"\n📈 Comparison with Baseline (Medium model without optimization):")
    baseline_speed_ratio = 0.915  # 從之前的測試結果
    baseline_time = audio_duration * baseline_speed_ratio
    improvement = ((baseline_time - processing_time) / baseline_time) * 100

    logger.info(f"   Baseline processing time: {baseline_time:.1f}s ({baseline_time/60:.1f} min)")
    logger.info(f"   Optimized processing time: {processing_time:.1f}s ({processing_time/60:.1f} min)")
    logger.info(f"   Improvement: {improvement:.1f}%")
    logger.info(f"   Speedup factor: {baseline_time/processing_time:.2f}x")

    logger.info("="*80)

    # 構建測試結果
    test_result = {
        "success": True,
        "passed": passed,
        "audio_path": audio_path,
        "audio_duration": audio_duration,
        "audio_size_mb": audio_size_mb,
        "model_size": model_size,
        "processing_time": processing_time,
        "speed_ratio": speed_ratio,
        "quality_score": quality_score,
        "total_segments": stats["total_segments"],
        "text_length": len(result["full_text"]),
        "vad_enabled": config["vad_enabled"],
        "chunk_count": config["chunk_count"],
        "workers": config["max_workers"],
        "diarization_enabled": diarization_enabled,
        "diarization_error": diarization_error,
        "speakers": speaker_summary,
        "full_result": result
    }

    return test_result


def save_test_result(test_result: dict, output_file: str):
    """儲存測試結果"""
    logger = logging.getLogger(__name__)

    # 移除 full_result 以減少檔案大小
    summary = {k: v for k, v in test_result.items() if k != "full_result"}

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    logger.info(f"\nTest result saved to: {output_file}")


def main():
    """主程式"""
    parser = argparse.ArgumentParser(
        description="POC 1 - Optimized Whisper Transcription Pipeline Test"
    )

    parser.add_argument(
        "--audio",
        required=True,
        help="Path to audio file"
    )

    parser.add_argument(
        "--model",
        default="medium",
        choices=["tiny", "base", "small", "medium", "large-v3"],
        help="Whisper model size (default: medium)"
    )

    parser.add_argument(
        "--device",
        default="cpu",
        choices=["cpu", "cuda"],
        help="Device to use (default: cpu)"
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=6,
        help="Number of parallel workers (default: 6)"
    )

    parser.add_argument(
        "--vad-preset",
        default="meeting",
        choices=["meeting", "presentation", "noisy", "default"],
        help="VAD preset configuration (default: meeting)"
    )

    parser.add_argument(
        "--output-dir",
        help="Output directory for transcription files"
    )

    parser.add_argument(
        "--output",
        default="poc1_optimized_results.json",
        help="Output file for test results (default: poc1_optimized_results.json)"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    parser.add_argument(
        "--diarization",
        action="store_true",
        help="Enable speaker diarization"
    )

    parser.add_argument(
        "--diarization-token",
        help="Hugging Face token for pyannote.audio diarization (optional)"
    )

    parser.add_argument(
        "--diarization-model",
        default="pyannote/speaker-diarization",
        help="Speaker diarization model identifier (default: pyannote/speaker-diarization)"
    )

    parser.add_argument(
        "--allow-diarization-overlap",
        action="store_true",
        help="Keep overlapping speaker segments instead of truncating (default: disabled)"
    )

    args = parser.parse_args()

    # 設定日誌
    setup_logging(args.verbose)

    logger = logging.getLogger(__name__)
    logger.info("Starting Optimized Whisper Pipeline Test...")

    # 執行測試
    test_result = test_optimized_pipeline(
        audio_path=args.audio,
        model_size=args.model,
        device=args.device,
        workers=args.workers,
        vad_preset=args.vad_preset,
        output_dir=args.output_dir,
        enable_diarization=args.diarization,
        diarization_token=args.diarization_token,
        diarization_model=args.diarization_model,
        diarization_allow_overlap=args.allow_diarization_overlap
    )

    # 儲存結果
    save_test_result(test_result, args.output)

    # 返回結果
    if test_result["success"] and test_result["passed"]:
        logger.info("\n✅ TEST PASSED")
        return 0
    elif test_result["success"]:
        logger.warning("\n⚠️  TEST COMPLETED BUT DID NOT MEET PERFORMANCE TARGETS")
        return 1
    else:
        logger.error("\n❌ TEST FAILED")
        return 1


if __name__ == "__main__":
    exit(main())
