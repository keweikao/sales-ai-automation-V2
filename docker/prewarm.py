"""
Container warm-up helper.

Downloads and loads the Whisper model (and optional diarization models) so
Cloud Run instances are ready before serving traffic.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

import numpy as np
import soundfile as sf

from faster_whisper import WhisperModel

from transcription.diarization import create_diarizer

logger = logging.getLogger("warmup")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def _generate_silence(duration_sec: float = 2.0, sample_rate: int = 16000) -> Path:
    """Create a temporary WAV file containing silence."""
    samples = int(duration_sec * sample_rate)
    data = np.zeros((samples,), dtype=np.float32)
    fd, path = tempfile.mkstemp(suffix=".wav", prefix="warmup_", dir="/tmp")
    os.close(fd)
    sf.write(path, data, sample_rate)
    return Path(path)


def warmup_whisper():
    model_size = os.getenv("WHISPER_MODEL_SIZE", "tiny")
    compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
    device = os.getenv("WHISPER_DEVICE", "cpu")

    logger.info(
        "Loading Whisper model (size=%s, compute=%s, device=%s)…",
        model_size,
        compute_type,
        device,
    )
    model = WhisperModel(
        model_size,
        device=device,
        compute_type=compute_type,
    )

    silence_path = _generate_silence()
    try:
        logger.info("Running Whisper warm-up inference on silent audio…")
        list(model.transcribe(str(silence_path), beam_size=1))
        logger.info("Whisper warm-up complete.")
    finally:
        silence_path.unlink(missing_ok=True)


def warmup_diarizer():
    enable = os.getenv("ENABLE_DIARIZATION", "false").lower() == "true"
    if not enable:
        logger.info("Diarization warm-up skipped (ENABLE_DIARIZATION=false).")
        return

    token = os.getenv("HUGGINGFACE_TOKEN")
    allow_overlap = os.getenv("DIARIZATION_ALLOW_OVERLAP", "false").lower() == "true"

    logger.info("Loading diarization backend (overlap=%s)…", allow_overlap)
    diarizer = create_diarizer(
        use_auth_token=token,
        allow_overlap=allow_overlap,
    )

    if diarizer is None:
        logger.warning("Diarizer factory returned None; skipping warm-up.")
        return

    logger.info("Running diarizer warm-up with synthetic transcript segments…")
    silence_path = _generate_silence()
    mock_segments = [
        {"start": 0.0, "end": 1.0, "text": "warmup"},
        {"start": 1.0, "end": 2.0, "text": "placeholder"},
    ]
    try:
        diarizer.diarize(str(silence_path), transcript_segments=mock_segments)
        logger.info("Diarizer warm-up complete.")
    finally:
        silence_path.unlink(missing_ok=True)


def main():
    logger.info("==== Warm-up sequence started ====")
    try:
        warmup_whisper()
    except Exception as exc:  # pragma: no cover - warm-up best effort
        logger.exception("Whisper warm-up failed: %s", exc)

    try:
        warmup_diarizer()
    except Exception as exc:  # pragma: no cover
        logger.exception("Diarizer warm-up failed: %s", exc)

    logger.info("==== Warm-up sequence finished ====")


if __name__ == "__main__":
    main()
