"""Minimalist article generation module for lowest cost closed loop."""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import re

logger = logging.getLogger(__name__)


def slugify(text: str, max_length: int = 60) -> str:
    """Convert text to URL-safe slug.
    
    Args:
        text: Input text
        max_length: Maximum slug length
        
    Returns:
        URL-safe slug
    """
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text[:max_length].rstrip('-')


def generate_article(
    keyword: str,
    search_results: List[Dict[str, Any]] = None,
    dry_run: bool = False,
    language: str = "zh-CN"
) -> Optional[Dict[str, Any]]:
    """Generate a simple article from search results or keyword alone.
    
    Args:
        keyword: The keyword/topic
        search_results: List of search results (max 5) from Serper with title, snippet, link
                       If None or empty, article is generated from keyword knowledge only
        dry_run: If True, return mock article without calling OpenAI
        language: Language code (zh-CN or en-US)
        
    Returns:
        Dict with title, body, metadata, or None if failed
    """
    if search_results is None:
        search_results = []
    
    if dry_run:
        logger.info(f"[DRY_RUN] Generating mock article for keyword: {keyword}")
        return _generate_mock_article(keyword, search_results)
    
    # Import OpenAI at runtime to avoid issues if key is not set
    try:
        from openai import OpenAI
    except ImportError:
        logger.error("OpenAI client not available")
        return None
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not set")
        return None
    
    client = OpenAI(api_key=api_key)
    
    # Prepare sources for context
    sources = []
    source_text = ""
    
    if search_results:
        for i, result in enumerate(search_results[:5], 1):
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            link = result.get("link", "")
            sources.append({"title": title, "link": link})
            source_text += f"{i}. [{title}]({link})\n   {snippet}\n\n"
    
    # Build prompt (with graceful handling of missing search context)
    if language == "zh-CN":
        if source_text:
            prompt = f"""基于以下搜索结果，为关键词"{keyword}"写一篇 600-800 字的中文文章。

搜索结果：
{source_text}

要求：
1. 文章结构：标题、导语（100字左右）、正文、小结
2. 完全基于搜索结果的信息，不要编造数据
3. 如果无法确定的信息，用"据称"、"据报道"或"暂无公开数据"等措辞
4. 文章末尾必须列出 3-5 个参考链接（从搜索结果中选取）
5. 使用 Markdown 格式
6. 专业、客观的语态

输出格式（就是这个格式，不要加任何其他内容）：
# [文章标题]

## 导语

[导语内容，100字左右]

## 正文

[正文内容，400-600字]"""
        else:
            # No search results - use broader general knowledge prompt
            prompt = f"""为关键词"{keyword}"写一篇 600-800 字的中文文章。

要求：
1. 文章结构：标题、导语（100字左右）、正文、小结
2. 基于一般知识和常见认知进行创作（清楚标注假如有的话的信息来源）
3. 使用 Markdown 格式
4. 专业、客观的语态
5. 文章末尾如果有参考信息来源，请列出

输出格式（就是这个格式，不要加任何其他内容）：
# [文章标题]

## 导语

[导语内容，100字左右]

## 正文

[正文内容，400-600字]

## 小结

[小结，100字左右]

## 参考链接

- [链接1标题](链接URL)
- [链接2标题](链接URL)
...
"""
    else:
        # English version
        prompt = f"""Based on the following search results, write a 500-800 word English article about "{keyword}".

Search results:
{source_text}

Requirements:
1. Structure: Title, Introduction (80 words), Body, Conclusion
2. Base completely on search results, no fabrication
3. For uncertain information, use phrases like "reportedly", "according to", or "no public data available"
4. End with 3-5 reference links (from search results)
5. Use Markdown format
6. Professional and objective tone

Output format (this format exactly, nothing else):
# [Article Title]

## Introduction

[Introduction content, ~80 words]

## Body

[Main content, 300-500 words]

## Conclusion

[Conclusion, ~80 words]

## References

- [Link 1 Title](Link URL)
- [Link 2 Title](Link URL)
...
"""
    
    try:
        logger.info(f"Calling OpenAI API for keyword: {keyword}")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional editor writing factual, well-researched articles. Always cite your sources."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1200,
            timeout=30
        )
        
        content = response.choices[0].message.content.strip()
        logger.info(f"Article generated for keyword: {keyword}")
        
        # Parse the response
        article = _parse_article_response(content)
        if article:
            article["keyword"] = keyword
            article["sources"] = sources
            article["word_count"] = len(content.split())
            return article
        else:
            logger.error("Failed to parse article response")
            return None
            
    except Exception as e:
        logger.error(f"OpenAI API call failed: {e}")
        return None


def _generate_mock_article(
    keyword: str,
    search_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Generate a mock article for DRY_RUN mode.
    
    Args:
        keyword: The keyword/topic
        search_results: Search results (unused in mock)
        
    Returns:
        Dict with mock article data
    """
    sources = []
    for i, result in enumerate(search_results[:5], 1):
        sources.append({
            "title": result.get("title", f"Source {i}"),
            "link": result.get("link", f"https://example.com/{i}")
        })
    
    title = f"Understanding {keyword} in 2024"
    
    markdown = f"""# {title}

## Introduction

This is a mock article about {keyword} generated in DRY_RUN mode. 
In production, this would be a real article sourced from search results and generated by GPT-4o-mini.
The article would be 600-800 words with proper citations and structure.

## Body

{keyword} continues to be an important topic in the technology landscape.
Based on recent data and reports, we can see several key trends emerging:

1. First trend related to {keyword}
2. Second trend related to {keyword}
3. Third trend related to {keyword}

These trends demonstrate the growing importance of {keyword} in modern systems and practices.

## Conclusion

{keyword} remains a critical area for ongoing research and development.
As the landscape evolves, organizations should stay informed about these developments
to make strategic decisions.

## References

"""
    
    for source in sources:
        markdown += f"- [{source['title']}]({source['link']})\n"
    
    return {
        "title": title,
        "body": markdown,
        "keyword": keyword,
        "sources": sources,
        "word_count": sum(len(line.split()) for line in markdown.split('\n')),
        "dry_run": True
    }


def _parse_article_response(content: str) -> Optional[Dict[str, str]]:
    """Parse article response from LLM.
    
    Args:
        content: Raw response from LLM
        
    Returns:
        Dict with title and body, or None if parsing failed
    """
    try:
        # Extract title (first # heading)
        title_match = re.search(r'^#+\s*(.+?)$', content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else "Article"
        
        # Entire content is the body
        body = content.strip()
        
        return {
            "title": title,
            "body": body
        }
    except Exception as e:
        logger.error(f"Failed to parse article response: {e}")
        return None


def save_article(
    article: Dict[str, Any],
    output_dir: str = "outputs/articles"
) -> Optional[str]:
    """Save article to disk in outputs/articles/YYYY-MM-DD/<slug>.md and .json
    
    Args:
        article: Article dict with title, body, keyword, sources, word_count
        output_dir: Base output directory
        
    Returns:
        Path to saved article, or None if failed
    """
    try:
        # Create date-based directory
        today = datetime.now().strftime("%Y-%m-%d")
        article_dir = Path(output_dir) / today
        article_dir.mkdir(parents=True, exist_ok=True)
        
        # Create slug from title
        slug = slugify(article.get("title", article.get("keyword", "article")))
        
        # Save markdown
        md_path = article_dir / f"{slug}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(article["body"])
        logger.info(f"Saved article markdown: {md_path}")
        
        # Save JSON metadata
        metadata = {
            "title": article.get("title", ""),
            "keyword": article.get("keyword", ""),
            "keywords": [article.get("keyword", "")],
            "sources": article.get("sources", []),
            "created_at": datetime.now().isoformat(),
            "word_count": article.get("word_count", 0),
            "file_path": str(md_path)
        }
        json_path = article_dir / f"{slug}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved article metadata: {json_path}")
        
        return str(md_path)
        
    except Exception as e:
        logger.error(f"Failed to save article: {e}")
        return None
