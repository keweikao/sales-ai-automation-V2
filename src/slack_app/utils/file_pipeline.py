"""
Helpers for Slack audio ingestion: download from Slack, upload to GCS,
and enqueue Cloud Tasks for downstream processing.
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Optional

import requests
from google.cloud import storage, tasks_v2


def download_slack_file(file_info: dict, token: str) -> Path:
    """
    Download a Slack file to a temporary location.

    Args:
        file_info: Slack file metadata (expects `url_private` or `url_private_download`).
        token: Slack Bot token for authentication.

    Returns:
        Path to the downloaded temporary file.
    """
    download_url = file_info.get("url_private_download") or file_info.get("url_private")
    if not download_url:
        raise ValueError("Slack file metadata missing download URL")

    response = requests.get(
        download_url,
        headers={"Authorization": f"Bearer {token}"},
        stream=True,
        timeout=60,
    )
    response.raise_for_status()

    suffix = Path(file_info.get("name", "")).suffix or ".dat"
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)

    with temp_file as fp:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                fp.write(chunk)

    return Path(temp_file.name)


def upload_to_gcs(
    local_path: Path,
    bucket_name: str,
    destination_blob: str,
    storage_client: Optional[storage.Client] = None,
) -> str:
    """
    Upload a local file to GCS and return the gs:// URI.
    """
    client = storage_client or storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob)
    blob.upload_from_filename(str(local_path))

    return f"gs://{bucket_name}/{destination_blob}"


def enqueue_transcription_task(
    *,
    case_id: str,
    gcs_path: str,
    queue: str,
    location: str,
    project: str,
    handler_url: str,
    service_account_email: Optional[str] = None,
    tasks_client: Optional[tasks_v2.CloudTasksClient] = None,
) -> tasks_v2.types.Task:
    """
    Enqueue a Cloud Task to trigger transcription/analysis pipeline.
    """
    client = tasks_client or tasks_v2.CloudTasksClient()
    parent = client.queue_path(project, location, queue)

    payload = {
        "caseId": case_id,
        "gcsPath": gcs_path,
        "source": "slack",
    }

    http_request: dict = {
        "http_method": tasks_v2.HttpMethod.POST,
        "url": handler_url,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload).encode("utf-8"),
    }

    if service_account_email:
        http_request["oidc_token"] = {
            "service_account_email": service_account_email,
            "audience": handler_url,
        }

    task = {"http_request": http_request}
    return client.create_task(parent=parent, task=task)
