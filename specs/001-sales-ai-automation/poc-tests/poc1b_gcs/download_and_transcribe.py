#!/usr/bin/env python3
"""
POC 1b: Cloud Storage Audio Intake (Leads)
-----------------------------------------

Workflow:
1. List audio blobs from configured GCS bucket/prefix.
2. Download each blob to a local temp file.
3. Pass the file to the transcription pipeline.
4. Persist results with source metadata (`sourceType=leads`).
5. Move processed blobs to a `processed/` prefix (optional).

Usage:
  export GOOGLE_APPLICATION_CREDENTIALS=...
  export GCP_PROJECT_ID=sales-ai-automation-v2
  python download_and_transcribe.py \
      --bucket sales-ai-automation-leads-staging \
      --prefix incoming/leads/ \
      --limit 3 \
      --move-to processed/leads/
"""

import argparse
import json
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

from google.cloud import storage

# Re-use transcription pipeline (placeholder import; replace with actual module)
try:
    from src.transcription.pipeline import transcribe_file  # noqa: F401
except ImportError:
    # For local POC execution when package not installed
    def transcribe_file(audio_path: str, **kwargs):
        raise NotImplementedError("Import src.transcription.pipeline before running this script.")


@dataclass
class GCSConfig:
    bucket_name: str
    prefix: str
    move_to: Optional[str] = None
    limit: Optional[int] = None


def list_audio_blobs(client: storage.Client, config: GCSConfig) -> List[storage.Blob]:
    """List audio files under a prefix, limited by --limit."""
    blobs_iter = client.list_blobs(
        config.bucket_name,
        prefix=config.prefix,
    )
    candidates = []
    for blob in blobs_iter:
        if blob.name.endswith((".m4a", ".mp3", ".wav", ".flac")):
            candidates.append(blob)
        if config.limit and len(candidates) >= config.limit:
            break
    return candidates


def download_blob(blob: storage.Blob, destination: Path) -> float:
    """Download blob to destination, return elapsed seconds."""
    start = time.time()
    blob.download_to_filename(destination.as_posix())
    return time.time() - start


def process_blob(blob: storage.Blob, config: GCSConfig, output_dir: Path) -> dict:
    """Download, transcribe, and optionally move processed blob."""
    tmp_path = Path(tempfile.mkstemp(prefix="gcs_audio_", suffix=Path(blob.name).suffix)[1])
    download_time = download_blob(blob, tmp_path)

    result = {
        "gcsUri": f"gs://{config.bucket_name}/{blob.name}",
        "download_seconds": download_time,
        "transcription": None,
        "error": None,
        "sourceType": "leads",
    }

    try:
        transcription = transcribe_file(
            tmp_path.as_posix(),
            metadata={
                "sourceType": "leads",
                "gcsUri": result["gcsUri"],
            },
        )
        result["transcription"] = transcription
    except Exception as exc:  # noqa: BLE001
        result["error"] = str(exc)
    finally:
        tmp_path.unlink(missing_ok=True)

    # Move to processed prefix if configured & transcription succeeded
    if not result["error"] and config.move_to:
        destination_name = os.path.join(config.move_to.rstrip("/"), Path(blob.name).name)
        blob.bucket.copy_blob(blob, blob.bucket, destination_name)
        blob.delete()
        result["processedUri"] = f"gs://{config.bucket_name}/{destination_name}"

    return result


def main():
    parser = argparse.ArgumentParser(description="POC 1b – Download audio from GCS and transcribe")
    parser.add_argument("--bucket", default=os.getenv("GCS_AUDIO_BUCKET"), help="GCS bucket name")
    parser.add_argument("--prefix", default=os.getenv("GCS_AUDIO_PREFIX", ""), help="Prefix within the bucket")
    parser.add_argument("--move-to", help="Where to move processed blobs (prefix inside same bucket)")
    parser.add_argument("--limit", type=int, help="Limit number of files to process")
    parser.add_argument("--output", default="poc1b_results.json", help="Where to write summary output")

    args = parser.parse_args()
    if not args.bucket:
        parser.error("Bucket is required (use --bucket or set GCS_AUDIO_BUCKET)")

    config = GCSConfig(
        bucket_name=args.bucket,
        prefix=args.prefix,
        move_to=args.move_to,
        limit=args.limit,
    )

    client = storage.Client(project=os.getenv("GCP_PROJECT_ID"))
    blobs = list_audio_blobs(client, config)

    print(f"Found {len(blobs)} audio blobs under gs://{config.bucket_name}/{config.prefix}")
    results = []

    for blob in blobs:
        print(f"Processing {blob.name}...")
        outcome = process_blob(blob, config, Path(args.output).parent)
        status = "✅" if not outcome["error"] else f"❌ {outcome['error']}"
        print(f"   {status}")
        results.append(outcome)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nResults written to {args.output}")


if __name__ == "__main__":
    main()
