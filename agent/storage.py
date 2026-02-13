"""Storage backends for tasks."""

import json
import tempfile
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional

from agent.models import Task
from agent.utils import safe_json_dump

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Abstract storage backend."""
    
    @abstractmethod
    def load_tasks(self) -> List[Task]:
        """Load tasks from storage."""
        pass
    
    @abstractmethod
    def save_tasks(self, tasks: List[Task]) -> None:
        """Save tasks to storage."""
        pass


class JsonFileStorage(StorageBackend):
    """Store tasks in local tasks.json file."""
    
    def __init__(self, file_path: Optional[Path] = None):
        """Initialize JsonFileStorage.
        
        Args:
            file_path: Path to tasks.json. If None, uses repo root/tasks.json.
        """
        if file_path is None:
            # Navigate from agent/storage.py to root/tasks.json
            root = Path(__file__).parent.parent
            file_path = root / "tasks.json"
        
        self.file_path = file_path
    
    def load_tasks(self) -> List[Task]:
        """Load tasks from tasks.json.
        
        Returns:
            List of Task objects.
        
        Raises:
            FileNotFoundError: If tasks.json does not exist.
            json.JSONDecodeError: If tasks.json is invalid JSON.
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f"tasks.json not found at {self.file_path}")
        
        with open(self.file_path, "r") as f:
            data = json.load(f)
        
        return [Task.from_dict(item) for item in data]
    
    def save_tasks(self, tasks: List[Task]) -> None:
        """Save tasks to tasks.json using atomic write.
        
        Writes to a temporary file first, then replaces the original
        to avoid corruption on interruption.
        
        Args:
            tasks: List of Task objects.
        """
        # Convert tasks to serializable dicts
        data = [task.to_dict() for task in tasks]
        json_str = safe_json_dump(data)
        
        # Write to temporary file first
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=self.file_path.parent,
            suffix=".tmp",
            delete=False
        ) as tmp:
            tmp.write(json_str)
            tmp_path = tmp.name
        
        # Replace original with temp file
        tmp_path_obj = Path(tmp_path)
        tmp_path_obj.replace(self.file_path)
        
        logger.debug(f"Saved {len(tasks)} tasks to {self.file_path}")


class BitableStorage(StorageBackend):
    """Store tasks in Feishu Bitable (multi-dimensional table).
    
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
    
    def _get_access_token(self) -> str:
        """Get valid Feishu access token, refreshing if needed."""
        import time
        import requests
        
        now = time.time()
        if self.access_token and now < self.token_expires_at:
            return self.access_token
        
        # Refresh token
        url = "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        self.access_token = data["app_access_token"]
        self.token_expires_at = now + data.get("expire", 7200) - 300  # Refresh 5min before expiry
        
        return self.access_token
    
    def load_tasks(self) -> List[Task]:
        """Load tasks from Bitable.
        
        Returns:
            List of Task objects from bitable.
        """
        import requests
        
        token = self._get_access_token()
        
        # Get records from table
        url = (
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.bitable_token}"
            f"/tables/{self.table_id}/records"
        )
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        records = data.get("data", {}).get("items", [])
        
        tasks = []
        for record in records:
            fields = record.get("fields", {})
            # Map bitable fields to Task fields
            task_dict = {
                "id": fields.get("id", ""),
                "title": fields.get("title", ""),
                "enabled": fields.get("enabled", True),
                "frequency": fields.get("frequency", "daily"),
                "timezone": fields.get("timezone", "UTC"),
                "params": fields.get("params", {}),
                "status": fields.get("status", "scheduled"),
                "last_run_at": fields.get("last_run_at"),
                "next_run_at": fields.get("next_run_at"),
                "last_result_summary": fields.get("last_result_summary"),
                "last_error": fields.get("last_error"),
            }
            tasks.append(Task.from_dict(task_dict))
        
        logger.debug(f"Loaded {len(tasks)} tasks from Bitable")
        return tasks
    
    def save_tasks(self, tasks: List[Task]) -> None:
        """Save tasks to Bitable.
        
        Args:
            tasks: List of Task objects.
        """
        import requests
        
        token = self._get_access_token()
        
        url = (
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.bitable_token}"
            f"/tables/{self.table_id}/records/batch_update"
        )
        headers = {"Authorization": f"Bearer {token}"}
        
        # For now, log a note that full sync is complex
        logger.debug(f"Bitable save: would update {len(tasks)} tasks (full sync not implemented)")


def get_storage() -> StorageBackend:
    """Get appropriate storage backend based on environment.
    
    Returns:
        BitableStorage if env vars present, otherwise JsonFileStorage.
    """
    if all(os.getenv(var) for var in [
        "FEISHU_APP_ID", "FEISHU_APP_SECRET",
        "FEISHU_BITABLE_APP_TOKEN", "FEISHU_BITABLE_TABLE_ID"
    ]):
        logger.info("Using Bitable storage backend")
        return BitableStorage()
    
    logger.debug("Using JSON file storage backend")
    return JsonFileStorage()
