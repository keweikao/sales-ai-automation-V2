"""
Scheduler Service implementation.

Manages and executes scheduled jobs.
"""

from datetime import datetime
from typing import Callable, Optional
from dataclasses import dataclass


@dataclass
class JobConfig:
    """Configuration for a scheduled job."""
    name: str
    cron: str
    enabled: bool = True
    handler: Optional[str] = None  # Module path to handler function


class Scheduler:
    """
    Manages scheduled jobs.

    Jobs are typically triggered by Cloud Scheduler
    and handled by this service.
    """

    def __init__(self):
        self._jobs: dict[str, JobConfig] = {}
        self._handlers: dict[str, Callable] = {}
        self._load_jobs()

    def _load_jobs(self):
        """Load job configurations."""
        # TODO: Load from config
        self._jobs = {
            "weekly_report": JobConfig(
                name="weekly_report",
                cron="0 9 * * 1",  # Monday 9 AM
                enabled=True,
            ),
            "daily_reminder": JobConfig(
                name="daily_reminder",
                cron="0 18 * * 1-5",  # Weekdays 6 PM
                enabled=False,
            ),
        }

    def register_handler(self, job_name: str, handler: Callable):
        """Register a handler function for a job."""
        self._handlers[job_name] = handler

    async def run_job(self, job_name: str, **kwargs) -> dict:
        """
        Execute a scheduled job.

        Args:
            job_name: Name of the job to run
            **kwargs: Arguments to pass to job handler

        Returns:
            Job execution result
        """
        if job_name not in self._jobs:
            raise ValueError(f"Unknown job: {job_name}")

        job = self._jobs[job_name]
        if not job.enabled:
            return {"status": "skipped", "reason": "Job is disabled"}

        handler = self._handlers.get(job_name)
        if not handler:
            # Try to load from jobs directory
            handler = await self._load_handler(job_name)

        if not handler:
            return {"status": "error", "reason": "No handler found"}

        try:
            result = await handler(**kwargs)
            return {
                "status": "success",
                "job": job_name,
                "executed_at": datetime.utcnow().isoformat(),
                "result": result,
            }
        except Exception as e:
            return {
                "status": "error",
                "job": job_name,
                "error": str(e),
            }

    async def _load_handler(self, job_name: str) -> Optional[Callable]:
        """Dynamically load handler from jobs directory."""
        # TODO: Implement dynamic loading
        return None

    def list_jobs(self) -> list[dict]:
        """List all configured jobs."""
        return [
            {
                "name": job.name,
                "cron": job.cron,
                "enabled": job.enabled,
            }
            for job in self._jobs.values()
        ]
