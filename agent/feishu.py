"""Feishu (Lark) notification module via Incoming Webhook Bot."""

import os
import requests


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
