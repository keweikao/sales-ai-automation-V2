"""
Metrics module for Cloud Monitoring integration.

P2 Enhancement: Observability and monitoring with custom metrics.

Usage:
    from .metrics import metrics
    
    # Record latency
    metrics.record_latency("gemini_api", duration_ms=2500)
    
    # Record success/error
    metrics.record_success("analysis")
    metrics.record_error("analysis", "timeout")
    
    # Get summary for Slack reports
    summary = metrics.get_daily_summary()
"""

import logging
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Single metric data point."""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """
    In-process metrics collector with Cloud Monitoring export capability.
    
    Collects:
    - Latency distributions (P50, P95, P99)
    - Success/Error counts
    - Circuit breaker states
    - Rate limiter states
    
    Can export to:
    - Cloud Monitoring (custom metrics)
    - Slack (daily summaries)
    - Logs (structured format)
    """
    
    def __init__(self):
        self._latencies: Dict[str, list] = defaultdict(list)
        self._success_counts: Dict[str, int] = defaultdict(int)
        self._error_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._last_reset: float = time.time()
        self._reset_interval: int = 3600  # 1 hour
    
    def _maybe_reset(self) -> None:
        """Reset counters periodically to prevent unbounded growth."""
        if time.time() - self._last_reset > self._reset_interval:
            self._latencies.clear()
            self._success_counts.clear()
            self._error_counts.clear()
            self._last_reset = time.time()
            logger.info("[METRICS] Counters reset")
    
    def record_latency(self, service: str, duration_ms: float) -> None:
        """Record latency for a service."""
        self._maybe_reset()
        self._latencies[service].append(duration_ms)
        
        # Keep only last 1000 samples per service
        if len(self._latencies[service]) > 1000:
            self._latencies[service] = self._latencies[service][-1000:]
        
        logger.debug(f"[METRICS] {service} latency: {duration_ms:.0f}ms")
    
    def record_success(self, service: str) -> None:
        """Record successful operation."""
        self._maybe_reset()
        self._success_counts[service] += 1
        logger.debug(f"[METRICS] {service} success (total: {self._success_counts[service]})")
    
    def record_error(self, service: str, error_type: str = "unknown") -> None:
        """Record error with type classification."""
        self._maybe_reset()
        self._error_counts[service][error_type] += 1
        total = sum(self._error_counts[service].values())
        logger.warning(f"[METRICS] {service} error: {error_type} (total: {total})")
    
    def get_latency_stats(self, service: str) -> Dict[str, float]:
        """Get latency statistics for a service."""
        samples = self._latencies.get(service, [])
        if not samples:
            return {"count": 0, "p50": 0, "p95": 0, "p99": 0, "avg": 0}
        
        sorted_samples = sorted(samples)
        n = len(sorted_samples)
        
        return {
            "count": n,
            "p50": sorted_samples[int(n * 0.5)] if n > 0 else 0,
            "p95": sorted_samples[int(n * 0.95)] if n > 0 else 0,
            "p99": sorted_samples[int(n * 0.99)] if n > 0 else 0,
            "avg": sum(samples) / n if n > 0 else 0,
            "min": min(samples) if samples else 0,
            "max": max(samples) if samples else 0,
        }
    
    def get_error_rate(self, service: str) -> float:
        """Calculate error rate for a service."""
        success = self._success_counts.get(service, 0)
        errors = sum(self._error_counts.get(service, {}).values())
        total = success + errors
        return (errors / total * 100) if total > 0 else 0
    
    def get_summary(self) -> Dict[str, Any]:
        """Get full metrics summary for all services."""
        services = set(
            list(self._latencies.keys()) + 
            list(self._success_counts.keys()) + 
            list(self._error_counts.keys())
        )
        
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "period_seconds": int(time.time() - self._last_reset),
            "services": {}
        }
        
        for service in services:
            latency_stats = self.get_latency_stats(service)
            success = self._success_counts.get(service, 0)
            errors = self._error_counts.get(service, {})
            
            summary["services"][service] = {
                "success_count": success,
                "error_count": sum(errors.values()),
                "error_breakdown": dict(errors),
                "error_rate": self.get_error_rate(service),
                "latency": latency_stats,
            }
        
        return summary
    
    def format_slack_message(self) -> str:
        """Format metrics summary for Slack notification."""
        summary = self.get_summary()
        period_min = summary["period_seconds"] // 60
        
        lines = [
            f"📊 *系統監控報告* ({period_min} 分鐘)",
            "",
        ]
        
        for service, data in summary["services"].items():
            success = data["success_count"]
            errors = data["error_count"]
            error_rate = data["error_rate"]
            latency = data["latency"]
            
            # Status emoji
            if error_rate > 10:
                status = "🔴"
            elif error_rate > 5:
                status = "🟡"
            else:
                status = "🟢"
            
            lines.append(f"{status} *{service}*")
            lines.append(f"  • 成功: {success} | 錯誤: {errors} ({error_rate:.1f}%)")
            
            if latency["count"] > 0:
                lines.append(f"  • 延遲 P95: {latency['p95']:.0f}ms | 平均: {latency['avg']:.0f}ms")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def should_alert(self) -> Optional[str]:
        """Check if any alert condition is met. Returns alert message or None."""
        alerts = []
        
        for service in self._success_counts.keys() | self._error_counts.keys():
            error_rate = self.get_error_rate(service)
            
            # Alert if error rate > 10%
            if error_rate > 10:
                alerts.append(f"🔴 {service} 錯誤率過高: {error_rate:.1f}%")
            
            # Alert if latency P95 > 30s
            latency = self.get_latency_stats(service)
            if latency["p95"] > 30000:
                alerts.append(f"🟡 {service} 延遲過高: P95={latency['p95']:.0f}ms")
        
        return "\n".join(alerts) if alerts else None


# Global metrics instance
metrics = MetricsCollector()


def send_slack_alert(webhook_url: str, message: str) -> bool:
    """Send alert to Slack via webhook."""
    import urllib.request
    import json
    
    try:
        payload = {
            "text": message,
            "username": "Analytics Monitor",
            "icon_emoji": ":chart_with_upwards_trend:",
        }
        
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status == 200
            
    except Exception as e:
        logger.error(f"Failed to send Slack alert: {e}")
        return False
