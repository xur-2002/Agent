#!/usr/bin/env python3
"""Quick import test for route 2 implementation."""

try:
    from agent.article_generator import generate_article, save_article
    print("✓ article_generator module imported")
except Exception as e:
    print(f"✗ Failed to import article_generator: {e}")
    exit(1)

try:
    from agent.feishu import send_article_generation_results
    print("✓ feishu.send_article_generation_results imported")
except Exception as e:
    print(f"✗ Failed to import feishu: {e}")
    exit(1)

try:
    from agent.task_runner import run_article_generate
    print("✓ task_runner.run_article_generate imported")
except Exception as e:
    print(f"✗ Failed to import task_runner: {e}")
    exit(1)

try:
    from agent.main import main
    print("✓ main.main imported")
except Exception as e:
    print(f"✗ Failed to import main: {e}")
    exit(1)

print("\n✅ All imports successful - Route 2 implementation is ready!")
