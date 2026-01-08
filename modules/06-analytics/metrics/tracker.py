"""
Metrics tracker for service value measurement.

Tracks processing times, success rates, and engagement metrics.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from google.cloud import firestore

logger = logging.getLogger(__name__)


class MetricsTracker:
    """
    Tracks service metrics in Firestore.

    All metrics are stored under the `metrics` field in each case document.
    """

    def __init__(self, db: Optional[firestore.Client] = None):
        self._db = db

    def is_enabled(self) -> bool:
        return self._db is not None

    def _get_case_ref(self, case_id: str):
        """Get Firestore document reference for a case."""
        if not self._db:
            return None
        return self._db.collection("cases").document(case_id)

    # =========================================================================
    # Timestamp Tracking
    # =========================================================================

    def record_transcription_start(self, case_id: str) -> None:
        """Record when transcription begins."""
        if not self.is_enabled():
            return

        try:
            self._get_case_ref(case_id).set({
                "metrics": {
                    "timestamps": {
                        "transcriptionStartedAt": firestore.SERVER_TIMESTAMP,
                    }
                }
            }, merge=True)
            logger.debug(f"Recorded transcription start for {case_id}")
        except Exception as e:
            logger.warning(f"Failed to record transcription start: {e}")

    def record_transcription_complete(
        self,
        case_id: str,
        duration_seconds: Optional[float] = None,
        audio_duration_seconds: Optional[float] = None,
    ) -> None:
        """Record transcription completion with duration."""
        if not self.is_enabled():
            return

        try:
            update_data: Dict[str, Any] = {
                "metrics": {
                    "timestamps": {
                        "transcriptionCompletedAt": firestore.SERVER_TIMESTAMP,
                    }
                }
            }

            if duration_seconds is not None:
                update_data["metrics"]["durations"] = {
                    "transcriptionSeconds": duration_seconds,
                }

            if audio_duration_seconds is not None:
                update_data["metrics"]["audio"] = {
                    "durationSeconds": audio_duration_seconds,
                }

            self._get_case_ref(case_id).set(update_data, merge=True)
            logger.debug(f"Recorded transcription complete for {case_id}: {duration_seconds}s")
        except Exception as e:
            logger.warning(f"Failed to record transcription complete: {e}")

    def record_analysis_start(self, case_id: str) -> None:
        """Record when analysis begins."""
        if not self.is_enabled():
            return

        try:
            self._get_case_ref(case_id).set({
                "metrics": {
                    "timestamps": {
                        "analysisStartedAt": firestore.SERVER_TIMESTAMP,
                    }
                }
            }, merge=True)
            logger.debug(f"Recorded analysis start for {case_id}")
        except Exception as e:
            logger.warning(f"Failed to record analysis start: {e}")

    def record_analysis_complete(
        self,
        case_id: str,
        duration_seconds: float,
        agent_durations: Optional[Dict[str, float]] = None,
        success: bool = True,
    ) -> None:
        """Record analysis completion with duration and agent metrics."""
        if not self.is_enabled():
            return

        try:
            update_data: Dict[str, Any] = {
                "metrics": {
                    "timestamps": {
                        "analysisCompletedAt": firestore.SERVER_TIMESTAMP,
                    },
                    "durations": {
                        "analysisSeconds": duration_seconds,
                    },
                    "analysisSuccess": success,
                }
            }

            if agent_durations:
                update_data["metrics"]["agents"] = {
                    agent_id: {"durationSeconds": dur}
                    for agent_id, dur in agent_durations.items()
                }

            self._get_case_ref(case_id).set(update_data, merge=True)
            logger.debug(f"Recorded analysis complete for {case_id}: {duration_seconds}s")
        except Exception as e:
            logger.warning(f"Failed to record analysis complete: {e}")

    def record_total_processing_time(
        self,
        case_id: str,
        total_seconds: float,
    ) -> None:
        """Record total end-to-end processing time."""
        if not self.is_enabled():
            return

        try:
            self._get_case_ref(case_id).set({
                "metrics": {
                    "durations": {
                        "totalProcessingSeconds": total_seconds,
                    }
                }
            }, merge=True)
            logger.debug(f"Recorded total processing time for {case_id}: {total_seconds}s")
        except Exception as e:
            logger.warning(f"Failed to record total processing time: {e}")

    # =========================================================================
    # Audio Metrics
    # =========================================================================

    def record_audio_metadata(
        self,
        case_id: str,
        duration_seconds: Optional[float] = None,
        file_size_bytes: Optional[int] = None,
    ) -> None:
        """Record audio file metadata."""
        if not self.is_enabled():
            return

        try:
            update_data: Dict[str, Any] = {"metrics": {"audio": {}}}

            if duration_seconds is not None:
                update_data["metrics"]["audio"]["durationSeconds"] = duration_seconds

            if file_size_bytes is not None:
                update_data["metrics"]["audio"]["fileSizeBytes"] = file_size_bytes

            self._get_case_ref(case_id).set(update_data, merge=True)
            logger.debug(f"Recorded audio metadata for {case_id}")
        except Exception as e:
            logger.warning(f"Failed to record audio metadata: {e}")

    # =========================================================================
    # Agent Metrics
    # =========================================================================

    def record_agent_execution(
        self,
        case_id: str,
        agent_id: str,
        duration_seconds: float,
        success: bool,
        retry_count: int = 0,
    ) -> None:
        """Record individual agent execution metrics."""
        if not self.is_enabled():
            return

        try:
            self._get_case_ref(case_id).set({
                "metrics": {
                    "agents": {
                        agent_id: {
                            "durationSeconds": duration_seconds,
                            "success": success,
                            "retryCount": retry_count,
                        }
                    }
                }
            }, merge=True)
            logger.debug(f"Recorded {agent_id} metrics for {case_id}")
        except Exception as e:
            logger.warning(f"Failed to record agent execution: {e}")

    # =========================================================================
    # Batch Update
    # =========================================================================

    def record_full_metrics(
        self,
        case_id: str,
        metrics_data: Dict[str, Any],
    ) -> None:
        """Record complete metrics data in a single update."""
        if not self.is_enabled():
            return

        try:
            self._get_case_ref(case_id).set({
                "metrics": metrics_data,
            }, merge=True)
            logger.info(f"Recorded full metrics for {case_id}")
        except Exception as e:
            logger.warning(f"Failed to record full metrics: {e}")

    # =========================================================================
    # Calculate Derived Metrics
    # =========================================================================

    def calculate_and_store_total_time(self, case_id: str) -> Optional[float]:
        """
        Calculate total processing time from stored timestamps.

        Returns the total time in seconds, or None if not calculable.
        """
        if not self.is_enabled():
            return None

        try:
            doc = self._get_case_ref(case_id).get()
            if not doc.exists:
                return None

            data = doc.to_dict() or {}
            metrics = data.get("metrics", {})
            timestamps = metrics.get("timestamps", {})

            # Get start time (use createdAt as fallback)
            start_time = timestamps.get("transcriptionStartedAt") or data.get("createdAt")
            end_time = timestamps.get("analysisCompletedAt")

            if not start_time or not end_time:
                return None

            # Calculate total seconds
            if isinstance(start_time, datetime) and isinstance(end_time, datetime):
                total_seconds = (end_time - start_time).total_seconds()
                self.record_total_processing_time(case_id, total_seconds)
                return total_seconds

            return None
        except Exception as e:
            logger.warning(f"Failed to calculate total time: {e}")
            return None
