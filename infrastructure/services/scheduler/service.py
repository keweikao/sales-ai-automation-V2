"""
Scheduler Service implementation.

Manages and executes scheduled jobs.
"""

import importlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class JobConfig:
    """Configuration for a scheduled job."""

    name: str
    cron: str
    enabled: bool = True
    handler: Optional[str] = None  # Module path to handler function
    description: str = ""
    config: dict[str, Any] = field(default_factory=dict)


class Scheduler:
    """
    Manages scheduled jobs.

    Jobs are typically triggered by Cloud Scheduler
    and handled by this service.
    """

    def __init__(self):
        self._jobs: dict[str, JobConfig] = {}
        self._handlers: dict[str, Callable] = {}
        self._defaults: dict[str, Any] = {}
        self._load_jobs()

    def _load_jobs(self):
        """Load job configurations from YAML."""
        config_path = Path(__file__).parent / "config" / "jobs.yaml"

        try:
            if config_path.exists():
                with open(config_path, "r") as f:
                    config = yaml.safe_load(f)
                    logger.info(f"Loaded scheduler config from {config_path}")

                    # Load defaults
                    self._defaults = config.get("defaults", {})

                    # Load jobs
                    jobs_config = config.get("jobs", {})
                    for job_id, job_data in jobs_config.items():
                        self._jobs[job_id] = JobConfig(
                            name=job_data.get("name", job_id),
                            cron=job_data.get("cron", ""),
                            enabled=job_data.get("enabled", True),
                            handler=job_data.get("handler"),
                            description=job_data.get("description", ""),
                            config=job_data.get("config", {}),
                        )

                    logger.info(f"Loaded {len(self._jobs)} jobs from config")
                    return
            else:
                logger.warning(f"Scheduler config not found at {config_path}")

        except Exception as e:
            logger.error(f"Failed to load scheduler config: {e}")

        # Fallback to defaults
        self._jobs = {
            "weekly_report": JobConfig(
                name="weekly_report",
                cron="0 9 * * 1",
                enabled=True,
            ),
            "daily_reminder": JobConfig(
                name="daily_reminder",
                cron="0 18 * * 1-5",
                enabled=False,
            ),
            "weekly_upload_report": JobConfig(
                name="weekly_upload_report",
                cron="0 9 * * 1",
                enabled=True,
                handler="infrastructure.services.scheduler.jobs.weekly_upload_report.send_weekly_upload_report",
            ),
        }

    def register_handler(self, job_name: str, handler: Callable):
        """Register a handler function for a job."""
        self._handlers[job_name] = handler
        logger.info(f"Registered handler for job: {job_name}")

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

        # Get handler
        handler = self._handlers.get(job_name)
        if not handler:
            handler = await self._load_handler(job)

        if not handler:
            return {"status": "error", "reason": "No handler found"}

        # Merge job config with kwargs
        merged_kwargs = {**job.config, **kwargs}

        try:
            logger.info(f"Executing job: {job_name}")
            result = await handler(**merged_kwargs)
            return {
                "status": "success",
                "job": job_name,
                "executed_at": datetime.utcnow().isoformat(),
                "result": result,
            }
        except Exception as e:
            logger.error(f"Job {job_name} failed: {e}", exc_info=True)
            return {
                "status": "error",
                "job": job_name,
                "error": str(e),
            }

    async def _load_handler(self, job: JobConfig) -> Optional[Callable]:
        """Dynamically load handler from module path."""
        if not job.handler:
            return None

        try:
            # Split handler path into module and function
            parts = job.handler.rsplit(".", 1)
            if len(parts) != 2:
                logger.error(f"Invalid handler path: {job.handler}")
                return None

            module_path, func_name = parts

            # Import module
            module = importlib.import_module(module_path)

            # Get function
            handler = getattr(module, func_name, None)
            if handler is None:
                logger.error(f"Handler function not found: {func_name} in {module_path}")
                return None

            # Cache for future use
            self._handlers[job.name] = handler
            logger.info(f"Loaded handler for {job.name}: {job.handler}")

            return handler

        except ImportError as e:
            logger.error(f"Failed to import handler module {job.handler}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to load handler {job.handler}: {e}")
            return None

    def list_jobs(self) -> list[dict]:
        """List all configured jobs."""
        return [
            {
                "name": job.name,
                "cron": job.cron,
                "enabled": job.enabled,
                "description": job.description,
                "handler": job.handler,
            }
            for job in self._jobs.values()
        ]

    def get_job(self, job_name: str) -> Optional[JobConfig]:
        """Get a specific job configuration."""
        return self._jobs.get(job_name)

    def enable_job(self, job_name: str) -> bool:
        """Enable a job."""
        if job_name in self._jobs:
            self._jobs[job_name].enabled = True
            logger.info(f"Enabled job: {job_name}")
            return True
        return False

    def disable_job(self, job_name: str) -> bool:
        """Disable a job."""
        if job_name in self._jobs:
            self._jobs[job_name].enabled = False
            logger.info(f"Disabled job: {job_name}")
            return True
        return False
