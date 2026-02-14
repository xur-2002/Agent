"""Data models for agent tasks and results."""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional, List
from datetime import datetime


@dataclass
class TaskResult:
    """Result of a task execution."""
    status: str  # "success", "failed", "skipped"
    summary: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_sec: float = 0.0


@dataclass
class TaskState:
    """Per-task state (persisted separately from config)."""
    task_id: str
    status: str = "pending"  # pending, running, success, failed, skipped
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    last_result_summary: Optional[str] = None
    last_error: Optional[str] = None
    attempts: int = 0
    last_attempt_at: Optional[str] = None
    run_id: Optional[str] = None  # Unique ID for current run

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskState":
        """Create from dictionary."""
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


@dataclass
class Task:
    """Task configuration (mostly static)."""
    id: str
    title: str = ""
    enabled: bool = True
    frequency: str = "daily"  # every_minute, hourly, daily, weekly, once_per_day
    timezone: str = "UTC"
    params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Create from dictionary."""
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)
