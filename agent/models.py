"""Data models for agent tasks and results."""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional
from datetime import datetime


@dataclass
class TaskResult:
    """Result of a task execution."""
    status: str  # "ok", "failed", "skipped"
    summary: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_sec: float = 0.0


@dataclass
class Task:
    """Task definition."""
    id: str
    title: str
    enabled: bool = True
    frequency: str = "daily"  # every_minute, hourly, daily, weekly, cron
    timezone: str = "UTC"
    params: Dict[str, Any] = field(default_factory=dict)
    status: str = "scheduled"  # scheduled, running, ok, failed
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    last_result_summary: Optional[str] = None
    last_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Create from dictionary."""
        # Filter out extra fields
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)
