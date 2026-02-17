"""Feishu (Lark) notification module via Incoming Webhook Bot."""

import os
import logging
import requests
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def _push_enabled() -> bool:
    return (os.getenv("FEISHU_PUSH_ENABLED", "0") or "0").strip().lower() in ("1", "true", "yes", "on")


def send_text(text: str) -> None:
    """Send a text message to Feishu using Incoming Webhook Bot.
    
    Args:
        text: The message text to send.
    
    Raises:
        ValueError: If FEISHU_WEBHOOK_URL environment variable is not set.
        requests.RequestException: If the HTTP request fails.
    """
    if not _push_enabled():
        logger.info("Feishu push disabled (set FEISHU_PUSH_ENABLED=1 to enable), skipping text message")
        return

    webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
    
    if not webhook_url:
        raise ValueError("FEISHU_WEBHOOK_URL environment variable not set")
    
    payload = {
        "msg_type": "text",
        "content": {
            "text": text
        }
    }
    
    # Set timeout to 20 seconds for robustness
    response = requests.post(webhook_url, json=payload, timeout=20)
    response.raise_for_status()
    
    logger.debug(f"Feishu text message sent (status: {response.status_code})")


def send_card(title: str, sections: List[Dict[str, Any]]) -> None:
    """Send an interactive card to Feishu.
    
    Args:
        title: Card title.
        sections: List of section dicts with content.
    
    Raises:
        ValueError: If FEISHU_WEBHOOK_URL is not set.
        requests.RequestException: If the HTTP request fails.
    """
    if not _push_enabled():
        logger.info("Feishu push disabled (set FEISHU_PUSH_ENABLED=1 to enable), skipping card")
        return

    webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
    
    if not webhook_url:
        raise ValueError("FEISHU_WEBHOOK_URL environment variable not set")
    
    # Build card payload
    payload = {
        "msg_type": "interactive",
        "card": {
            "elements": [
                {
                    "tag": "markdown",
                    "content": f"## {title}"
                }
            ]
        }
    }
    
    # Add sections as dividers and text
    for section in sections:
        if "title" in section:
            payload["card"]["elements"].append({
                "tag": "markdown",
                "content": f"**{section['title']}**"
            })
        
        if "content" in section:
            payload["card"]["elements"].append({
                "tag": "markdown",
                "content": section["content"]
            })
    
    response = requests.post(webhook_url, json=payload, timeout=20)
    response.raise_for_status()
    
    logger.debug(f"Feishu card sent (status: {response.status_code})")


def send_alert(task_id: str, title: str, error: str) -> None:
    """Send an alert card for a failed task.
    
    Args:
        task_id: ID of the failed task.
        title: Task title.
        error: Error message.
    
    Raises:
        ValueError: If FEISHU_WEBHOOK_URL is not set.
        requests.RequestException: If the HTTP request fails.
    """
    if not _push_enabled():
        logger.info("Feishu push disabled (set FEISHU_PUSH_ENABLED=1 to enable), skipping alert")
        return

    webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
    
    if not webhook_url:
        raise ValueError("FEISHU_WEBHOOK_URL environment variable not set")
    
    payload = {
        "msg_type": "interactive",
        "card": {
            "elements": [
                {
                    "tag": "markdown",
                    "content": f"❌ **Task Failed: {title}**"
                },
                {
                    "tag": "markdown",
                    "content": f"**Task ID:** {task_id}\n**Error:** {error[:500]}"
                }
            ]
        }
    }
    
    response = requests.post(webhook_url, json=payload, timeout=20)
    response.raise_for_status()
    
    logger.debug(f"Feishu alert sent (status: {response.status_code})")


def send_rich_card(
    executed_tasks: List[Dict[str, Any]],
    failed_tasks: List[Dict[str, Any]],
    duration_sec: float,
    all_success: bool,
    run_id: str
) -> None:
    """Send a rich Feishu card with consolidated task execution results.
    
    Args:
        executed_tasks: List of successful/skipped task results (dicts with id, title, summary, duration, metrics).
        failed_tasks: List of failed task results (dicts with id, title, error, duration).
        duration_sec: Total run duration in seconds.
        all_success: Whether all tasks succeeded.
        run_id: Unique run identifier.
    
    Raises:
        ValueError: If FEISHU_WEBHOOK_URL is not set.
        requests.RequestException: If the HTTP request fails.
    """
    if not _push_enabled():
        logger.info("Feishu push disabled (set FEISHU_PUSH_ENABLED=1 to enable), skipping rich card")
        return

    webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
    
    if not webhook_url:
        raise ValueError("FEISHU_WEBHOOK_URL environment variable not set")
    
    # Ensure lists are valid
    if executed_tasks is None:
        executed_tasks = []
    if failed_tasks is None:
        failed_tasks = []
    
    # Count skipped tasks
    skipped_tasks = [t for t in executed_tasks if t.get("summary", "").startswith("⊘")]
    successful_only = [t for t in executed_tasks if not t.get("summary", "").startswith("⊘")]
    
    # Determine status emoji and color
    status_emoji = "✅" if all_success else "⚠️"
    status_text = "🟢 All Pass" if all_success else "🔴 Some Issues"
    
    # Build card elements
    elements = []
    
    # Title
    elements.append({
        "tag": "markdown",
        "content": f"## {status_emoji} Agent Run Results"
    })
    
    # Summary section with proper counts
    summary_content = (
        f"**Status:** {status_text}\n"
        f"**Results:** {len(successful_only)} ✓ · {len(skipped_tasks)} ⊘ · {len(failed_tasks)} ✗\n"
        f"**Duration:** {duration_sec:.2f}s\n"
        f"**Run ID:** `{run_id}`"
    )
    elements.append({
        "tag": "markdown",
        "content": summary_content
    })
    
    # Successful tasks section (if any)
    if successful_only:
        success_header = f"**✅ Successful Tasks ({len(successful_only)})**"
        elements.append({
            "tag": "markdown",
            "content": success_header
        })
        
        for task in successful_only[:5]:  # Limit to 5 for readability
            task_summary = task.get("summary", "No summary") or "No summary"
            if len(task_summary) > 60:
                task_summary = task_summary[:57] + "..."
            
            task_content = (
                f"**{task.get('title', 'Unknown')}** ({task.get('duration', 0):.2f}s)\n"
                f"_{task_summary}_"
            )
            elements.append({
                "tag": "markdown",
                "content": task_content
            })
        
        if len(successful_only) > 5:
            elements.append({
                "tag": "markdown",
                "content": f"_... and {len(successful_only) - 5} more_"
            })
    
    # Skipped tasks section (if any) - show why they were skipped
    if skipped_tasks:
        skipped_header = f"**⊘ Skipped Tasks ({len(skipped_tasks)})**"
        elements.append({
            "tag": "markdown",
            "content": skipped_header
        })
        
        for task in skipped_tasks[:3]:
            task_summary = task.get("summary", "No reason") or "No reason"
            # Remove ⊘ prefix if present
            if task_summary.startswith("⊘ "):
                task_summary = task_summary[2:]
            if len(task_summary) > 80:
                task_summary = task_summary[:77] + "..."
            
            task_content = (
                f"**{task.get('title', 'Unknown')}**\n"
                f"_{task_summary}_"
            )
            elements.append({
                "tag": "markdown",
                "content": task_content
            })
        
        if len(skipped_tasks) > 3:
            elements.append({
                "tag": "markdown",
                "content": f"_... and {len(skipped_tasks) - 3} more_"
            })
    
    # Failed tasks section (if any) - with more detailed error messages
    if failed_tasks:
        failed_header = f"**❌ Failed Tasks ({len(failed_tasks)})**"
        elements.append({
            "tag": "markdown",
            "content": failed_header
        })
        
        for task in failed_tasks[:5]:  # Limit to 5 for readability
            error_msg = task.get("error", "Unknown error") or "Unknown error"
            if len(error_msg) > 80:
                error_msg = error_msg[:77] + "..."
            
            task_content = (
                f"**{task.get('title', 'Unknown')}**\n"
                f"_❌ {error_msg}_"
            )
            elements.append({
                "tag": "markdown",
                "content": task_content
            })
        
        if len(failed_tasks) > 5:
            elements.append({
                "tag": "markdown",
                "content": f"_... and {len(failed_tasks) - 5} more_"
            })
    
    # Build full payload
    payload = {
        "msg_type": "interactive",
        "card": {
            "elements": elements
        }
    }
    
    response = requests.post(webhook_url, json=payload, timeout=20)
    response.raise_for_status()
    
    logger.debug(f"Feishu rich card sent (status: {response.status_code})")


def send_alert_card(failed_tasks: List[Dict[str, Any]], run_id: str) -> None:
    """Send a dedicated alert card for failed tasks.
    
    Args:
        failed_tasks: List of failed task results (dicts with id, title, error).
        run_id: Unique run identifier for tracking.
    
    Raises:
        ValueError: If FEISHU_WEBHOOK_URL is not set.
        requests.RequestException: If the HTTP request fails.
    """
    if not failed_tasks:
        logger.debug("No failed tasks, skipping alert card")
        return
    
    if not _push_enabled():
        logger.info("Feishu push disabled (set FEISHU_PUSH_ENABLED=1 to enable), skipping alert card")
        return

    webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
    
    if not webhook_url:
        raise ValueError("FEISHU_WEBHOOK_URL environment variable not set")
    
    # Build alert elements
    elements = []
    
    # Alert header
    elements.append({
        "tag": "markdown",
        "content": f"## 🚨 Task Failures Alert"
    })
    
    elements.append({
        "tag": "markdown",
        "content": f"**Run ID:** `{run_id}`\n**Failed Count:** {len(failed_tasks)}"
    })
    
    # List each failed task with error
    for task in failed_tasks[:10]:  # Limit to 10 for readability
        error_msg = task.get("error", "Unknown error")
        if len(error_msg) > 80:
            error_msg = error_msg[:77] + "..."
        
        task_content = (
            f"**{task['title']}**\n"
            f"```\n{error_msg}\n```"
        )
        elements.append({
            "tag": "markdown",
            "content": task_content
        })
    
    if len(failed_tasks) > 10:
        elements.append({
            "tag": "markdown",
            "content": f"_... and {len(failed_tasks) - 10} more failures_"
        })
    
    # Build payload
    payload = {
        "msg_type": "interactive",
        "card": {
            "elements": elements
        }
    }
    
    response = requests.post(webhook_url, json=payload, timeout=20)
    response.raise_for_status()
    
    logger.debug(f"Feishu alert card sent (status: {response.status_code})")


def send_article_generation_results(
    successful_articles: List[Dict[str, Any]] = None,
    failed_articles: List[Dict[str, Any]] = None,
    skipped_articles: List[Dict[str, Any]] = None,
    total_time: float = 0,
    provider: str = "unknown",
    run_id: str = ""
) -> None:
    """Send article generation results card to Feishu.
    
    Args:
        successful_articles: List of successfully generated articles
        failed_articles: List of failed article generations
        skipped_articles: List of skipped keywords
        total_time: Total execution time in seconds
        provider: LLM provider used (groq, openai, dry_run, etc.)
        run_id: GitHub Actions run ID (optional)
    
    Note: Safely handles None values without crashing
    """
    # Safe defaults
    successful_articles = successful_articles or []
    failed_articles = failed_articles or []
    skipped_articles = skipped_articles or []
    total_time = total_time or 0
    provider = provider or "unknown"
    run_id = run_id or ""
    
    if not _push_enabled():
        logger.info("Feishu push disabled (set FEISHU_PUSH_ENABLED=1 to enable), skipping article results")
        return

    webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
    if not webhook_url:
        logger.info("FEISHU_WEBHOOK_URL not set - skipping Feishu notification")
        return
    
    # Build elements
    elements = []
    
    # Title with status
    if successful_articles and not failed_articles and not skipped_articles:
        status_emoji = "✅"
        title_status = "Success"
    elif skipped_articles and not successful_articles and not failed_articles:
        status_emoji = "⊘"
        title_status = "Skipped"
    elif successful_articles:
        status_emoji = "⚠️"
        title_status = "Partial Success"
    else:
        status_emoji = "❌"
        title_status = "Failed"
    
    title = f"{status_emoji} Article Generation Results"
    
    elements.append({
        "tag": "markdown",
        "content": f"# {title}"
    })
    
    # Summary
    summary_text = f"📊 **Summary**\n"
    summary_text += f"• ✅ Successful: {len(successful_articles) or 0}\n"
    summary_text += f"• ❌ Failed: {len(failed_articles) or 0}\n"
    summary_text += f"• ⊘ Skipped: {len(skipped_articles) or 0}\n"
    summary_text += f"• ⏱️ Time: {float(total_time):.1f}s\n"
    summary_text += f"• 🤖 Provider: {provider}\n"
    if run_id:
        summary_text += f"• 🔗 Run ID: `{run_id}`"
    
    elements.append({
        "tag": "markdown",
        "content": summary_text
    })
    
    # Successful articles
    if successful_articles:
        success_count = len(successful_articles) or 0
        elements.append({
            "tag": "markdown",
            "content": f"### ✅ Successful Articles ({success_count})"
        })
        
        for i, article in enumerate(successful_articles[:3]):  # Show max 3
            if not article:  # Skip None items
                continue
                
            title_text = article.get('title') or 'Untitled'
            keyword = article.get('keyword') or 'N/A'
            word_count = article.get('word_count') or 0
            sources_count = article.get('sources_count') or 0
            # Prefer inline content or a readable link over local file paths
            file_path = article.get('file_path') or 'N/A'
            read_content = article.get('body')
            article_text = f"**{title_text}**\n"
            article_text += f"📌 Keyword: `{keyword}`\n"
            article_text += f"📝 Words: {word_count}\n"
            article_text += f"📚 Sources: {sources_count}\n"
            if read_content:
                # Include a short preview and a Read section will show full body below
                preview = read_content[:1000]
                article_text += f"\n\n{preview}\n\n"
            else:
                article_text += f"\n\n📄 File: {file_path}\n"
            
            elements.append({
                "tag": "markdown",
                "content": article_text
            })
        
        if len(successful_articles) > 3:
            elements.append({
                "tag": "markdown",
                "content": f"_... and {len(successful_articles) - 3} more articles_"
            })
    
    # Skipped articles
    if skipped_articles:
        skipped_count = len(skipped_articles) or 0
        elements.append({
            "tag": "markdown",
            "content": f"### ⊘ Skipped Articles ({skipped_count})"
        })
        
        for i, skipped in enumerate(skipped_articles[:2]):  # Show max 2
            if not skipped:  # Skip None items
                continue
                
            keyword = skipped.get('keyword') or 'Unknown'
            reason = skipped.get('reason') or 'No reason provided'
            # Truncate reason to 200 chars
            if len(reason) > 200:
                reason = reason[:200] + "..."
            
            skipped_text = f"**{keyword}**\n"
            skipped_text += f"⊘ Reason: {reason}"
            
            elements.append({
                "tag": "markdown",
                "content": skipped_text
            })
        
        if len(skipped_articles) > 2:
            elements.append({
                "tag": "markdown",
                "content": f"_... and {len(skipped_articles) - 2} more skipped keywords_"
            })
    
    # Failed articles
    if failed_articles:
        failed_count = len(failed_articles) or 0
        elements.append({
            "tag": "markdown",
            "content": f"### ❌ Failed Articles ({failed_count})"
        })
        
        for i, failed in enumerate(failed_articles[:2]):  # Show max 2
            if not failed:  # Skip None items
                continue
                
            keyword = failed.get('keyword') or 'Unknown'
            reason = failed.get('reason') or failed.get('error') or 'Unknown error'
            # Truncate reason to 200 chars
            if len(reason) > 200:
                reason = reason[:200] + "..."
            
            failed_text = f"**{keyword}**\n"
            failed_text += f"❌ Error: {reason}"
            
            elements.append({
                "tag": "markdown",
                "content": failed_text
            })
        
        if len(failed_articles) > 2:
            elements.append({
                "tag": "markdown",
                "content": f"_... and {len(failed_articles) - 2} more failures_"
            })
    
    # Build payload
    payload = {
        "msg_type": "interactive",
        "card": {
            "elements": elements or []  # Safe empty list
        }
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=20)
        response.raise_for_status()
        logger.info(f"Feishu article results card sent: {len(successful_articles)} successful, {len(failed_articles)} failed, {len(skipped_articles)} skipped")
    except Exception as e:
        logger.error(f"Failed to send Feishu card: {e}", exc_info=True)
        # Don't raise - Feishu failure shouldn't crash the whole workflow
    # Additionally, if there are successful articles with full bodies, append first full article body as a separate message
    try:
        for art in successful_articles or []:
            body = art.get('body')
            if body:
                # Send a follow-up text with the full body (markdown) so users can read it in Feishu
                send_text(body)
                break
    except Exception:
        logger.debug('Failed to send full article body as follow-up')

