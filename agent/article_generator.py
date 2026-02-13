"""Minimalist article generation module for lowest cost closed loop.

Supports multiple LLM providers:
- groq: Free tier via OpenAI-compatible API, llama-3.1-8b-instant
- openai: OpenAI GPT-4o-mini (paid)
- dry_run: Mock article generation (free)
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import re

logger = logging.getLogger(__name__)


# ============================================================================
# Exception Types
# ============================================================================

class LLMProviderError(Exception):
    """Base exception for LLM provider issues."""
    def __init__(self, message: str, provider: str, retriable: bool = True):
        self.message = message
        self.provider = provider
        self.retriable = retriable
        super().__init__(f"[{provider}] {message}")


class MissingAPIKeyError(LLMProviderError):
    """API key not configured."""
    def __init__(self, provider: str):
        super().__init__(f"API key not configured", provider, retriable=False)


class InsufficientQuotaError(LLMProviderError):
    """API quota exhausted or billing issue."""
    def __init__(self, provider: str):
        super().__init__(f"Insufficient quota / billing issue", provider, retriable=False)


class RateLimitError(LLMProviderError):
    """Rate limit hit."""
    def __init__(self, provider: str):
        super().__init__(f"Rate limited", provider, retriable=True)


class TransientError(LLMProviderError):
    """Transient network/timeout error."""
    def __init__(self, provider: str, original_error: str):
        super().__init__(f"Network error: {original_error}", provider, retriable=True)


# ============================================================================
# LLM Provider Factory
# ============================================================================

def _get_llm_client(provider: str) -> Tuple[Any, str, bool]:
    """Get LLM client for a specific provider.
    
    Args:
        provider: groq, openai, or dry_run
        
    Returns:
        Tuple of (client, model, is_dry_run)
        
    Raises:
        MissingAPIKeyError: If API key not configured
    """
    from agent.config import Config
    
    if provider == "groq":
        api_key = Config.GROQ_API_KEY.strip()
        if not api_key:
            raise MissingAPIKeyError("groq")
        
        try:
            from openai import OpenAI
        except ImportError:
            raise LLMProviderError("openai package not installed", "groq", False)
        
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1"
        )
        model = Config.GROQ_MODEL
        logger.info(f"Initialized Groq client (model: {model})")
        return client, model, False
    
    elif provider == "openai":
        api_key = Config.OPENAI_API_KEY.strip()
        if not api_key:
            raise MissingAPIKeyError("openai")
        
        try:
            from openai import OpenAI
        except ImportError:
            raise LLMProviderError("openai package not installed", "openai", False)
        
        client = OpenAI(api_key=api_key)
        model = Config.OPENAI_MODEL
        logger.info(f"Initialized OpenAI client (model: {model})")
        return client, model, False
    
    elif provider == "dry_run":
        logger.info("Using DRY_RUN mock mode")
        return None, "mock", True
    
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


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
    language: str = "zh-CN",
    provider: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Generate article with configurable LLM provider.
    
    Args:
        keyword: The keyword/topic
        search_results: List of search results with title, snippet, link
        dry_run: If True, use mock generation mode
        language: zh-CN or en-US
        provider: groq, openai, dry_run (if None, use Config.LLM_PROVIDER)
        
    Returns:
        Dict with article data including provider/model info, or None if failed
        
    Raises:
        LLMProviderError: On API errors (with retriable flag)
    """
    from agent.config import Config
    
    if search_results is None:
        search_results = []
    
    if provider is None:
        provider = Config.LLM_PROVIDER
    
    # Override with dry_run parameter
    if dry_run:
        provider = "dry_run"
    
    # Get client for provider
    try:
        client, model, is_dry_run = _get_llm_client(provider)
    except LLMProviderError:
        raise
    
    # Generate mock article for dry_run
    if is_dry_run:
        logger.info(f"[DRY_RUN] Generating mock article for keyword: {keyword}")
        article = _generate_mock_article(keyword, search_results)
        article["provider"] = "dry_run"
        article["model"] = "mock"
        return article
    
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
    
    # Build prompt
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
            prompt = f"""为关键词"{keyword}"写一篇 600-800 字的中文文章。

要求：
1. 文章结构：标题、导语（100字左右）、正文、小结
2. 基于一般知识和常见认知进行创作
3. 使用 Markdown 格式
4. 专业、客观的语态

输出格式（就是这个格式，不要加任何其他内容）：
# [文章标题]

## 导语

[导语内容，100字左右]

## 正文

[正文内容，400-600字]

## 小结

[小结，100字左右]"""
    else:
        if source_text:
            prompt = f"""Based on the following search results, write a 500-800 word English article about "{keyword}".

Search results:
{source_text}

Requirements:
1. Structure: Title, Introduction (80 words), Body, Conclusion
2. Based on search results only, no fabrication
3. For uncertain information, use "reportedly", "according to", etc.
4. Add 3-5 reference links
5. Use Markdown format
6. Professional and objective tone

Output format (exactly this format, nothing else):
# [Article Title]

## Introduction

[Introduction content, ~80 words]

## Body

[Main content, 300-500 words]

## Conclusion

[Conclusion, ~80 words]

## References

- [Link Title](URL)
- [Link Title](URL)
"""
        else:
            prompt = f"""Write a 500-800 word English article about "{keyword}".

Requirements:
1. Structure: Title, Introduction (80 words), Body, Conclusion
2. Based on general knowledge
3. Use Markdown format
4. Professional and objective tone

Output format (exactly this format, nothing else):
# [Article Title]

## Introduction

[Introduction content, ~80 words]

## Body

[Main content, 300-500 words]

## Conclusion

[Conclusion, ~80 words]"""
    
    # Call the LLM
    try:
        logger.info(f"Calling {provider} API for keyword: {keyword}")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a professional editor writing factual, well-researched articles."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1200,
            timeout=30
        )
        
        content = response.choices[0].message.content.strip()
        logger.info(f"Article generated by {provider} for keyword: {keyword}")
        
        # Parse the response
        article = _parse_article_response(content)
        if article:
            article["keyword"] = keyword
            article["sources"] = sources
            article["provider"] = provider
            article["model"] = model
            article["word_count"] = len(content.split())
            article["sources_count"] = len(sources)
            return article
        else:
            logger.error("Failed to parse article response")
            return None
            
    except Exception as e:
        # Classify the exception
        error_str = str(e).lower()
        
        if "insufficient_quota" in error_str or "billing" in error_str or "quota" in error_str:
            raise InsufficientQuotaError(provider)
        elif "invalid_api_key" in error_str or "401" in error_str or "unauthorized" in error_str:
            raise MissingAPIKeyError(provider)
        elif "rate_limit" in error_str or "429" in error_str:
            raise RateLimitError(provider)
        elif "timeout" in error_str or "connection" in error_str or "network" in error_str:
            raise TransientError(provider, str(e))
        else:
            # Generic error
            logger.error(f"{provider} API call failed: {e}")
            raise LLMProviderError(f"API call failed: {str(e)[:100]}", provider, retriable=True)


def _generate_mock_article(
    keyword: str,
    search_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Generate a mock article for DRY_RUN/testing mode.
    
    Args:
        keyword: The keyword/topic
        search_results: Search results (unused in mock)
        
    Returns:
        Dict with full article data
    """
    sources = []
    for i, result in enumerate(search_results[:5], 1):
        sources.append({
            "title": result.get("title", f"Source {i}"),
            "link": result.get("link", f"https://example.com/{i}")
        })
    
    title = f"Understanding {keyword}"
    
    markdown = f"""# {title}

## Introduction

This article explores {keyword} and its importance in today's world.
Understanding {keyword} is crucial for professionals and organizations.

## Body

{keyword} is a significant topic that requires careful consideration. Here are the key aspects:

1. **First Aspect**: {keyword} has grown significantly in importance
2. **Second Aspect**: Organizations are increasingly focusing on {keyword}
3. **Third Aspect**: The future of {keyword} depends on several factors

These factors demonstrate the relevance and importance of {keyword} in the current landscape.

## Conclusion

{keyword} continues to be an important area for development and innovation.
As the landscape evolves, stakeholders should stay informed about the latest developments.

## References

"""
    
    for source in sources:
        markdown += f"- [{source['title']}]({source['link']})\n"
    
    return {
        "title": title,
        "body": markdown,
        "keyword": keyword,
        "sources": sources,
        "provider": "dry_run",
        "model": "mock",
        "word_count": sum(len(line.split()) for line in markdown.split('\n')),
        "sources_count": len(sources)
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
    """Save article to disk in outputs/articles/YYYY-MM-DD/<slug>.*
    
    Args:
        article: Article dict with provider, model, keyword, sources, etc.
        output_dir: Base output directory
        
    Returns:
        Path to saved markdown file, or None if failed
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
        
        # Save JSON metadata with provider info
        metadata = {
            "title": article.get("title", ""),
            "keyword": article.get("keyword", ""),
            "provider": article.get("provider", "unknown"),
            "model": article.get("model", "unknown"),
            "sources": article.get("sources", []),
            "created_at": datetime.now().isoformat(),
            "word_count": article.get("word_count", 0),
            "sources_count": article.get("sources_count", 0),
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
