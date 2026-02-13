"""Utility functions for the agent."""

import json
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Optional, TypeVar
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


def parse_iso_datetime(iso_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO 8601 datetime string, return None if invalid."""
    if not iso_str:
        return None
    try:
        return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def now_utc() -> datetime:
    """Get current time in UTC."""
    return datetime.now(timezone.utc)


def now_iso() -> str:
    """Get current time as ISO 8601 string."""
    return now_utc().isoformat()


def retry(func: Callable[..., T], max_attempts: int = 3, delay_sec: float = 1.0) -> T:
    """Retry a function with exponential backoff.
    
    Args:
        func: Function to retry.
        max_attempts: Number of attempts.
        delay_sec: Initial delay between retries.
    
    Returns:
        Result of function call.
    
    Raises:
        Exception: If all attempts fail.
    """
    last_exc = None
    for attempt in range(max_attempts):
        try:
            return func()
        except Exception as e:
            last_exc = e
            if attempt < max_attempts - 1:
                wait = delay_sec * (2 ** attempt)
                logger.debug(f"Retry attempt {attempt + 1}/{max_attempts} after {wait}s: {e}")
                time.sleep(wait)
    
    raise last_exc or Exception("All retries failed")


def safe_json_dump(data: Any, indent: int = 2) -> str:
    """Safely dump data to JSON string, handling datetime objects.
    
    Args:
        data: Data to dump.
        indent: Indentation level.
    
    Returns:
        JSON string.
    """
    def default_handler(obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
    
    return json.dumps(data, indent=indent, default=default_handler)


def truncate_str(s: str, max_len: int = 400) -> str:
    """Truncate string to max length.
    
    Args:
        s: String to truncate.
        max_len: Maximum length.
    
    Returns:
        Truncated string.
    """
    if len(s) <= max_len:
        return s
    return s[:max_len - 3] + "..."
