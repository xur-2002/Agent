"""Article writer using LLM (OpenAI)."""

import os
import json
import logging
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
import requests

logger = logging.getLogger(__name__)


@dataclass
class ArticleDraft:
    """Generated article draft."""
    title: str
    summary_bullets: List[str]
    body: str
    key_takeaways: List[str]
    sources_section: str
    language: str = "zh-CN"
    style: str = "news"
    length: str = "medium"
    word_count: int = 0
    model: str = "gpt-3.5-turbo"
    tokens_used: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class OpenAIWriter:
    """Article writer using OpenAI API."""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        """Initialize OpenAI writer.
        
        Args:
            api_key: OpenAI API key
            model: Model name (default gpt-3.5-turbo)
        """
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.openai.com/v1"
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")
    
    def write_article(
        self,
        title: str,
        sources_text: str,
        language: str = "zh-CN",
        style: str = "news",
        tone: str = "professional",
        length: str = "medium",
        citations_required: bool = True
    ) -> Optional[ArticleDraft]:
        """Generate article from sources.
        
        Args:
            title: Article title/topic
            sources_text: Concatenated source texts
            language: Language to write in (default zh-CN)
            style: Article style ('news', 'explainer', 'opinion', 'howto')
            tone: Writing tone (default 'professional')
            length: Article length ('short'~300w, 'medium'~800w, 'long'~1500w)
            citations_required: Include source citations
            
        Returns:
            ArticleDraft or None if failed
        """
        # Determine word count target
        length_map = {
            "short": 300,
            "medium": 800,
            "long": 1500
        }
        target_words = length_map.get(length, 800)
        
        # Build system prompt
        system_prompt = self._build_system_prompt(
            language, style, tone, length, citations_required, target_words
        )
        
        # Build user prompt
        user_prompt = self._build_user_prompt(title, sources_text, citations_required)
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": target_words + 500,
                    "timeout": 30
                },
                timeout=35
            )
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            tokens = result.get("usage", {}).get("total_tokens", 0)
            
            # Parse response
            draft = self._parse_response(content, language, style, length, self.model, tokens)
            
            if draft:
                logger.info(f"Generated article: '{draft.title}' ({draft.word_count} words, {tokens} tokens)")
                return draft
            else:
                logger.error("Failed to parse article response")
                return None
            
        except requests.RequestException as e:
            logger.error(f"OpenAI API failed: {e}")
            return None
    
    def _build_system_prompt(
        self,
        language: str,
        style: str,
        tone: str,
        length: str,
        citations_required: bool,
        target_words: int
    ) -> str:
        """Build system prompt for article writing."""
        lang_name = "Chinese" if language == "zh-CN" else "English"
        
        prompt = f"""You are a professional content writer. Your task is to write a high-quality article in {lang_name}.

Writing Guidelines:
- Language: {lang_name}
- Style: {style} (news/explainer/opinion/howto)
- Tone: {tone}
- Target length: approximately {target_words} words
- Citations: {'Required - cite sources with [Source: URL]' if citations_required else 'Optional'}

CRITICAL RULES:
1. ONLY USE FACTS PRESENT IN THE PROVIDED SOURCES
2. If information is not in sources, explicitly write: {'暂无可靠信息' if language == 'zh-CN' else 'No reliable information available'}
3. Do NOT hallucinate facts or make up information
4. Each claim should be traceable to at least one source

Response Format (REQUIRED - use exactly this structure):

---START ARTICLE---
**TITLE:** [Article Title Here]

**Summary Bullets:**
- Bullet 1
- Bullet 2
- Bullet 3

**Main Body:**
[Write the article with clear headings and paragraphs. Include citations like [Source: domain.com]]

**Key Takeaways:**
1. [Takeaway 1]
2. [Takeaway 2]
3. [Takeaway 3]

**Sources:**
- [Source](URL)
- [Source](URL)

---END ARTICLE---

Now write the article based on the provided sources."""
        
        return prompt
    
    def _build_user_prompt(self, title: str, sources_text: str, citations_required: bool) -> str:
        """Build user prompt with sources."""
        prompt = f"""Please write an article about: {title}

Here are the source materials:

{sources_text}

Requirements:
- Focus on: {title}
- Cite sources as you use them
- Be factual and avoid speculation
- Use the exact response format specified in the system prompt"""
        
        return prompt
    
    def _parse_response(
        self,
        content: str,
        language: str,
        style: str,
        length: str,
        model: str,
        tokens: int
    ) -> Optional[ArticleDraft]:
        """Parse LLM response into ArticleDraft.
        
        Looks for markers: ---START ARTICLE---, TITLE:, Summary Bullets:, Main Body:, etc.
        """
        try:
            # Extract between markers
            start_idx = content.find("---START ARTICLE---")
            end_idx = content.find("---END ARTICLE---")
            
            if start_idx < 0 or end_idx < 0:
                logger.warning("Article markers not found, attempting to parse anyway")
                article_text = content
            else:
                article_text = content[start_idx + len("---START ARTICLE---"):end_idx].strip()
            
            # Parse sections
            title = self._extract_section(article_text, r"\*\*TITLE:\*\*\s*(.+?)(?:\n|$)", "Untitled")
            
            summary_bullets = self._extract_list_section(
                article_text,
                r"\*\*Summary Bullets:\*\*\s*\n((?:- .+\n?)+)",
                "summary_bullets"
            )
            
            body = self._extract_section(
                article_text,
                r"\*\*Main Body:\*\*\s*\n(.+?)\n\*\*Key Takeaways:",
                ""
            )
            
            key_takeaways = self._extract_list_section(
                article_text,
                r"\*\*Key Takeaways:\*\*\s*\n((?:\d+\. .+\n?)+)",
                "key_takeaways"
            )
            
            sources_section = self._extract_section(
                article_text,
                r"\*\*Sources:\*\*\s*\n(.+)$",
                ""
            )
            
            # Count words
            word_count = len(body.split())
            
            draft = ArticleDraft(
                title=title,
                summary_bullets=summary_bullets,
                body=body,
                key_takeaways=key_takeaways,
                sources_section=sources_section,
                language=language,
                style=style,
                length=length,
                word_count=word_count,
                model=model,
                tokens_used=tokens
            )
            
            return draft
            
        except Exception as e:
            logger.error(f"Parse error: {e}")
            return None
    
    @staticmethod
    def _extract_section(text: str, pattern: str, default: str = "") -> str:
        """Extract a section using regex."""
        import re
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return default
    
    @staticmethod
    def _extract_list_section(text: str, pattern: str, section_type: str) -> List[str]:
        """Extract a list section."""
        import re
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            lines = match.group(1).strip().split("\n")
            # Remove bullet/numbering
            items = []
            for line in lines:
                line = line.strip()
                if section_type == "summary_bullets":
                    line = re.sub(r"^- ", "", line)
                else:  # key_takeaways
                    line = re.sub(r"^\d+\. ", "", line)
                
                if line:
                    items.append(line)
            
            return items
        
        return []
