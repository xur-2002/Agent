"""Semi-automatic Toutiao (今日头条) publishing adapter."""

import logging
from dataclasses import dataclass
from typing import Dict, List

logger = logging.getLogger(__name__)


@dataclass
class ToutiaoDraft:
    """Toutiao draft format."""
    title: str
    content: str
    cover_image_path: str
    keywords: List[str]
    category: str = "news"  # news, tech, entertainment, etc


def prepare_toutiao_draft(
    article_title: str,
    article_text: str,
    cover_path: str,
    keywords: list
) -> ToutiaoDraft:
    """Prepare article for Toutiao publishing.
    
    Args:
        article_title: Article title
        article_text: Article text
        cover_path: Path to cover image
        keywords: Article keywords
        
    Returns:
        ToutiaoDraft ready for manual publishing
    """
    return ToutiaoDraft(
        title=article_title,
        content=article_text,
        cover_image_path=cover_path,
        keywords=keywords
    )


def get_toutiao_copy_instructions() -> str:
    """Get publishing instructions."""
    return """
TOUTIAO (今日头条) PUBLISHING

1. Go to: https://mp.toutiao.com/ -> 创作中心
2. Click: 发布文章 (Publish Article)
3. Title: Paste article title
4. Featured image: Upload cover.png
5. Content: Paste article text (markdown or plain)
6. Category: Select appropriate category
7. Keywords: Add article keywords
8. Save to drafts
9. Schedule or publish

Tips:
- Toutiao algorithmic algorithm favors engagement
- Use clear titles with keywords
- First paragraph determines preview
- Include relevant category
- Test preview before publishing
"""
