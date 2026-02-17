import json

import agent.feishu_webhook as feishu_webhook
import scripts.generate_ad as generate_ad


def test_feishu_webhook_push_smoke(tmp_path, monkeypatch):
    class FakeClient:
        def __init__(self):
            self.base_url = "https://api.groq.com/openai/v1"

    class FakeResponse:
        def __init__(self, status_code=200, text='{"code":0,"msg":"success"}'):
            self.status_code = status_code
            self.text = text

        def json(self):
            return {
                "code": 0,
                "msg": "success",
                "data": {"message_id": "om_test_123", "open_message_id": "om_test_123"},
            }

    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append({"url": url, "payload": json})
        return FakeResponse()

    def fake_hot_topics(category, city=None, seed=None):
        return {
            "hot_topics": ["预算怎么定", "避坑清单", "口碑争议点"],
            "sources": [
                {
                    "title": "示例来源",
                    "url": "https://example.com/a",
                    "snippet": "示例摘要",
                }
            ],
            "fallback_used": True,
            "warnings": [],
            "provider": "serper",
            "serper_ok": True,
            "serper_status": 200,
        }

    def fake_generate_publishable_ads_with_meta(**kwargs):
        brand = kwargs.get("brand") or "TKM AUTO"
        contents = {
            "wechat": f"# {brand} wechat\n\n{brand} 内容\n\n{brand}",
            "xiaohongshu": f"# {brand} xhs\n\n{brand} 内容\n\n{brand}",
            "douyin": f"| 镜头编号 | 画面 | 旁白 | 字幕 | 音效/转场 |\n|---|---|---|---|---|\n|1|开场|{brand}|{brand}|砰|",
        }
        usage = {
            ch: {
                "model": "gpt-4o-mini",
                "usage": {"total_tokens": 100},
                "request_url": "https://api.groq.com/openai/v1/chat/completions",
            }
            for ch in contents
        }
        return contents, usage, []

    monkeypatch.setenv("FEISHU_WEBHOOK_URL", "https://open.feishu.cn/open-apis/bot/v2/hook/test")
    monkeypatch.setattr(feishu_webhook.requests, "post", fake_post)

    monkeypatch.setattr(generate_ad, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(generate_ad, "LLMClient", FakeClient)
    monkeypatch.setattr(generate_ad, "collect_hot_topics", fake_hot_topics)
    monkeypatch.setattr(generate_ad, "generate_publishable_ads_with_meta", fake_generate_publishable_ads_with_meta)

    code = generate_ad.main([
        "--category",
        "卡车/皮卡/越野车改装配件",
        "--brand",
        "TKM AUTO",
        "--city",
        "全国",
        "--channels",
        "wechat,xiaohongshu,douyin",
        "--push",
        "feishu",
        "--seed",
        "2",
    ])

    assert code == 0
    assert len(calls) >= 1
    first_text = (((calls[0].get("payload") or {}).get("content") or {}).get("text") or "")
    assert "Receipt" in first_text

    output_dirs = list((tmp_path / "outputs" / "ads").glob("*/*"))
    assert output_dirs
    out = output_dirs[0]
    meta_path = out / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert "feishu_push" in meta
    assert isinstance(meta["feishu_push"].get("webhook_set"), bool)
    assert isinstance(meta["feishu_push"].get("responses"), list)
    assert meta["feishu_push"]["responses"][0].get("http_status") == 200
    assert meta["feishu_push"]["responses"][0].get("message_id") == "om_test_123"

    push_log = json.loads((out / "feishu_push_log.json").read_text(encoding="utf-8"))
    first_record = (push_log.get("records") or [])[0]
    assert first_record.get("webhook_hash")
    assert first_record.get("webhook_host") == "open.feishu.cn"
    assert "hook/test" not in json.dumps(first_record, ensure_ascii=False)
