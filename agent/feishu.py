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
