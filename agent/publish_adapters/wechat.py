"""Semi-automatic WeChat Official Account publishing adapter.

This is NOT automatic publishing (no official API for WeChat OA draft publishing).
Instead, it prepares formatted content for manual copy-paste into the draft box.
"""

import logging
from dataclasses import dataclass
from typing import Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class WeChatDraft:
    """WeChat Official Account draft format."""
    title: str
    summary: str
    content_html: str
    cover_image_path: str
    keywords: list


def prepare_wechat_draft(
    article_title: str,
    summary_bullets: list,
    article_html: str,
    cover_path: str,
    keywords: list
) -> WeChatDraft:
    """Prepare article for WeChat OA publishing.
    
    Args:
        article_title: Article title
        summary_bullets: Summary bullets
        article_html: Article in HTML format
        cover_path: Path to cover image
        keywords: Article keywords
        
    Returns:
        WeChatDraft ready for manual publishing
    """
    summary = summary_bullets[0] if summary_bullets else article_title
    
    return WeChatDraft(
        title=article_title,
        summary=summary,
        content_html=article_html,
        cover_image_path=cover_path,
        keywords=keywords
    )


def get_wechat_copy_instructions() -> str:
    """Get step-by-step instructions for WeChat publishing.
    
    Returns:
        Instruction string
    """
    return """
WEIXIN OFFICIAL ACCOUNT PUBLISHING (微信公众号)

1. Go to: https://mp.weixin.qq.com/ -> 素材管理 (Material)
2. Click: 新增 -> 图文消息 (New -> Graphic Content)
3. Title field: Paste the article title
4. Featured image: Upload cover.png
5. In content area, paste the formatted HTML content
6. Auto-link: Enable to convert URLs to clickable links
7. Review and save to drafts
8. Schedule or publish from drafts

Tips:
- Use the HTML version for best formatting
- WeChat will auto-wrap text
- Test preview before publishing
- Use emoji in headlines to increase engagement
"""
