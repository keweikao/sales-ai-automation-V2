"""
Speaker diarization using SpeechBrain embeddings and clustering.

This fallback approach extracts speaker embeddings for transcription
segments and clusters them into distinct speakers without requiring
gated models or external tokens.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import torch
import torchaudio
import huggingface_hub


logger = logging.getLogger(__name__)

if not hasattr(torchaudio, "set_audio_backend"):
    def _set_audio_backend_stub(name: str):  # type: ignore
        logger.debug("torchaudio.set_audio_backend stub used (%s)", name)

    torchaudio.set_audio_backend = _set_audio_backend_stub  # type: ignore

if not hasattr(torchaudio, "list_audio_backends"):
    def _list_audio_backends_stub():  # type: ignore
        logger.debug("torchaudio.list_audio_backends stub used")
        return ["soundfile"]

    torchaudio.list_audio_backends = _list_audio_backends_stub  # type: ignore


_original_hf_hub_download = huggingface_hub.hf_hub_download


def _hf_hub_download_compat(*args, use_auth_token=None, token=None, **kwargs):
    if token is None:
        token = use_auth_token
    return _original_hf_hub_download(*args, token=token, **kwargs)


huggingface_hub.hf_hub_download = _hf_hub_download_compat


@dataclass
class SpeakerSegment:
    """Represents a diarized speaker segment."""

    start: float
    end: float
    speaker: str


class EmbeddingClusterDiarizer:
    """Diarizer based on SpeechBrain speaker embeddings and clustering."""

    def __init__(
        self,
        max_speakers: int = 4,
        sample_rate: int = 16000,
        window_pad: float = 0.2,
    ):
        try:
            from speechbrain.pretrained import EncoderClassifier  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "speechbrain is required for embedding-based diarization. "
                "Install it with `pip install speechbrain`."
            ) from exc

        self.encoder = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir="pretrained_models/spkrec-ecapa-voxceleb",
        )
        self.max_speakers = max(1, max_speakers)
        self.sample_rate = sample_rate
        self.window_pad = window_pad

    def diarize(
        self,
        audio_path: str,
        transcript_segments: Optional[List[Dict]] = None,
    ) -> List[SpeakerSegment]:
        if not transcript_segments:
            raise RuntimeError(
                "EmbeddingClusterDiarizer requires transcript segments to infer speakers."
            )

        waveform, sr = torchaudio.load(audio_path)
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)

        if sr != self.sample_rate:
            waveform = torchaudio.functional.resample(
                waveform, orig_freq=sr, new_freq=self.sample_rate
            )
            sr = self.sample_rate

        embeddings = []
        segment_spans = []

        for segment in transcript_segments:
            start = max(0.0, float(segment["start"]) - self.window_pad)
            end = float(segment["end"]) + self.window_pad

            start_idx = int(start * sr)
            end_idx = int(end * sr)
            if end_idx <= start_idx:
                continue

            audio_slice = waveform[:, start_idx:end_idx]
            if audio_slice.numel() == 0:
                continue

            with torch.no_grad():
                embedding = self.encoder.encode_batch(audio_slice)
            embeddings.append(embedding.squeeze().cpu().numpy())
            segment_spans.append((float(segment["start"]), float(segment["end"])))

        if not embeddings:
            raise RuntimeError("Failed to extract embeddings for diarization.")

        labels = self._cluster_embeddings(np.vstack(embeddings))
        speaker_segments = self._build_speaker_segments(segment_spans, labels)

        logger.info(
            "Embedding diarization produced %d speaker segments across %d speakers",
            len(speaker_segments),
            len({seg.speaker for seg in speaker_segments}),
        )

        return speaker_segments

    def summarize(self, segments: List[SpeakerSegment]) -> List[Dict[str, float]]:
        summary: Dict[str, Dict[str, float]] = {}
        for segment in segments:
            duration = max(0.0, segment.end - segment.start)
            info = summary.setdefault(
                segment.speaker,
                {"speaker": segment.speaker, "duration": 0.0, "segment_count": 0},
            )
            info["duration"] += duration
            info["segment_count"] += 1

        return list(summary.values())

    def _cluster_embeddings(self, embeddings: np.ndarray) -> np.ndarray:
        from sklearn.cluster import AgglomerativeClustering
        from sklearn.metrics import silhouette_score

        if embeddings.shape[0] == 1:
            return np.array([0])

        best_k = 1
        best_score = -1.0

        max_k = min(self.max_speakers, embeddings.shape[0])
        for k in range(2, max_k + 1):
            clustering = AgglomerativeClustering(n_clusters=k)
            labels = clustering.fit_predict(embeddings)
            score = silhouette_score(embeddings, labels)
            if score > best_score:
                best_score = score
                best_k = k

        if best_k == 1:
            return np.zeros(embeddings.shape[0], dtype=int)

        clustering = AgglomerativeClustering(n_clusters=best_k)
        return clustering.fit_predict(embeddings)

    def _build_speaker_segments(
        self, spans: List[tuple], labels: np.ndarray
    ) -> List[SpeakerSegment]:
        speaker_map: Dict[int, str] = {}
        next_id = 1
        segments: List[SpeakerSegment] = []

        current_label: Optional[int] = None
        current_start = 0.0
        current_end = 0.0

        for (start, end), label in zip(spans, labels):
            if current_label is None:
                current_label = label
                current_start = start
                current_end = end
                continue

            if label == current_label and start <= current_end + 0.5:
                current_end = max(current_end, end)
            else:
                speaker_name = speaker_map.setdefault(
                    current_label, f"Speaker {next_id}"
                )
                if speaker_name == f"Speaker {next_id}":
                    speaker_map[current_label] = speaker_name
                    next_id += 1

                segments.append(
                    SpeakerSegment(start=current_start, end=current_end, speaker=speaker_name)
                )
                current_label = label
                current_start = start
                current_end = end

        if current_label is not None:
            speaker_name = speaker_map.setdefault(
                current_label, f"Speaker {next_id}"
            )
            segments.append(
                SpeakerSegment(start=current_start, end=current_end, speaker=speaker_name)
            )

        return segments
