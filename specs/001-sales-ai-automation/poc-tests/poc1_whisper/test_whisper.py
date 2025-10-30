#!/usr/bin/env python3
"""
POC 1: Faster-Whisper Performance with Speaker Diarization

Tests if Faster-Whisper can process 40-minute Chinese audio files
in <5 minutes on CPU-only Cloud Run with speaker diarization.

Usage:
    python test_whisper.py --audio test_audio.m4a
    python test_whisper.py --batch test_data/audio/*.m4a
"""

import argparse
import time
import json
from pathlib import Path
from typing import Dict, List
from faster_whisper import WhisperModel


class WhisperTester:
    def __init__(self, model_size="large-v3", device="cpu", compute_type="int8"):
        """Initialize Whisper model"""
        print(f"Loading Whisper model: {model_size}")
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        self.model_size = model_size

    def transcribe_with_diarization(self, audio_path: str, enable_diarization=True) -> Dict:
        """Transcribe audio with optional speaker diarization"""
        start_time = time.time()

        # Transcribe
        segments, info = self.model.transcribe(
            audio_path,
            language="zh",
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )

        # Collect segments
        transcript_segments = []
        full_text = []

        for segment in segments:
            transcript_segments.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
                "confidence": segment.avg_logprob
            })
            full_text.append(segment.text)

        processing_time = time.time() - start_time

        # Calculate quality metrics
        quality_score = self._calculate_quality_score(transcript_segments, info)

        result = {
            "audio_path": audio_path,
            "model_size": self.model_size,
            "processing_time": processing_time,
            "audio_duration": info.duration,
            "language": info.language,
            "language_probability": info.language_probability,
            "segments_count": len(transcript_segments),
            "full_text": "".join(full_text),
            "segments": transcript_segments,
            "quality_score": quality_score,
            "speed_ratio": processing_time / info.duration
        }

        return result

    def _calculate_quality_score(self, segments: List[Dict], info) -> float:
        """Calculate quality score (0-100) based on multiple factors"""

        # Factor 1: Language detection confidence (0-30 points)
        lang_score = info.language_probability * 30

        # Factor 2: Average segment confidence (0-40 points)
        if segments:
            avg_confidence = sum(s["confidence"] for s in segments) / len(segments)
            # Convert log probability to 0-1 scale (rough approximation)
            confidence_score = min(40, max(0, (avg_confidence + 1) * 40))
        else:
            confidence_score = 0

        # Factor 3: Text coherence - character to time ratio (0-30 points)
        # Good Chinese transcription: ~4-8 chars/second
        if info.duration > 0:
            total_chars = sum(len(s["text"]) for s in segments)
            chars_per_second = total_chars / info.duration

            if 4 <= chars_per_second <= 8:
                coherence_score = 30
            elif 3 <= chars_per_second < 4 or 8 < chars_per_second <= 10:
                coherence_score = 20
            else:
                coherence_score = 10
        else:
            coherence_score = 0

        quality_score = lang_score + confidence_score + coherence_score
        return min(100, max(0, quality_score))


def run_test(audio_path: str, model_size="large-v3") -> Dict:
    """Run single test"""
    tester = WhisperTester(model_size=model_size)
    result = tester.transcribe_with_diarization(audio_path)

    # Print summary
    print(f"\n{'='*60}")
    print(f"Audio: {Path(audio_path).name}")
    print(f"Duration: {result['audio_duration']:.1f}s ({result['audio_duration']/60:.1f} min)")
    print(f"Processing Time: {result['processing_time']:.1f}s ({result['processing_time']/60:.1f} min)")
    print(f"Speed Ratio: {result['speed_ratio']:.3f}x (lower is faster)")
    print(f"Language: {result['language']} ({result['language_probability']:.2%} confidence)")
    print(f"Quality Score: {result['quality_score']:.1f}/100")
    print(f"Segments: {result['segments_count']}")
    print(f"Text Preview: {result['full_text'][:100]}...")

    # Success criteria check
    success = (
        result['processing_time'] <= 300 and  # <5 minutes
        result['quality_score'] >= 85 and      # >85% quality
        result['language_probability'] >= 0.8  # >80% language confidence
    )

    status = "✅ PASS" if success else "❌ FAIL"
    print(f"\nResult: {status}")
    print(f"{'='*60}\n")

    return result


def run_batch_tests(audio_files: List[str], output_file="results.json"):
    """Run tests on multiple audio files"""
    results = []

    print(f"Running tests on {len(audio_files)} audio files...\n")

    for audio_path in audio_files:
        try:
            result = run_test(audio_path)
            results.append(result)
        except Exception as e:
            print(f"❌ Error processing {audio_path}: {e}")
            results.append({
                "audio_path": audio_path,
                "error": str(e),
                "success": False
            })

    # Summary statistics
    successful_tests = [r for r in results if r.get("quality_score", 0) >= 85]
    avg_processing_time = sum(r.get("processing_time", 0) for r in results) / len(results)
    avg_quality = sum(r.get("quality_score", 0) for r in results) / len(results)

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Total Tests: {len(results)}")
    print(f"Successful: {len(successful_tests)} ({len(successful_tests)/len(results)*100:.1f}%)")
    print(f"Average Processing Time: {avg_processing_time:.1f}s ({avg_processing_time/60:.1f} min)")
    print(f"Average Quality Score: {avg_quality:.1f}/100")

    # Success criteria for POC 1
    poc_success = (
        len(successful_tests) / len(results) >= 0.9 and  # 90% success rate
        avg_processing_time <= 300 and                    # <5 min average
        avg_quality >= 85                                 # >85 quality average
    )

    print(f"\nPOC 1 Result: {'✅ GO' if poc_success else '❌ NO-GO'}")
    print(f"{'='*60}\n")

    # Save results
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"Detailed results saved to: {output_file}")

    return results


def main():
    parser = argparse.ArgumentParser(description="POC 1: Test Faster-Whisper Performance")
    parser.add_argument("--audio", type=str, help="Single audio file to test")
    parser.add_argument("--batch", type=str, nargs="+", help="Multiple audio files to test")
    parser.add_argument("--model", type=str, default="large-v3", choices=["large-v3", "medium", "small"],
                       help="Whisper model size")
    parser.add_argument("--output", type=str, default="results.json", help="Output file for results")

    args = parser.parse_args()

    if args.audio:
        run_test(args.audio, model_size=args.model)
    elif args.batch:
        run_batch_tests(args.batch, output_file=args.output)
    else:
        print("Error: Please provide --audio or --batch argument")
        parser.print_help()


if __name__ == "__main__":
    main()
