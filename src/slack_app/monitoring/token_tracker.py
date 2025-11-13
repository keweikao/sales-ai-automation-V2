"""
Token usage monitoring for MCP optimization validation.

# derived from Anthropic official doc (2025)
"""

import tiktoken
from datetime import datetime
from typing import Dict, Any, Optional


class TokenUsageTracker:
    """Track token savings from MCP optimization."""

    def __init__(self):
        self.encoder = tiktoken.get_encoding("cl100k_base")
        self.metrics = []

    def measure_optimization(
        self,
        tool_name: str,
        raw_data_size: int,
        filtered_data: Any,
        context_mode: str,
        model_name: Optional[str] = None # New parameter
    ) -> Dict[str, Any]:
        """
        Measure token reduction achieved.

        Args:
            tool_name: Tool identifier
            raw_data_size: Number of raw records returned
            filtered_data: Filtered data passed to model
            context_mode: Context mode used
            model_name: The AI model used for the interaction (e.g., "gemini-pro", "claude-opus") # New description

        Returns:
            Optimization metrics
        """
        # Estimate raw tokens (assuming 50 fields per record)
        estimated_raw_tokens = raw_data_size * 50 * 10  # ~500 tokens per record

        # Measure actual filtered tokens
        filtered_tokens = len(self.encoder.encode(str(filtered_data)))

        # Calculate reduction
        reduction_pct = (
            (estimated_raw_tokens - filtered_tokens) / estimated_raw_tokens * 100
            if estimated_raw_tokens > 0 else 0
        )

        metric = {
            "timestamp": datetime.utcnow().isoformat(),
            "tool_name": tool_name,
            "context_mode": context_mode,
            "raw_records": raw_data_size,
            "estimated_raw_tokens": estimated_raw_tokens,
            "filtered_tokens": filtered_tokens,
            "reduction_pct": round(reduction_pct, 2),
            "target_met": reduction_pct >= 90,  # Target: 90%+ reduction
            "model_name": model_name # Store the model name
        }

        self.metrics.append(metric)
        return metric

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        if not self.metrics:
            return {"total_measurements": 0}

        total_raw = sum(m["estimated_raw_tokens"] for m in self.metrics)
        total_filtered = sum(m["filtered_tokens"] for m in self.metrics)
        avg_reduction = sum(m["reduction_pct"] for m in self.metrics) / len(self.metrics)
        target_met_count = sum(1 for m in self.metrics if m["target_met"])

        return {
            "total_measurements": len(self.metrics),
            "total_raw_tokens": total_raw,
            "total_filtered_tokens": total_filtered,
            "overall_reduction_pct": round((total_raw - total_filtered) / total_raw * 100, 2),
            "avg_reduction_pct": round(avg_reduction, 2),
            "target_met_pct": round(target_met_count / len(self.metrics) * 100, 2),
            "by_context_mode": self._group_by_context_mode()
        }

    def _group_by_context_mode(self) -> Dict[str, Dict]:
        """Group metrics by context mode."""
        grouped = {}
        for metric in self.metrics:
            mode = metric["context_mode"]
            if mode not in grouped:
                grouped[mode] = []
            grouped[mode].append(metric)

        return {
            mode: {
                "count": len(metrics),
                "avg_reduction": round(
                    sum(m["reduction_pct"] for m in metrics) / len(metrics), 2
                )
            }
            for mode, metrics in grouped.items()
        }
