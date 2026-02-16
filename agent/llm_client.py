"""Lightweight OpenAI-compatible LLM client for universal ad CLI."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit, urlunsplit

import requests


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
        self.model = (model or os.getenv("LLM_MODEL") or "gpt-4o-mini").strip()
        self.timeout = int(timeout)

        if not self.api_key:
            raise ValueError("Missing LLM_API_KEY")
        if not raw_base_url:
            raise ValueError("Missing LLM_BASE_URL")

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

        response = requests.post(
            request_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.timeout,
        )
        try:
            response.raise_for_status()
        except requests.RequestException as exc:
            body = ""
            try:
                body = response.text[:300]
            except Exception:
                body = ""
            redacted_url = self._redact_url(request_url)
            raise RuntimeError(f"LLM request failed: url={redacted_url}; error={exc}; body={body}") from exc

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
