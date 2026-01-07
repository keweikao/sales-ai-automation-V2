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
        timeout=300,
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
    max_retries: int = 3,
) -> str:
    """
    Upload a local file to GCS and return the gs:// URI.
    
    Uses resumable upload with retry logic to handle SSL errors.
    """
    import logging
    import time
    from google.api_core import retry as api_retry
    from google.api_core import exceptions as api_exceptions
    
    logger = logging.getLogger(__name__)
    
    # Create a fresh client for each upload to avoid connection pooling issues
    client = storage_client or storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob)
    
    file_size = local_path.stat().st_size
    logger.info(f"Uploading {local_path.name} ({file_size / 1024 / 1024:.2f} MB) to gs://{bucket_name}/{destination_blob}")
    
    # Retry configuration for transient errors
    retry_errors = (
        api_exceptions.ServiceUnavailable,
        api_exceptions.GatewayTimeout,
        api_exceptions.InternalServerError,
        ConnectionError,
        TimeoutError,
    )
    
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Upload attempt {attempt}/{max_retries}")
            
            # Use resumable upload for large files (>8MB is automatic)
            # Set num_retries for internal resumable upload retries
            blob.upload_from_filename(
                str(local_path),
                timeout=900,
                num_retries=3,  # Built-in retries for resumable upload chunks
            )
            
            logger.info(f"Upload successful on attempt {attempt}")
            return f"gs://{bucket_name}/{destination_blob}"
            
        except Exception as e:
            last_error = e
            error_type = type(e).__name__
            logger.warning(f"Upload attempt {attempt} failed: {error_type}: {str(e)[:200]}")
            
            # Check if error is retryable
            is_ssl_error = "SSL" in str(type(e).__mro__) or "SSL" in str(e)
            is_connection_error = isinstance(e, retry_errors) or is_ssl_error
            
            if attempt < max_retries and is_connection_error:
                wait_time = 2 ** attempt  # Exponential backoff: 2, 4, 8 seconds
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                
                # Create fresh client to get new connection
                client = storage.Client()
                bucket = client.bucket(bucket_name)
                blob = bucket.blob(destination_blob)
            else:
                raise
    
    raise last_error


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
    file_id: Optional[str] = None,
) -> tasks_v2.types.Task:
    """
    Enqueue a Cloud Task to trigger transcription/analysis pipeline.

    Args:
        case_id: Firestore case identifier.
        gcs_path: gs:// URI pointing to uploaded audio.
        file_id: Optional Slack file ID for progress tracking.
        ... (other params unchanged)
    """
    import logging
    import sys
    logger = logging.getLogger(__name__)

    logger.info("Creating Cloud Tasks client...")
    sys.stdout.flush()
    client = tasks_client or tasks_v2.CloudTasksClient()

    logger.info("Building queue path: project=%s, location=%s, queue=%s", project, location, queue)
    sys.stdout.flush()
    parent = client.queue_path(project, location, queue)
    logger.info("Queue path: %s", parent)
    sys.stdout.flush()

    payload = {
        "caseId": case_id,
        "gcs_uri": gcs_path,  # Use gcs_uri as expected by transcription service
        "gcsPath": gcs_path,  # Also include gcsPath for backwards compatibility
        "source": "slack",
    }
    if file_id:
        payload["fileId"] = file_id
    logger.info("Task payload: %s", payload)
    sys.stdout.flush()

    http_request: dict = {
        "http_method": tasks_v2.HttpMethod.POST,
        "url": handler_url,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload).encode("utf-8"),
    }

    if service_account_email:
        logger.info("Adding OIDC token with service account: %s", service_account_email)
        sys.stdout.flush()
        http_request["oidc_token"] = {
            "service_account_email": service_account_email,
            "audience": handler_url,
        }

    task = {
        "http_request": http_request,
        # Set dispatch deadline to 30 minutes for long audio transcription
        "dispatch_deadline": {"seconds": 1800},  # 30 minutes
    }
    logger.info("Creating task in queue: %s (timeout: 30 min)", parent)
    sys.stdout.flush()

    try:
        response = client.create_task(parent=parent, task=task)
        logger.info("Task created successfully: %s", response.name)
        sys.stdout.flush()
        return response
    except Exception as e:
        logger.error("Failed to create task: %s", e, exc_info=True)
        sys.stdout.flush()
        raise
