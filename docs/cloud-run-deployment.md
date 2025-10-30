# Cloud Run Deployment Guide

This guide captures the recommended configuration for running the
transcription pipeline on Google Cloud Run with predictable performance
and reasonable cost.

## Container Image

1. Build the image locally (or in CI):

   ```bash
   docker build -t gcr.io/PROJECT_ID/sales-ai-transcriber:latest .
   ```

2. Push to Artifact Registry / Container Registry:

   ```bash
   docker push gcr.io/PROJECT_ID/sales-ai-transcriber:latest
   ```

### Required Runtime Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WHISPER_MODEL_SIZE` | `tiny` | Whisper weights to load (`tiny`, `small`, `medium`…) |
| `WHISPER_DEVICE` | `cpu` | Execution device (`cpu` or `cuda`) |
| `WHISPER_COMPUTE_TYPE` | `int8` | Compute precision (`int8`, `float16`, `float32`) |
| `VAD_PRESET` | `meeting` | VAD configuration preset |
| `TRANSCRIBE_WORKERS` | `1` | Worker count passed to the transcription pipeline |
| `ENABLE_DIARIZATION` | `false` | Enable speaker diarization warm-up |
| `HUGGINGFACE_TOKEN` | _(secret)_ | Token required for pyannote models (store in Secret Manager) |
| `DIARIZATION_ALLOW_OVERLAP` | `false` | Whether diarization keeps overlapping speakers |

## Recommended Cloud Run Settings

| Setting | Suggested Value | Notes |
|---------|-----------------|-------|
| **CPU / RAM** | `--cpu=4 --memory=8Gi` | Enough headroom for medium Whisper + diarization |
| **Concurrency** | `--concurrency=1` | Prevents multiple long jobs competing for memory |
| **Min Instances** | `--min-instances=1` | Keeps a warm container ready, avoids cold start |
| **CPU Allocation** | `--cpu-boost` (Always Allocated) | Ensures CPU available even when idle |
| **Max Instances** | `--max-instances=N` | Scale horizontally based on expected peak load |
| **Execution Env** | `--execution-environment=gen2` | Faster startup and latest CPU platforms |

### Example Deploy Command

```bash
gcloud run deploy sales-ai-transcriber \
  --image=gcr.io/PROJECT_ID/sales-ai-transcriber:latest \
  --region=us-central1 \
  --platform=managed \
  --cpu=4 \
  --memory=8Gi \
  --concurrency=1 \
  --min-instances=1 \
  --max-instances=10 \
  --cpu-boost \
  --execution-environment=gen2 \
  --set-env-vars=WHISPER_MODEL_SIZE=medium,WHISPER_COMPUTE_TYPE=int8 \
  --set-env-vars=TRANSCRIBE_WORKERS=1,VAD_PRESET=meeting \
  --set-secrets=HUGGINGFACE_TOKEN=projects/PROJECT_NUM/secrets/pyannote-token:latest
```

Replace `PROJECT_ID` / `PROJECT_NUM` / region as needed.

## Warm-up Behaviour

The container’s entrypoint runs `docker/prewarm.py` before executing the
main command:

1. Downloads (if necessary) and loads the Whisper model.
2. Executes a short silent inference to populate runtime caches.
3. Optionally loads the diarization backend (pyannote or fallback) when
   `ENABLE_DIARIZATION=true`.

Warm-up failures are logged but do **not** stop the container. Review
Cloud Logging for warnings about missing tokens or model downloads.

## Verification Checklist

1. **Local Test**: `docker run --rm -p 8080:8080 gcr.io/... /bin/bash` to
   ensure warm-up completes and the desired command starts.
2. **Staging Cloud Run**: Deploy to a staging service, run POC1 tests
   (including `--diarization`) using the same audio samples to confirm
   performance matches expectations.
3. **Monitoring**: Add dashboards for CPU, memory, request latency,
   warm-up duration, and transcription success rate.
4. **Autoscaling Policy**: Adjust `--max-instances` and Cloud Tasks /
   Pub/Sub throttling to match expected workload.
