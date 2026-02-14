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


def select_topics_for_persona(persona: Dict[str, Any], daily_quota: int = 3, geo: str = 'CN', cooldown_days: int = 3, state: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """Select topics relevant to a restaurant persona.

    Uses `select_topics` as primary source then filters by relevance to persona.
    Falls back to persona seed queries if relevance is low.
    """
    # Build seed queries tuned for restaurants
    city = persona.get('city', '')
    seeds = [
        f"本周美食 热搜 {city}",
        f"{persona.get('cuisine','')} 餐厅 热门",
        "餐厅 营销",
        "团购 外卖",
        "节日 餐厅 活动",
        "周末 约会 餐厅",
    ]

    # Get general trends first
    topics = select_topics(seeds, daily_quota=daily_quota, geo=geo, cooldown_days=cooldown_days, state=state)

    # Relevance filter: require topic to match at least one of the strong keywords
    must_keywords = ['台州', '临海', '浙江', '海鲜', '台州菜', '探店', '餐厅', '宴请', '年夜饭', '节日', '周末']
    blacklist = ['体育', '明星', '演唱会', '电影首映', '海外', '国际政', '转会']

    relevant = []
    for t in topics:
        txt = (t.get('topic') or '').lower()
        # filter obvious blacklist
        if any(b in txt for b in blacklist):
            continue

        score = t.get('score', 0)
        # boost on explicit keyword match
        for kw in must_keywords:
            if kw in txt:
                score += 25
        # also boost if source indicates food domain
        src = (t.get('source') or '').lower()
        if any(k in src for k in ['food', 'meishi', 'dianping', '大众点评', 'meituan', '美团']):
            score += 10

        t['score'] = score
        if score >= 20:
            relevant.append(t)

    # If not enough relevant topics, use persona-focused seeds (region+food scenarios)
    if len(relevant) < daily_quota:
        for s in seeds:
            if len(relevant) >= daily_quota:
                break
            relevant.append({'topic': s, 'score': 25, 'source': 'persona_seed', 'explain': 'persona seed fallback'})

    # Trim and return
    return relevant[:daily_quota]
