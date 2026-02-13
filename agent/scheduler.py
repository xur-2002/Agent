"""Task scheduling logic."""

from datetime import datetime, timezone, timedelta
import logging
from agent.models import Task
from agent.utils import parse_iso_datetime, now_utc

logger = logging.getLogger(__name__)


def should_run(task: Task) -> bool:
    """Determine if a task should run now based on its frequency and last_run_at.
    
    Args:
        task: Task to check.
    
    Returns:
        True if task should run, False otherwise.
    """
    if not task.enabled:
        return False
    
    now = now_utc()
    last_run = parse_iso_datetime(task.last_run_at)
    
    # If never run, should run
    if last_run is None:
        return True
    
    frequency = task.frequency.lower()
    
    if frequency == "every_minute":
        # Run if at least 60 seconds have passed
        return (now - last_run).total_seconds() >= 60
    elif frequency == "hourly":
        # Run if at least 1 hour has passed
        return (now - last_run).total_seconds() >= 3600
    elif frequency == "daily":
        # Run if at least 1 day has passed
        return (now - last_run).total_seconds() >= 86400
    elif frequency == "weekly":
        # Run if at least 7 days have passed
        return (now - last_run).total_seconds() >= 604800
    else:
        # Unknown frequency, run it
        logger.warning(f"Unknown frequency '{frequency}' for task {task.id}, allowing run")
        return True


def compute_next_run(task: Task, run_time: datetime) -> datetime:
    """Compute next run time for a task based on its frequency.
    
    Args:
        task: Task definition.
        run_time: Time the task just ran.
    
    Returns:
        Next run time as datetime.
    """
    frequency = task.frequency.lower()
    
    if frequency == "every_minute":
        return run_time + timedelta(minutes=1)
    elif frequency == "hourly":
        return run_time + timedelta(hours=1)
    elif frequency == "daily":
        return run_time + timedelta(days=1)
    elif frequency == "weekly":
        return run_time + timedelta(weeks=1)
    else:
        # Default to daily
        return run_time + timedelta(days=1)
