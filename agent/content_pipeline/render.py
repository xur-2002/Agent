"""Render articles to Markdown and HTML formats."""

import logging
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


def slugify(text: str) -> str:
    """Convert text to URL-safe slug.
    
    Args:
        text: Input text
        
    Returns:
        Slug string
    """
    text = text.lower().strip()
    # Convert Chinese to pinyin or remove
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text[:50].rstrip("-")


class ArticleRenderer:
    """Render articles to various formats."""
    
    @staticmethod
    def to_markdown(
        title: str,
        summary_bullets: list,
        body: str,
        key_takeaways: list,
        sources_section: str
    ) -> str:
        """Convert article to Markdown.
        
        Args:
            title: Article title
            summary_bullets: List of bullet points
            body: Main body text
            key_takeaways: List of key takeaways
            sources_section: Sources section text
            
        Returns:
            Markdown string
        """
        md = f"# {title}\n\n"
        
        # Summary
        if summary_bullets:
            md += "## Summary\n\n"
            for bullet in summary_bullets:
                md += f"- {bullet}\n"
            md += "\n"
        
        # Body
        md += "## Article\n\n"
        md += body + "\n\n"
        
        # Key takeaways
        if key_takeaways:
            md += "## Key Takeaways\n\n"
            for i, takeaway in enumerate(key_takeaways, 1):
                md += f"{i}. {takeaway}\n"
            md += "\n"
        
        # Sources
        if sources_section.strip():
            md += "## Sources\n\n"
            md += sources_section + "\n"
        
        return md
    
    @staticmethod
    def to_html(
        title: str,
        summary_bullets: list,
        body: str,
        key_takeaways: list,
        sources_section: str,
        cover_image: bool = False
    ) -> str:
        """Convert article to HTML.
        
        Args:
            title: Article title
            summary_bullets: List of bullet points
            body: Main body text
            key_takeaways: List of key takeaways
            sources_section: Sources section text
            cover_image: Whether article has cover image
            
        Returns:
            HTML string
        """
        bullets_html = "".join(
            f"<li>{ArticleRenderer._escape_html(bullet)}</li>"
            for bullet in summary_bullets
        )
        
        takeaways_html = "".join(
            f"<li>{ArticleRenderer._escape_html(takeaway)}</li>"
            for takeaway in key_takeaways
        )
        
        # Convert body to HTML (simple - just escape and make paragraphs)
        body_html = ""
        for para in body.split("\n\n"):
            para = para.strip()
            if para:
                body_html += f"<p>{ArticleRenderer._escape_html(para)}</p>\n"
        
        cover_section = ""
        if cover_image:
            cover_section = '<img src="cover.png" alt="Cover" class="cover">\n'
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{ArticleRenderer._escape_html(title)}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.8; color: #333; }}
        .container {{ max-width: 800px; margin: 0 auto; padding: 40px 20px; }}
        h1 {{ font-size: 2.5em; margin-bottom: 20px; color: #000; }}
        h2 {{ font-size: 1.5em; margin-top: 40px; margin-bottom: 20px; color: #222; border-bottom: 2px solid #0066cc; padding-bottom: 10px; }}
        p {{ margin-bottom: 16px; }}
        ul {{ margin-left: 20px; margin-bottom: 16px; }}
        li {{ margin-bottom: 8px; }}
        .cover {{ max-width: 100%; height: auto; margin: 20px 0; border-radius: 8px; }}
        .meta {{ color: #666; font-size: 0.9em; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{ArticleRenderer._escape_html(title)}</h1>
        
        {cover_section}
        
        {'<h2>Summary</h2><ul>' + bullets_html + '</ul>' if bullets_html else ''}
        
        <h2>Article</h2>
        {body_html}
        
        {'<h2>Key Takeaways</h2><ul>' + takeaways_html + '</ul>' if takeaways_html else ''}
        
        {f'<h2>Sources</h2><div>{ArticleRenderer._escape_html(sources_section)}</div>' if sources_section.strip() else ''}
    </div>
</body>
</html>
"""
        return html
    
    @staticmethod
    def _escape_html(text: str) -> str:
        """Escape HTML special characters."""
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#39;"))


class MetadataWriter:
    """Write article metadata."""
    
    @staticmethod
    def create_metadata(
        title: str,
        keywords: list,
        style: str,
        length: str,
        sources: list,
        created_at: datetime = None
    ) -> Dict[str, Any]:
        """Create article metadata dict.
        
        Args:
            title: Article title
            keywords: List of keywords
            style: Article style
            length: Article length
            sources: List of source URLs
            created_at: Creation timestamp
            
        Returns:
            Metadata dictionary
        """
        if created_at is None:
            created_at = datetime.utcnow()
        
        return {
            "title": title,
            "keywords": keywords,
            "style": style,
            "length": length,
            "sources": sources,
            "created_at": created_at.isoformat(),
            "version": "1.0"
        }
    
    @staticmethod
    def save_metadata(metadata: Dict[str, Any], path: Path) -> bool:
        """Save metadata to JSON file.
        
        Args:
            metadata: Metadata dict
            path: Output file path
            
        Returns:
            True if successful
        """
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved metadata to {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
            return False


class SocialPreview:
    """Generate social media preview text."""
    
    @staticmethod
    def generate_previews(
        title: str,
        summary_bullets: list,
        keyword: str = ""
    ) -> Dict[str, str]:
        """Generate platform-specific preview texts.
        
        Args:
            title: Article title
            summary_bullets: Summary bullets
            keyword: Original keyword/topic
            
        Returns:
            Dict with keys: wechat, xiaohongshu, toutiao, baijiahao
        """
        # WeChat (Official Account): headline + call to action
        wechat = f"{title} #阅读 #深度\n{summary_bullets[0] if summary_bullets else keyword}"[:120].rstrip()
        
        # Xiaohongshu (Little Red Book): emoji-heavy, lifestyle focused
        xhs = f"✨ {title}\n📌 {summary_bullets[0] if summary_bullets else keyword}\n#新知 #内容 #分享"[:140].rstrip()
        
        # Toutiao (Toutiao): news-style, direct
        toutiao = f"{title}\n{summary_bullets[0] if summary_bullets else ''}\n点击阅读全文"[:130].rstrip()
        
        # Baijiahao (Baidu): journalistic style
        baijiahao = f"{title}\n摘要：{summary_bullets[0] if summary_bullets else keyword}"[:120].rstrip()
        
        return {
            "wechat": wechat,
            "xiaohongshu": xhs,
            "toutiao": toutiao,
            "baijiahao": baijiahao
        }
    
    @staticmethod
    def save_social_previews(previews: Dict[str, str], path: Path) -> bool:
        """Save social previews to file.
        
        Args:
            previews: Dict of platform -> preview text
            path: Output file path
            
        Returns:
            True if successful
        """
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            content = ""
            for platform, text in previews.items():
                content += f"=== {platform.upper()} ===\n{text}\n\n"
            
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Saved social previews to {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save social previews: {e}")
            return False
