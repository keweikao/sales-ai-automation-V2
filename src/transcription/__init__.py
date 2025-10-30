"""
Optimized Audio Transcription Module
"""

from .pipeline import OptimizedTranscriptionPipeline
from .vad.processor import VADProcessor
from .chunking.chunker import AudioChunker
from .parallel.transcriber import ParallelTranscriber
from .merging.merger import TranscriptionMerger

__all__ = [
    "OptimizedTranscriptionPipeline",
    "VADProcessor",
    "AudioChunker",
    "ParallelTranscriber",
    "TranscriptionMerger"
]

__version__ = "1.0.0"
