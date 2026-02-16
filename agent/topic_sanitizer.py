"""Sanitize hot topics and source snippets with simple blocklist rules."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

BLOCKLIST_TERMS: List[str] = [
    "外围",
    "地陪",
    "一条龙",
    "博彩",
    "彩票",
    "成人",
    "客服微信",
    "空降",
    "模特空降",
    "上门服务",
]


def _match_term(text: str) -> str:
    value = str(text or "")
    lower_value = value.lower()
    for term in BLOCKLIST_TERMS:
        if term.lower() in lower_value:
            return term
    return ""


def sanitize_hot_topics(
    hot_topics: List[str],
    sources: List[Dict[str, Any]],
) -> Tuple[List[str], List[Dict[str, Any]], Dict[str, Any]]:
    """Remove unsafe topics/sources by blocklist terms.

    Returns:
        clean_topics, clean_sources, report
    """
    removed_items: List[Dict[str, Any]] = []

    clean_topics: List[str] = []
    for topic in list(hot_topics or []):
        hit = _match_term(topic)
        if hit:
            removed_items.append(
                {
                    "type": "topic",
                    "reason": "blocklist_term",
                    "matched_term": hit,
                    "field": "hot_topics",
                    "original": str(topic),
                }
            )
            continue
        clean_topics.append(str(topic))

    clean_sources: List[Dict[str, Any]] = []
    for source in list(sources or []):
        item = dict(source or {})
        matched_field = ""
        matched_term = ""
        for field in ("title", "snippet", "url"):
            hit = _match_term(item.get(field, ""))
            if hit:
                matched_field = field
                matched_term = hit
                break

        if matched_term:
            removed_items.append(
                {
                    "type": "source",
                    "reason": "blocklist_term",
                    "matched_term": matched_term,
                    "field": matched_field,
                    "original": {
                        "title": str(item.get("title") or ""),
                        "url": str(item.get("url") or ""),
                        "snippet": str(item.get("snippet") or ""),
                    },
                }
            )
            continue

        clean_sources.append(item)

    report: Dict[str, Any] = {
        "topic_before": len(hot_topics or []),
        "topic_after": len(clean_topics),
        "source_before": len(sources or []),
        "source_after": len(clean_sources),
        "removed_items": removed_items,
        "removed_items_count": len(removed_items),
    }

    if removed_items:
        logger.warning("topic sanitizer removed %d unsafe items", len(removed_items))

    return clean_topics, clean_sources, report
