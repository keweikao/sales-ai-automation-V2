"""
Slack audio source handler.

Downloads audio files from Slack.
"""

import tempfile
import httpx


class SlackAudioSource:
    """Handler for audio files shared in Slack."""

    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.headers = {"Authorization": f"Bearer {bot_token}"}

    async def download(self, file_url: str) -> str:
        """
        Download audio file from Slack.

        Args:
            file_url: Slack private file URL

        Returns:
            Local path to downloaded file
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                file_url,
                headers=self.headers,
                follow_redirects=True,
            )
            response.raise_for_status()

            # Determine extension from content type
            content_type = response.headers.get("content-type", "")
            ext = self._get_extension(content_type)

            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}")
            temp_file.write(response.content)
            temp_file.close()

            return temp_file.name

    async def get_file_info(self, file_id: str) -> dict:
        """
        Get file metadata from Slack.

        Args:
            file_id: Slack file ID

        Returns:
            File info dict
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://slack.com/api/files.info",
                headers=self.headers,
                params={"file": file_id},
            )
            data = response.json()

            if not data.get("ok"):
                raise Exception(f"Slack API error: {data.get('error')}")

            return data.get("file", {})

    def _get_extension(self, content_type: str) -> str:
        """Map content type to file extension."""
        mapping = {
            "audio/mp4": "m4a",
            "audio/x-m4a": "m4a",
            "audio/mpeg": "mp3",
            "audio/wav": "wav",
            "audio/webm": "webm",
            "audio/ogg": "ogg",
        }
        return mapping.get(content_type, "mp3")
