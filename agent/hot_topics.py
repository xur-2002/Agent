"""Hot topics collection with strong fallback for universal ad generation."""

from __future__ import annotations

import logging
import os
import random
import re
from typing import Any, Dict, List, Optional

from agent.content_pipeline import search as search_module

SearchResult = search_module.SearchResult

logger = logging.getLogger(__name__)


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

    serper_key = (os.getenv("SERPER_API_KEY") or "").strip()
    if serper_key:
        query_parts = [category, "热点", "趋势", "选购", "避坑", "测评"]
        if city:
            query_parts.insert(1, city)
        query = " ".join(query_parts)

        try:
            if hasattr(search_module, "search_sources_with_meta"):
                results, errors, meta = search_module.search_sources_with_meta(query=query, limit=8)
                provider = str((meta or {}).get("provider") or "serper")
            else:
                provider_client = search_module.get_search_provider("serper")
                result_rows = provider_client.search(query=query, limit=8)
                results = result_rows or []
                errors = []
                meta = {"provider": "serper", "status_code": 200, "error_type": None}
                provider = "serper"

            if errors:
                warnings.append(f"search_errors: {' | '.join(errors)}")

            for result in results or []:
                sources.append(_safe_source(result))
                hot_topics.extend(_topic_from_text(result.title))
                hot_topics.extend(_topic_from_text(result.snippet))

            if not results:
                status = (meta or {}).get("status_code")
                err = (meta or {}).get("error_type")
                warnings.append(f"serper_no_results status={status} error={err}")
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
    }
