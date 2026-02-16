"""Hot topics collection with strong fallback for universal ad generation."""

from __future__ import annotations

import logging
import os
import random
import re
import time
from typing import Any, Dict, List, Optional

import requests

from agent.content_pipeline.search import SearchResult

try:
    from agent.content_pipeline.search import search_sources_with_meta  # type: ignore
except Exception:
    search_sources_with_meta = None  # type: ignore

logger = logging.getLogger(__name__)


SERPER_URL = "https://google.serper.dev/search"


def _truncate(text: str, limit: int = 300) -> str:
    raw = str(text or "")
    if len(raw) <= limit:
        return raw
    return raw[:limit]


def _serper_search(query: str, num: int = 8) -> Dict[str, Any]:
    api_key = (os.getenv("SERPER_API_KEY") or "").strip()
    if not api_key:
        return {"ok": False, "status": None, "error": "SERPER_API_KEY missing", "data": None}

    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "q": str(query or "").strip(),
        "gl": "cn",
        "hl": "zh-CN",
        "num": int(num),
    }

    max_attempts = 3
    last_status: Optional[int] = None
    last_error = ""

    for attempt in range(max_attempts):
        try:
            response = requests.post(SERPER_URL, headers=headers, json=payload, timeout=15)
        except requests.RequestException as exc:
            last_error = str(exc)
            if attempt < max_attempts - 1:
                sleep_s = (2 ** attempt) * 0.6 + random.uniform(0.0, 0.35)
                time.sleep(sleep_s)
                continue
            return {"ok": False, "status": None, "error": last_error, "data": None}

        status = int(response.status_code)
        last_status = status
        body = _truncate(response.text or "")

        if 200 <= status < 300:
            try:
                return {"ok": True, "status": status, "error": None, "data": response.json()}
            except Exception as exc:
                return {"ok": False, "status": status, "error": f"invalid_json:{exc}; body={body}", "data": None}

        if status == 400:
            return {"ok": False, "status": status, "error": f"serper_400 body={body}", "data": None}

        if status in {401, 403, 429, 500, 502, 503, 504}:
            if attempt < max_attempts - 1 and status in {429, 500, 502, 503, 504}:
                sleep_s = (2 ** attempt) * 0.7 + random.uniform(0.0, 0.35)
                time.sleep(sleep_s)
                continue
            return {"ok": False, "status": status, "error": f"serper_http_{status} body={body}", "data": None}

        return {"ok": False, "status": status, "error": f"serper_http_{status} body={body}", "data": None}

    return {"ok": False, "status": last_status, "error": last_error or "serper_unknown_error", "data": None}


def serper_self_check(query: str) -> dict:
    result = _serper_search(query=query or "测试", num=1)
    return {
        "ok": bool(result.get("ok")),
        "status": result.get("status"),
        "error": result.get("error"),
    }


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    output: List[str] = []
    for item in items:
        text = str(item or "").strip()
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        output.append(text)
    return output


def _topic_from_text(text: str) -> List[str]:
    raw = str(text or "").strip()
    if not raw:
        return []

    cleaned = re.sub(r"\s+", " ", raw)
    chunks = re.split(r"[：:|｜，,。；;（）()【】\[\]·]", cleaned)
    candidates: List[str] = []

    for chunk in chunks:
        phrase = chunk.strip(" -_\t")
        if len(phrase) < 4:
            continue
        if len(phrase) > 22:
            phrase = phrase[:22].rstrip("、，,。 ")
        if phrase:
            candidates.append(phrase)

    return candidates[:3]


def _build_fallback_topics(category: str, city: Optional[str]) -> List[str]:
    scope = str(city or "全国").strip() or "全国"
    base = str(category or "该品类").strip() or "该品类"

    return [
        f"{base}近期价格与预算分层怎么选",
        f"{scope}{base}选购避坑高频问题",
        f"同预算下{base}对比维度与决策顺序",
        f"新手入门{base}先看哪些核心指标",
        f"{base}真实使用场景下的性能差异",
        f"{base}口碑测评里反复出现的优缺点",
        f"{base}今年讨论热度上升的配置趋势",
        f"{base}购买前必问清单与FAQ",
        f"{base}从需求到下单的最短决策路径",
        f"{scope}消费者对{base}服务体验关注点",
    ]


def _safe_source(result: SearchResult) -> Dict[str, str]:
    return {
        "title": str(result.title or "").strip(),
        "url": str(result.url or "").strip(),
        "snippet": str(result.snippet or "").strip(),
    }


def collect_hot_topics(category: str, city: Optional[str] = None, seed: Optional[int] = None) -> Dict[str, Any]:
    """Collect hot topics for a category with best-effort search and strong fallback.

    Returns:
        {
            "hot_topics": List[str],
            "sources": List[{"title","url","snippet"}],
            "fallback_used": bool,
            "warnings": List[str],
            "provider": str
        }
    """
    category = str(category or "").strip()
    city = str(city or "").strip() or None

    if not category:
        raise ValueError("category is required")

    warnings: List[str] = []
    hot_topics: List[str] = []
    sources: List[Dict[str, str]] = []
    fallback_used = False
    provider = "serper"
    serper_ok = False
    serper_status: Optional[int] = None

    serper_key = (os.getenv("SERPER_API_KEY") or "").strip()
    if serper_key:
        query_parts = [category, "热点", "趋势", "选购", "避坑", "测评"]
        if city:
            query_parts.insert(1, city)
        query = " ".join(query_parts)

        try:
            serper_result = _serper_search(query=query, num=8)
            serper_ok = bool(serper_result.get("ok"))
            serper_status = serper_result.get("status")

            if not serper_ok:
                warnings.append(
                    f"serper_failed status={serper_status} error={serper_result.get('error') or 'unknown'}"
                )
            else:
                data = serper_result.get("data") or {}
                organic = data.get("organic") or []
                for row in organic[:8]:
                    result = SearchResult(
                        title=str((row or {}).get("title") or "").strip(),
                        url=str((row or {}).get("link") or "").strip(),
                        snippet=str((row or {}).get("snippet") or "").strip(),
                    )
                    sources.append(_safe_source(result))
                    hot_topics.extend(_topic_from_text(result.title))
                    hot_topics.extend(_topic_from_text(result.snippet))

                if not organic:
                    warnings.append("serper_no_results status=200 error=empty_organic")
        except Exception as exc:
            warnings.append(f"serper_exception: {exc}")
            logger.warning("collect_hot_topics serper failed: %s", exc)
    else:
        warnings.append("SERPER_API_KEY missing, use fallback hot topics")

    if len(hot_topics) < 5:
        fallback_used = True
        fallback_topics = _build_fallback_topics(category=category, city=city)
        if seed is not None:
            rng = random.Random(seed)
            rng.shuffle(fallback_topics)
        hot_topics.extend(fallback_topics)

    hot_topics = _dedupe_keep_order(hot_topics)

    if seed is not None:
        rng = random.Random(seed + 17)
        sampled = list(hot_topics)
        rng.shuffle(sampled)
        hot_topics = sampled

    hot_topics = hot_topics[:12]
    if len(hot_topics) < 5:
        emergency = _build_fallback_topics(category=category, city=city)
        hot_topics = _dedupe_keep_order(hot_topics + emergency)[:8]
        fallback_used = True

    return {
        "hot_topics": hot_topics,
        "sources": sources[:12],
        "fallback_used": fallback_used,
        "warnings": warnings,
        "provider": provider,
        "serper_ok": serper_ok,
        "serper_status": serper_status,
    }
