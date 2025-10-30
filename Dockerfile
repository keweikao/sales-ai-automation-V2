FROM python:3.11-slim as base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/root/.local/bin:${PATH}"

WORKDIR /app

# System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg git build-essential && \
    rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY src/transcription/requirements.txt /tmp/transcription-requirements.txt
RUN pip install --user -r /tmp/transcription-requirements.txt && \
    rm /tmp/transcription-requirements.txt

# Copy application sources
COPY pyproject.toml /app/pyproject.toml
COPY src /app/src
COPY specs /app/specs
COPY scripts /app/scripts
COPY docker /app/docker

# Install specify CLI (optional but keeps entrypoints available)
RUN pip install --user -e .

# Ensure source tree is importable
ENV PYTHONPATH=/app/src

RUN chmod +x /app/docker/entrypoint.sh

# Default runtime configuration (override in deployment)
ENV WHISPER_MODEL_SIZE=tiny \
    WHISPER_DEVICE=cpu \
    WHISPER_COMPUTE_TYPE=int8 \
    VAD_PRESET=meeting \
    ENABLE_DIARIZATION=false \
    TRANSCRIBE_WORKERS=1

# Entrypoint handles warm-up then executes CMD
ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["python", "-m", "specify_cli"]
