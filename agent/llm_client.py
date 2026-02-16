"""Lightweight OpenAI-compatible LLM client for universal ad CLI."""

from __future__ import annotations

import logging
import os
import random
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit, urlunsplit

import requests


logger = logging.getLogger(__name__)


class LLMClient:
    """Simple chat completion client using OpenAI-compatible API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 45,
    ) -> None:
        self.api_key = (api_key or os.getenv("LLM_API_KEY") or "").strip()
        raw_base_url = (base_url or os.getenv("LLM_BASE_URL") or "").strip()
        self.model = (model if model is not None else os.getenv("LLM_MODEL") or "").strip()
        self.timeout = int(timeout)
        self.max_retries = 2

        if not self.api_key:
            raise ValueError("Missing LLM_API_KEY")
        if not raw_base_url:
            raise ValueError("Missing LLM_BASE_URL")
        if not self.model:
            raise ValueError("Missing LLM_MODEL")

        normalized = raw_base_url.rstrip("/")
        if normalized.endswith("/v1"):
            self.base_url = normalized
        else:
            self.base_url = f"{normalized}/v1"

    @staticmethod
    def _redact_url(url: str) -> str:
        parts = urlsplit(str(url or ""))
        host = parts.hostname or ""
        if parts.port:
            host = f"{host}:{parts.port}"
        return urlunsplit((parts.scheme, host, parts.path, "", ""))

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.9,
        max_tokens: int = 1200,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": float(temperature),
            "max_tokens": int(max_tokens),
        }
        if seed is not None:
            payload["seed"] = int(seed)

        request_url = f"{self.base_url}/chat/completions"

        response = None
        warned_retry = False
        redacted_url = self._redact_url(request_url)

        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(
                    request_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=self.timeout,
                )
            except requests.RequestException as exc:
                if attempt < self.max_retries:
                    if not warned_retry:
                        logger.warning("LLM transient failure, retrying with backoff: %s", exc)
                        warned_retry = True
                    sleep_s = (2 ** attempt) * 0.7 + random.uniform(0.0, 0.35)
                    time.sleep(sleep_s)
                    continue
                raise RuntimeError(f"LLM request failed: url={redacted_url}; error={exc}; body=") from exc

            status = int(response.status_code)
            if 200 <= status < 300:
                break

            body = ""
            try:
                body = (response.text or "")[:300]
            except Exception:
                body = ""

            if status in {429, 500, 502, 503, 504} and attempt < self.max_retries:
                if not warned_retry:
                    logger.warning("LLM HTTP transient status=%s, retrying with backoff", status)
                    warned_retry = True
                sleep_s = (2 ** attempt) * 0.7 + random.uniform(0.0, 0.35)
                time.sleep(sleep_s)
                continue

            raise RuntimeError(
                f"LLM request failed: url={redacted_url}; error={status} Client Error; body={body}"
            )

        if response is None:
            raise RuntimeError(f"LLM request failed: url={redacted_url}; error=unknown; body=")

        data = response.json()
        choice = ((data.get("choices") or [{}])[0]).get("message") or {}
        content = str(choice.get("content") or "").strip()

        return {
            "content": content,
            "model": data.get("model") or self.model,
            "usage": data.get("usage") or {},
            "request_url": self._redact_url(request_url),
            "raw": data,
        }
