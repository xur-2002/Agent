"""Semi-automatic Xiaohongshu (小红书) publishing adapter."""

import logging
from dataclasses import dataclass
from typing import Dict, List

logger = logging.getLogger(__name__)


@dataclass
class XiaohongshhuDraft:
    """Xiaohongshu draft format."""
    title: str
    content: str
    cover_image_path: str
    hashtags: List[str]
    emoji_hints: List[str]


def prepare_xhs_draft(
    article_title: str,
    summary_bullets: list,
    article_text: str,
    cover_path: str,
    keywords: list
) -> XiaohongshhuDraft:
    """Prepare article for Xiaohongshu publishing.
    
    Args:
        article_title: Article title
        summary_bullets: Summary bullets
        article_text: Article text (markdown or plain)
        cover_path: Path to cover image
        keywords: Article keywords
        
    Returns:
        XiaohongshhuDraft ready for manual publishing
    """
    # Xiaohongshu is emoji and hashtag heavy
    summary = summary_bullets[0] if summary_bullets else article_title
    hashtags = keywords + ["新知", "内容分享", "有趣知识", "知识分享"]
    
    # Suggest emojis for visual appeal
    emoji_hints = ["✨", "📌", "💡", "🎯", "📚", "🔥"]
    
    return XiaohongshhuDraft(
        title=article_title,
        content=f"{summary}\n\n{article_text}",
        cover_image_path=cover_path,
        hashtags=hashtags,
        emoji_hints=emoji_hints
    )


def get_xhs_copy_instructions() -> str:
    """Get step-by-step instructions for Xiaohongshu publishing.
    
    Returns:
        Instruction string
    """
    return """
XIAOHONGSHU (小红书) PUBLISHING

1. Go to: https://creator.xiaohongshu.com/ -> Create
2. Click: 创建笔记 (Create Note)
3. Add cover image: Upload cover.png (1200x628 preferred)
4. Title: Use suggested title with emojis
5. Content: 
   - Start with engaging emoji
   - First line should be hook/summary
   - Include full article text
   - Add hashtags at end (#新知 #分享 etc)
6. Tags: Add 3-5 hashtags from keywords
7. Save to drafts
8. Schedule or publish

Tips:
- Xiaohongshu loves visual content
- Use emojis liberally (✨💡🔥 etc)
- Keep first 30 chars catchy
- Include trending hashtags
- High-quality cover images increase engagement
- Test preview before publishing
"""
