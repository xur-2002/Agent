"""Telegram notification module."""

import os
import requests


def send_message(text: str) -> None:
    """Send a message to Telegram using Bot API.
    
    Args:
        text: The message text to send.
    
    Raises:
        ValueError: If required environment variables are not set.
        requests.RequestException: If the HTTP request fails.
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")
    if not chat_id:
        raise ValueError("TELEGRAM_CHAT_ID environment variable not set")
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    
    # Set timeout to 20 seconds for robustness
    response = requests.post(url, json=payload, timeout=20)
    response.raise_for_status()
