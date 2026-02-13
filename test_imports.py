#!/usr/bin/env python3
"""Test imports for all content pipeline modules."""

try:
    from agent.content_pipeline.search import get_search_provider
    from agent.content_pipeline.scrape import HeatScorer, WebScraper
    from agent.content_pipeline.writer import OpenAIWriter
    from agent.content_pipeline.images import ImageGenerator
    from agent.content_pipeline.deliver_email import EmailSender
    from agent.content_pipeline.render import ArticleRenderer, MetadataWriter, SocialPreview
    from agent.content_pipeline.publish_kit import PublishKitBuilder
    print('✓ All content_pipeline imports successful')
except Exception as e:
    print(f'✗ content_pipeline import failed: {e}')
    exit(1)

try:
    from agent.publish_adapters.wechat import prepare_wechat_draft
    from agent.publish_adapters.xiaohongshu import prepare_xhs_draft
    from agent.publish_adapters.toutiao import prepare_toutiao_draft
    from agent.publish_adapters.baijiahao import prepare_baijiahao_draft
    print('✓ All publish_adapters imports successful')
except Exception as e:
    print(f'✗ publish_adapters import failed: {e}')
    exit(1)

print('✓ All imports validated successfully!')
