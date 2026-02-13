import os
from agent.article_generator import generate_article_from_material


def test_article_template_fallback(monkeypatch):
    # Ensure environment has no LLM credentials
    monkeypatch.setenv('GROQ_API_KEY', '')
    monkeypatch.setenv('OPENAI_API_KEY', '')

    material = {'sources': [{'title': 'S1', 'link': 'https://example.com/1', 'snippet': 'Example snippet one.'}], 'key_points': ['Point A', 'Point B']}
    art = generate_article_from_material('test topic', material)
    assert art['provider'] == 'none'
    assert 'test topic' in art['title'] or '深度解读' in art['title']
    assert art['fallback_used'] is True
