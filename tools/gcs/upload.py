"""
Tool: gcs_upload
Category: gcs
Version: 1.0.0
Description: Upload a file to Google Cloud Storage.

# derived from Google Cloud official doc (2025)
"""

from google.cloud import storage
from typing import Dict, Any

def upload(
    bucket_name: str,
    source_file_name: str,
    destination_blob_name: str,
) -> Dict[str, Any]:
    """
    Uploads a file to the specified GCS bucket.

    Args:
        bucket_name: The name of the GCS bucket.
        source_file_name: The path to the file to upload.
        destination_blob_name: The name of the blob in the bucket.

    Returns:
        A dictionary with the status of the upload.
    """

    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)

        blob.upload_from_filename(source_file_name)

        return {
            "status": "success",
            "bucket_name": bucket_name,
            "destination_blob_name": destination_blob_name,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }
