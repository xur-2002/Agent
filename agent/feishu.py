"""Feishu (Lark) notification module via Incoming Webhook Bot."""

import os
import logging
import requests
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def send_text(text: str) -> None:
    """Send a text message to Feishu using Incoming Webhook Bot.
    
    Args:
        text: The message text to send.
    
    Raises:
        ValueError: If FEISHU_WEBHOOK_URL environment variable is not set.
        requests.RequestException: If the HTTP request fails.
    """
    webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
    
    if not webhook_url:
        raise ValueError("FEISHU_WEBHOOK_URL environment variable not set")
    
    payload = {
        "msg_type": "text",
        "content": {
            "text": text
        }
    }
    
    # Set timeout to 20 seconds for robustness
    response = requests.post(webhook_url, json=payload, timeout=20)
    response.raise_for_status()
    
    logger.debug(f"Feishu text message sent (status: {response.status_code})")


def send_card(title: str, sections: List[Dict[str, Any]]) -> None:
    """Send an interactive card to Feishu.
    
    Args:
        title: Card title.
        sections: List of section dicts with content.
    
    Raises:
        ValueError: If FEISHU_WEBHOOK_URL is not set.
        requests.RequestException: If the HTTP request fails.
    """
    webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
    
    if not webhook_url:
        raise ValueError("FEISHU_WEBHOOK_URL environment variable not set")
    
    # Build card payload
    payload = {
        "msg_type": "interactive",
        "card": {
            "elements": [
                {
                    "tag": "markdown",
                    "content": f"## {title}"
                }
            ]
        }
    }
    
    # Add sections as dividers and text
    for section in sections:
        if "title" in section:
            payload["card"]["elements"].append({
                "tag": "markdown",
                "content": f"**{section['title']}**"
            })
        
        if "content" in section:
            payload["card"]["elements"].append({
                "tag": "markdown",
                "content": section["content"]
            })
    
    response = requests.post(webhook_url, json=payload, timeout=20)
    response.raise_for_status()
    
    logger.debug(f"Feishu card sent (status: {response.status_code})")


def send_alert(task_id: str, title: str, error: str) -> None:
    """Send an alert card for a failed task.
    
    Args:
        task_id: ID of the failed task.
        title: Task title.
        error: Error message.
    
    Raises:
        ValueError: If FEISHU_WEBHOOK_URL is not set.
        requests.RequestException: If the HTTP request fails.
    """
    webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
    
    if not webhook_url:
        raise ValueError("FEISHU_WEBHOOK_URL environment variable not set")
    
    payload = {
        "msg_type": "interactive",
        "card": {
            "elements": [
                {
                    "tag": "markdown",
                    "content": f"❌ **Task Failed: {title}**"
                },
                {
                    "tag": "markdown",
                    "content": f"**Task ID:** {task_id}\n**Error:** {error[:500]}"
                }
            ]
        }
    }
    
    response = requests.post(webhook_url, json=payload, timeout=20)
    response.raise_for_status()
    
    logger.debug(f"Feishu alert sent (status: {response.status_code})")


def send_rich_card(
    executed_tasks: List[Dict[str, Any]],
    failed_tasks: List[Dict[str, Any]],
    duration_sec: float,
    all_success: bool,
    run_id: str
) -> None:
    """Send a rich Feishu card with consolidated task execution results.
    
    Args:
        executed_tasks: List of successful task results (dicts with id, title, summary, duration, metrics).
        failed_tasks: List of failed task results (dicts with id, title, error, duration).
        duration_sec: Total run duration in seconds.
        all_success: Whether all tasks succeeded.
        run_id: Unique run identifier.
    
    Raises:
        ValueError: If FEISHU_WEBHOOK_URL is not set.
        requests.RequestException: If the HTTP request fails.
    """
    webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
    
    if not webhook_url:
        raise ValueError("FEISHU_WEBHOOK_URL environment variable not set")
    
    # Ensure lists are valid
    if executed_tasks is None:
        executed_tasks = []
    if failed_tasks is None:
        failed_tasks = []
    
    # Determine status emoji and color
    status_emoji = "✅" if all_success else "⚠️"
    status_text = "🟢 All Pass" if all_success else "🔴 Failures"
    
    # Build card elements
    elements = []
    
    # Title
    elements.append({
        "tag": "markdown",
        "content": f"## {status_emoji} Agent Run Results"
    })
    
    # Summary section
    summary_content = (
        f"**Status:** {status_text}\n"
        f"**Tasks:** {len(executed_tasks)} ✓ · {len(failed_tasks)} ✗\n"
        f"**Duration:** {duration_sec:.2f}s\n"
        f"**Run ID:** `{run_id}`"
    )
    elements.append({
        "tag": "markdown",
        "content": summary_content
    })
    
    # Successful tasks section (if any)
    if executed_tasks:
        success_header = f"**✅ Successful Tasks ({len(executed_tasks)})**"
        elements.append({
            "tag": "markdown",
            "content": success_header
        })
        
        for task in executed_tasks[:5]:  # Limit to 5 for readability
            task_summary = task.get("summary", "No summary") or "No summary"
            if len(task_summary) > 60:
                task_summary = task_summary[:57] + "..."
            
            task_content = (
                f"**{task.get('title', 'Unknown')}** ({task.get('duration', 0):.2f}s)\n"
                f"_{task_summary}_"
            )
            elements.append({
                "tag": "markdown",
                "content": task_content
            })
        
        if len(executed_tasks) > 5:
            elements.append({
                "tag": "markdown",
                "content": f"_... and {len(executed_tasks) - 5} more_"
            })
    
    # Failed tasks section (if any)
    if failed_tasks:
        failed_header = f"**❌ Failed Tasks ({len(failed_tasks)})**"
        elements.append({
            "tag": "markdown",
            "content": failed_header
        })
        
        for task in failed_tasks[:5]:  # Limit to 5 for readability
            error_msg = task.get("error", "Unknown error") or "Unknown error"
            if len(error_msg) > 50:
                error_msg = error_msg[:47] + "..."
            
            task_content = (
                f"**{task.get('title', 'Unknown')}**\n"
                f"_Error: {error_msg}_"
            )
            elements.append({
                "tag": "markdown",
                "content": task_content
            })
        
        if len(failed_tasks) > 5:
            elements.append({
                "tag": "markdown",
                "content": f"_... and {len(failed_tasks) - 5} more_"
            })
    
    # Build full payload
    payload = {
        "msg_type": "interactive",
        "card": {
            "elements": elements
        }
    }
    
    response = requests.post(webhook_url, json=payload, timeout=20)
    response.raise_for_status()
    
    logger.debug(f"Feishu rich card sent (status: {response.status_code})")


def send_alert_card(failed_tasks: List[Dict[str, Any]], run_id: str) -> None:
    """Send a dedicated alert card for failed tasks.
    
    Args:
        failed_tasks: List of failed task results (dicts with id, title, error).
        run_id: Unique run identifier for tracking.
    
    Raises:
        ValueError: If FEISHU_WEBHOOK_URL is not set.
        requests.RequestException: If the HTTP request fails.
    """
    if not failed_tasks:
        logger.debug("No failed tasks, skipping alert card")
        return
    
    webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
    
    if not webhook_url:
        raise ValueError("FEISHU_WEBHOOK_URL environment variable not set")
    
    # Build alert elements
    elements = []
    
    # Alert header
    elements.append({
        "tag": "markdown",
        "content": f"## 🚨 Task Failures Alert"
    })
    
    elements.append({
        "tag": "markdown",
        "content": f"**Run ID:** `{run_id}`\n**Failed Count:** {len(failed_tasks)}"
    })
    
    # List each failed task with error
    for task in failed_tasks[:10]:  # Limit to 10 for readability
        error_msg = task.get("error", "Unknown error")
        if len(error_msg) > 80:
            error_msg = error_msg[:77] + "..."
        
        task_content = (
            f"**{task['title']}**\n"
            f"```\n{error_msg}\n```"
        )
        elements.append({
            "tag": "markdown",
            "content": task_content
        })
    
    if len(failed_tasks) > 10:
        elements.append({
            "tag": "markdown",
            "content": f"_... and {len(failed_tasks) - 10} more failures_"
        })
    
    # Build payload
    payload = {
        "msg_type": "interactive",
        "card": {
            "elements": elements
        }
    }
    
    response = requests.post(webhook_url, json=payload, timeout=20)
    response.raise_for_status()
    
    logger.debug(f"Feishu alert card sent (status: {response.status_code})")
