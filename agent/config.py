"""Configuration management for the agent."""

import os
from typing import Dict, Any


class Config:
    """Centralized configuration from environment variables."""

    # Feishu integration
    FEISHU_WEBHOOK_URL: str = os.getenv("FEISHU_WEBHOOK_URL", "")
    FEISHU_MENTION: str = os.getenv("FEISHU_MENTION", "")  # Optional @user_id on failure

    # State persistence
    PERSIST_STATE: str = os.getenv("PERSIST_STATE", "local")  # local, repo, bitable (repo requires git)
    STATE_FILE: str = os.getenv("STATE_FILE", "state.json")  # Where to persist task state

    # Concurrency & reliability
    MAX_CONCURRENCY: int = int(os.getenv("MAX_CONCURRENCY", "5"))
    RETRY_COUNT: int = int(os.getenv("RETRY_COUNT", "2"))
    RETRY_BACKOFF: str = os.getenv("RETRY_BACKOFF", "1s,3s,7s")  # Exponential backoff timings

    # Timezone & execution
    TIMEZONE: str = os.getenv("TIMEZONE", "UTC")
    DRY_RUN: bool = os.getenv("DRY_RUN", "0").lower() in ("1", "true", "yes")

    # GitHub (for repo persistence)
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")

    # Optional: Bitable backend
    FEISHU_TABLE_APP_ID: str = os.getenv("FEISHU_TABLE_APP_ID", "")
    FEISHU_TABLE_TABLE_ID: str = os.getenv("FEISHU_TABLE_TABLE_ID", "")
    FEISHU_APP_ID: str = os.getenv("FEISHU_APP_ID", "")
    FEISHU_APP_SECRET: str = os.getenv("FEISHU_APP_SECRET", "")
    
    # LLM Provider (article generation)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq").lower()  # groq, openai, dry_run
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    # Content pipeline (Direction 1)
    SEARCH_PROVIDER: str = os.getenv("SEARCH_PROVIDER", "serper")
    SERPER_API_KEY: str = os.getenv("SERPER_API_KEY", "")
    BING_SEARCH_KEY: str = os.getenv("BING_SEARCH_KEY", "")
    # Daily content generation defaults
    CONTENT_DAILY_QUOTA: int = int(os.getenv("CONTENT_DAILY_QUOTA", "3"))
    SEED_KEYWORDS: str = os.getenv("SEED_KEYWORDS", "")  # comma-separated
    COOLDOWN_DAYS: int = int(os.getenv("COOLDOWN_DAYS", "3"))
    
    # Email delivery
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASS: str = os.getenv("SMTP_PASS", "")
    SMTP_TO: str = os.getenv("SMTP_TO", "")
    
    # Content directories
    CONTENT_DRAFTS_DIR: str = os.getenv("CONTENT_DRAFTS_DIR", "drafts")
    CONTENT_PUBLISH_KITS_DIR: str = os.getenv("CONTENT_PUBLISH_KITS_DIR", "publish_kits")

    @classmethod
    def validate(cls) -> None:
        """Validate required configuration."""
        if not cls.FEISHU_WEBHOOK_URL:
            raise ValueError("FEISHU_WEBHOOK_URL environment variable is required")

    @classmethod
    def get_retry_backoff_list(cls) -> list[float]:
        """Parse retry backoff timings (e.g., '1s,3s,7s' -> [1.0, 3.0, 7.0])."""
        backoffs = []
        for item in cls.RETRY_BACKOFF.split(","):
            item = item.strip()
            if item.endswith("s"):
                backoffs.append(float(item[:-1]))
            else:
                backoffs.append(float(item))
        return backoffs

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Return all config as dict."""
        return {
            "FEISHU_WEBHOOK_URL": "***" if cls.FEISHU_WEBHOOK_URL else "",
            "FEISHU_MENTION": cls.FEISHU_MENTION,
            "PERSIST_STATE": cls.PERSIST_STATE,
            "STATE_FILE": cls.STATE_FILE,
            "MAX_CONCURRENCY": cls.MAX_CONCURRENCY,
            "RETRY_COUNT": cls.RETRY_COUNT,
            "RETRY_BACKOFF": cls.RETRY_BACKOFF,
            "TIMEZONE": cls.TIMEZONE,
            "DRY_RUN": cls.DRY_RUN,
            "GITHUB_TOKEN": "***" if cls.GITHUB_TOKEN else "",
        }
