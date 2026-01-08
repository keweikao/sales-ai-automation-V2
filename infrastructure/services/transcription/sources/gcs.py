"""
GCS audio source handler.

Downloads audio files from Google Cloud Storage.
"""

import tempfile
from typing import Optional
from google.cloud import storage


class GCSAudioSource:
    """Handler for audio files stored in GCS."""

    def __init__(self, project: Optional[str] = None):
        self.client = storage.Client(project=project)

    async def download(self, bucket_name: str, blob_path: str) -> str:
        """
        Download audio file from GCS to local temp file.

        Args:
            bucket_name: GCS bucket name
            blob_path: Path to blob in bucket

        Returns:
            Local path to downloaded file
        """
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(blob_path)

        # Determine file extension
        ext = blob_path.split(".")[-1] if "." in blob_path else "mp3"
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}")

        blob.download_to_filename(temp_file.name)
        return temp_file.name

    async def get_signed_url(
        self,
        bucket_name: str,
        blob_path: str,
        expiration_minutes: int = 60,
    ) -> str:
        """
        Get a signed URL for direct access to the audio.

        Args:
            bucket_name: GCS bucket name
            blob_path: Path to blob
            expiration_minutes: URL expiration time

        Returns:
            Signed URL string
        """
        from datetime import timedelta

        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(blob_path)

        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=expiration_minutes),
            method="GET",
        )
        return url

    def parse_gcs_uri(self, gcs_uri: str) -> tuple[str, str]:
        """
        Parse gs:// URI into bucket and path.

        Args:
            gcs_uri: URI like gs://bucket/path/to/file.mp3

        Returns:
            Tuple of (bucket_name, blob_path)
        """
        if not gcs_uri.startswith("gs://"):
            raise ValueError(f"Invalid GCS URI: {gcs_uri}")

        path = gcs_uri[5:]  # Remove "gs://"
        parts = path.split("/", 1)

        if len(parts) != 2:
            raise ValueError(f"Invalid GCS URI format: {gcs_uri}")

        return parts[0], parts[1]
