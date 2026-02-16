import scripts.generate_ad as generate_ad


def test_missing_llm_model_fails(monkeypatch, capsys):
    monkeypatch.setenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.delenv("LLM_MODEL", raising=False)

    code = generate_ad.main([
        "--category",
        "葡萄酒",
        "--brand",
        "台州红酒庄",
        "--city",
        "台州",
        "--channels",
        "all",
    ])

    captured = capsys.readouterr()
    assert code != 0
    assert "Missing LLM_MODEL" in (captured.err or captured.out)
