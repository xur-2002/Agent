"""Storage backends for tasks and state (refactored with separation)."""

import json
import tempfile
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional

from agent.models import Task, TaskState
from agent.utils import safe_json_dump

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Abstract storage backend."""
    
    @abstractmethod
    def load_tasks(self) -> List[Task]:
        """Load task configurations from storage."""
        pass
    
    @abstractmethod
    def load_state(self) -> Dict[str, TaskState]:
        """Load task state from storage. Returns dict of {task_id: TaskState}."""
        pass
    
    @abstractmethod
    def save_state(self, state: Dict[str, TaskState]) -> None:
        """Save task state to storage."""
        pass


class JsonFileStorage(StorageBackend):
    """Store tasks in local tasks.json and state in state.json."""
    
    def __init__(self, state_file: Optional[str] = None):
        """Initialize JsonFileStorage.
        
        Args:
            state_file: Path to state.json. If None, uses repo root/state.json.
        """
        root = Path(__file__).parent.parent
        self.tasks_file = root / "tasks.json"
        
        # State file: use STATE_FILE env var or parameter or default to state.json
        if state_file:
            state_file_path = Path(state_file)
        else:
            state_file_path = Path(os.getenv("STATE_FILE", "state.json"))
        
        if not state_file_path.is_absolute():
            self.state_file = root / state_file_path
        else:
            self.state_file = state_file_path
    
    def load_tasks(self) -> List[Task]:
        """Load tasks from tasks.json (read-only config).
        
        Returns:
            List of Task objects.
        
        Raises:
            FileNotFoundError: If tasks.json does not exist.
            json.JSONDecodeError: If tasks.json is invalid JSON.
        """
        if not self.tasks_file.exists():
            raise FileNotFoundError(f"tasks.json not found at {self.tasks_file}")
        
        with open(self.tasks_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        tasks = [Task.from_dict(item) for item in data]
        logger.debug(f"Loaded {len(tasks)} task configurations from {self.tasks_file}")
        return tasks
    
    def load_state(self) -> Dict[str, TaskState]:
        """Load task state from state.json.
        
        Returns:
            Dict of {task_id: TaskState}. Empty dict if file doesn't exist.
        """
        if not self.state_file.exists():
            logger.debug(f"State file not found at {self.state_file}, starting fresh")
            return {}
        
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            state_dict = {}
            for task_id, state_data in data.items():
                state_dict[task_id] = TaskState.from_dict(state_data)
            
            logger.debug(f"Loaded state for {len(state_dict)} tasks from {self.state_file}")
            return state_dict
        except Exception as e:
            logger.warning(f"Failed to load state file: {e}, starting fresh")
            return {}
    
    def save_state(self, state: Dict[str, TaskState]) -> None:
        """Save task state to state.json using atomic write.
        
        Writes to a temporary file first, then replaces the original
        to avoid corruption on interruption.
        
        Args:
            state: Dict of {task_id: TaskState}.
        """
        # Convert state to serializable dicts
        state_data = {task_id: ts.to_dict() for task_id, ts in state.items()}
        json_str = safe_json_dump(state_data)
        
        # Ensure directory exists
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to temporary file first (atomic write)
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=self.state_file.parent,
            suffix=".tmp",
            delete=False,
            encoding="utf-8"
        ) as tmp:
            tmp.write(json_str)
            tmp_path = tmp.name
        
        # Replace original with temp file (atomic on POSIX systems)
        tmp_path_obj = Path(tmp_path)
        tmp_path_obj.replace(self.state_file)
        
        logger.debug(f"Saved state for {len(state)} tasks to {self.state_file}")


class BitableStorage(StorageBackend):
    """Store tasks and state in Feishu Bitable (multi-dimensional table).
    
    Requires environment variables:
    - FEISHU_APP_ID
    - FEISHU_APP_SECRET
    - FEISHU_BITABLE_APP_TOKEN
    - FEISHU_BITABLE_TABLE_ID
    """
    
    def __init__(self):
        """Initialize BitableStorage from environment variables."""
        self.app_id = os.getenv("FEISHU_APP_ID")
        self.app_secret = os.getenv("FEISHU_APP_SECRET")
        self.bitable_token = os.getenv("FEISHU_BITABLE_APP_TOKEN")
        self.table_id = os.getenv("FEISHU_BITABLE_TABLE_ID")
        
        if not all([self.app_id, self.app_secret, self.bitable_token, self.table_id]):
            raise ValueError(
                "BitableStorage requires FEISHU_APP_ID, FEISHU_APP_SECRET, "
                "FEISHU_BITABLE_APP_TOKEN, and FEISHU_BITABLE_TABLE_ID"
            )
        
        self.access_token = None
        self.token_expires_at = 0
    
    def load_tasks(self) -> List[Task]:
        """Load task configurations from Bitable.
        
        Returns:
            List of Task objects from bitable.
        """
        # TODO: Implement fetching from Bitable
        # For now, fallback to JSON file
        fallback = JsonFileStorage()
        return fallback.load_tasks()
    
    def load_state(self) -> Dict[str, TaskState]:
        """Load task state from Bitable.
        
        Returns:
            Dict of {task_id: TaskState}.
        """
        # TODO: Implement fetching state from Bitable
        # For now, fallback to local
        fallback = JsonFileStorage()
        return fallback.load_state()
    
    def save_state(self, state: Dict[str, TaskState]) -> None:
        """Save task state to Bitable.
        
        Args:
            state: Dict of {task_id: TaskState}.
        """
        # TODO: Implement saving state to Bitable
        # For now, fallback to local
        fallback = JsonFileStorage()
        fallback.save_state(state)


def get_storage(state_file: Optional[str] = None) -> StorageBackend:
    """Factory function to get appropriate storage backend based on config.
    
    Args:
        state_file: Optional path to state file.
    
    Returns:
        StorageBackend instance.
    """
    persist_mode = os.getenv("PERSIST_STATE", "local").lower()
    
    if persist_mode == "bitable":
        return BitableStorage()
    else:
        # Default to JSON (covers 'local', 'repo', or any other value)
        return JsonFileStorage(state_file)
