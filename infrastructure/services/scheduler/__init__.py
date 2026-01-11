"""
Scheduler Service

Manages scheduled jobs like weekly reports and daily reminders.

Usage:
    from infrastructure.services.scheduler import Scheduler

    scheduler = Scheduler()
    await scheduler.run_job("weekly_report")
"""


def __getattr__(name):
    """Lazy import to avoid loading yaml dependency when only importing jobs."""
    if name == "Scheduler":
        from .service import Scheduler

        return Scheduler
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["Scheduler"]
