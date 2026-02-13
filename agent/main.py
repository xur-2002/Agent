"""Main agent orchestration module with concurrency and scheduling."""

import sys
import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import List, Dict, Any

from agent.models import Task, TaskResult
from agent.storage import get_storage
from agent.task_runner import run_task
from agent.scheduler import should_run, compute_next_run
from agent.feishu import send_card, send_alert, send_text
from agent.utils import now_utc, now_iso, truncate_str

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> int:
    """Main agent orchestration logic.
    
    Returns:
        0 on success, 1 on any task failure or delivery failure.
    """
    logger.info("=" * 60)
    logger.info("Agent run started")
    
    run_start = now_utc()
    all_success = True
    executed_tasks: List[Dict[str, Any]] = []
    failed_tasks: List[Dict[str, Any]] = []
    
    try:
        # Load tasks
        logger.info("Loading tasks from storage...")
        storage = get_storage()
        tasks = storage.load_tasks()
        logger.info(f"Loaded {len(tasks)} tasks")
        
        # Filter eligible tasks
        eligible_tasks = [t for t in tasks if t.enabled and should_run(t)]
        logger.info(f"Found {len(eligible_tasks)} eligible tasks to run")
        
        if not eligible_tasks:
            logger.info("No tasks to run")
            return 0
        
        # Execute tasks concurrently
        max_workers = min(4, len(eligible_tasks))
        logger.info(f"Starting concurrent execution with {max_workers} worker(s)")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Start all tasks
            future_to_task = {
                executor.submit(run_task, task): task 
                for task in eligible_tasks
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                task_id = task.id
                
                try:
                    result = future.result()
                    
                    # Update task
                    task.status = result.status
                    task.last_run_at = now_iso()
                    task.next_run_at = compute_next_run(task, now_utc()).isoformat()
                    task.last_result_summary = truncate_str(result.summary, 400)
                    
                    if result.error:
                        task.last_error = truncate_str(result.error, 400)
                        all_success = False
                        failed_tasks.append({
                            "id": task_id,
                            "title": task.title,
                            "summary": task.last_result_summary,
                            "error": task.last_error,
                            "duration": result.duration_sec
                        })
                        
                        logger.error(f"[{task_id}] ✗ FAILED: {task.last_error}")
                        
                        # Send immediate alert
                        try:
                            send_alert(task_id, task.title, task.last_error)
                        except Exception as alert_exc:
                            logger.warning(f"[{task_id}] Failed to send alert: {alert_exc}")
                    else:
                        executed_tasks.append({
                            "id": task_id,
                            "title": task.title,
                            "summary": task.last_result_summary,
                            "duration": result.duration_sec,
                            "metrics": result.metrics
                        })
                        
                        logger.info(f"[{task_id}] ✓ OK: {task.last_result_summary}")
                
                except Exception as e:
                    all_success = False
                    error_msg = str(e)
                    logger.error(f"[{task_id}] Task crashed: {error_msg}")
                    
                    task.status = "failed"
                    task.last_run_at = now_iso()
                    task.last_error = truncate_str(error_msg, 400)
                    
                    failed_tasks.append({
                        "id": task_id,
                        "title": task.title,
                        "error": task.last_error
                    })
                    
                    try:
                        send_alert(task_id, task.title, error_msg)
                    except Exception as alert_exc:
                        logger.warning(f"[{task_id}] Failed to send alert: {alert_exc}")
        
        # Save updated tasks
        logger.info("Saving tasks to storage...")
        storage.save_tasks(tasks)
        logger.info(f"Saved {len(tasks)} tasks")
        
        # Send consolidated Feishu card
        run_duration = (now_utc() - run_start).total_seconds()
        
        try:
            send_consolidated_card(
                executed_tasks,
                failed_tasks,
                run_duration,
                all_success
            )
        except Exception as card_exc:
            logger.error(f"Failed to send Feishu card: {card_exc}")
            all_success = False
        
        logger.info("=" * 60)
        logger.info(f"Agent run completed in {run_duration:.2f}s")
        
        if all_success and not failed_tasks:
            logger.info("✓ All systems operational")
            return 0
        else:
            logger.error(f"✗ Run had failures: {len(failed_tasks)} task(s) failed")
            return 1
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        all_success = False
        
        # Try to send alert
        try:
            send_alert("agent", "Agent Fatal Error", str(e))
        except Exception as alert_exc:
            logger.warning(f"Failed to send fatal error alert: {alert_exc}")
        
        return 1


def send_consolidated_card(
    executed_tasks: List[Dict[str, Any]],
    failed_tasks: List[Dict[str, Any]],
    duration_sec: float,
    all_success: bool
) -> None:
    """Send a consolidated Feishu card with all task results.
    
    Args:
        executed_tasks: List of successful task results.
        failed_tasks: List of failed task results.
        duration_sec: Total run duration.
        all_success: Whether all tasks succeeded.
    """
    status_icon = "✅" if all_success else "⚠️"
    title = f"Agent Run {status_icon} {now_utc().strftime('%Y-%m-%d %H:%M UTC')}"
    
    sections = []
    
    # Summary section
    sections.append({
        "title": "Summary",
        "content": (
            f"• Successful: {len(executed_tasks)}\n"
            f"• Failed: {len(failed_tasks)}\n"
            f"• Duration: {duration_sec:.2f}s"
        )
    })
    
    # Successful tasks
    if executed_tasks:
        success_lines = []
        for task in executed_tasks:
            success_lines.append(
                f"✓ **{task['title']}** ({task.get('duration', 0):.2f}s)\n"
                f"  {task['summary'][:100]}"
            )
        sections.append({
            "title": "Successful Tasks",
            "content": "\n".join(success_lines)
        })
    
    # Failed tasks
    if failed_tasks:
        failed_lines = []
        for task in failed_tasks:
            error_preview = task.get('error', 'Unknown error')[:100]
            failed_lines.append(
                f"✗ **{task['title']}**\n"
                f"  {error_preview}"
            )
        sections.append({
            "title": "Failed Tasks",
            "content": "\n".join(failed_lines)
        })
    
    send_card(title, sections)


if __name__ == "__main__":
    sys.exit(main())
