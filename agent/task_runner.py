"""Task execution module."""

import logging
import time
import requests
from datetime import datetime, timezone
from typing import Dict, Any

from agent.models import Task, TaskResult
from agent.utils import now_utc, truncate_str

logger = logging.getLogger(__name__)


def run_task(task: Task) -> TaskResult:
    """Execute a task and return the result.
    
    Dispatches to specific task implementations based on task.id.
    
    Args:
        task: Task object to execute.
    
    Returns:
        TaskResult with status, summary, metrics, and optional error.
    """
    task_id = task.id
    start_time = now_utc()
    
    logger.info(f"[{task_id}] Starting task execution")
    
    try:
        if task_id == "daily_briefing":
            result = run_daily_briefing(task)
        elif task_id == "health_check_url":
            result = run_health_check_url(task)
        elif task_id == "rss_watch":
            result = run_rss_watch(task)
        else:
            raise ValueError(f"Unknown task ID: {task_id}")
        
        # Add duration
        result.duration_sec = (now_utc() - start_time).total_seconds()
        logger.info(f"[{task_id}] Task completed: {result.status} ({result.duration_sec:.2f}s)")
        return result
    
    except Exception as e:
        duration = (now_utc() - start_time).total_seconds()
        error_msg = str(e)
        logger.error(f"[{task_id}] Task failed after {duration:.2f}s: {error_msg}")
        return TaskResult(
            status="failed",
            summary=f"Task execution failed",
            error=error_msg,
            duration_sec=duration
        )


def run_daily_briefing(task: Task) -> TaskResult:
    """Generate a daily briefing.
    
    Args:
        task: Task object (may contain custom params).
    
    Returns:
        TaskResult with briefing summary.
    """
    now = now_utc()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M UTC")
    
    briefing = (
        f"Daily Briefing for {date_str}\n"
        f"Generated at {time_str}\n"
        f"Status: Agent is running successfully.\n"
        f"All systems operational."
    )
    
    summary = truncate_str(briefing)
    
    return TaskResult(
        status="ok",
        summary=summary,
        metrics={"type": "briefing"}
    )


def run_health_check_url(task: Task) -> TaskResult:
    """Check if a URL is accessible.
    
    Expected params:
    - url: URL to check (required)
    - timeout_sec: Request timeout (default 10)
    - expected_status: Expected HTTP status code (default 200)
    
    Args:
        task: Task with params.
    
    Returns:
        TaskResult with health check result.
    """
    params = task.params
    url = params.get("url")
    timeout_sec = params.get("timeout_sec", 10)
    expected_status = params.get("expected_status", 200)
    
    if not url:
        raise ValueError("health_check_url requires 'url' parameter")
    
    try:
        start = time.time()
        response = requests.get(url, timeout=timeout_sec)
        duration = time.time() - start
        
        if response.status_code == expected_status:
            summary = f"✓ {url} returned {response.status_code} ({duration:.2f}s)"
            return TaskResult(
                status="ok",
                summary=summary,
                metrics={"status_code": response.status_code, "response_time_sec": duration}
            )
        else:
            summary = f"✗ {url} returned {response.status_code} (expected {expected_status})"
            return TaskResult(
                status="failed",
                summary=summary,
                error=f"Status mismatch: got {response.status_code}, expected {expected_status}",
                metrics={"status_code": response.status_code}
            )
    
    except requests.RequestException as e:
        return TaskResult(
            status="failed",
            summary=f"✗ Health check failed for {url}",
            error=str(e)
        )


def run_rss_watch(task: Task) -> TaskResult:
    """Watch an RSS feed for new items.
    
    Expected params:
    - feed_url: URL to RSS feed (required)
    - max_items: Max items to retrieve (default 3)
    - last_seen_guid: Previous GUID to track (optional, stored in params)
    
    Args:
        task: Task with params.
    
    Returns:
        TaskResult with feed items.
    """
    params = task.params
    feed_url = params.get("feed_url")
    max_items = params.get("max_items", 3)
    last_seen_guid = params.get("last_seen_guid")
    
    if not feed_url:
        raise ValueError("rss_watch requires 'feed_url' parameter")
    
    try:
        import feedparser
    except ImportError:
        return TaskResult(
            status="failed",
            summary="RSS watch unavailable",
            error="feedparser not installed (optional dependency)"
        )
    
    try:
        feed = feedparser.parse(feed_url)
        
        if feed.bozo:
            logger.warning(f"[rss_watch] Feed parse warning: {feed.bozo_exception}")
        
        items = []
        new_guid = last_seen_guid
        
        for entry in feed.entries[:max_items]:
            guid = entry.get("id") or entry.get("link")
            
            # Track first new item
            if not new_guid and guid:
                new_guid = guid
            
            # Skip if we've seen this before
            if guid == last_seen_guid:
                break
            
            items.append({
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "summary": (entry.get("summary", "")[:100] + "...") if entry.get("summary") else ""
            })
        
        # Update cursor in params for next run
        if new_guid:
            task.params["last_seen_guid"] = new_guid
        
        summary = f"Found {len(items)} new items from {feed_url.split('/')[-1]}"
        metrics = {
            "items_count": len(items),
            "feed_title": feed.feed.get("title", ""),
            "has_updates": len(items) > 0
        }
        
        return TaskResult(
            status="ok",
            summary=summary,
            metrics=metrics
        )
    
    except Exception as e:
        return TaskResult(
            status="failed",
            summary=f"Failed to fetch RSS feed",
            error=str(e)
        )
