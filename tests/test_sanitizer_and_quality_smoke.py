from agent.topic_sanitizer import sanitize_hot_topics


def test_sanitize_hot_topics_removes_blocked_terms():
    hot_topics = [
        "卡车改装预算怎么分配",
        "高端外围服务指南",
        "皮卡配件避坑清单",
    ]
    sources = [
        {"title": "正规改装案例", "url": "https://example.com/a", "snippet": "讲解预算与改装流程"},
        {"title": "一条龙客服微信", "url": "https://example.com/b", "snippet": "客服微信直连"},
        {"title": "越野配件对比", "url": "https://example.com/c", "snippet": "地陪安排与空降"},
    ]

    clean_topics, clean_sources, report = sanitize_hot_topics(hot_topics, sources)

    assert "高端外围服务指南" not in clean_topics
    assert len(clean_topics) == 2
    assert len(clean_sources) == 1
    assert report["removed_items_count"] >= 3
    assert any(item.get("matched_term") in {"外围", "一条龙", "地陪", "空降", "客服微信"} for item in report["removed_items"])
