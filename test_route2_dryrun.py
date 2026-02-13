#!/usr/bin/env python3
"""Quick DRY_RUN test for Route 2."""

import os
import sys

# Set DRY_RUN mode
os.environ['DRY_RUN'] = '1'
os.environ['FEISHU_WEBHOOK_URL'] = 'https://example.com/webhook'

print("[TEST] Starting Route 2 DRY_RUN test...")
print(f"[TEST] DRY_RUN={os.getenv('DRY_RUN')}")
print()

try:
    from agent.article_generator import generate_article, save_article, _generate_mock_article
    
    print("[TEST] Testing mock article generation...")
    
    # Create mock search results
    search_results = [
        {
            "title": "Test Article 1",
            "snippet": "This is a test snippet about AI.",
            "link": "https://example1.com"
        },
        {
            "title": "Test Article 2", 
            "snippet": "Another test article about machine learning.",
            "link": "https://example2.com"
        }
    ]
    
    # Generate mock article
    article = generate_article(
        keyword="artificial intelligence",
        search_results=search_results,
        dry_run=True,
        language="zh-CN"
    )
    
    if article:
        print(f"✓ Mock article generated:")
        print(f"  - Title: {article.get('title', 'N/A')}")
        print(f"  - Keyword: {article.get('keyword', 'N/A')}")
        print(f"  - Word count: {article.get('word_count', 0)}")
        print(f"  - Sources: {len(article.get('sources', []))}")
        
        # Save article
        print("\n[TEST] Saving article to disk...")
        file_path = save_article(article)
        if file_path:
            print(f"✓ Article saved to: {file_path}")
            
            # Verify file exists
            import os.path
            if os.path.exists(file_path):
                print(f"✓ File verified to exist")
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    print(f"✓ File readable ({len(content)} bytes)")
            else:
                print(f"✗ File not found: {file_path}")
        else:
            print(f"✗ Failed to save article")
    else:
        print("✗ Mock article generation failed")
        
    print("\n✅ Route 2 DRY_RUN test completed successfully!")
    
except Exception as e:
    print(f"✗ Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
