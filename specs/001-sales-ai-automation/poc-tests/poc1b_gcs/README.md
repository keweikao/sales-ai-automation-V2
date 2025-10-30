# POC 1b – Cloud Storage Audio Intake (Leads)

## Purpose
Verify that we can ingest audio recordings stored in Google Cloud Storage buckets, download them efficiently, hand them off to the existing transcription pipeline, and tag the resulting opportunities as **leads**. This complements POC 1 (Slack uploads → opportunity) by covering the second ingestion path required in the architecture.

## Questions To Answer
1. Can we list and download audio files from a designated GCS bucket within acceptable latency (per-file download <30 s for ~50 MB audio)?
2. Does the transcription pipeline (same as POC 1) succeed when fed with locally downloaded blobs?
3. Are metadata tags applied correctly (`sourceType: leads`, references to original `gcsUri`)?
4. Failure handling: corrupt files, missing metadata, network hiccups.

## Success Criteria
| Metric | Target |
|--------|--------|
| Audio fetch latency | ≤ 30 s per 50 MB file |
| Transcription success rate | ≥ 95% on test batch |
| Source tagging | Every transcript stored with `sourceType=leads` and original `gcsUri` |
| Error handling | Retries for transient errors, clear logs for permanent failures |

## Test Data
- Create a staging bucket, e.g. `gs://sales-ai-automation-leads-staging`.
- Upload 3–5 sample `.m4a` files (~10–50 MB), plus a deliberately corrupted file to test error handling.
- Optional: include metadata object (JSON) alongside each audio blob for customer identifiers.

## Steps Overview
1. List candidate objects via `google.cloud.storage`.
2. Filter by prefix/suffix (e.g. only `.m4a` under `incoming/leads/`).
3. Download to temp directory.
4. Call transcription pipeline (`transcription.pipeline.transcribe_file`).
5. Persist results with metadata (`sourceType=leads`, `opportunityStage=lead`, `gcsUri`, etc.).
6. Move processed file to `processed/` prefix or delete after success.
7. Record outcomes in `poc1b_results.json` (per-file latency, success/failure, error message).

## Required Setup
- **GCP Project**: same as main project (`sales-ai-automation-v2`).
- **Credentials**: service account with `storage.objectAdmin` (for tests) or read-only + write to processed path.
- Env vars:
  ```bash
  export GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa.json
  export GCP_PROJECT_ID=sales-ai-automation-v2
  export GCS_AUDIO_BUCKET=sales-ai-automation-leads-staging
  export GCS_AUDIO_PREFIX=incoming/leads/
  ```

## Deliverables
- `download_and_transcribe.py`: CLI script performing steps above.
- `poc1b_results.json`: summary metrics.
- Updated documentation in `docs/cloud-run-deployment.md` or spec/plan as needed.

## Extensions (Later Phases)
- Integrate with Cloud Tasks for scheduled polling.
- Add Pub/Sub trigger when new blob arrives.
- Support streaming transcode if raw format is not Whisper-friendly.
