"""
Service health checker.

Monitors health of all system services including transcription,
analysis, notification, and database services.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

import httpx
from google.cloud import firestore


class ServiceStatus(str, Enum):
    """Service health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceHealthResult:
    """Result of a health check for a single service."""
    service_name: str
    status: ServiceStatus
    latency_ms: Optional[float] = None
    last_success: Optional[datetime] = None
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemHealthReport:
    """Complete system health report."""
    overall_status: ServiceStatus
    services: Dict[str, ServiceHealthResult]
    checked_at: datetime
    summary: str


class HealthChecker:
    """Checks health of all system services."""

    # Cloud Run service URLs (from environment or config)
    DEFAULT_SERVICE_URLS = {
        "transcription": "https://transcription-service-xxxxx.run.app",
        "analysis": "https://analysis-service-xxxxx.run.app",
        "notification": "https://notification-service-xxxxx.run.app",
        "api_gateway": "https://api-gateway-xxxxx.run.app",
        "llm_gateway": "https://llm-gateway-xxxxx.run.app",
    }

    def __init__(
        self,
        service_urls: Optional[Dict[str, str]] = None,
        db: Optional[firestore.Client] = None,
        timeout_seconds: float = 10.0,
    ):
        self.service_urls = service_urls or self.DEFAULT_SERVICE_URLS
        self.db = db or firestore.Client()
        self.timeout = timeout_seconds

    async def check_all(self) -> Dict[str, ServiceStatus]:
        """
        Check health of all services.

        Returns:
            Dict mapping service name to status
        """
        report = await self.get_full_report()
        return {name: result.status for name, result in report.services.items()}

    async def get_full_report(self) -> SystemHealthReport:
        """
        Get a complete health report for all services.

        Returns:
            SystemHealthReport with detailed status for each service
        """
        # Run all health checks concurrently
        results = await asyncio.gather(
            self.check_transcription(),
            self.check_analysis(),
            self.check_notification(),
            self.check_database(),
            self.check_llm_gateway(),
            return_exceptions=True,
        )

        service_names = ["transcription", "analysis", "notification", "database", "llm_gateway"]
        services: Dict[str, ServiceHealthResult] = {}

        for name, result in zip(service_names, results):
            if isinstance(result, Exception):
                services[name] = ServiceHealthResult(
                    service_name=name,
                    status=ServiceStatus.UNHEALTHY,
                    error_message=str(result),
                )
            else:
                services[name] = result

        # Determine overall status
        statuses = [s.status for s in services.values()]
        if all(s == ServiceStatus.HEALTHY for s in statuses):
            overall = ServiceStatus.HEALTHY
            summary = "All services are healthy"
        elif any(s == ServiceStatus.UNHEALTHY for s in statuses):
            unhealthy = [n for n, r in services.items() if r.status == ServiceStatus.UNHEALTHY]
            overall = ServiceStatus.UNHEALTHY
            summary = f"Services unhealthy: {', '.join(unhealthy)}"
        elif any(s == ServiceStatus.DEGRADED for s in statuses):
            degraded = [n for n, r in services.items() if r.status == ServiceStatus.DEGRADED]
            overall = ServiceStatus.DEGRADED
            summary = f"Services degraded: {', '.join(degraded)}"
        else:
            overall = ServiceStatus.UNKNOWN
            summary = "Unable to determine system status"

        return SystemHealthReport(
            overall_status=overall,
            services=services,
            checked_at=datetime.now(timezone.utc),
            summary=summary,
        )

    async def check_transcription(self) -> ServiceHealthResult:
        """Check Transcription Service health."""
        service_name = "transcription"
        url = self.service_urls.get(service_name)

        if not url or "xxxxx" in url:
            # Check by querying recent transcription jobs instead
            return await self._check_service_by_recent_activity(
                service_name=service_name,
                status_field="transcriptionStatus",
                success_value="completed",
            )

        return await self._check_http_health(service_name, f"{url}/healthz")

    async def check_analysis(self) -> ServiceHealthResult:
        """Check Analysis Service health."""
        service_name = "analysis"
        url = self.service_urls.get(service_name)

        if not url or "xxxxx" in url:
            # Check by querying recent analysis jobs
            return await self._check_service_by_recent_activity(
                service_name=service_name,
                status_field="analysisStatus",
                success_value="completed",
            )

        return await self._check_http_health(service_name, f"{url}/healthz")

    async def check_notification(self) -> ServiceHealthResult:
        """Check Notification Service health."""
        service_name = "notification"
        url = self.service_urls.get(service_name)

        if not url or "xxxxx" in url:
            # Assume healthy if no URL configured (notifications are optional)
            return ServiceHealthResult(
                service_name=service_name,
                status=ServiceStatus.HEALTHY,
                details={"note": "No health endpoint configured, assuming healthy"},
            )

        return await self._check_http_health(service_name, f"{url}/healthz")

    async def check_database(self) -> ServiceHealthResult:
        """Check Firestore database health."""
        service_name = "database"
        start_time = datetime.now(timezone.utc)

        try:
            # Simple read operation to check connectivity
            test_query = self.db.collection("cases").limit(1)
            list(test_query.stream())

            latency = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            # Degraded if latency > 500ms
            status = ServiceStatus.HEALTHY if latency < 500 else ServiceStatus.DEGRADED

            return ServiceHealthResult(
                service_name=service_name,
                status=status,
                latency_ms=latency,
                last_success=datetime.now(timezone.utc),
            )
        except Exception as e:
            return ServiceHealthResult(
                service_name=service_name,
                status=ServiceStatus.UNHEALTHY,
                error_message=str(e),
            )

    async def check_llm_gateway(self) -> ServiceHealthResult:
        """Check LLM Gateway health."""
        service_name = "llm_gateway"
        url = self.service_urls.get(service_name)

        if not url or "xxxxx" in url:
            # Check by looking at recent LLM usage
            return await self._check_llm_by_recent_usage()

        return await self._check_http_health(service_name, f"{url}/healthz")

    async def _check_http_health(
        self,
        service_name: str,
        url: str
    ) -> ServiceHealthResult:
        """Check service health via HTTP endpoint."""
        start_time = datetime.now(timezone.utc)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=self.timeout)
                latency = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

                if response.status_code == 200:
                    # Degraded if latency > 1000ms
                    status = ServiceStatus.HEALTHY if latency < 1000 else ServiceStatus.DEGRADED
                    return ServiceHealthResult(
                        service_name=service_name,
                        status=status,
                        latency_ms=latency,
                        last_success=datetime.now(timezone.utc),
                    )
                else:
                    return ServiceHealthResult(
                        service_name=service_name,
                        status=ServiceStatus.UNHEALTHY,
                        latency_ms=latency,
                        error_message=f"HTTP {response.status_code}",
                    )
        except httpx.TimeoutException:
            return ServiceHealthResult(
                service_name=service_name,
                status=ServiceStatus.UNHEALTHY,
                error_message="Request timed out",
            )
        except Exception as e:
            return ServiceHealthResult(
                service_name=service_name,
                status=ServiceStatus.UNHEALTHY,
                error_message=str(e),
            )

    async def _check_service_by_recent_activity(
        self,
        service_name: str,
        status_field: str,
        success_value: str,
        hours_lookback: int = 1,
    ) -> ServiceHealthResult:
        """Check service health by looking at recent job success rate."""
        from google.cloud.firestore_v1.base_query import FieldFilter

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_lookback)

        try:
            # Query recent cases
            query = (
                self.db.collection("cases")
                .where(filter=FieldFilter("createdAt", ">=", cutoff))
                .limit(50)
            )

            docs = list(query.stream())

            if not docs:
                # No recent activity - could be quiet period, assume healthy
                return ServiceHealthResult(
                    service_name=service_name,
                    status=ServiceStatus.HEALTHY,
                    details={"note": "No recent activity to check"},
                )

            # Calculate success rate
            total = len(docs)
            successful = sum(
                1 for doc in docs
                if doc.to_dict().get(status_field) == success_value
            )
            failed = sum(
                1 for doc in docs
                if doc.to_dict().get(status_field) == "failed"
            )

            success_rate = successful / total if total > 0 else 0

            if success_rate >= 0.95:
                status = ServiceStatus.HEALTHY
            elif success_rate >= 0.7:
                status = ServiceStatus.DEGRADED
            else:
                status = ServiceStatus.UNHEALTHY

            return ServiceHealthResult(
                service_name=service_name,
                status=status,
                details={
                    "success_rate": success_rate,
                    "total_checked": total,
                    "successful": successful,
                    "failed": failed,
                },
            )
        except Exception as e:
            return ServiceHealthResult(
                service_name=service_name,
                status=ServiceStatus.UNKNOWN,
                error_message=str(e),
            )

    async def _check_llm_by_recent_usage(self) -> ServiceHealthResult:
        """Check LLM gateway by looking at recent analysis completions."""
        # LLM is healthy if analysis jobs are completing
        return await self._check_service_by_recent_activity(
            service_name="llm_gateway",
            status_field="analysisStatus",
            success_value="completed",
        )
