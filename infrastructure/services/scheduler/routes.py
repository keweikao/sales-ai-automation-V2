"""
Scheduler Service API routes.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


class RunJobRequest(BaseModel):
    """Request to run a job."""
    job_name: str
    params: Optional[dict] = None


@router.post("/run")
async def run_job(request: RunJobRequest):
    """Manually trigger a scheduled job."""
    # TODO: Connect to Scheduler service
    return {"message": f"Job {request.job_name} triggered (pending implementation)"}


@router.get("/jobs")
async def list_jobs():
    """List all scheduled jobs."""
    # TODO: Connect to Scheduler service
    return {
        "jobs": [
            {"name": "weekly_report", "cron": "0 9 * * 1", "enabled": True},
            {"name": "daily_reminder", "cron": "0 18 * * 1-5", "enabled": False},
        ]
    }
