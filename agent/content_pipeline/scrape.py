"""Web scraping and heat scoring for trend detection."""

import logging
import time
import re
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class TrendTopic:
    """A trending topic with scoring."""
    keyword: str
    topic: str
    heat_score: float
    sources_count: int
    avg_recency_hours: float
    top_sources: List[str] = field(default_factory=list)
    snippets: List[str] = field(default_factory=list)
    generated: bool = False  # Whether article already generated today
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class SourceDoc:
    """Extracted source document."""
    url: str
    title: str
    domain: str
    snippet: str
    published_date: Optional[str]
    fetched_at: str
    readable_text: str = ""
    image_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class HeatScorer:
    """Calculate heat scores for topics."""
    
    def __init__(self, recency_days: int = 7):
        """Initialize scorer.
        
        Args:
            recency_days: Consider content newer than N days (default 7)
        """
        self.recency_days = recency_days
    
    def score_sources(
        self,
        sources: List[SourceDoc],
        keyword: str
    ) -> float:
        """Calculate heat score from sources.
        
        Factors:
        - Source count (more = hotter)
        - Recency (recent = hotter)
        - Keyword frequency in snippets
        
        Args:
            sources: List of source documents
            keyword: Original keyword
            
        Returns:
            Heat score (0-100)
        """
        if not sources:
            return 0.0
        
        now = datetime.utcnow()
        cutoff = now - timedelta(days=self.recency_days)
        
        # Factor 1: Source count (normalized to 0-40 points)
        # 5+ sources = 40 points, 1 source = 8 points
        count_score = min(40, max(8, len(sources) * 4))
        
        # Factor 2: Recency (normalized to 0-30 points)
        recent_sources = 0
        for source in sources:
            if source.published_date:
                try:
                    pub_date = datetime.fromisoformat(source.published_date.replace("Z", "+00:00"))
                    if pub_date > cutoff:
                        recent_sources += 1
                except (ValueError, AttributeError):
                    pass
        
        recency_score = min(30, (recent_sources / len(sources) * 30)) if sources else 0
        
        # Factor 3: Keyword frequency in snippets (0-30 points)
        keyword_lower = keyword.lower()
        keyword_count = sum(
            source.snippet.lower().count(keyword_lower)
            for source in sources
        )
        freq_score = min(30, keyword_count * 2)
        
        total_score = count_score + recency_score + freq_score
        return min(100.0, total_score)
    
    def avg_recency_hours(self, sources: List[SourceDoc]) -> float:
        """Calculate average recency of sources in hours.
        
        Args:
            sources: List of sources
            
        Returns:
            Average hours ago (e.g., 12.5 = 12.5 hours ago)
        """
        if not sources:
            return 24 * 7  # Default to 1 week
        
        now = datetime.utcnow()
        hours = []
        
        for source in sources:
            if source.published_date:
                try:
                    pub_date = datetime.fromisoformat(source.published_date.replace("Z", "+00:00"))
                    age_hours = (now - pub_date).total_seconds() / 3600
                    hours.append(age_hours)
                except (ValueError, AttributeError):
                    pass
        
        return sum(hours) / len(hours) if hours else 24 * 7


class WebScraper:
    """Scrape web pages for readable content."""
    
    def __init__(self, timeout: int = 10, retries: int = 2):
        """Initialize scraper.
        
        Args:
            timeout: Request timeout in seconds
            retries: Number of retries on failure
        """
        self.timeout = timeout
        self.retries = retries
    
    def fetch_and_extract(self, url: str) -> Optional[str]:
        """Fetch URL and extract readable text.
        
        Args:
            url: URL to fetch
            
        Returns:
            Readable text content or None if failed
        """
        if not url.startswith(("http://", "https://")):
            return None
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        for attempt in range(self.retries):
            try:
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=self.timeout,
                    allow_redirects=True
                )
                response.raise_for_status()
                
                # Only process HTML
                if "text/html" not in response.headers.get("content-type", ""):
                    return None
                
                return self._extract_readable_text(response.text, url)
                
            except requests.RequestException as e:
                logger.warning(f"Fetch attempt {attempt + 1} failed for {url}: {e}")
                if attempt < self.retries - 1:
                    time.sleep(1)
        
        return None
    
    def _extract_readable_text(self, html: str, url: str) -> str:
        """Extract main text from HTML.
        
        Removes boilerplate, nav, script, style, etc.
        
        Args:
            html: Raw HTML
            url: Source URL (for context)
            
        Returns:
            Cleaned readable text
        """
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # Remove unwanted tags
            for tag in soup(["script", "style", "nav", "footer", "button", "form"]):
                tag.decompose()
            
            # Try to find main content area
            main_content = None
            for selector in ["main", "article", "[role='main']", ".content", ".post", ".article"]:
                elem = soup.select_one(selector)
                if elem:
                    main_content = elem
                    break
            
            # Fallback to body
            if not main_content:
                main_content = soup.find("body") or soup
            
            # Extract paragraphs
            paragraphs = []
            for p in main_content.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "dd"]):
                text = p.get_text(strip=True)
                if len(text) > 20:  # Skip short fragments
                    paragraphs.append(text)
            
            readable = "\n".join(paragraphs)
            
            # Clean up whitespace
            readable = re.sub(r"\n{3,}", "\n\n", readable)
            readable = re.sub(r" {2,}", " ", readable)
            
            return readable[:10000]  # Limit length
            
        except Exception as e:
            logger.error(f"Text extraction failed for {url}: {e}")
            return ""


def extract_sources(
    search_results: List,  # From search.py SearchResult
    scraper: WebScraper
) -> List[SourceDoc]:
    """Extract and scrape source documents from search results.
    
    Args:
        search_results: List of SearchResult objects
        scraper: WebScraper instance
        
    Returns:
        List of SourceDoc objects
    """
    sources = []
    now_iso = datetime.utcnow().isoformat() + "Z"
    
    for result in search_results:
        # Skip if content looks low-quality
        if not result.snippet or len(result.snippet) < 30:
            logger.debug(f"Skipping {result.url} (poor snippet)")
            continue
        
        # Fetch and extract readable text
        readable = scraper.fetch_and_extract(result.url)
        if not readable:
            logger.debug(f"Skipping {result.url} (extraction failed)")
            continue
        
        source = SourceDoc(
            url=result.url,
            title=result.title,
            domain=result.domain or "",
            snippet=result.snippet,
            published_date=result.published_date,
            fetched_at=now_iso,
            readable_text=readable
        )
        sources.append(source)
    
    logger.info(f"Extracted {len(sources)} source documents from {len(search_results)} results")
    return sources
