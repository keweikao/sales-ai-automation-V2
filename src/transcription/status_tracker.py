"""Utilities for persisting transcription progress to Firestore."""

from __future__ import annotations

import logging
from typing import Optional

from google.cloud import firestore

logger = logging.getLogger(__name__)


class TranscriptionStatusTracker:
    """Writes fine-grained transcription progress into Firestore."""

    def __init__(self, db: Optional[firestore.Client]):
        self._db = db

    def is_enabled(self) -> bool:
        return self._db is not None

    def update(
        self,
        *,
        case_id: Optional[str],
        file_id: Optional[str] = None,
        step: Optional[str] = None,
        detail: Optional[str] = None,
        progress: Optional[float] = None,
        total_chunks: Optional[int] = None,
        completed_chunks: Optional[int] = None,
        chunk_id: Optional[int] = None,
        chunk_status: Optional[str] = None,
        chunk_duration: Optional[float] = None,
        error: Optional[str] = None,
    ) -> None:
        if not self.is_enabled() or not case_id:
            return

        try:
            case_updates: dict = {
                "analysis.transcription.updatedAt": firestore.SERVER_TIMESTAMP,
            }
            if step:
                case_updates["analysis.transcription.step"] = step
            if detail:
                case_updates["analysis.transcription.detail"] = detail
            if progress is not None:
                case_updates["analysis.transcription.progress"] = progress
            if total_chunks is not None:
                case_updates["analysis.transcription.totalChunks"] = total_chunks
            if completed_chunks is not None:
                case_updates["analysis.transcription.completedChunks"] = completed_chunks
                if total_chunks:
                    case_updates["analysis.transcription.progress"] = completed_chunks / max(total_chunks, 1)
            if error:
                case_updates["analysis.transcription.error"] = error

            if chunk_id is not None:
                chunk_path = f"analysis.transcription.chunks.{chunk_id}"
                chunk_payload = {
                    "status": chunk_status or step,
                    "updatedAt": firestore.SERVER_TIMESTAMP,
                }
                if chunk_duration is not None:
                    chunk_payload["duration"] = chunk_duration
                case_updates[chunk_path] = chunk_payload

            self._db.collection("cases").document(case_id).set(case_updates, merge=True)

            if file_id:
                processed_updates = {
                    "updatedAt": firestore.SERVER_TIMESTAMP,
                }
                if step:
                    processed_updates["transcriptionStep"] = step
                if progress is not None:
                    processed_updates["transcriptionProgress"] = progress
                if total_chunks is not None:
                    processed_updates["transcriptionTotalChunks"] = total_chunks
                if completed_chunks is not None:
                    processed_updates["transcriptionCompletedChunks"] = completed_chunks
                if detail:
                    processed_updates["transcriptionDetail"] = detail
                if error:
                    processed_updates["error"] = error
                if chunk_id is not None:
                    processed_updates[f"transcriptionChunks.{chunk_id}"] = {
                        "status": chunk_status or step,
                        "updatedAt": firestore.SERVER_TIMESTAMP,
                        **({"duration": chunk_duration} if chunk_duration is not None else {}),
                    }

                self._db.collection("processed_files").document(file_id).set(processed_updates, merge=True)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Failed to update transcription status: %s", exc)

    def mark_failed(self, *, case_id: Optional[str], file_id: Optional[str], error: str) -> None:
        self.update(case_id=case_id, file_id=file_id, step="failed", error=error)

    def mark_completed(self, *, case_id: Optional[str], file_id: Optional[str]) -> None:
        self.update(case_id=case_id, file_id=file_id, step="completed", progress=1.0, detail="轉錄完成")
