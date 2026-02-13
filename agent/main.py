"""Enhanced main agent orchestration with state management, retry logic, and rich Feishu cards."""

import sys
import os
import logging
import uuid
import subprocess
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional

from agent.config import Config
from agent.models import Task, TaskState, TaskResult
from agent.storage import get_storage
from agent.task_runner import run_task_with_retry, run_heartbeat
from agent.scheduler import should_run, compute_next_run
from agent.feishu import send_rich_card, send_alert_card, send_article_generation_results
from agent.utils import now_utc, now_iso, truncate_str

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> int:
    """Main agent orchestration with state management and retries.
    
    Returns:
        0 on success, 1 on any task failure.
    """
    logger.info("=" * 70)
    logger.info("AGENT RUN STARTED")
    logger.info("=" * 70)
    
    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    
    run_id = str(uuid.uuid4())[:8]
    run_start = now_utc()
    all_success = True
    attempted_tasks = []
    executed_tasks = []
    failed_tasks = []
    error_msg = None
    
    try:
        # Load task configuration and state
        logger.info("Loading task configuration and state...")
        storage = get_storage()
        tasks = storage.load_tasks()
        task_state = storage.load_state()
        
        logger.info(f"Loaded {len(tasks)} task configurations")
        logger.info(f"Loaded state for {len(task_state)} previous task runs")
        
        # Always include heartbeat task
        heartbeat_task = Task(
            id="heartbeat",
            title="Heartbeat",
            enabled=True,
            frequency="every_minute"
        )
        
        # Filter eligible tasks (including heartbeat)
        eligible_tasks = []
        
        # Add heartbeat
        eligible_tasks.append(heartbeat_task)
        
        # Add other tasks that are due
        for task in tasks:
            if should_run(task, task_state.get(task.id)):
                eligible_tasks.append(task)
        
        logger.info(f"Found {len(eligible_tasks)} eligible tasks to run")
        
        if len(eligible_tasks) == 1:  # Only heartbeat
            logger.info("No user tasks due, running heartbeat only")
        
        # Execute tasks concurrently  
        max_workers = min(Config.MAX_CONCURRENCY, len(eligible_tasks))
        logger.info(f"Concurrent execution: {max_workers}worker(s), max_concurrency={Config.MAX_CONCURRENCY}")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {
                executor.submit(
                    run_task_with_retry,
                    task,
                    Config.RETRY_COUNT,
                    Config.get_retry_backoff_list()
                ): task
                for task in eligible_tasks
            }
            
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                task_id = task.id
                attempted_tasks.append(task_id)
                
                try:
                    result: TaskResult = future.result()
                    
                    # Update state  
                    state = task_state.get(task_id) or TaskState(task_id=task_id)
                    state.status = result.status
                    state.last_run_at = now_iso()
                    state.next_run_at = compute_next_run(task, now_utc()).isoformat()
                    state.last_result_summary = truncate_str(result.summary, 500)
                    state.last_error = truncate_str(result.error or "", 500) if result.error else None
                    state.attempts = state.attempts + 1
                    state.last_attempt_at = now_iso()
                    state.run_id = run_id
                    
                    task_state[task_id] = state
                    
                    # Record result
                    if result.status == "success":
                        executed_tasks.append({
                            "id": task_id,
                            "title": task.title,
                            "summary": result.summary,
                            "duration": result.duration_sec,
                            "metrics": result.metrics
                        })
                        logger.info(f"✓ [{task_id}] SUCCESS ({result.duration_sec:.2f}s)")
                        
                        # Send article generation results to Feishu if this is article_generate task
                        if task_id == "article_generate" and not Config.DRY_RUN:
                            try:
                                data = result.data or {}
                                successful_articles = data.get("successful_articles", [])
                                failed_articles = data.get("failed_articles", [])
                                dry_run = data.get("dry_run", False)
                                
                                logger.info(f"Sending article generation results to Feishu: {len(successful_articles)} successful, {len(failed_articles)} failed")
                                send_article_generation_results(
                                    successful_articles=successful_articles,
                                    failed_articles=failed_articles,
                                    total_time=result.duration_sec,
                                    run_id=run_id,
                                    dry_run=dry_run
                                )
                            except Exception as e:
                                logger.warning(f"Failed to send article generation results to Feishu: {e}")
                    else:
                        all_success = False
                        failed_tasks.append({
                            "id": task_id,
                            "title": task.title,
                            "summary": result.summary,
                            "error": result.error,
                            "duration": result.duration_sec
                        })
                        logger.error(f"✗ [{task_id}] FAILED: {result.error}")
                
                except Exception as e:
                    all_success = False
                    error_str = str(e)
                    logger.error(f"✗ [{task_id}] CRASHED: {error_str}")
                    
                    state = task_state.get(task_id) or TaskState(task_id=task_id)
                    state.status = "failed"
                    state.last_run_at = now_iso()
                    state.last_error = truncate_str(error_str, 500)
                    task_state[task_id] = state
                    
                    failed_tasks.append({
                        "id": task_id,
                        "title": task.title,
                        "error": error_str
                    })
        
        # Save state
        logger.info("Saving task state...")
        if not Config.DRY_RUN:
            storage.save_state(task_state)
        else:
            logger.info("[DRY RUN] Skipped state save")
        
        # Send consolidated Feishu card
        run_duration = (now_utc() - run_start).total_seconds()
        logger.info(f"Agent run completed in {run_duration:.2f}s")
        
        try:
            logger.info("Sending Feishu card...")
            if not Config.DRY_RUN:
                send_rich_card(
                    executed_tasks,
                    failed_tasks,
                    run_duration,
                    all_success,
                    run_id
                )
                if failed_tasks:
                    send_alert_card(failed_tasks, run_id)
            else:
                logger.info("[DRY RUN] Skipped Feishu notification")
        except Exception as e:
            logger.error(f"Failed to send Feishu card: {e}")
            error_msg = str(e)
            all_success = False
        
        # Try to persist state to repo if requested
        if Config.PERSIST_STATE == "repo":
            try:
                logger.info("Persisting state to repository...")
                subprocess.run([
                    "git",
                    "config",
                    "--local",
                    "user.email",
                    "agent@github.com"
                ], check=True)
                subprocess.run([
                    "git",
                    "config",
                    "--local",
                    "user.name",
                    "Agent Workflow"
                ], check=True)
                subprocess.run(["git", "add", Config.STATE_FILE], check=True)
                subprocess.run([
                    "git",
                    "commit",
                    "-m",
                    f"chore: update agent state (run_id={run_id})"
                ], check=False)  # Don't fail if nothing to commit
                subprocess.run(["git", "push"], check=True)
                logger.info("State persisted to repository")
            except Exception as e:
                logger.warning(f"Failed to persist state to repo: {e}")
        
        logger.info("=" * 70)
        logger.info(f"RESULTS: {len(executed_tasks)} succeeded, {len(failed_tasks)} failed")
        logger.info("=" * 70)
        
        return 0 if all_success else 1
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        error_msg = str(e)
        
        try:
            if not Config.DRY_RUN:
                send_alert_card([{
                    "id": "agent",
                    "title": "Agent Error",
                    "error": error_msg
                }], "fatal")
        except Exception as alert_e:
            logger.warning(f"Couldnot send alert: {alert_e}")
        
        return 1


if __name__ == "__main__":
    sys.exit(main())

