import os
from agent import trends


def test_trends_rss_fetch_or_fallback(monkeypatch):
    # Simulate _fetch_trends_rss failing
    def fail_fetch(geo):
        raise RuntimeError('network')

    monkeypatch.setattr(trends, '_fetch_trends_rss', fail_fetch)

    seed = ['alpha', 'beta', 'gamma']
    topics = trends.select_topics(seed_keywords=seed, daily_quota=2, geo='US', cooldown_days=1, state={})
    assert len(topics) == 2
    assert topics[0]['source'].startswith('seed')
