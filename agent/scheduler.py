"""Task scheduling logic."""

from datetime import datetime, timezone, timedelta
import logging
from typing import Optional, Dict
from agent.models import Task, TaskState
from agent.utils import parse_iso_datetime, now_utc

logger = logging.getLogger(__name__)


def should_run(task: Task, task_state: Optional[TaskState] = None) -> bool:
    """Determine if a task should run now based on its frequency and last_run_at.
    
    Args:
        task: Task configuration.
        task_state: Optional task state with last_run_at info. If None, task hasn't run yet.
    
    Returns:
        True if task should run, False otherwise.
    """
    if not task.enabled:
        return False
    
    now = now_utc()
    
    # If no state or never run, should run
    if task_state is None or task_state.last_run_at is None:
        return True
    
    last_run = parse_iso_datetime(task_state.last_run_at)
    if last_run is None:
        return True
    
    frequency = task.frequency.lower()
    elapsed_seconds = (now - last_run).total_seconds()
    
    # Parse frequency patterns
    if frequency == "every_minute":
        return elapsed_seconds >= 60
    elif frequency == "every_5_min" or frequency == "every_5_minutes":
        return elapsed_seconds >= 5 * 60
    elif frequency == "every_15_min" or frequency == "every_15_minutes":
        return elapsed_seconds >= 15 * 60
    elif frequency == "every_30_min" or frequency == "every_30_minutes":
        return elapsed_seconds >= 30 * 60
    elif frequency == "hourly" or frequency == "every_hour":
        return elapsed_seconds >= 3600
    elif frequency == "daily" or frequency == "once_per_day":
        return elapsed_seconds >= 86400
    elif frequency == "weekly":
        return elapsed_seconds >= 604800  # 7 days
    else:
        # Unknown frequency, log warning but allow run
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
    elif frequency == "every_5_min" or frequency == "every_5_minutes":
        return run_time + timedelta(minutes=5)
    elif frequency == "every_15_min" or frequency == "every_15_minutes":
        return run_time + timedelta(minutes=15)
    elif frequency == "every_30_min" or frequency == "every_30_minutes":
        return run_time + timedelta(minutes=30)
    elif frequency == "hourly" or frequency == "every_hour":
        return run_time + timedelta(hours=1)
    elif frequency == "daily" or frequency == "once_per_day":
        return run_time + timedelta(days=1)
    elif frequency == "weekly":
        return run_time + timedelta(weeks=1)
    else:
        # Default to daily
        logger.warning(f"Unknown frequency '{frequency}, defaulting to daily")
        return run_time + timedelta(days=1)
