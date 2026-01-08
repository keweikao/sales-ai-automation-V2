"""
Shared utilities for Gemini-based analysis agents.

These helpers make it easy to load prompt templates, render conversational
context, call Gemini, and extract structured JSON responses. The goal is to
keep the individual agent implementations focused on domain-specific prompt
construction while centralising the boilerplate (model configuration, response
parsing, error handling).

Migration note: From analysis-service/src/agents/base.py
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

# Retry mechanism (P0 Fix)
try:
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False

# Circuit Breaker (P1 Fix)
try:
    from infrastructure.services.llm_gateway.resilience import CircuitBreaker, CircuitOpenError
    CIRCUIT_BREAKER_AVAILABLE = True
except ImportError:
    CIRCUIT_BREAKER_AVAILABLE = False
    CircuitBreaker = None
    CircuitOpenError = Exception

# Rate Limiter (P1 Fix)
try:
    from infrastructure.services.llm_gateway.resilience import RateLimiter, RateLimitExceeded
    RATE_LIMITER_AVAILABLE = True
except ImportError:
    RATE_LIMITER_AVAILABLE = False
    RateLimiter = None
    RateLimitExceeded = Exception

# Metrics (P2 Enhancement)
try:
    from infrastructure.services.llm_gateway.metrics import metrics
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    metrics = None

import time
import logging

# Module-level logger for observability
_base_logger = logging.getLogger(__name__)


JSON_CONTENT_TYPE = "application/json"
DEFAULT_MODEL_NAME = "gemini-2.0-flash"  # Stable default
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

    Supports two formats:
    1. <JSON>...</JSON> tags (preferred)
    2. ```json...``` markdown blocks (fallback)

    Returns:
        tuple: (report_text, json_data)

    Raises:
        GeminiClientError: If JSON block is not found or invalid
    """
    import re
    import logging
    logger = logging.getLogger(__name__)

    json_str = None
    report_text = ""

    # Try format 1: <JSON>...</JSON> tags
    json_pattern = r'<JSON>(.*?)</JSON>'
    json_match = re.search(json_pattern, output, re.DOTALL | re.IGNORECASE)

    if json_match:
        json_str = json_match.group(1).strip()
        report_text = output[:json_match.start()].strip()
    else:
        # Try format 2: ```json...``` markdown blocks
        # Use a more robust pattern that captures everything between ```json and ```
        markdown_pattern = r'```(?:json)?\s*\n?([\s\S]*?)\n?```'
        markdown_match = re.search(markdown_pattern, output, re.DOTALL)

        if markdown_match:
            json_str = markdown_match.group(1).strip()
            report_text = output[:markdown_match.start()].strip()
            logger.info("Using markdown JSON block format (fallback)")
        else:
            # Try format 3: Find raw JSON object using brace matching
            start = output.find("{")
            if start != -1:
                # Find matching closing brace
                depth = 0
                end = start
                for i, char in enumerate(output[start:], start):
                    if char == '{':
                        depth += 1
                    elif char == '}':
                        depth -= 1
                        if depth == 0:
                            end = i
                            break
                if end > start:
                    json_str = output[start:end + 1]
                    report_text = output[:start].strip()
                    logger.info("Using raw JSON object format (last resort)")

    if not json_str:
        logger.error(f"No JSON found in output. Preview: {output[:500]!r}")
        raise GeminiClientError("未在模型回應中找到 JSON 資料。")

    # Parse JSON
    try:
        json_data = json.loads(json_str, strict=False)
    except json.JSONDecodeError as exc:
        logger.error(f"JSON decode error. JSON string: {json_str[:500]!r}")
        raise GeminiClientError(f"無法解析 JSON 區塊：{exc}") from exc

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

    # Global context path (relative to prompts directory)
    GLOBAL_CONTEXT_FILENAME = "global-context.md"

    def __init__(
        self,
        prompt_path: Path,
        model_name: str = DEFAULT_MODEL_NAME,
        temperature: float = DEFAULT_TEMPERATURE,
        model_factory: Optional[Callable[[], Any]] = None,
        inject_global_context: bool = True,
    ) -> None:
        # Load the agent-specific prompt
        agent_prompt = Path(prompt_path).read_text(encoding="utf-8")

        # Load and inject global context if enabled
        if inject_global_context:
            global_context = self._load_global_context(prompt_path)
            if global_context:
                self.prompt_template = f"{global_context}\n\n---\n\n{agent_prompt}"
            else:
                self.prompt_template = agent_prompt
        else:
            self.prompt_template = agent_prompt

        self.model_name = model_name
        self._model_factory = model_factory or default_model_factory(
            model_name=model_name,
            temperature=temperature,
        )
        self._model: Optional[Any] = None

    def _load_global_context(self, prompt_path: Path) -> str:
        """Load the global context file from the prompts directory."""
        try:
            prompts_dir = Path(prompt_path).resolve().parent
            global_context_path = prompts_dir / self.GLOBAL_CONTEXT_FILENAME

            if global_context_path.exists():
                return global_context_path.read_text(encoding="utf-8")
        except Exception:
            pass  # Silently fail if global context can't be loaded
        return ""

    def build_prompt(self, **kwargs: Any) -> str:  # pragma: no cover - abstract
        """Return the full prompt string. Subclasses must override."""
        raise NotImplementedError

    def _ensure_model(self) -> Any:
        if self._model is None:
            self._model = self._model_factory()
        return self._model

    def _generate(self, prompt: str) -> str:
        """
        Generate content with retry, circuit breaker, rate limiter, and observability.

        P0 Fixes:
        - Retry with exponential backoff (3 attempts)
        - Timing metrics for observability
        - Structured logging for monitoring

        P1 Fixes:
        - Circuit Breaker to prevent cascade failures
        - Rate Limiter to respect Gemini API limits (60 RPM)
        """
        # P1: Check Circuit Breaker before making request
        if CIRCUIT_BREAKER_AVAILABLE and CircuitBreaker:
            cb = CircuitBreaker.get_instance("gemini_api", failure_threshold=5, recovery_timeout=30)
            if not cb.can_execute():
                _base_logger.warning(f"[CIRCUIT:gemini_api] Request blocked - circuit is OPEN")
                raise CircuitOpenError("Gemini API circuit breaker is open")

        # P1: Apply Rate Limiting (60 requests per minute = 1 per second)
        if RATE_LIMITER_AVAILABLE and RateLimiter:
            rl = RateLimiter.get_instance("gemini_api", max_tokens=60, refill_rate=1.0)
            if not rl.acquire(tokens=1, wait=True, timeout=30.0):
                _base_logger.warning(f"[RATE:gemini_api] Rate limit exceeded")
                raise RateLimitExceeded("Gemini API rate limit exceeded")

        start_time = time.time()
        attempt = 0
        max_attempts = 3
        last_error = None

        while attempt < max_attempts:
            attempt += 1
            try:
                model = self._ensure_model()
                response = model.generate_content(prompt)

                # Parse response
                text = getattr(response, "text", None)
                if text:
                    result = text.strip()
                else:
                    # Fallback: concatenate candidate parts
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
                    result = "\n".join(parts).strip() if parts else str(response).strip()

                # Success - log timing metrics and update circuit breaker
                duration = time.time() - start_time
                duration_ms = duration * 1000
                _base_logger.info(
                    f"[METRICS] model={self.model_name} status=success "
                    f"attempt={attempt} duration={duration:.2f}s"
                )

                # P2: Record metrics
                if METRICS_AVAILABLE and metrics:
                    metrics.record_latency("gemini_api", duration_ms)
                    metrics.record_success("gemini_api")

                # P1: Record success in Circuit Breaker
                if CIRCUIT_BREAKER_AVAILABLE and CircuitBreaker:
                    CircuitBreaker.get_instance("gemini_api").record_success()

                return result

            except Exception as e:
                last_error = e
                error_str = str(e)
                duration = time.time() - start_time

                # Check if retryable error
                is_retryable = any(x in error_str.lower() for x in [
                    "timeout", "rate limit", "503", "500", "429", "quota",
                    "resource exhausted", "deadline exceeded", "temporarily unavailable"
                ])

                _base_logger.warning(
                    f"[METRICS] model={self.model_name} status=error "
                    f"attempt={attempt}/{max_attempts} duration={duration:.2f}s "
                    f"error={error_str[:100]} retryable={is_retryable}"
                )

                # Try genai SDK fallback for permission errors
                if ("404" in error_str or "403" in error_str or "PermissionDenied" in error_str) and genai is not None:
                    api_key = os.environ.get("GEMINI_API_KEY")
                    if api_key:
                        _base_logger.info(f"Falling back to genai SDK for model: {self.model_name}")
                        genai.configure(api_key=api_key)
                        model_mapping = {
                            "gemini-2.5-flash": "gemini-2.0-flash",
                            "gemini-1.5-flash": "gemini-2.0-flash",
                        }
                        fallback_model = model_mapping.get(self.model_name, "gemini-2.0-flash")
                        self._model = genai.GenerativeModel(fallback_model)
                        continue  # Retry with fallback model

                # If not retryable or last attempt, raise
                if not is_retryable or attempt >= max_attempts:
                    _base_logger.error(
                        f"[METRICS] model={self.model_name} status=failed "
                        f"total_attempts={attempt} total_duration={duration:.2f}s"
                    )

                    # P2: Record error metrics
                    if METRICS_AVAILABLE and metrics:
                        error_type = "rate_limit" if "429" in error_str else "api_error"
                        metrics.record_error("gemini_api", error_type)

                    # P1: Record failure in Circuit Breaker
                    if CIRCUIT_BREAKER_AVAILABLE and CircuitBreaker:
                        CircuitBreaker.get_instance("gemini_api").record_failure()

                    raise

                # Exponential backoff: 1s, 2s, 4s
                wait_time = 2 ** (attempt - 1)
                _base_logger.info(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)

        # Should not reach here, but just in case
        raise last_error or RuntimeError("Max retries exceeded")

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

    def refine(
        self,
        transcript_segments: List[Dict[str, Any]],
        previous_result: Dict[str, Any],
        feedback: str,
        **kwargs: Any
    ) -> GeminiResponse:
        """
        Refine a previous result based on feedback (Self-Correction / Reflexion).

        This method builds a new prompt that includes:
        1. The original transcript
        2. The previous (flawed) result
        3. Specific feedback on what to fix

        Args:
            transcript_segments: Original transcript data
            previous_result: The JSON output from the previous attempt
            feedback: Specific guidance on what to correct
            **kwargs: Additional context data

        Returns:
            GeminiResponse with the refined output
        """
        import json

        # Build the refinement prompt
        transcript_block = render_transcript(transcript_segments)
        previous_json = json.dumps(previous_result, ensure_ascii=False, indent=2)

        refinement_prompt = f"""# 修正任務 (Refinement Task)

你是一位分析修正專家。你的任務是根據反饋修正先前的分析結果。

## 原始對話內容
{transcript_block}

## 先前的分析結果 (需要修正)
```json
{previous_json}
```

## 修正指示
{feedback}

## 要求
1. 仔細閱讀修正指示
2. 重新分析原始對話內容
3. 產出修正後的完整 JSON 結果
4. 確保修正後的結果符合原始的 JSON Schema

請直接輸出修正後的 JSON，不需要額外說明。使用 <JSON>...</JSON> 標籤包裹輸出。
"""

        raw_output = self._generate(refinement_prompt)

        # Parse the response
        report_text = None
        try:
            report_text, data = parse_dual_mode_output(raw_output)
        except GeminiClientError:
            data = extract_json_from_response(raw_output)

        return GeminiResponse(
            data=data,
            raw_text=raw_output,
            prompt=refinement_prompt,
            model_name=self.model_name,
            report=report_text,
        )
