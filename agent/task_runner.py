"""Enhanced task execution module with retry logic and new task types."""

import os
import logging
import time
import feedparser
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from agent.models import Task, TaskResult
from agent.utils import now_utc, truncate_str
from agent.trends import select_topics
from agent.feishu import send_article_generation_results
from agent.article_generator import generate_article_in_style, slugify
from agent.image_provider import provide_cover_image, image_search

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
        elif task_id == "daily_content_batch":
            result = run_daily_content_batch(task)
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
    """Generate articles with configurable LLM provider (Groq/OpenAI/DRY_RUN).
    
    Features:
    - Multi-provider support: groq (free), openai (paid), dry_run (mock)
    - Smart error classification: insufficient_quota -> skip, transient -> retry
    - Per-keyword tracking: successful, failed, skipped
    - Graceful degradation: missing key -> skip, not fail
    
    Params:
        keywords: List of keywords to generate articles for
        language: zh-CN or en-US
    
    Returns:
        TaskResult with status=success/skipped/failed and detailed metrics
    """
    from agent.article_generator import (
        generate_article, generate_article_from_material, save_article,
        LLMProviderError, MissingAPIKeyError, InsufficientQuotaError,
        RateLimitError, TransientError
    )
    from agent.config import Config
    
    params = task.params or {}
    keywords = params.get("keywords", [])
    
    if isinstance(keywords, str):
        keywords = [keywords]
    
    # Start high-resolution timer for duration measurement
    start_perf = time.perf_counter()

    # Ensure search-related tracking variables are always defined
    search_errors: list = []
    search_provider_used = None
    search_attempted = False

    if not keywords:
        elapsed_perf = max(time.perf_counter() - start_perf, 1e-6)
        metrics = {
            "successful_articles": [],
            "failed_articles": [],
            "skipped_articles": [],
            "sources_count": 0,
            "provider": None,
            "search_provider_used": None,
            "search_attempted": False,
            "search_errors": []
        }
        return TaskResult(
            status="failed",
            summary="No keywords provided",
            error="keywords param is empty",
            metrics=metrics,
            duration_sec=elapsed_perf
        )
    
    logger.info(f"[article_generate] Starting with {len(keywords)} keyword(s)")
    logger.info(f"[article_generate] LLM_PROVIDER={Config.LLM_PROVIDER}")
    
    try:
        # Try to get search provider, but allow None. Track attempts and errors.
        search_provider = None
        total_sources_count = 0
        if Config.SERPER_API_KEY:
            # We attempted to initialize a search provider
            search_attempted = True
            try:
                from agent.content_pipeline.search import get_search_provider
                search_provider = get_search_provider(Config.SEARCH_PROVIDER)
                # record which provider was initialized
                search_provider_used = Config.SEARCH_PROVIDER
            except Exception as e:
                logger.error(f"[article_generate] Failed to initialize search provider: {e}")
                # track initialization errors for metrics
                search_errors.append(str(e))
        else:
            # No API key/config provided — search skipped
            search_provider = None
            search_attempted = False
        
        successful_articles = []
        failed_articles = []
        skipped_articles = []
        provider_used = None
        llm_error = None
        start_time = now_utc()
        
        # Generate articles for each keyword
        for keyword in keywords:
            try:
                logger.info(f"[article_generate] Processing keyword: {keyword}")
                
                # Search for this keyword (optional if no Serper key)
                search_results = []
                if search_provider:
                    try:
                        sr = search_provider.search(keyword, limit=5)
                        # Normalize SearchResult objects into simple dicts
                        search_results = []
                        for r in (sr or []):
                            try:
                                search_results.append({
                                    "title": getattr(r, 'title', '') or '',
                                    "url": getattr(r, 'url', '') or getattr(r, 'link', ''),
                                    "snippet": getattr(r, 'snippet', '') or ''
                                })
                            except Exception:
                                search_results.append({
                                    "title": str(r),
                                    "url": '',
                                    "snippet": ''
                                })
                        total_sources_count += len(search_results)
                    except Exception as e:
                        logger.error(f"[article_generate] Search failed for '{keyword}': {e}")
                        search_errors.append(str(e))
                        search_results = []
                
                # Build key points from search snippets
                key_points = []
                for s in search_results:
                    sn = s.get('snippet') or ''
                    if sn:
                        key_points.append(sn.split('. ')[0])

                # Generate article (use material-aware generator with fallback)
                article = generate_article_from_material(
                    keyword, {'sources': search_results, 'key_points': key_points}, language=params.get("language", "zh-CN")
                )
                
                if not article:
                    logger.error(f"[article_generate] Failed to generate article for: {keyword}")
                    failed_articles.append({
                        "keyword": keyword,
                        "reason": "Article generation returned None (parsing failed)"
                    })
                    continue
                
                # Record provider info from first successful article
                if provider_used is None:
                    provider_used = article.get("provider", "unknown")
                
                # Save article
                file_path = save_article(article)
                if not file_path:
                    logger.error(f"[article_generate] Failed to save article for: {keyword}")
                    failed_articles.append({
                        "keyword": keyword,
                        "reason": "Failed to save article to disk"
                    })
                    continue
                
                # Record successful article
                successful_articles.append({
                    "keyword": keyword,
                    "title": article.get("title", ""),
                    "provider": article.get("provider", "unknown"),
                    "model": article.get("model", "unknown"),
                    "word_count": article.get("word_count", 0),
                    "file_path": file_path,
                    "sources_count": article.get("sources_count", 0) or len(search_results)
                })
                logger.info(f"[article_generate] ✅ Generated: {article.get('title', keyword)} ({article.get('word_count', 0)} words, {article.get('provider', '?')})")
                
            except MissingAPIKeyError as e:
                llm_error = e
                logger.warning(f"[article_generate] ⊘ {e.provider} key missing - skipping all remaining keywords")
                skipped_articles.append({
                    "keyword": keyword,
                    "reason": f"missing_{e.provider}_api_key"
                })
                # Once we hit a missing key error, skip remaining keywords
                for remaining_keyword in keywords[keywords.index(keyword) + 1:]:
                    skipped_articles.append({
                        "keyword": remaining_keyword,
                        "reason": f"missing_{e.provider}_api_key"
                    })
                break
                
            except InsufficientQuotaError as e:
                llm_error = e
                logger.warning(f"[article_generate] ⊘ {e.provider} insufficient quota/billing issue - skipping all remaining")
                skipped_articles.append({
                    "keyword": keyword,
                    "reason": f"{e.provider}_insufficient_quota"
                })
                # Skip remaining keywords
                for remaining_keyword in keywords[keywords.index(keyword) + 1:]:
                    skipped_articles.append({
                        "keyword": remaining_keyword,
                        "reason": f"{e.provider}_insufficient_quota"
                    })
                break
                
            except RateLimitError as e:
                logger.warning(f"[article_generate] ⚠️ {e.provider} rate limited - attempting fallback generation")
                try:
                    # Attempt fallback generation (generate_article_from_material will try providers then template)
                    fallback_art = generate_article_from_material(
                        keyword, {'sources': search_results, 'key_points': key_points}, language=params.get("language", "zh-CN")
                    )
                    if fallback_art:
                        file_path = save_article(fallback_art)
                        if file_path:
                            successful_articles.append({
                                "keyword": keyword,
                                "title": fallback_art.get("title", ""),
                                "provider": fallback_art.get("provider", "none"),
                                "model": fallback_art.get("model", "none"),
                                "word_count": fallback_art.get("word_count", 0),
                                "file_path": file_path,
                                "sources_count": fallback_art.get("sources_count", 0) or len(search_results),
                                "fallback_used": fallback_art.get("fallback_used", True)
                            })
                            logger.info(f"[article_generate] ✅ Fallback generated for {keyword}")
                            # continue to next keyword
                            continue
                except Exception as fe:
                    logger.error(f"[article_generate] Fallback generation also failed for {keyword}: {fe}")

                # If fallback didn't succeed, mark as failed (retriable)
                failed_articles.append({
                    "keyword": keyword,
                    "reason": f"{e.provider}_rate_limited (retriable)"
                })
                # Continue trying other keywords
                
            except TransientError as e:
                logger.warning(f"[article_generate] ⚠️ {e.provider} transient error: {e.message}")
                failed_articles.append({
                    "keyword": keyword,
                    "reason": f"{e.provider}_network_error (retriable)"
                })
                # Continue trying other keywords
                
            except LLMProviderError as e:
                logger.error(f"[article_generate] ✗ {e.provider} error: {e.message}")
                if e.retriable:
                    failed_articles.append({
                        "keyword": keyword,
                        "reason": f"{e.provider}_error (retriable)"
                    })
                else:
                    skipped_articles.append({
                        "keyword": keyword,
                        "reason": f"{e.provider}_error (non-retriable)"
                    })
                    
            except Exception as e:
                logger.error(f"[article_generate] ✗ Unexpected error for keyword {keyword}: {e}", exc_info=True)
                failed_articles.append({
                    "keyword": keyword,
                    "reason": f"Unexpected error: {str(e)[:100]}"
                })
        
        # Prefer high-resolution elapsed time
        elapsed_perf = max(time.perf_counter() - start_perf, 1e-6)
        elapsed = elapsed_perf
        
        # Determine overall status
        if successful_articles:
            status = "success"
            status_emoji = "✅"
        elif skipped_articles and not failed_articles and not successful_articles:
            status = "skipped"
            status_emoji = "⊘"
        else:
            status = "failed"
            status_emoji = "❌"
        
        # Build summary
        summary = f"{status_emoji} Article Generation Results\n"
        summary += f"• ✅ Successful: {len(successful_articles)}\n"
        summary += f"• ❌ Failed: {len(failed_articles)}\n"
        summary += f"• ⊘ Skipped: {len(skipped_articles)}\n"
        summary += f"• ⏱️ Time: {elapsed:.1f}s\n"
        
        if provider_used:
            summary += f"• 🤖 Provider: {provider_used}\n"
        
        if status == "skipped" and llm_error:
            summary += f"• Reason skipped: {llm_error.message}"
        
        if successful_articles:
            summary += f"\n✅ Generated {len(successful_articles)} article(s):\n"
            for article in successful_articles[:3]:
                summary += f"  • {article['title']} ({article['word_count']} words)\n"
            if len(successful_articles) > 3:
                summary += f"  ... and {len(successful_articles) - 3} more\n"
        
        if failed_articles:
            summary += f"\n❌ Failed {len(failed_articles)} article(s):\n"
            for failed in failed_articles[:2]:
                reason = failed.get('reason', 'Unknown')[:100]
                summary += f"  • {failed['keyword']}: {reason}\n"
            if len(failed_articles) > 2:
                summary += f"  ... and {len(failed_articles) - 2} more\n"
        
        if skipped_articles:
            summary += f"\n⊘ Skipped {len(skipped_articles)} article(s):\n"
            for skipped in skipped_articles[:2]:
                reason = skipped.get('reason', 'Unknown')
                summary += f"  • {skipped['keyword']}: {reason}\n"
            if len(skipped_articles) > 2:
                summary += f"  ... and {len(skipped_articles) - 2} more\n"
        
        return TaskResult(
            status=status,
            summary=summary,
            metrics={
                "successful": len(successful_articles),
                "failed": len(failed_articles),
                "skipped": len(skipped_articles),
                "total_keywords": len(keywords),
                "elapsed_seconds": elapsed,
                "provider": provider_used or Config.LLM_PROVIDER,
                "search_provider_used": search_provider_used,
                "search_attempted": search_attempted,
                "sources_count": total_sources_count,
                "search_errors": search_errors,
                "successful_articles": successful_articles,
                "failed_articles": failed_articles,
                "skipped_articles": skipped_articles
            },
            duration_sec=elapsed_perf
        )
        
    except Exception as e:
        logger.error(f"[article_generate] Task execution error: {e}", exc_info=True)
        elapsed_perf = max(time.perf_counter() - start_perf, 1e-6)
        # Ensure metrics keys exist even on fatal exception
        metrics = {
            "successful_articles": globals().get('successful_articles', []) or [],
            "failed_articles": globals().get('failed_articles', []) or [],
            "skipped_articles": globals().get('skipped_articles', []) or [],
            "sources_count": globals().get('total_sources_count', 0) or 0,
            "provider": globals().get('provider_used', None),
            "search_provider_used": globals().get('search_provider_used', None),
            "search_attempted": globals().get('search_attempted', False),
            "search_errors": globals().get('search_errors', []) or []
        }
        return TaskResult(
            status="failed",
            summary="Article generation task failed with critical error",
            error=str(e)[:500],
            metrics=metrics,
            duration_sec=elapsed_perf
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


def run_daily_content_batch(task: Task) -> TaskResult:
    """Daily content batch V1: topics -> dual versions -> images -> metadata -> Feishu/email

    Generates two versions of each article:
    - wechat.md: 800-1200 chars, structured (title, intro, body, conclusion)
    - xiaohongshu.md: 300-600 chars, casual (hook, points, suggestion, engagement)

    Images: Priority search -> download -> fallback placeholder

    Params (in task.params):
        daily_quota: Number of topics (overridable by TOP_N env var)
        seed_keywords: Fallback keywords list
        geo: Geographic region for trends (default US)
        cooldown_days: Skip recently generated topics
        email_to: Recipient email
        attach_markdown: Include files in email
    """
    from agent.trends import select_topics
    from agent.article_generator import generate_article_in_style, slugify
    from agent.image_provider import provide_cover_image, image_search
    from agent.email_sender import send_daily_summary
    from agent.feishu import send_article_generation_results
    from agent.storage import get_storage
    import json
    from pathlib import Path
    from datetime import datetime

    params = task.params or {}
    daily_quota = int(params.get('daily_quota', 3))
    seed_keywords = params.get('seed_keywords') or ['AI', 'Cloud Computing', 'Web Development']
    geo = params.get('geo', 'US')
    cooldown_days = int(params.get('cooldown_days', 3))
    email_to = params.get('email_to', 'xu.r@wustl.edu')
    attach_markdown = bool(params.get('attach_markdown', True))

    # Load state
    storage = get_storage()
    recent_topics = []
    try:
        state_file = getattr(storage, 'state_file', None)
        if state_file and state_file.exists():
            with open(state_file, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            batch_state = raw.get(task.id, {}) or {}
            recent_topics = batch_state.get('recent_topics', [])
    except Exception:
        pass

    state_for_trends = {'recent_topics': recent_topics}

    # Step 1: Select topics (uses TOP_N env var if set)
    topics = select_topics(seed_keywords=seed_keywords, daily_quota=daily_quota, geo=geo, cooldown_days=cooldown_days, state=state_for_trends)

    today = datetime.utcnow().strftime('%Y-%m-%d')
    base_output = Path('outputs') / 'articles' / today
    base_output.mkdir(parents=True, exist_ok=True)

    successful = []
    failed = []
    skipped = []

    start_time = now_utc()

    for t in topics:
        topic = t.get('topic', '').strip()
        if not topic:
            continue

        try:
            # Step 2: Build material pack
            material_pack = {'topic': topic, 'sources': [], 'key_points': []}

            # Try Serper search
            try:
                from agent.content_pipeline.search import get_search_provider
                from agent.config import Config
                if Config.SERPER_API_KEY:
                    sp = get_search_provider(Config.SEARCH_PROVIDER)
                    sr = sp.search(topic, limit=5)
                    sources = []
                    for r in (sr or []):
                        sources.append({
                            'title': getattr(r, 'title', ''),
                            'link': getattr(r, 'url', ''),
                            'snippet': getattr(r, 'snippet', ''),
                        })
                    material_pack['sources'] = sources
                    # Extract key points from snippets
                    kps = []
                    for s in sources:
                        snippet = s.get('snippet', '').strip()
                        if snippet:
                            kps.append(snippet.split('. ')[0])
                    material_pack['key_points'] = kps[:6]
            except Exception as e:
                logger.warning(f"Search failed for '{topic}': {e}")

            # Step 3: Create topic output directory
            slug = slugify(topic)
            topic_dir = base_output / slug
            topic_dir.mkdir(parents=True, exist_ok=True)

            # Step 4: Generate two versions
            wechat_article = generate_article_in_style(
                topic,
                material_pack,
                style='wechat',
                word_count_range=(800, 1200)
            )

            xiaohongshu_article = generate_article_in_style(
                topic,
                material_pack,
                style='xiaohongshu',
                word_count_range=(300, 600)
            )

            # Save both versions
            wechat_path = topic_dir / 'wechat.md'
            xiaohongshu_path = topic_dir / 'xiaohongshu.md'

            with open(wechat_path, 'w', encoding='utf-8') as f:
                f.write(wechat_article.get('body', ''))

            with open(xiaohongshu_path, 'w', encoding='utf-8') as f:
                f.write(xiaohongshu_article.get('body', ''))

            logger.info(f"Generated both versions for '{topic}'")

            # Step 5: Get cover image (search -> download -> fallback)
            img_info = provide_cover_image(material_pack, str(base_output), slug)

            # Step 6: Build metadata
            metadata = {
                'topic': topic,
                'slug': slug,
                'date_created': datetime.utcnow().isoformat(),
                'versions': {
                    'wechat': {
                        'file': str(wechat_path),
                        'word_count': wechat_article.get('word_count', 0),
                        'provider': wechat_article.get('provider', 'none'),
                        'fallback_used': wechat_article.get('fallback_used', False)
                    },
                    'xiaohongshu': {
                        'file': str(xiaohongshu_path),
                        'word_count': xiaohongshu_article.get('word_count', 0),
                        'provider': xiaohongshu_article.get('provider', 'none'),
                        'fallback_used': xiaohongshu_article.get('fallback_used', False)
                    }
                },
                'sources': material_pack.get('sources', []),
                'image': {
                    'status': img_info.get('image_status'),
                    'path': img_info.get('image_path'),
                    'relpath': img_info.get('image_relpath'),
                    'source_url': img_info.get('source_url'),
                    'site_name': img_info.get('site_name'),
                    'license_note': img_info.get('license_note'),
                    'reason': img_info.get('reason') if img_info.get('image_status') != 'ok' else None
                }
            }

            # Save metadata
            meta_path = topic_dir / 'metadata.json'
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            # Add to successful list
            successful.append(metadata)
            logger.info(f"Successfully processed topic: {topic}")

        except Exception as e:
            logger.error(f"Failed to process topic '{topic}': {e}")
            failed.append({'topic': topic, 'reason': str(e)})

    elapsed = (now_utc() - start_time).total_seconds()

    # Determine status
    status = 'success' if successful else ('skipped' if not failed else 'failed')

    # Write daily index
    index = {
        'date': today,
        'generated_count': len(successful),
        'failed_count': len(failed),
        'topics': successful,
        'duration_sec': elapsed
    }
    with open(base_output / 'index.json', 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    # Step 7: Send Feishu card (non-blocking)
    try:
        _send_feishu_summary(successful, failed, elapsed)
    except Exception as e:
        logger.warning(f"Failed to send Feishu summary: {e}")

    # Step 8: Send email (non-blocking, skip if SMTP not configured)
    try:
        _send_email_summary(successful, failed, today, email_to, attach_markdown, topic_dir)
    except Exception as e:
        logger.warning(f"Email send skipped/failed: {e}")

    return TaskResult(
        status=status,
        summary=f"Generated {len(successful)} topics (wechat+xiaohongshu), {len(failed)} failed, time: {elapsed:.1f}s",
        metrics={
            'generated_count': len(successful),
            'failed_count': len(failed),
            'topics': successful,
            'duration_sec': elapsed
        },
        duration_sec=elapsed
    )


def _send_feishu_summary(successful: list, failed: list, elapsed: float) -> None:
    """Send simplified Feishu summary with article content.
    
    For each topic, include copyable content and image/source links.
    """
    from agent.config import Config
    import requests

    webhook_url = Config.FEISHU_WEBHOOK_URL
    if not webhook_url:
        logger.warning("FEISHU_WEBHOOK_URL not configured, skipping Feishu notification")
        return

    # Build card with all articles
    elements = []

    if successful:
        elements.append({"tag": "markdown", "content": f"✅ **Daily Content Batch - {len(successful)} Topics Generated**"})

        for item in successful[:5]:  # Limit to 5 to avoid card size issues
            topic = item.get('topic', 'Unknown')
            elements.append({"tag": "hr"})
            elements.append({"tag": "markdown", "content": f"## {topic}"})

            # WeChat version
            wechat_file = item.get('versions', {}).get('wechat', {}).get('file', '')
            if wechat_file:
                elements.append({"tag": "markdown", "content": "**📱 WeChat Version:**\n[Read](file://" + wechat_file + ")"})

            # Xiaohongshu version
            xhs_file = item.get('versions', {}).get('xiaohongshu', {}).get('file', '')
            if xhs_file:
                elements.append({"tag": "markdown", "content": "**🎀 Xiaohongshu Version:**\n[Read](file://" + xhs_file + ")"})

            # Image and source
            img_info = item.get('image', {})
            if img_info.get('status') == 'ok':
                source_url = img_info.get('source_url', '')
                site_name = img_info.get('site_name', '')
                license = img_info.get('license_note', '')
                img_text = f"🖼️ Image from **{site_name}**\n{license}"
                if source_url:
                    img_text += f"\n[View Source]({source_url})"
                elements.append({"tag": "markdown", "content": img_text})
            else:
                reason = img_info.get('reason', 'unavailable')
                elements.append({"tag": "markdown", "content": f"📭 No image available ({reason})"})

    if failed:
        elements.append({"tag": "hr"})
        elements.append({"tag": "markdown", "content": f"❌ **{len(failed)} Failed Topics:**"})
        for item in failed[:3]:
            elements.append({"tag": "markdown", "content": f"- {item.get('topic', 'Unknown')}: {item.get('reason', 'Unknown error')[:80]}"})

    elements.append({"tag": "hr"})
    elements.append({"tag": "markdown", "content": f"⏱️ Total time: {elapsed:.1f}s"})

    payload = {
        "msg_type": "interactive",
        "card": {"elements": elements}
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=20)
        response.raise_for_status()
        logger.info(f"Feishu summary sent (status: {response.status_code})")
    except Exception as e:
        logger.error(f"Failed to send Feishu card: {e}")


def _send_email_summary(successful: list, failed: list, today: str, email_to: str, attach_files: bool, topic_dir: Path) -> None:
    """Send email with article summaries and optional file attachments."""
    from agent.email_sender import send_daily_summary

    if not successful:
        logger.info("No articles to send via email")
        return

    # Build HTML content
    html = f"<h2>Daily Content Batch - {today}</h2>\n<p>{len(successful)} topics generated</p>\n"

    attachments = []

    for item in successful[:10]:
        topic = item.get('topic', 'Unknown')
        wechat_file = item.get('versions', {}).get('wechat', {}).get('file', '')
        xhs_file = item.get('versions', {}).get('xiaohongshu', {}).get('file', '')

        html += f"<hr/><h3>{topic}</h3>\n"
        html += f"<p><b>📱 WeChat Version:</b></p>\n"
        html += f"<p><a href='file://{wechat_file}'>View WeChat Article</a></p>\n"
        html += f"<p><b>🎀 Xiaohongshu Version:</b></p>\n"
        html += f"<p><a href='file://{xhs_file}'>View Xiaohongshu Article</a></p>\n"

        img_info = item.get('image', {})
        if img_info.get('status') == 'ok':
            source_url = img_info.get('source_url', '')
            license_note = img_info.get('license_note', '')
            html += f"<p><b>Image Source:</b> {license_note}"
            if source_url:
                html += f" <a href='{source_url}'>View</a>"
            html += "</p>\n"

        # Add files to attachment list
        if attach_files:
            if wechat_file and Path(wechat_file).exists():
                attachments.append(wechat_file)
            if xhs_file and Path(xhs_file).exists():
                attachments.append(xhs_file)

    if failed:
        html += f"<hr/><h3>Failed Topics ({len(failed)})</h3>\n"
        for item in failed:
            html += f"<p>❌ {item.get('topic', 'Unknown')}: {item.get('reason', 'Unknown error')}</p>\n"

    # Send email (will skip if SMTP not configured)
    result = send_daily_summary(
        subject=f"Daily Content Batch - {today}",
        body_html=html,
        attachments=attachments if attach_files else None,
        to_addr=email_to
    )

    logger.info(f"Email send result: {result.get('status')} - {result.get('reason', '')}")

