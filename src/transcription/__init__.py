"""
Optimized Audio Transcription Module
"""

# We do NOT import submodules here to prevent eager loading of heavy dependencies (like torch/whisper)
# when they are not needed (e.g. when using Gemini engine).

__version__ = "1.0.0"
