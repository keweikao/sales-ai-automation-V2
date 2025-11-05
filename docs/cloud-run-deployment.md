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
| `MODEL_SIZE` | `medium` | Faster-Whisper weights (`tiny`, `base`, `small`, `medium`, `large-v3`) |
| `DEVICE` | `cpu` | Execution device (`cpu` or `cuda`) |
| `COMPUTE_TYPE` | `int8` | Precision mode (`int8`, `float16`, `float32`) |
| `MAX_WORKERS` | `3` | Parallel chunk workers (increase to 6 on ≥8 CPU) |
| `TARGET_CHUNK_DURATION` | `600` | Target chunk length in seconds (default 10 分鐘) |
| `OVERLAP_DURATION` | `2` | Overlap between chunks in seconds |
| `VAD_PRESET` | `meeting` | VAD preset (`meeting`, `presentation`, `noisy`) |
| `TRANSCRIPTION_LANGUAGE` | `zh` | Primary language hint passed to Whisper |
| `ENABLE_DIARIZATION` | `false` | Enable speaker diarization post-processing |
| `DIARIZATION_MODEL` | `pyannote/speaker-diarization` | Hugging Face model id |
| `DIARIZATION_ALLOW_OVERLAP` | `false` | Keep overlapping speakers if model supports it |
| `HUGGINGFACE_TOKEN` | *(secret)* | Token for pyannote model downloads (store in Secret Manager) |

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
  --set-env-vars=MODEL_SIZE=medium,COMPUTE_TYPE=int8,DEVICE=cpu \
  --set-env-vars=MAX_WORKERS=6,VAD_PRESET=meeting,TARGET_CHUNK_DURATION=600 \
  --set-env-vars=ENABLE_DIARIZATION=true,DIARIZATION_MODEL=pyannote/speaker-diarization \
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

## Quality Metrics (FR-010)

每次轉錄完成後，服務會回傳 `quality` 欄位，內容包含：

- `score`：整體品質分數（0-100）
- `language_confidence`：語言偵測信心（平均 chunk 機率）
- `coherence`：平均段落長度與一致性
- `char_time_ratio`：每秒字數（合理範圍 2-4 字/秒）
- `repetition`：重複段落比例
- `speaker_separation`：說話者標註覆蓋率（啟用 diarization 時）

建議在 Cloud Logging / Monitoring 建立儀表板或警報，當品質分數低於門檻（如 85 分）時通知維運與產品負責人。

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
