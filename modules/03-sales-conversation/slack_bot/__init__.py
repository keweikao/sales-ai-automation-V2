"""
Slack bot for sales conversation module.

Migration note: From src/slack_app/

Handles:
- File upload and processing trigger
- Interactive message responses
- Summary editing workflow
- Customer summary delivery
"""

from .interactions import SummaryEditor, SummarySender
from .utils import download_slack_file, upload_to_gcs, enqueue_transcription_task

__all__ = [
    # Interactions
    "SummaryEditor",
    "SummarySender",
    # Utils
    "download_slack_file",
    "upload_to_gcs",
    "enqueue_transcription_task",
]
