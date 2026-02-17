import json

import scripts.generate_ad as generate_ad


def test_generate_ad_multichannel_smoke(tmp_path, monkeypatch):
    class FakeClient:
        def __init__(self):
            self.base_url = "https://api.groq.com/openai/v1"

    def fake_hot_topics(category, city=None, seed=None):
        return {
            "hot_topics": ["预算怎么定", "避坑清单", "口碑争议点", "选购优先级", "适合人群"],
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
        brand = kwargs.get("brand") or "台州红酒庄"
        contents = {
            "wechat": f"# {brand} 公众号文案\n\n这是一段可发布正文。\n\n私信咨询。\n\n{brand}",
            "xiaohongshu": (
                f"# {brand} 小红书爆款标题\n\n真的太值了。\n\n"
                f"{brand} 这次方案我愿意反复回购。\n\n"
                "评论区扣1。\n\n#葡萄酒 #选购 #避坑 #预算 #推荐 #台州 #红酒 #指南"
            ),
            "douyin": (
                "| 镜头编号 | 画面 | 旁白 | 字幕 | 音效/转场 |\n"
                "|---|---|---|---|---|\n"
                f"| 1 | 产品特写 | {brand} 开场钩子 | 3秒抓人 | 砰 |\n"
                f"| 2 | 对比画面 | {brand} 讲清怎么选 | 避坑清单 | 转场 |\n"
                f"| 3 | CTA画面 | 私信关键词领取方案 | 立即行动 | 收尾 |"
            ),
        }
        usage = {
            k: {
                "model": "gpt-4o-mini",
                "usage": {"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
                "request_url": "https://api.groq.com/openai/v1/chat/completions",
            }
            for k in contents
        }
        return contents, usage, []

    monkeypatch.setattr(generate_ad, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(generate_ad, "LLMClient", FakeClient)
    monkeypatch.setattr(generate_ad, "collect_hot_topics", fake_hot_topics)
    monkeypatch.setattr(generate_ad, "generate_publishable_ads_with_meta", fake_generate_publishable_ads)

    code = generate_ad.main([
        "--category", "葡萄酒",
        "--brand", "台州红酒庄",
        "--city", "台州",
        "--tone", "高级、克制、有品位",
        "--channels", "all",
        "--seed", "2",
    ])
    assert code == 0

    output_dirs = list((tmp_path / "outputs" / "ads").glob("*/*"))
    assert output_dirs, "no output dir generated"
    out = output_dirs[0]

    wechat = out / "wechat.md"
    xhs = out / "xiaohongshu.md"
    douyin = out / "douyin_script.md"
    meta_path = out / "meta.json"

    assert wechat.exists()
    assert xhs.exists()
    assert douyin.exists()
    assert meta_path.exists()

    wechat_text = wechat.read_text(encoding="utf-8")
    xhs_text = xhs.read_text(encoding="utf-8")
    douyin_text = douyin.read_text(encoding="utf-8")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    assert wechat_text.count("台州红酒庄") >= 2
    assert xhs_text.count("台州红酒庄") >= 2
    assert douyin_text.count("台州红酒庄") >= 2

    wc = meta.get("channel_word_count") or meta.get("word_count")
    assert isinstance(wc, dict)
    assert "wechat" in wc and wc["wechat"] > 0
    assert "xiaohongshu" in wc and wc["xiaohongshu"] > 0
    assert "douyin" in wc and wc["douyin"] > 0

    files = meta.get("files")
    assert isinstance(files, list)
    assert "wechat.md" in files
    assert "xiaohongshu.md" in files
    assert "douyin_script.md" in files

    channels = meta.get("channels")
    assert channels == ["wechat", "xiaohongshu", "douyin"]
    assert "word_count" in meta and isinstance(meta["word_count"], dict)

    channels_meta = meta.get("channels_meta")
    assert isinstance(channels_meta, dict)
    assert channels_meta["wechat"]["file"] == "wechat.md"
    assert channels_meta["xiaohongshu"]["file"] == "xiaohongshu.md"
    assert channels_meta["douyin"]["file"] == "douyin_script.md"
    assert channels_meta["wechat"]["word_count"] > 0
    assert channels_meta["xiaohongshu"]["word_count"] > 0
    assert channels_meta["douyin"]["word_count"] > 0
