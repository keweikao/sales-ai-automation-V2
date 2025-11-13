#!/usr/bin/env python3
"""
Diarization Integration Test

Tests the full diarization pipeline with sample audio.
Requires a valid HUGGINGFACE_TOKEN environment variable.
"""

import os
import sys
import logging
import tempfile
import json
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_environment():
    """Check environment variables and dependencies."""
    logger.info("=" * 70)
    logger.info("Testing Environment Setup")
    logger.info("=" * 70)

    # Check token
    token = os.getenv("HUGGINGFACE_TOKEN")
    if not token:
        logger.error("ERROR: HUGGINGFACE_TOKEN environment variable not set")
        return False

    logger.info(f"✓ HUGGINGFACE_TOKEN found: {token[:10]}...{token[-10:]}")

    # Check dependencies
    dependencies = [
        ("torch", "PyTorch"),
        ("torchaudio", "torchaudio"),
        ("faster_whisper", "faster-whisper"),
        ("pyannote", "pyannote.audio"),
        ("numpy", "NumPy"),
    ]

    all_ok = True
    for module_name, display_name in dependencies:
        try:
            __import__(module_name)
            logger.info(f"✓ {display_name} installed")
        except ImportError:
            logger.error(f"✗ {display_name} NOT installed")
            all_ok = False

    return all_ok


def test_diarizer_initialization():
    """Test initializing the diarizer."""
    logger.info("\n" + "=" * 70)
    logger.info("Testing Diarizer Initialization")
    logger.info("=" * 70)

    try:
        # Add src to path
        sys.path.insert(0, str(Path(__file__).parent / "src"))

        from transcription.diarization import PyannoteDiarizer

        token = os.getenv("HUGGINGFACE_TOKEN")

        logger.info("Creating PyannoteDiarizer instance...")
        diarizer = PyannoteDiarizer(
            model_name="pyannote/speaker-diarization",
            use_auth_token=token,
            enable_overlap=False,
        )

        logger.info("✓ Diarizer initialized successfully")
        logger.info(f"  Pipeline type: {type(diarizer.pipeline)}")
        logger.info(f"  Overlap enabled: {diarizer.enable_overlap}")

        return True, diarizer

    except Exception as e:
        logger.error(f"✗ Diarizer initialization failed: {e}")
        logger.error(f"  Error type: {type(e).__name__}")
        return False, None


def test_diarizer_with_sample_audio(diarizer):
    """Test diarization with a sample audio file."""
    logger.info("\n" + "=" * 70)
    logger.info("Testing Diarization with Sample Audio")
    logger.info("=" * 70)

    try:
        import numpy as np
        import soundfile as sf

        # Create a simple test audio file
        logger.info("Creating sample audio file...")
        duration = 5  # 5 seconds
        sample_rate = 16000
        num_samples = duration * sample_rate

        # Create stereo audio with two distinct patterns
        audio = np.zeros((num_samples, 2), dtype=np.float32)

        # Channel 1: silence
        audio[:, 0] = 0

        # Channel 2: simple sine wave
        t = np.arange(num_samples) / sample_rate
        audio[:, 1] = 0.1 * np.sin(2 * np.pi * 440 * t)

        # Save to temporary file
        with tempfile.NamedTemporaryFile(
            suffix=".wav", delete=False
        ) as tmp_file:
            tmp_path = tmp_file.name

        sf.write(tmp_path, audio, sample_rate)
        logger.info(f"✓ Sample audio created: {tmp_path}")
        logger.info(f"  Duration: {duration}s, Sample rate: {sample_rate}Hz")

        # Run diarization
        logger.info("Running diarization...")
        try:
            segments = diarizer.diarize(tmp_path)

            logger.info(f"✓ Diarization completed")
            logger.info(f"  Detected {len(segments)} speaker segments")

            for i, seg in enumerate(segments, 1):
                logger.info(
                    f"    Segment {i}: Speaker '{seg.speaker}' "
                    f"from {seg.start:.2f}s to {seg.end:.2f}s"
                )

            # Clean up
            os.remove(tmp_path)
            return True

        except Exception as diarize_error:
            logger.error(f"✗ Diarization failed: {diarize_error}")
            os.remove(tmp_path)
            return False

    except Exception as e:
        logger.error(f"✗ Sample audio test failed: {e}")
        return False


def test_full_pipeline():
    """Test the full transcription pipeline with diarization."""
    logger.info("\n" + "=" * 70)
    logger.info("Testing Full Transcription Pipeline with Diarization")
    logger.info("=" * 70)

    try:
        sys.path.insert(0, str(Path(__file__).parent / "src"))

        from transcription.pipeline import OptimizedTranscriptionPipeline

        token = os.getenv("HUGGINGFACE_TOKEN")

        logger.info("Initializing pipeline with diarization enabled...")
        pipeline = OptimizedTranscriptionPipeline(
            model_size="tiny",  # Use smallest model for testing
            device="cpu",
            enable_diarization=True,
            diarization_model="pyannote/speaker-diarization",
            diarization_auth_token=token,
        )

        logger.info("✓ Pipeline initialized successfully")
        logger.info("  Configuration:")
        logger.info("    - Model: tiny")
        logger.info("    - Device: cpu")
        logger.info("    - Diarization: enabled")
        logger.info("    - Model: pyannote/speaker-diarization")

        return True

    except Exception as e:
        logger.error(f"✗ Pipeline initialization failed: {e}")
        logger.error(f"  Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    logger.info("Diarization Integration Test Suite\n")

    tests = [
        ("Environment Setup", test_environment),
        ("Diarizer Initialization", lambda: test_diarizer_initialization()),
        ("Full Pipeline", test_full_pipeline),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            if test_name == "Diarizer Initialization":
                success, diarizer = test_func()
                results[test_name] = success

                # If successful, run additional diarization test
                if success and diarizer:
                    logger.info("\nRunning diarization test...")
                    diarization_ok = test_diarizer_with_sample_audio(diarizer)
                    results["Diarization with Sample Audio"] = diarization_ok

            else:
                success = test_func()
                results[test_name] = success

        except Exception as e:
            logger.error(f"Test '{test_name}' crashed: {e}")
            results[test_name] = False

    # Print summary
    logger.info("\n" + "=" * 70)
    logger.info("TEST SUMMARY")
    logger.info("=" * 70)

    for test_name, success in results.items():
        symbol = "✓" if success else "✗"
        status = "PASS" if success else "FAIL"
        logger.info(f"{symbol} {test_name}: {status}")

    all_passed = all(results.values())

    logger.info("\n" + "=" * 70)
    if all_passed:
        logger.info("SUCCESS: All tests passed!")
        logger.info("Your Hugging Face token and diarization setup are working correctly.")
    else:
        logger.error("FAILURE: Some tests failed.")
        logger.error("Please check the error messages above for remediation steps.")
    logger.info("=" * 70)

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
