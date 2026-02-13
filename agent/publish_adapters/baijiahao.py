"""Semi-automatic Baijiahao (百家号) publishing adapter."""

import logging
from dataclasses import dataclass
from typing import Dict, List

logger = logging.getLogger(__name__)


@dataclass
class BaijihaoDraft:
    """Baijiahao draft format."""
    title: str
    content: str
    cover_image_path: str
    keywords: List[str]
    tags: List[str]


def prepare_baijiahao_draft(
    article_title: str,
    article_text: str,
    cover_path: str,
    keywords: list
) -> BaijihaoDraft:
    """Prepare article for Baijiahao publishing.
    
    Args:
        article_title: Article title
        article_text: Article text
        cover_path: Path to cover image
        keywords: Article keywords
        
    Returns:
        BaijihaoDraft ready for manual publishing
    """
    return BaijihaoDraft(
        title=article_title,
        content=article_text,
        cover_image_path=cover_path,
        keywords=keywords,
        tags=keywords[:3]  # Top 3 keywords as tags
    )


def get_baijiahao_copy_instructions() -> str:
    """Get publishing instructions."""
    return """
BAIJIAHAO (百家号) PUBLISHING

1. Go to: https://baijiahao.baidu.com/ -> 创建
2. Select: 发布文章 (Publish Article)
3. Title: Paste article title
4. Cover: Upload cover.png (1200x628)
5. Content: Paste article text
6. Tags: Add 3-5 relevant tags
7. Category: Select appropriate category
8. SEO title/description: Use keywords
9. Save to drafts
10. Schedule or publish

Tips:
- Baijiahao has excellent Baidu SEO
- Write for search engines
- Use H2/H3 headings in content
- Include keywords naturally
- Longer content performs better
- Test preview before publishing
"""
