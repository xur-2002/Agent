"""Google Trends RSS based topic selector with cooldown and fallback to seed keywords.

Provides: select_topics(seed_keywords, daily_quota, geo, cooldown_days, state)

Note: daily_quota can be overridden by env var TOP_N
"""
from typing import List, Dict, Any
import feedparser
import random
import os
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def _fetch_trends_rss(geo: str) -> List[Dict[str, Any]]:
    url = f"https://trends.google.com/trending/rss?geo={geo}"
    d = feedparser.parse(url)
    items = []
    if getattr(d, 'bozo', False):
        raise RuntimeError('Failed to parse RSS')
    for i, entry in enumerate(d.entries or []):
        title = entry.get('title', '').strip()
        summary = entry.get('summary', '')
        link = entry.get('link', '')
        items.append({
            'topic': title,
            'rank': i + 1,
            'explain': summary,
            'source': 'google_trends_rss',
        })
    return items


def select_topics(seed_keywords: List[str], daily_quota: int = 3, geo: str = 'US', cooldown_days: int = 3, state: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """Return list of topics (dict) of length up to daily_quota.

    state: dict with previously generated topics {'recent_topics': [{'topic': str, 'date': 'YYYY-MM-DD'}]}
    
    Supports env var TOP_N to override daily_quota
    """
    # Override daily_quota with TOP_N env var if set
    top_n_env = os.getenv('TOP_N', '').strip()
    if top_n_env and top_n_env.isdigit():
        daily_quota = int(top_n_env)
    
    if state is None:
        state = {}
    recent = set()
    for rec in state.get('recent_topics', []):
        try:
            d = rec.get('date')
            if d:
                dt = datetime.fromisoformat(d).date()
                if (datetime.utcnow().date() - dt).days < cooldown_days:
                    recent.add(rec.get('topic'))
        except Exception:
            continue

    topics = []
    try:
        items = _fetch_trends_rss(geo)
        # Fetch enough candidates (at least 30) to ensure quality
        for it in items[:max(30, daily_quota * 10)]:
            if len(topics) >= daily_quota:
                break
            t = it.get('topic')
            if not t or t in recent:
                continue
            score = max(0, 100 - (it.get('rank', 0) * 2))
            topics.append({'topic': t, 'score': score, 'source': it.get('source'), 'explain': it.get('explain')})
    except Exception as e:
        logger.warning(f"Trends RSS fetch failed: {e}; falling back to seed keywords")

    # If not enough topics, fallback to seed keywords
    if len(topics) < daily_quota:
        candidates = [k for k in (seed_keywords or []) if k and k not in recent]
        random.shuffle(candidates)
        for k in candidates:
            if len(topics) >= daily_quota:
                break
            topics.append({'topic': k, 'score': 30, 'source': 'seed_fallback', 'explain': 'fallback seed keyword'})

    # If still not enough, allow recent repetition (last resort)
    if len(topics) < daily_quota:
        pool = list(seed_keywords or [])
        random.shuffle(pool)
        for k in pool:
            if len(topics) >= daily_quota:
                break
            topics.append({'topic': k, 'score': 10, 'source': 'seed_repeat', 'explain': 'forced seed repeat'})

    # Trim to daily_quota
    return topics[:daily_quota]
