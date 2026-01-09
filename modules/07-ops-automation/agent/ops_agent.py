"""
Ops Agent - Intelligent operations analysis using LLM.

Uses Gemini to analyze system health and provide recommendations.
This is an optional component - the system works without it.
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Try to import Gemini SDK
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    GENAI_AVAILABLE = False
    logger.warning("google-generativeai not installed, OpsAgent will be unavailable")


@dataclass
class OpsAnalysisResult:
    """Result of ops analysis."""

    overall_status: str  # healthy, warning, critical
    summary: str
    issues: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    raw_response: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "overall_status": self.overall_status,
            "summary": self.summary,
            "issues": self.issues,
            "recommendations": self.recommendations,
            "insights": self.insights,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OpsAnalysisResult":
        """Create from dictionary."""
        return cls(
            overall_status=data.get("overall_status", "unknown"),
            summary=data.get("summary", ""),
            issues=data.get("issues", []),
            recommendations=data.get("recommendations", []),
            insights=data.get("insights", []),
        )


class OpsAgent:
    """
    Intelligent operations agent using Gemini.

    Analyzes system health data and provides:
    - Status assessment
    - Issue identification
    - Remediation recommendations
    - Trend analysis
    """

    DEFAULT_MODEL = "gemini-2.0-flash"
    DEFAULT_TEMPERATURE = 0.1

    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        api_key: Optional[str] = None,
    ):
        if not GENAI_AVAILABLE:
            raise ImportError(
                "google-generativeai is required for OpsAgent. "
                "Install with: pip install google-generativeai"
            )

        self.model_name = model_name or os.environ.get(
            "OPS_AGENT_MODEL", self.DEFAULT_MODEL
        )
        self.temperature = temperature

        # Configure API key
        api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)

        # Load prompt template
        self.prompt_template = self._load_prompt_template()

        # Create model
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config={
                "temperature": self.temperature,
                "max_output_tokens": 2048,
            },
        )

    def _load_prompt_template(self) -> str:
        """Load the prompt template from file."""
        prompt_path = Path(__file__).parent / "prompts" / "ops-analysis.md"
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")

        # Fallback minimal prompt
        return """
分析以下系統健康數據並提供 JSON 格式的回應：

{HEALTH_REPORT}
{PROCESSING_STATS}

以 <JSON>...</JSON> 格式回應，包含：
- overall_status: healthy/warning/critical
- summary: 摘要
- issues: 問題列表
- recommendations: 建議列表
- insights: 洞察列表
"""

    def _build_prompt(
        self,
        health_report: Dict[str, Any],
        processing_stats: Optional[Dict[str, Any]] = None,
        error_stats: Optional[Dict[str, Any]] = None,
        retry_stats: Optional[Dict[str, Any]] = None,
        cleanup_stats: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build the analysis prompt with all ops data."""
        return self.prompt_template.format(
            HEALTH_REPORT=json.dumps(health_report, ensure_ascii=False, indent=2),
            PROCESSING_STATS=json.dumps(
                processing_stats or {}, ensure_ascii=False, indent=2
            ),
            ERROR_STATS=json.dumps(error_stats or {}, ensure_ascii=False, indent=2),
            RETRY_STATS=json.dumps(retry_stats or {}, ensure_ascii=False, indent=2),
            CLEANUP_STATS=json.dumps(cleanup_stats or {}, ensure_ascii=False, indent=2),
        )

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from <JSON>...</JSON> tags or raw JSON."""
        # Try to find JSON in tags
        match = re.search(r"<JSON>\s*(.*?)\s*</JSON>", text, re.DOTALL | re.IGNORECASE)
        if match:
            json_str = match.group(1)
        else:
            # Try to find raw JSON
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                raise ValueError("No JSON found in response")

        return json.loads(json_str)

    def analyze(
        self,
        health_report: Dict[str, Any],
        error_stats: Optional[Dict[str, Any]] = None,
        retry_stats: Optional[Dict[str, Any]] = None,
        cleanup_stats: Optional[Dict[str, Any]] = None,
        processing_stats: Optional[Dict[str, Any]] = None,
    ) -> OpsAnalysisResult:
        """
        Analyze ops data and provide recommendations.

        Args:
            health_report: System health check results
            error_stats: Error statistics from ErrorNotifier
            retry_stats: Auto-retry results
            cleanup_stats: Cleanup results
            processing_stats: Processing statistics

        Returns:
            OpsAnalysisResult with analysis and recommendations
        """
        prompt = self._build_prompt(
            health_report=health_report,
            processing_stats=processing_stats,
            error_stats=error_stats,
            retry_stats=retry_stats,
            cleanup_stats=cleanup_stats,
        )

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text

            logger.debug(f"OpsAgent raw response: {response_text[:500]}...")

            # Parse JSON from response
            data = self._extract_json(response_text)

            return OpsAnalysisResult(
                overall_status=data.get("overall_status", "unknown"),
                summary=data.get("summary", ""),
                issues=data.get("issues", []),
                recommendations=data.get("recommendations", []),
                insights=data.get("insights", []),
                raw_response=response_text,
            )

        except Exception as e:
            logger.error(f"OpsAgent analysis failed: {e}")

            # Return fallback result
            return OpsAnalysisResult(
                overall_status=health_report.get("overall_status", "unknown"),
                summary=f"自動分析失敗: {str(e)}",
                issues=[],
                recommendations=["請手動檢查系統狀態"],
                insights=[],
            )

    def analyze_simple(
        self,
        health_report: Dict[str, Any],
    ) -> str:
        """
        Quick analysis returning just a summary string.

        Useful for simple status checks without full analysis.
        """
        result = self.analyze(health_report=health_report)
        return result.summary
