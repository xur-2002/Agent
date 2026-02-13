"""Storage module for tasks.json persistence."""

import json
import tempfile
from pathlib import Path


def get_tasks_file() -> Path:
    """Get the path to tasks.json in the repository root."""
    # Navigate from agent/storage.py to root/tasks.json
    root = Path(__file__).parent.parent
    return root / "tasks.json"


def load_tasks() -> list:
    """Load tasks from tasks.json.
    
    Returns:
        List of task dictionaries.
    
    Raises:
        FileNotFoundError: If tasks.json does not exist.
        json.JSONDecodeError: If tasks.json is invalid JSON.
    """
    tasks_file = get_tasks_file()
    if not tasks_file.exists():
        raise FileNotFoundError(f"tasks.json not found at {tasks_file}")
    
    with open(tasks_file, "r") as f:
        return json.load(f)


def save_tasks(tasks: list) -> None:
    """Save tasks to tasks.json safely using atomic writes.
    
    Writes to a temporary file first, then replaces the original
    to avoid corruption on interruption.
    
    Args:
        tasks: List of task dictionaries to save.
    """
    tasks_file = get_tasks_file()
    
    # Write to temporary file first
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=tasks_file.parent,
        suffix=".tmp",
        delete=False
    ) as tmp:
        json.dump(tasks, tmp, indent=2)
        tmp_path = tmp.name
    
    # Replace original with temp file
    tmp_path_obj = Path(tmp_path)
    tmp_path_obj.replace(tasks_file)
