"""
Shared utilities for Gemini-based analysis agents.

These helpers make it easy to load prompt templates, render conversational
context, call Gemini, and extract structured JSON responses. The goal is to
keep the individual agent implementations focused on domain-specific prompt
construction while centralising the boilerplate (model configuration, response
parsing, error handling).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover - runtime dependency
    genai = None  # type: ignore


JSON_CONTENT_TYPE = "application/json"
DEFAULT_MODEL_NAME = "gemini-2.0-flash-exp"
DEFAULT_TEMPERATURE = 0.2


class GeminiClientError(RuntimeError):
    """Raised when the Gemini response cannot be parsed as valid JSON."""


def format_timestamp(seconds: Optional[float]) -> str:
    """Format seconds as mm:ss (or ?? when unavailable)."""
    if seconds is None or seconds < 0:
        return "??:??"
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes:02d}:{secs:02d}"


def render_transcript(segments: Iterable[Dict[str, Any]]) -> str:
    """
    Convert transcript segments into a human-readable block.

    Expected keys in each segment:
      - start (seconds)
      - end (seconds)
      - speaker / speakerId
      - text
    """
    lines: List[str] = []
    for seg in segments:
        start = format_timestamp(seg.get("start"))
        end = format_timestamp(seg.get("end"))
        speaker = seg.get("speaker") or seg.get("speakerId") or "Speaker-Unknown"
        text = (seg.get("text") or "").strip()
        lines.append(f"[{start}-{end}] {speaker}: {text}")
    return "\n".join(lines).strip()


def extract_json_from_response(payload: str) -> Dict[str, Any]:
    """Locate the first JSON object in the payload and parse it."""
    start = payload.find("{")
    end = payload.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise GeminiClientError("未在模型回應中找到 JSON 物件。")

    snippet = payload[start : end + 1]
    try:
        return json.loads(snippet)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive path
        raise GeminiClientError(f"無法解析模型回應：{exc}") from exc


def _build_generation_config(
    temperature: float = DEFAULT_TEMPERATURE,
    response_mime_type: str = "text/plain",
) -> Any:
    """Create a GenerationConfig object if google-generativeai is installed."""
    if genai is None:
        raise GeminiClientError(
            "google-generativeai 套件未安裝，無法呼叫 Gemini 模型。"
        )
    return genai.types.GenerationConfig(
        temperature=temperature,
        candidate_count=1,
        response_mime_type=response_mime_type,
    )


def default_model_factory(
    model_name: str,
    temperature: float = DEFAULT_TEMPERATURE,
) -> Callable[[], Any]:
    """
    Create a callable that returns a configured GenerativeModel.

    The factory delays actual model instantiation until the returned callable
    is invoked, ensuring that environment configuration happens at runtime.
    """

    def _factory() -> Any:
        if genai is None:  # pragma: no cover - runtime dependency
            raise GeminiClientError(
                "google-generativeai 套件未安裝，無法呼叫 Gemini 模型。"
            )

        try:
            api_key = os.environ["GEMINI_API_KEY"]
        except KeyError as exc:  # pragma: no cover - requires runtime secret
            raise GeminiClientError("需要設定 GEMINI_API_KEY 環境變數。") from exc

        genai.configure(api_key=api_key)
        generation_config = _build_generation_config(temperature=temperature)
        return genai.GenerativeModel(
            model_name,
            generation_config=generation_config,
        )

    return _factory


@dataclass
class GeminiResponse:
    """Normalized response structure returned by GeminiJSONAgent."""

    data: Dict[str, Any]
    raw_text: str
    prompt: str
    model_name: str


class GeminiJSONAgent:
    """
    Base class for agents that prompt Gemini and expect JSON outputs.
    """

    def __init__(
        self,
        prompt_path: Path,
        model_name: str = DEFAULT_MODEL_NAME,
        temperature: float = DEFAULT_TEMPERATURE,
        model_factory: Optional[Callable[[], Any]] = None,
    ) -> None:
        self.prompt_template = Path(prompt_path).read_text(encoding="utf-8")
        self.model_name = model_name
        self._model_factory = model_factory or default_model_factory(
            model_name=model_name,
            temperature=temperature,
        )
        self._model: Optional[Any] = None

    def build_prompt(self, **kwargs: Any) -> str:  # pragma: no cover - abstract
        """Return the full prompt string. Subclasses must override."""
        raise NotImplementedError

    def _ensure_model(self) -> Any:
        if self._model is None:
            self._model = self._model_factory()
        return self._model

    def _generate(self, prompt: str) -> str:
        model = self._ensure_model()
        response = model.generate_content(prompt)

        # Primary path: response.text (Gemini SDK convenience property)
        text = getattr(response, "text", None)
        if text:
            return text.strip()

        # Fallback: concatenate candidate parts (handles streaming or alt shapes)
        candidates = getattr(response, "candidates", []) or []
        parts: List[str] = []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            if content is None:
                continue
            candidate_parts = getattr(content, "parts", None)
            if candidate_parts:
                for part in candidate_parts:
                    value = getattr(part, "text", None)
                    if value:
                        parts.append(value)
            else:
                value = getattr(content, "text", None)
                if value:
                    parts.append(value)

        if parts:
            return "\n".join(parts).strip()

        return str(response).strip()

    def invoke(self, **kwargs: Any) -> GeminiResponse:
        """Execute the agent and return parsed JSON alongside metadata."""
        prompt = self.build_prompt(**kwargs)
        raw_output = self._generate(prompt)
        data = extract_json_from_response(raw_output)
        return GeminiResponse(
            data=data,
            raw_text=raw_output,
            prompt=prompt,
            model_name=self.model_name,
        )
