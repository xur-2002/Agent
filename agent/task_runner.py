"""Task execution module."""

from datetime import datetime, timezone
from typing import Dict, Any


def run_task(task: Dict[str, Any]) -> str:
    """Execute a task and return the result summary.
    
    Dispatches to specific task implementations based on task["id"].
    
    Args:
        task: Task dictionary with id, title, status, etc.
    
    Returns:
        A brief result summary (max 400 chars).
    
    Raises:
        ValueError: If task ID is not recognized.
    """
    task_id = task.get("id")
    
    if task_id == "daily_briefing":
        return run_daily_briefing()
    else:
        raise ValueError(f"Unknown task ID: {task_id}")


def run_daily_briefing() -> str:
    """Generate a daily briefing.
    
    Returns:
        A brief briefing summary.
    """
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M UTC")
    
    briefing = (
        f"Daily Briefing for {date_str}\n"
        f"Generated at {time_str}\n"
        f"Status: Agent is running successfully.\n"
        f"All systems operational."
    )
    
    return briefing
