import json

import scripts.generate_ad as generate_ad


def test_generate_ad_smoke_with_mocks(tmp_path, monkeypatch):
    def fake_hot_topics(category, city=None, seed=None):
        return {
            "hot_topics": [
                "预算怎么定", "避坑点", "口碑争议点", "选购优先级", "真实使用场景"
            ],
            "sources": [
                {
                    "title": "示例来源",
                    "url": "https://example.com/a",
                    "snippet": "示例摘要"
                }
            ],
            "fallback_used": True,
            "warnings": ["SERPER_API_KEY missing, use fallback hot topics"],
            "provider": "serper",
        }

    def fake_generate_publishable_ads(**kwargs):
        content = (
            "台州红酒庄这次把选择葡萄酒这件事讲透了。\n\n"
            "最近大家讨论最多的不是花哨名词，而是预算、口感和真实体验。"
            "台州红酒庄把这些问题拆得很实在：你要聚会、送礼、还是自己喝，"
            "选法完全不同。\n\n"
            "如果你不想再靠运气踩坑，现在就私信咨询，我们会按你的预算和偏好给出建议。"
        )
        return {
            "wechat": content,
        }, {
            "wechat": {
                "model": "gpt-4o-mini",
                "usage": {"prompt_tokens": 111, "completion_tokens": 222, "total_tokens": 333},
                "request_url": "https://api.groq.com/openai/v1/chat/completions",
            }
        }, []

    monkeypatch.setattr(generate_ad, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(generate_ad, "collect_hot_topics", fake_hot_topics)
    monkeypatch.setattr(generate_ad, "generate_publishable_ads", fake_generate_publishable_ads)

    code = generate_ad.main([
        "--category", "葡萄酒",
        "--brand", "台州红酒庄",
        "--city", "台州",
        "--channel", "公众号",
        "--tone", "高级、克制、有品位",
        "--seed", "2",
    ])
    assert code == 0

    ad_files = list((tmp_path / "outputs" / "ads").glob("*/*/ad.md"))
    meta_files = list((tmp_path / "outputs" / "ads").glob("*/*/meta.json"))

    assert len(ad_files) == 1
    assert len(meta_files) == 1

    ad_text = ad_files[0].read_text(encoding="utf-8").strip()
    meta = json.loads(meta_files[0].read_text(encoding="utf-8"))

    assert ad_text
    assert meta["category"] == "葡萄酒"
    assert meta["brand"] == "台州红酒庄"
    assert meta["tone"] == "高级、克制、有品位"
    assert isinstance(meta.get("hot_topics"), list)
    assert isinstance(meta.get("sources"), list)
    assert isinstance(meta.get("usage"), dict)
    assert "elapsed" in meta

    banned_terms = ["Hook", "卖什么", "给谁", "为什么现在", "场景", "CTA"]
    for term in banned_terms:
        assert term not in ad_text
