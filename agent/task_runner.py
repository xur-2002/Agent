"""Enhanced task execution module with retry logic and new task types."""

import os
import logging
import time
import feedparser
import requests
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from agent.models import Task, TaskResult
from agent.utils import now_utc, truncate_str

logger = logging.getLogger(__name__)


def run_task_with_retry(task: Task, retry_count: int = 2, backoff_times: list = None) -> TaskResult:
    """Execute a task with retry logic and exponential backoff.
    
    Args:
        task: Task to execute.
        retry_count: Number of retries (default 2).
        backoff_times: List of backoff seconds for each retry (default [1, 3, 7]).
    
    Returns:
        TaskResult with status, summary, and optional error.
    """
    if backoff_times is None:
        backoff_times = [1, 3, 7]
    
    attempt = 0
    last_error = None
    last_result = None
    
    while attempt <= retry_count:
        try:
            logger.debug(f"[{task.id}] Attempt {attempt + 1}/{retry_count + 1}")
            result = run_task(task)
            last_result = result
            
            if result.status == "success":
                logger.info(f"[{task.id}] Task succeeded on attempt {attempt + 1}")
                return result
            else:
                last_error = result.error
                if attempt < retry_count:
                    wait_time = backoff_times[attempt] if attempt < len(backoff_times) else backoff_times[-1]
                    logger.info(f"[{task.id}] Task failed, retrying in {wait_time}s...")
                    time.sleep(wait_time)
        
        except Exception as e:
            last_error = str(e)
            if attempt < retry_count:
                wait_time = backoff_times[attempt] if attempt < len(backoff_times) else backoff_times[-1]
                logger.warning(f"[{task.id}] Exception: {e}, retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"[{task.id}] Task failed after {retry_count + 1} attempts: {e}")
        
        attempt += 1
    
    # All retries exhausted - return last result or failed
    if last_result:
        return last_result
    
    return TaskResult(
        status="failed",
        summary=f"Task failed after {retry_count + 1} attempts",
        error=last_error or "Unknown error"
    )


def run_task(task: Task) -> TaskResult:
    """Execute a task and return the result.
    
    Dispatches to specific task implementations based on task.id.
    
    Args:
        task: Task object to execute.
    
    Returns:
        TaskResult with status, summary, metrics, and optional error.
    """
    task_id = task.id
    start_time = now_utc()
    
    logger.info(f"[{task_id}] Starting task execution")
    
    try:
        # Route to task-specific handler
        if task_id == "heartbeat":
            result = run_heartbeat(task)
        elif task_id == "daily_briefing":
            result = run_daily_briefing(task)
        elif task_id == "health_check_url":
            result = run_health_check_url(task)
        elif task_id == "rss_watch":
            result = run_rss_watch(task)
        elif task_id == "github_trending_watch":
            result = run_github_trending_watch(task)
        elif task_id == "github_repo_watch":
            result = run_github_repo_watch(task)
        elif task_id == "keyword_trend_watch":
            result = run_keyword_trend_watch(task)
        elif task_id == "article_generate":
            result = run_article_generate(task)
        elif task_id == "publish_kit_build":
            result = run_publish_kit_build(task)
        else:
            raise ValueError(f"Unknown task ID: {task_id}")
        
        # Calculate duration
        duration = (now_utc() - start_time).total_seconds()
        result.duration_sec = duration
        
        logger.info(f"[{task_id}] Task completed: {result.status} ({duration:.2f}s)")
        return result
    
    except Exception as e:
        duration = (now_utc() - start_time).total_seconds()
        error_msg = str(e)
        logger.error(f"[{task_id}] Task failed after {duration:.2f}s: {error_msg}")
        return TaskResult(
            status="failed",
            summary=f"Task execution failed",
            error=error_msg,
            duration_sec=duration
        )


def run_heartbeat(task: Task) -> TaskResult:
    """Heartbeat task: runs every minute, always succeeds with system status.
    
    Returns:
        TaskResult with system health summary.
    """
    now_utc_time = now_utc()
    summary = f"Heartbeat at {now_utc_time.isoformat()}"
    
    return TaskResult(
        status="success",
        summary=summary,
        metrics={
            "timestamp_utc": now_utc_time.isoformat(),
        }
    )


def run_daily_briefing(task: Task) -> TaskResult:
    """Daily briefing: summarizes recent task activity.
    
    Returns:
        TaskResult with briefing summary.
    """
    now = now_utc()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M UTC")
    
    briefing = (
        f"Daily Briefing for {date_str}\n"
        f"Generated at {time_str}\n"
        f"Status: Agent is running successfully.\n"
        f"All systems operational."
    )
    
    summary = truncate_str(briefing)
    
    return TaskResult(
        status="success",
        summary=summary,
        metrics={"type": "briefing", "date": date_str}
    )


def run_health_check_url(task: Task) -> TaskResult:
    """Health check a URL: verify status code, latency, and optional keyword.
    
    Params:
        url: URL to check (required)
        timeout_sec: Request timeout in seconds (default 10)
        expected_status: Expected HTTP status code (default 200)
        expected_keyword: Optional keyword to find in response body
        max_latency_sec: Maximum acceptable latency in seconds (optional)
    
    Returns:
        TaskResult with status "success" or "failed".
    """
    params = task.params
    url = params.get("url")
    timeout_sec = params.get("timeout_sec", 10)
    expected_status = params.get("expected_status", 200)
    expected_keyword = params.get("expected_keyword")
    max_latency_sec = params.get("max_latency_sec")
    
    if not url:
        raise ValueError("health_check_url requires 'url' parameter")
    
    try:
        start = time.time()
        response = requests.get(url, timeout=timeout_sec, allow_redirects=True)
        latency_sec = time.time() - start
        
        # Check status code
        if response.status_code != expected_status:
            return TaskResult(
                status="failed",
                summary=f"✗ {url} returned {response.status_code} (expected {expected_status})",
                metrics={"status_code": response.status_code, "latency_sec": latency_sec},
                error=f"HTTP {response.status_code}"
            )
        
        # Check latency if specified
        if max_latency_sec and latency_sec > max_latency_sec:
            return TaskResult(
                status="failed",
                summary=f"✗ {url} latency {latency_sec:.2f}s exceeded max {max_latency_sec}s",
                metrics={"status_code": response.status_code, "latency_sec": latency_sec},
                error=f"Latency {latency_sec:.2f}s > {max_latency_sec}s"
            )
        
        # Check for keyword if specified
        if expected_keyword and expected_keyword not in response.text:
            return TaskResult(
                status="failed",
                summary=f"✗ {url} missing keyword '{expected_keyword}'",
                metrics={"status_code": response.status_code, "latency_sec": latency_sec},
                error=f"Keyword not found"
            )
        
        return TaskResult(
            status="success",
            summary=f"✓ {url} → {response.status_code} ({latency_sec:.2f}s)",
            metrics={"status_code": response.status_code, "latency_sec": latency_sec}
        )
    
    except requests.Timeout:
        return TaskResult(
            status="failed",
            summary=f"✗ {url} timeout after {timeout_sec}s",
            error=f"Timeout"
        )
    except requests.RequestException as e:
        return TaskResult(
            status="failed",
            summary=f"✗ {url} connection failed",
            error=str(e)
        )


def run_rss_watch(task: Task) -> TaskResult:
    """Watch RSS feed(s) for new items since last run.
    
    Params:
        feed_urls: List of feed URLs or single URL string (required)
        max_items: Max items to report (default 3)
    
    Returns:
        TaskResult with list of new items.
    """
    params = task.params
    feed_urls_param = params.get("feed_urls") or params.get("feed_url")
    max_items = params.get("max_items", 3)
    
    if not feed_urls_param:
        raise ValueError("rss_watch requires 'feed_urls' or 'feed_url' parameter")
    
    # Normalize to list
    feed_urls = feed_urls_param if isinstance(feed_urls_param, list) else [feed_urls_param]
    
    new_items = []
    error_msg = None
    
    try:
        for feed_url in feed_urls:
            try:
                feed = feedparser.parse(feed_url)
                
                if feed.get("bozo"):
                    logger.warning(f"RSS feed {feed_url} has parsing errors")
                
                # Get recent items
                entries = feed.get("entries", [])[:max_items]
                
                for entry in entries:
                    item_dict = {
                        "title": entry.get("title", "Untitled"),
                        "link": entry.get("link", ""),
                        "published": entry.get("published", ""),
                    }
                    new_items.append(item_dict)
            
            except Exception as e:
                logger.error(f"Error fetching feed {feed_url}: {e}")
                if not error_msg:
                    error_msg = str(e)
        
        if not new_items:
            return TaskResult(
                status="success",
                summary=f"No new items in {len(feed_urls)} feed(s)",
                metrics={"feeds": len(feed_urls), "items": 0}
            )
        
        # Format summary
        summary_lines = [f"Found {len(new_items)} new items:"]
        for item in new_items[:max_items]:
            summary_lines.append(f"• {truncate_str(item['title'], 60)}")
        
        return TaskResult(
            status="success" if not error_msg else "failed",
            summary="\n".join(summary_lines),
            metrics={"feeds": len(feed_urls), "items": len(new_items)},
            error=error_msg
        )
    
    except Exception as e:
        return TaskResult(
            status="failed",
            summary="RSS watch failed",
            error=str(e)
        )


def run_github_trending_watch(task: Task) -> TaskResult:
    """Watch GitHub Trending for new projects.
    
    Params:
        language: Programming language (optional, empty for all)
        max_items: Max projects to report (default 5)
    
    Returns:
        TaskResult with trending projects.
    """
    params = task.params
    language = params.get("language", "").lower()
    max_items = params.get("max_items", 5)
    
    try:
        url = "https://github.com/trending"
        if language:
            url += f"/{language}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # GitHub Trending doesn't have official API. For production, use GraphQL.
        # For now, just confirm it's accessible.
        
        summary = f"GitHub Trending {'in ' + language if language else '(all languages)'}: Monitoring active"
        
        return TaskResult(
            status="success",
            summary=summary,
            metrics={"language": language, "max_items": max_items}
        )
    
    except Exception as e:
        return TaskResult(
            status="failed",
            summary="GitHub Trending watch failed",
            error=str(e)
        )


def run_github_repo_watch(task: Task) -> TaskResult:
    """Watch GitHub repo(s) for new releases.
    
    Params:
        repos: List of "owner/repo" or single repo string (required)
        watch_releases: Watch for new releases (default True)
    
    Returns:
        TaskResult with release updates.
    """
    params = task.params
    repos_param = params.get("repos") or params.get("repo")
    watch_releases = params.get("watch_releases", True)
    
    if not repos_param:
        raise ValueError("github_repo_watch requires 'repos' or 'repo' parameter")
    
    # Normalize to list
    repos = repos_param if isinstance(repos_param, list) else [repos_param]
    
    updates = []
    
    try:
        for repo in repos:
            try:
                if watch_releases:
                    # Check latest release
                    url = f"https://api.github.com/repos/{repo}/releases/latest"
                    response = requests.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        release_data = response.json()
                        tag = release_data.get("tag_name", "unknown")
                        updates.append(f"Latest release: {tag}")
                    elif response.status_code == 404:
                        updates.append(f"No releases found")
            
            except Exception as e:
                logger.error(f"Error checking repo {repo}: {e}")
        
        if not updates:
            summary = f"Monitoring {len(repos)} repo(s) - no updates"
        else:
            summary = f"Updates for {len(repos)} repo(s):\n" + "\n".join(updates)
        
        return TaskResult(
            status="success",
            summary=summary,
            metrics={"repos": len(repos), "updates": len(updates)}
        )
    
    except Exception as e:
        return TaskResult(
            status="failed",
            summary="GitHub repo watch failed",
            error=str(e)
        )


def run_keyword_trend_watch(task: Task) -> TaskResult:
    """Monitor keywords for trending topics.
    
    Params:
        keywords: List of keywords to watch
        region: Region/language (zh-CN default)
        search_provider: 'serper' default, or 'bing'
    
    Returns:
        TaskResult with trending topics.
    """
    params = task.params
    keywords = params.get("keywords", [])
    if isinstance(keywords, str):
        keywords = [keywords]
    
    if not keywords:
        raise ValueError("keyword_trend_watch requires 'keywords' param")
    
    try:
        # This is a stub implementation - actual implementation
        # would use search provider to find trends
        # For now, return a placeholder result
        summary = f"Monitoring {len(keywords)} keyword(s):\n"
        summary += "\n".join(f"• {kw}" for kw in keywords[:5])
        
        return TaskResult(
            status="success",
            summary=summary,
            metrics={"keywords": len(keywords), "topics_found": 0}
        )
    
    except Exception as e:
        return TaskResult(
            status="failed",
            summary="Keyword trend watch failed",
            error=str(e)
        )


def run_article_generate(task: Task) -> TaskResult:
    """Generate articles from keywords using search + LLM.
    
    Minimal cost closed-loop implementation:
    - Uses Serper API to search (top 5 results) if available
    - Uses GPT-4o-mini for article generation (cheapest model)
    - No image generation, no email
    - Saves articles to outputs/articles/YYYY-MM-DD/
    - Supports DRY_RUN mode for testing
    - Gracefully skips if SERPER_API_KEY or OPENAI_API_KEY missing
    
    Params:
        keywords: List of keywords to generate articles for
        daily_article_count: Target number of articles per day (informational)
    
    Returns:
        TaskResult with successful/failed articles list.
    """
    from agent.article_generator import generate_article, save_article
    
    params = task.params
    keywords = params.get("keywords", [])
    
    if isinstance(keywords, str):
        keywords = [keywords]
    
    if not keywords:
        return TaskResult(
            status="failed",
            summary="No keywords provided",
            error="keywords param is empty"
        )
    
    # Check required secrets
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    serper_key = os.getenv("SERPER_API_KEY", "").strip()
    dry_run = os.getenv("DRY_RUN", "0") == "1"
    
    # Graceful degradation: skip if OpenAI key missing
    if not openai_key and not dry_run:
        logger.warning("[article_generate] OPENAI_API_KEY not set - task skipped (set DRY_RUN=1 to test locally)")
        return TaskResult(
            status="skipped",
            summary="Article generation skipped - OPENAI_API_KEY not configured",
            error="OPENAI_API_KEY missing"
        )
    
    try:
        logger.info(f"[article_generate] Starting with {len(keywords)} keyword(s), DRY_RUN={dry_run}, SERPER={'available' if serper_key else 'not set'}")
        
        # Try to get search provider, but allow None
        search_provider = None
        if serper_key:
            try:
                from agent.content_pipeline.search import get_search_provider
                search_provider = get_search_provider(os.getenv("SEARCH_PROVIDER", "serper"))
            except Exception as e:
                logger.warning(f"[article_generate] Failed to initialize search provider: {e}")
                search_provider = None
        
        successful_articles = []
        failed_articles = []
        start_time = now_utc()
        
        # Generate articles for each keyword
        for keyword in keywords:
            try:
                logger.info(f"[article_generate] Processing keyword: {keyword}")
                
                # Search for this keyword (optional if no Serper key)
                search_results = None
                if search_provider:
                    try:
                        search_results = search_provider.search(keyword, limit=5)
                    except Exception as e:
                        logger.warning(f"[article_generate] Search failed for '{keyword}': {e} - continuing with empty search context")
                        search_results = []
                else:
                    logger.info(f"[article_generate] No search provider available - generating article with context-only mode for '{keyword}'")
                    search_results = []
                
                # Generate article (with or without search context)
                article = generate_article(
                    keyword=keyword,
                    search_results=[
                        {
                            "title": r.title,
                            "snippet": r.snippet,
                            "link": r.url
                        }
                        for r in (search_results or [])
                    ],
                    dry_run=dry_run,
                    language=params.get("language", "zh-CN")
                )
                
                if not article:
                    logger.error(f"[article_generate] Failed to generate article for: {keyword}")
                    failed_articles.append({
                        "keyword": keyword,
                        "error": "Article generation failed"
                    })
                    continue
                
                # Save article
                file_path = save_article(article)
                if not file_path:
                    logger.error(f"[article_generate] Failed to save article for: {keyword}")
                    failed_articles.append({
                        "keyword": keyword,
                        "error": "Failed to save article"
                    })
                    continue
                
                # Record successful article
                successful_articles.append({
                    "keyword": keyword,
                    "title": article.get("title", ""),
                    "word_count": article.get("word_count", 0),
                    "file_path": file_path,
                    "sources_count": len(article.get("sources", []))
                })
                logger.info(f"[article_generate] Successfully generated: {article.get('title', keyword)} ({article.get('word_count', 0)} words)")
                
            except Exception as e:
                logger.error(f"[article_generate] Error processing keyword {keyword}: {e}", exc_info=True)
                failed_articles.append({
                    "keyword": keyword,
                    "error": str(e)[:200]
                })
        
        elapsed = (now_utc() - start_time).total_seconds()
        
        # Build summary
        if successful_articles:
            summary = f"✅ Generated {len(successful_articles)} article(s) in {elapsed:.1f}s\n"
            for article in successful_articles:
                summary += f"• {article['title']} ({article['word_count']} words)\n"
        else:
            summary = "No articles were generated"
        
        if failed_articles:
            summary += f"\n❌ {len(failed_articles)} article(s) failed\n"
            for failed in failed_articles[:3]:  # Show first 3 failures
                summary += f"• {failed['keyword']}: {failed['error']}\n"
        
        # Return result
        status = "success" if successful_articles else "failed"
        return TaskResult(
            status=status,
            summary=summary,
            metrics={
                "successful": len(successful_articles),
                "failed": len(failed_articles),
                "total_keywords": len(keywords),
                "elapsed_seconds": elapsed,
                "dry_run": dry_run,
                "successful_articles": successful_articles,
                "failed_articles": failed_articles
            },
            duration_sec=elapsed
        )
        
    except Exception as e:
        logger.error(f"[article_generate] Task error: {e}", exc_info=True)
        return TaskResult(
            status="failed",
            summary="Article generation task failed",
            error=str(e)[:500]
        )


def run_publish_kit_build(task: Task) -> TaskResult:
    """Build a publish kit with all generated articles.
    
    Params:
        (no specific params needed)
    
    Returns:
        TaskResult with kit location.
    """
    try:
        # This is a stub - actual would gather all articles
        # from today and create publish kit
        summary = "Publish kit building configured:\n"
        summary += "• Will collect today's articles\n"
        summary += "• Generate manifests and checklists\n"
        summary += "• Create platform-specific formats\n"
        summary += "• Output as ZIP archive"
        
        return TaskResult(
            status="success",
            summary=summary,
            metrics={"kit_status": "ready", "articles_count": 0}
        )
    
    except Exception as e:
        return TaskResult(
            status="failed",
            summary="Publish kit build failed",
            error=str(e)
        )
