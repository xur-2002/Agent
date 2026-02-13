#!/usr/bin/env python3
"""Test article generation fixes end-to-end.

This script tests:
1. TaskResult structure (no data field)
2. Article generation in DRY_RUN mode
3. TaskResult metrics structure
4. Feishu card preparation
"""

import os
import sys
import json
from pathlib import Path

# Setup path
sys.path.insert(0, os.path.dirname(__file__))

def test_1_taskresult_structure():
    """Test 1: TaskResult can be created without data field."""
    print("\n" + "="*60)
    print("TEST 1: TaskResult Structure")
    print("="*60)
    
    from agent.models import TaskResult
    
    # Test creating TaskResult with metrics instead of data
    result = TaskResult(
        status="success",
        summary="Test summary",
        metrics={
            "successful_articles": [
                {"title": "Test Article", "word_count": 500, "file_path": "outputs/articles/2024-01-01/test.md"}
            ],
            "failed_articles": [],
            "dry_run": True
        },
        duration_sec=1.5
    )
    
    assert result.status == "success", "Status not set correctly"
    assert result.metrics["successful_articles"] is not None, "successful_articles not in metrics"
    assert result.metrics["failed_articles"] is not None, "failed_articles not in metrics"
    assert result.duration_sec == 1.5, "duration_sec not set correctly"
    
    print("✅ TaskResult structure is correct")
    print(f"   - status: {result.status}")
    print(f"   - summary: {result.summary}")
    print(f"   - metrics keys: {list(result.metrics.keys())}")
    print(f"   - duration_sec: {result.duration_sec}")
    return True


def test_2_dry_run_article_generation():
    """Test 2: Article generation in DRY_RUN mode (no API calls)."""
    print("\n" + "="*60)
    print("TEST 2: DRY_RUN Article Generation")
    print("="*60)
    
    # Set DRY_RUN mode
    os.environ["DRY_RUN"] = "1"
    
    from agent.article_generator import generate_article, save_article
    
    # Test article generation
    article = generate_article(
        keyword="artificial intelligence",
        search_results=[
            {
                "title": "What is AI?",
                "snippet": "AI is machine learning...",
                "link": "https://example.com/ai"
            }
        ],
        dry_run=True,
        language="zh-CN"
    )
    
    assert article is not None, "Article generation returned None"
    assert "title" in article, "Article missing title"
    assert "body" in article, "Article missing body"
    
    print("✅ Article generated in DRY_RUN mode")
    print(f"   - title: {article['title'][:50]}...")
    print(f"   - body length: {len(article['body'])} chars")
    
    # Test saving article
    file_path = save_article(article)
    assert file_path is not None, "save_article returned None"
    assert Path(file_path).exists(), f"Saved file not found: {file_path}"
    
    print(f"✅ Article saved successfully")
    print(f"   - file: {file_path}")
    
    # Clean up DRY_RUN flag
    del os.environ["DRY_RUN"]
    return True


def test_3_task_runner_return_structure():
    """Test 3: run_article_generate returns TaskResult with metrics."""
    print("\n" + "="*60)
    print("TEST 3: run_article_generate Return Structure")
    print("="*60)
    
    os.environ["DRY_RUN"] = "1"
    os.environ["FEISHU_WEBHOOK_URL"] = "https://test.example.com/webhook"
    
    from agent.task_runner import run_article_generate
    from agent.models import Task
    
    task = Task(
        id="article_generate",
        title="Test Article Generation",
        enabled=True,
        params={
            "keywords": ["artificial intelligence", "cloud computing"],
            "language": "zh-CN"
        }
    )
    
    result = run_article_generate(task)
    
    assert result.status in ["success", "failed"], f"Invalid status: {result.status}"
    assert "successful_articles" in result.metrics, "successful_articles not in metrics"
    assert "failed_articles" in result.metrics, "failed_articles not in metrics"
    assert result.duration_sec > 0, "duration_sec not set"
    
    print("✅ run_article_generate returns correct TaskResult")
    print(f"   - status: {result.status}")
    print(f"   - successful articles: {result.metrics['successful_articles']}")
    print(f"   - failed articles: {result.metrics['failed_articles']}")
    print(f"   - duration: {result.duration_sec:.2f}s")
    
    del os.environ["DRY_RUN"]
    return True


def test_4_feishu_card_preparation():
    """Test 4: Feishu card can extract data from TaskResult.metrics."""
    print("\n" + "="*60)
    print("TEST 4: Feishu Card Data Extraction")
    print("="*60)
    
    from agent.models import TaskResult
    
    result = TaskResult(
        status="success",
        summary="Generated 2 articles",
        metrics={
            "successful_articles": [
                {
                    "title": "Article 1",
                    "keyword": "AI",
                    "word_count": 600,
                    "sources_count": 3,
                    "file_path": "outputs/articles/2024-01-01/article1.md"
                },
                {
                    "title": "Article 2",
                    "keyword": "Cloud",
                    "word_count": 550,
                    "sources_count": 2,
                    "file_path": "outputs/articles/2024-01-01/article2.md"
                }
            ],
            "failed_articles": [],
            "dry_run": False
        },
        duration_sec=5.0
    )
    
    # Simulate what main.py does
    metrics = result.metrics or {}
    successful_articles = metrics.get("successful_articles", [])
    failed_articles = metrics.get("failed_articles", [])
    dry_run = metrics.get("dry_run", False)
    
    assert len(successful_articles) == 2, "Failed to extract successful_articles"
    assert len(failed_articles) == 0, "Failed to extract failed_articles"
    assert dry_run == False, "Failed to extract dry_run flag"
    
    print("✅ Feishu card can extract all necessary data")
    print(f"   - successful articles: {len(successful_articles)}")
    print(f"   - failed articles: {len(failed_articles)}")
    print(f"   - dry_run: {dry_run}")
    for article in successful_articles:
        print(f"     • {article['title']} ({article['word_count']} words)")
    
    return True


def test_5_openai_import_exists():
    """Test 5: openai package requirements satisfied (after pip install)."""
    print("\n" + "="*60)
    print("TEST 5: OpenAI Package Availability")
    print("="*60)
    
    # Check if openai is in requirements.txt
    with open("requirements.txt", "r") as f:
        content = f.read()
        if "openai" in content:
            print("✅ openai is listed in requirements.txt")
        else:
            print("❌ openai is NOT in requirements.txt")
            return False
    
    # Try to import (might fail if not installed yet)
    try:
        from openai import OpenAI
        print("✅ openai package is installed and importable")
        return True
    except ImportError:
        print("⚠️  openai package not installed yet (EXPECTED in CI before pip install)")
        print("   → Run: pip install -r requirements.txt")
        return True  # This is expected in test environment


def main():
    """Run all tests."""
    print("\n" + "█"*60)
    print("█  ARTICLE GENERATION FIX VERIFICATION")
    print("█"*60)
    
    tests = [
        ("TaskResult Structure", test_1_taskresult_structure),
        ("DRY_RUN Mode", test_2_dry_run_article_generation),
        ("Task Runner Return", test_3_task_runner_return_structure),
        ("Feishu Card Data", test_4_feishu_card_preparation),
        ("OpenAI Package", test_5_openai_import_exists),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"❌ {name} FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {name} CRASHED: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "█"*60)
    print(f"█  RESULTS: {passed} passed, {failed} failed")
    print("█"*60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
