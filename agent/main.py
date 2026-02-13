"""Main agent orchestration module."""

import sys
from datetime import datetime, timezone
from typing import Optional

from agent.storage import load_tasks, save_tasks
from agent.task_runner import run_task
from agent.telegram import send_message


def main() -> int:
    """Main agent orchestration logic.
    
    Returns:
        0 on success, 1 on failure.
    """
    try:
        # Load tasks
        print("Loading tasks...")
        tasks = load_tasks()
        
        # Filter pending tasks
        pending_tasks = [t for t in tasks if t.get("status") == "pending"]
        
        if not pending_tasks:
            print("No pending tasks found.")
            return 0
        
        print(f"Found {len(pending_tasks)} pending task(s).")
        
        # Process each pending task
        for task in pending_tasks:
            task_id = task.get("id")
            print(f"\nProcessing task: {task_id}")
            
            try:
                # Execute task
                result_summary = run_task(task)
                
                # Update task with success
                task["status"] = "done"
                task["last_run_at"] = datetime.now(timezone.utc).isoformat()
                task["result_summary"] = result_summary[:400]  # Truncate if needed
                
                print(f"Task completed: {task_id}")
                print(f"Result: {result_summary[:100]}...")
                
                # Send result to Telegram
                message = f"✅ Task '{task['title']}' completed\n\n{result_summary}"
                send_message(message)
                print("Notification sent to Telegram.")
                
            except Exception as e:
                # Update task with failure
                task["status"] = "failed"
                task["last_run_at"] = datetime.now(timezone.utc).isoformat()
                task["error"] = str(e)
                
                print(f"Task failed: {task_id}")
                print(f"Error: {e}")
                
                # Send failure alert to Telegram
                error_message = f"❌ Task '{task['title']}' failed\n\nError: {str(e)}"
                try:
                    send_message(error_message)
                except Exception as notify_exc:
                    print(f"Failed to send Telegram notification: {notify_exc}")
        
        # Save updated tasks
        print("\nSaving tasks...")
        save_tasks(tasks)
        print("Tasks saved successfully.")
        
        return 0
        
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        # Try to send alert
        try:
            send_message(f"🔴 Agent encountered a fatal error:\n{str(e)}")
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
