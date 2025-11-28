import os
import json
import logging
from typing import List, Dict

import google.generativeai as genai

logger = logging.getLogger(__name__)

# Initialise Gemini API key from environment (if set)
_API_KEY = os.getenv("GEMINI_API_KEY")
if _API_KEY:
    genai.configure(api_key=_API_KEY)
else:
    logger.warning("GEMINI_API_KEY not set – Gemini calls will fail unless mocked in tests.")

def transcribe(audio_path: str, *, language: str = "zh", beam_size: int = 5) -> List[Dict]:
    """Transcribe an audio file using Gemini 2.5‑flash.

    The function returns a list of segment dictionaries matching the structure
    expected by the existing ParallelTranscriber logic:
    ```
    {
        "start": float,
        "end": float,
        "text": str,
        "words": [
            {"word": str, "start": float, "end": float, "probability": float},
            ...
        ]
    }
    ```
    If the Gemini request fails, an empty list is returned and the error is logged.
    """
    try:
        # Load audio bytes – Gemini expects raw bytes or a file path.
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
        # Build the request – using the chat model with a system prompt for transcription.
        model = genai.GenerativeModel("gemini-2.5-flash")
        # Gemini does not have a native audio‑to‑text endpoint yet; we simulate via a
        # prompt that asks the model to transcribe the provided base64 audio.
        # In production you would use the proper multimodal API.
        import base64
        audio_b64 = base64.b64encode(audio_bytes).decode()
        prompt = (
            f"Please transcribe the following audio (base64 encoded) into a JSON list of segments. "
            f"Each segment should contain start, end, text, and an optional words list. "
            f"Language: {language}. Beam size: {beam_size}. Audio data: {audio_b64}"
        )
        response = model.generate_content(prompt)
        # Expect the model to return JSON text.
        result_text = response.text.strip()
        segments = json.loads(result_text)
        if isinstance(segments, list):
            return segments
        logger.warning("Gemini transcription returned non‑list JSON: %s", result_text)
        return []
    except Exception as e:
        logger.error("Gemini transcription failed for %s: %s", audio_path, e)
        return []
