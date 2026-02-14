"""Search provider abstraction for finding articles by keyword."""

import os
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
import requests

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Result from a search query."""
    title: str
    url: str
    snippet: str
    published_date: Optional[str] = None
    domain: Optional[str] = None
    position: int = 0  # Rank in results


class SearchProvider(ABC):
    """Abstract search provider."""
    
    @abstractmethod
    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Search for query and return top results.
        
        Args:
            query: Search query string
            limit: Number of results to return
            
        Returns:
            List of SearchResult objects
        """
        pass


class SerperSearchProvider(SearchProvider):
    """Google Serper API search provider (https://serper.dev)."""
    
    def __init__(self, api_key: str):
        """Initialize Serper provider.
        
        Args:
            api_key: Serper API key from environment
        """
        self.api_key = api_key
        self.base_url = "https://google.serper.dev/search"
        
        if not api_key:
            raise ValueError("SERPER_API_KEY not set")
    
    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Search using Serper API.
        
        Args:
            query: Search query
            limit: Number of results (default 10, max 100)
            
        Returns:
            List of SearchResult objects
        """
        limit = min(limit, 100)
        
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "q": query,
            "num": limit,
            "gl": "cn",
            "hl": "zh-CN"
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            organic_results = data.get("organic", [])
            
            for i, item in enumerate(organic_results[:limit]):
                result = SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    published_date=item.get("date"),
                    domain=item.get("domain"),
                    position=i + 1
                )
                results.append(result)
            
            logger.info(f"Serper: Found {len(results)} results for '{query}'")
            return results
            
        except requests.RequestException as e:
            logger.error(f"Serper search failed: {e}")
            return []


class BingSearchProvider(SearchProvider):
    """Bing Search API provider (fallback)."""
    
    def __init__(self, api_key: str):
        """Initialize Bing provider.
        
        Args:
            api_key: Bing Search API key
        """
        self.api_key = api_key
        self.base_url = "https://api.bing.microsoft.com/v7.0/search"
        
        if not api_key:
            raise ValueError("BING_SEARCH_KEY not set")
    
    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Search using Bing API.
        
        Args:
            query: Search query
            limit: Number of results
            
        Returns:
            List of SearchResult objects
        """
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key
        }
        
        params = {
            "q": query,
            "count": min(limit, 50),
            "mkt": "zh-CN",
            "setLang": "zh"
        }
        
        try:
            response = requests.get(
                self.base_url,
                headers=headers,
                params=params,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            web_pages = data.get("webPages", {}).get("value", [])
            
            for i, page in enumerate(web_pages[:limit]):
                result = SearchResult(
                    title=page.get("name", ""),
                    url=page.get("url", ""),
                    snippet=page.get("snippet", ""),
                    position=i + 1
                )
                results.append(result)
            
            logger.info(f"Bing: Found {len(results)} results for '{query}'")
            return results
            
        except requests.RequestException as e:
            logger.error(f"Bing search failed: {e}")
            return []


def get_search_provider(provider: str = "serper") -> SearchProvider:
    """Get a search provider instance.
    
    Args:
        provider: Provider name ('serper' or 'bing')
        
    Returns:
        SearchProvider instance
        
    Raises:
        ValueError: If provider not found or API key not set
    """
    provider_lower = provider.lower()
    
    if provider_lower == "serper":
        api_key = os.getenv("SERPER_API_KEY")
        return SerperSearchProvider(api_key)
    
    elif provider_lower == "bing":
        api_key = os.getenv("BING_SEARCH_KEY")
        return BingSearchProvider(api_key)
    
    else:
        raise ValueError(f"Unknown search provider: {provider}")


def search_sources(query: str, persona: dict = None, limit: int = 5, retries: int = 2, backoff: float = 1.0):
    """High-level wrapper: run search with retries/backoff and always return (results_list, errors_list).

    Returns:
        (List[SearchResult], List[str])
    """
    errors = []
    results = []
    provider_name = os.getenv('SEARCH_PROVIDER', 'serper')

    # Pick provider
    try:
        provider = get_search_provider(provider_name)
    except Exception as e:
        errors.append(f"init:{str(e)}")
        return ([], errors)

    attempt = 0
    while attempt <= retries:
        try:
            results = provider.search(query, limit=limit)
            # ensure list
            if results is None:
                results = []
            return (results, errors)
        except Exception as e:
            err = str(e)
            errors.append(err)
            attempt += 1
            time.sleep(backoff * attempt)

    return (results or [], errors)
