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
    import vertexai
    from vertexai.generative_models import GenerationConfig, GenerativeModel
except ImportError:  # pragma: no cover - runtime dependency
    vertexai = None  # type: ignore
    GenerativeModel = None  # type: ignore
    GenerationConfig = None  # type: ignore

try:
    import google.generativeai as genai
except ImportError:
    genai = None  # type: ignore


JSON_CONTENT_TYPE = "application/json"
DEFAULT_MODEL_NAME = "gemini-1.0-pro"
DEFAULT_TEMPERATURE = 0.2
GCP_PROJECT = os.environ.get("GCP_PROJECT", "sales-ai-automation-v2")
GCP_LOCATION = os.environ.get("GCP_LOCATION", "asia-east1")


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


def parse_dual_mode_output(output: str) -> tuple[str, Dict[str, Any]]:
    """
    Parse dual-mode output into human-readable report and JSON data.
    
    Expected format:
        [Human-readable report in Traditional Chinese]
        <JSON>
        {...}
        </JSON>
    
    Returns:
        tuple: (report_text, json_data)
    
    Raises:
        GeminiClientError: If JSON block is not found or invalid
    """
    import re
    
    # Extract JSON block wrapped in <JSON>...</JSON> tags
    json_pattern = r'<JSON>(.*?)</JSON>'
    json_match = re.search(json_pattern, output, re.DOTALL | re.IGNORECASE)
    
    if not json_match:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"No <JSON> block found in output. Preview: {output[:500]!r}")
        raise GeminiClientError("未在模型回應中找到 <JSON>...</JSON> 標籤。")
    
    # Extract and parse JSON
    json_str = json_match.group(1).strip()
    try:
        json_data = json.loads(json_str, strict=False)
    except json.JSONDecodeError as exc:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"JSON decode error. JSON string: {json_str[:500]!r}")
        raise GeminiClientError(f"無法解析 JSON 區塊：{exc}") from exc
    
    # Extract report (everything before <JSON> tag)
    report_text = output[:json_match.start()].strip()
    
    return report_text, json_data


def extract_json_from_response(payload: str) -> Dict[str, Any]:
    """
    Locate and parse JSON from the payload, handling markdown blocks and common errors.
    
    This function now supports both legacy format (markdown JSON blocks) and 
    new dual-mode format (<JSON>...</JSON> tags). It will try dual-mode first.
    """
    import re
    
    # Try dual-mode format first
    try:
        _, json_data = parse_dual_mode_output(payload)
        return json_data
    except GeminiClientError:
        # Fall back to legacy format
        pass
    
    # 1. Try to find markdown JSON block
    json_block_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
    match = re.search(json_block_pattern, payload, re.DOTALL)
    
    if match:
        snippet = match.group(1)
    else:
        # 2. Fallback: Locate the first outer-most JSON object
        start = payload.find("{")
        end = payload.rfind("}")
        
        if start == -1 or end == -1 or end <= start:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to find JSON in response. Payload preview: {payload[:500]!r}")
            raise GeminiClientError("未在模型回應中找到 JSON 物件。")
            
        snippet = payload[start : end + 1]

    # 3. Parse with error handling and sanitization
    try:
        # strict=False allows control characters like newlines in strings
        return json.loads(snippet, strict=False)
    except json.JSONDecodeError:
        # 4. Retry with sanitization (escape unescaped newlines inside strings)
        try:
            # This is a naive heuristic: replace actual newlines with \n
            # It might break if the JSON is pretty-printed, so we only do it if normal parse fails
            sanitized = snippet.replace('\n', '\\n')
            return json.loads(sanitized, strict=False)
        except json.JSONDecodeError as exc:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"JSON decode error. Snippet: {snippet[:500]!r}")
            raise GeminiClientError(f"無法解析模型回應：{exc}") from exc


def _build_generation_config(
    temperature: float = DEFAULT_TEMPERATURE,
    response_mime_type: str = "text/plain",
) -> Any:
    """Create a GenerationConfig object if google-cloud-aiplatform is installed."""
    if GenerationConfig is None:
        raise GeminiClientError(
            "google-cloud-aiplatform 套件未安裝，無法呼叫 Gemini 模型。"
        )
    # Note: response_mime_type is not a direct param in Vertex AI's GenerationConfig
    return GenerationConfig(
        temperature=temperature,
        candidate_count=1,
    )


def default_model_factory(
    model_name: str,
    temperature: float = DEFAULT_TEMPERATURE,
) -> Callable[[], Any]:
    """
    Create a callable that returns a configured GenerativeModel.

    Tries Vertex AI first, falls back to Google Generative AI SDK with API key.
    """

    def _factory() -> Any:
        # Try Vertex AI first
        if vertexai is not None and GenerativeModel is not None:
            try:
                vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION)
                generation_config = _build_generation_config(temperature=temperature)
                return GenerativeModel(
                    model_name,
                    generation_config=generation_config,
                )
            except Exception as e:
                # Vertex AI failed, try fallback
                import logging
                logging.warning(f"Vertex AI initialization failed: {e}, falling back to genai SDK")

        # Fallback to Google Generative AI SDK with API key
        if genai is not None:
            api_key = os.environ.get("GEMINI_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                # Map model names if needed
                fallback_model = model_name.replace("gemini-1.5-flash-001", "gemini-1.5-flash")
                return genai.GenerativeModel(fallback_model)

        raise GeminiClientError(
            "無法初始化 Gemini 模型（Vertex AI 和 API Key 方式都失敗）"
        )

    return _factory


@dataclass
class GeminiResponse:
    """Normalized response structure returned by GeminiJSONAgent."""

    data: Dict[str, Any]
    raw_text: str
    prompt: str
    model_name: str
    report: Optional[str] = None  # Human-readable report (for dual-mode output)


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
        import logging
        logger = logging.getLogger(__name__)

        model = self._ensure_model()

        try:
            response = model.generate_content(prompt)
        except Exception as e:
            # If Vertex AI fails with 404 (Not Found) or 403 (Permission Denied), try fallback to genai SDK
            error_str = str(e)
            if ("404" in error_str or "403" in error_str or "PermissionDenied" in error_str) and genai is not None:
                logger.warning(f"Vertex AI failed with {error_str}, trying genai SDK fallback...")
                api_key = os.environ.get("GEMINI_API_KEY")
                if api_key:
                    genai.configure(api_key=api_key)
                    # Map Vertex AI model names to Gemini API model names
                    model_mapping = {
                        "gemini-2.0-flash-exp": "gemini-2.0-flash-exp",
                        "gemini-1.5-flash": "gemini-1.5-flash",
                        "gemini-2.5-flash": "gemini-1.5-flash", # Fallback mapping
                        "gemini-2.5-pro": "gemini-1.5-pro",     # Fallback mapping
                    }
                    # Use the exact model name first, then try mapping, then default
                    fallback_model = model_mapping.get(self.model_name, self.model_name)
                    
                    logger.info(f"Using genai SDK with model: {fallback_model}")
                    model = genai.GenerativeModel(fallback_model)
                    self._model = model  # Cache the fallback model
                    response = model.generate_content(prompt)
                    logger.info(f"✅ Successfully used genai SDK with model: {fallback_model}")
                else:
                    logger.error("GEMINI_API_KEY not found in environment variables.")
                    raise
            else:
                raise

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
        
        # Try to parse as dual-mode output first
        report_text = None
        try:
            report_text, data = parse_dual_mode_output(raw_output)
        except GeminiClientError:
            # Fall back to legacy JSON extraction
            data = extract_json_from_response(raw_output)
        
        return GeminiResponse(
            data=data,
            raw_text=raw_output,
            prompt=prompt,
            model_name=self.model_name,
            report=report_text,
        )
