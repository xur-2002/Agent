"""Build publish kits for semi-automatic publishing."""

import json
import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class PublishKitBuilder:
    """Build kits for semi-automatic publishing to platforms."""
    
    @staticmethod
    def create_publish_kit(
        date: datetime,
        articles: List[Dict[str, Any]],
        output_dir: Path
    ) -> Optional[Path]:
        """Create a publish kit with all articles and metadata.
        
        Kit structure:
        - publish_kit/
          - articles/
            - article1/
              - article.md
              - article.html
              - cover.png
              - meta.json
              - social.txt
            - article2/
            - ...
          - manifest.json
          - README.md
          - checklist.txt
        
        Args:
            date: Date of articles
            articles: List of article data
            output_dir: Output directory (typically publish_kits/YYYY-MM-DD)
            
        Returns:
            Path to created kit directory, or None if failed
        """
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create directory structure
            articles_dir = output_dir / "articles"
            articles_dir.mkdir(exist_ok=True)
            
            # Copy article files
            for article in articles:
                slug = article.get("slug", "article")
                article_dir = articles_dir / slug
                article_dir.mkdir(exist_ok=True)
                
                # Copy markdown
                if "article_md_path" in article:
                    src = Path(article["article_md_path"])
                    if src.exists():
                        shutil.copy(src, article_dir / "article.md")
                
                # Copy HTML
                if "article_html_path" in article:
                    src = Path(article["article_html_path"])
                    if src.exists():
                        shutil.copy(src, article_dir / "article.html")
                
                # Copy cover image
                if "cover_image_path" in article:
                    src = Path(article["cover_image_path"])
                    if src.exists():
                        shutil.copy(src, article_dir / "cover.png")
                
                # Copy metadata
                if "meta_json_path" in article:
                    src = Path(article["meta_json_path"])
                    if src.exists():
                        shutil.copy(src, article_dir / "meta.json")
                
                # Copy social previews
                if "social_txt_path" in article:
                    src = Path(article["social_txt_path"])
                    if src.exists():
                        shutil.copy(src, article_dir / "social.txt")
            
            # Create manifest
            PublishKitBuilder._create_manifest(output_dir, articles)
            
            # Create checklist
            PublishKitBuilder._create_checklist(output_dir, articles)
            
            # Create README with instructions
            PublishKitBuilder._create_readme(output_dir)
            
            logger.info(f"Created publish kit at {output_dir}")
            return output_dir
            
        except Exception as e:
            logger.error(f"Failed to create publish kit: {e}")
            return None
    
    @staticmethod
    def _create_manifest(kit_dir: Path, articles: List[Dict[str, Any]]) -> None:
        """Create manifest.json with article metadata."""
        manifest = {
            "created_at": datetime.utcnow().isoformat(),
            "article_count": len(articles),
            "articles": []
        }
        
        for article in articles:
            manifest["articles"].append({
                "slug": article.get("slug"),
                "title": article.get("title"),
                "keyword": article.get("keyword"),
                "created_at": article.get("created_at"),
                "files": {
                    "markdown": "article.md",
                    "html": "article.html",
                    "cover": "cover.png",
                    "metadata": "meta.json",
                    "social": "social.txt"
                }
            })
        
        with open(kit_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def _create_checklist(kit_dir: Path, articles: List[Dict[str, Any]]) -> None:
        """Create a plaintext checklist for publishing."""
        checklist = "# Publishing Checklist\n\n"
        checklist += f"Date: {datetime.utcnow().strftime('%Y-%m-%d')}\n"
        checklist += f"Total articles: {len(articles)}\n\n"
        
        checklist += "## Before Publishing\n"
        checklist += "- [ ] Review all article titles and content\n"
        checklist += "- [ ] Check cover images are appropriate\n"
        checklist += "- [ ] Verify keywords and metadata\n"
        checklist += "- [ ] Proofread for grammar and factual accuracy\n\n"
        
        checklist += "## Publishing Steps\n\n"
        
        for i, article in enumerate(articles, 1):
            title = article.get("title", "Article")
            slug = article.get("slug", "article")
            
            checklist += f"### Article {i}: {title}\n"
            checklist += f"(Slug: {slug})\n\n"
            
            checklist += "#### WeChat Official Account\n"
            checklist += "1. Open draft box: https://mp.weixin.qq.com/\n"
            checklist += "2. Open `articles/{slug}/social.txt` → Copy WeChat preview\n"
            checklist += "3. Paste as title\n"
            checklist += "4. Open `articles/{slug}/article.html` in browser\n"
            checklist += "5. Copy formatted text and paste to content\n"
            checklist += "6. Insert cover: `articles/{slug}/cover.png`\n"
            checklist += "7. Save as draft\n\n"
            
            checklist += "#### Xiaohongshu (小红书)\n"
            checklist += "1. Go to: https://creator.xiaohongshu.com/\n"
            checklist += "2. Create new note\n"
            checklist += "3. Use preview text from `articles/{slug}/social.txt` (小红书)\n"
            checklist += "4. Upload cover: `articles/{slug}/cover.png`\n"
            checklist += "5. Paste article content from HTML version\n"
            checklist += "6. Save as draft\n\n"
            
            checklist += "#### Toutiao (今日头条)\n"
            checklist += "1. Go to: https://mp.toutiao.com/\n"
            checklist += "2. Create article\n"
            checklist += "3. Title: from `articles/{slug}/social.txt` (Toutiao)\n"
            checklist += "4. Content: from `articles/{slug}/article.md`\n"
            checklist += "5. Cover: `articles/{slug}/cover.png`\n"
            checklist += "6. Save as draft\n\n"
            
            checklist += "#### Baijiahao (百家号)\n"
            checklist += "1. Go to: https://baijiahao.baidu.com/\n"
            checklist += "2. Publish → Article\n"
            checklist += "3. Title & content: see `articles/{slug}/article.md`\n"
            checklist += "4. Cover: `articles/{slug}/cover.png`\n"
            checklist += "5. Save as draft\n\n"
            
            checklist += "---\n\n"
        
        checklist += "## After Publishing\n"
        checklist += "- [ ] Verify all platforms have drafts/published correctly\n"
        checklist += "- [ ] Monitor engagement on each platform\n"
        checklist += "- [ ] Update state to mark as published\n"
        
        with open(kit_dir / "checklist.txt", "w", encoding="utf-8") as f:
            f.write(checklist)
    
    @staticmethod
    def _create_readme(kit_dir: Path) -> None:
        """Create README with kit instructions."""
        readme = """# Article Publish Kit

This directory contains articles ready for publishing to various social platforms.

## Kit Structure

- `manifest.json` - Complete metadata for all articles
- `articles/` - Individual article directories
  - `[article-slug]/` - Each article has:
    - `article.md` - Markdown version
    - `article.html` - Formatted HTML (ready to copy)
    - `cover.png` - Cover image (1200x628)
    - `meta.json` - Metadata (title, keywords, sources)
    - `social.txt` - Pre-formatted captions for each platform

- `checklist.txt` - Step-by-step publishing guide

## How to Use This Kit

### Option 1: Manual Publishing (Recommended for first-time)
1. Follow instructions in `checklist.txt`
2. Open each article directory
3. Read the platform-specific captions from `social.txt`
4. Copy article content from `.html` or `.md`
5. Use the cover image from `cover.png`
6. Paste into each platform's draft box

### Option 2: Bulk Upload (if platform supports)
1. Use the manifest.json to organize batch uploads
2. Some platforms may accept ZIP archives
3. Check platform documentation for bulk import

## Platform Guides

### WeChat Official Account (微信公众号)
- Supports rich text formatting
- Use HTML version for best formatting
- Cover images recommended: 1200x628px
- Link: https://mp.weixin.qq.com/

### Xiaohongshu (小红书)
- Popular with visual content
- Use high-quality cover images
- Include relevant hashtags
- Link: https://creator.xiaohongshu.com/

### Toutiao (今日头条)
- News-focused platform
- Automatic recommendation system
- Good for reach
- Link: https://mp.toutiao.com/

### Baijiahao (百家号)
- Baidu's content platform
- SEO friendly
- Good for long-form content
- Link: https://baijiahao.baidu.com/

## Notes

- Each article is independent - you can publish selectively
- No automatic publishing - this is semi-automatic for safety
- Always review content before publishing
- Customize captions per platform if needed
- Keep cover images consistent with your brand

## Generated At

""" + datetime.utcnow().isoformat()
        
        with open(kit_dir / "README.md", "w", encoding="utf-8") as f:
            f.write(readme)


class PublishKitCompressor:
    """Compress publish kits to ZIP."""
    
    @staticmethod
    def create_zip(kit_dir: Path, output_path: Optional[Path] = None) -> Optional[Path]:
        """Create a ZIP archive of the publish kit.
        
        Args:
            kit_dir: Directory containing the kit
            output_path: Output ZIP file path (default: kit_dir.zip)
            
        Returns:
            Path to created ZIP file, or None if failed
        """
        try:
            if output_path is None:
                output_path = kit_dir.parent / f"{kit_dir.name}.zip"
            
            shutil.make_archive(
                str(output_path.with_suffix("")),
                "zip",
                kit_dir.parent,
                kit_dir.name
            )
            
            logger.info(f"Created ZIP archive: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to create ZIP: {e}")
            return None
