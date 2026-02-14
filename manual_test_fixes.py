#!/usr/bin/env python3
"""Manual test to verify all three fixes without pytest."""

import sys
import os
sys.path.insert(0, str(os.path.dirname(__file__)))

# Test A: Check send_article_generation_results is exported from task_runner
print("=" * 60)
print("TEST A: Module-level export of send_article_generation_results")
print("=" * 60)
try:
    from agent.task_runner import send_article_generation_results
    from agent.task_runner import select_topics
    print("✓ PASS: Both send_article_generation_results and select_topics imported from task_runner")
except ImportError as e:
    print(f"✗ FAIL: {e}")
    sys.exit(1)

# Test B: Check image provider returns "skipped" for empty sources
print("\n" + "=" * 60)
print("TEST B: Image status = 'skipped' for empty sources")
print("=" * 60)
try:
    from agent.image_provider import provide_cover_image
    from pathlib import Path
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Test with empty sources
        material = {'sources': []}
        result = provide_cover_image(material, tmpdir, 'test-slug')
        
        if result.get('image_status') == 'skipped':
            print(f"✓ PASS: image_status = 'skipped' for empty sources")
            print(f"  Result: {result}")
        else:
            print(f"✗ FAIL: Expected 'skipped' but got '{result.get('image_status')}'")
            print(f"  Result: {result}")
            sys.exit(1)
            
        # Test with None material
        result2 = provide_cover_image(None, tmpdir, 'test-slug2')
        if result2.get('image_status') == 'skipped':
            print(f"✓ PASS: image_status = 'skipped' for None material")
            print(f"  Result: {result2}")
        else:
            print(f"✗ FAIL: Expected 'skipped' for None material but got '{result2.get('image_status')}'")
            sys.exit(1)
except Exception as e:
    print(f"✗ FAIL: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test C: Check WeChat article uses fallback and validates length
print("\n" + "=" * 60)
print("TEST C: WeChat article length validation and fallback")
print("=" * 60)
try:
    from agent.article_generator import generate_article_in_style, zh_char_count
    
    material = {'topic': 'Artificial Intelligence', 'sources': [], 'key_points': []}
    article = generate_article_in_style(
        'Artificial Intelligence',
        material,
        style='wechat',
        word_count_range=(800, 1200),
        language='zh-CN'
    )
    
    body = article.get('body', '')
    char_count = zh_char_count(body)
    word_split_count = len(body.split())
    
    print(f"✓ Article generated:")
    print(f"  - Style: {article.get('style')}")
    print(f"  - Fallback used: {article.get('fallback_used')}")
    print(f"  - Body char_count (zh_char_count): {char_count}")
    print(f"  - Body split() count: {word_split_count}")
    print(f"  - word_count in article: {article.get('word_count')}")
    
    # The test checks: len(article['body'].split()) >= 500
    # This is the LITERAL assertion from the test
    if word_split_count >= 500:
        print(f"✓ PASS: Test assertion len(body.split()) >= 500 will PASS ({word_split_count} >= 500)")
    else:
        print(f"✗ FAIL: Test assertion len(body.split()) >= 500 will FAIL ({word_split_count} < 500)")
        print(f"  Body preview (first 500 chars):\n{body[:500]}")
        sys.exit(1)
        
except Exception as e:
    print(f"✗ FAIL: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("ALL MANUAL TESTS PASSED ✓")
print("=" * 60)
