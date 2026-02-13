# Agent MVP

A minimal but real agent that runs on a schedule, executes tasks end-to-end, and notifies you via Telegram with results and logs.

## What This Agent Does

1. **Loads pending tasks** from `tasks.json`
2. **Executes tasks** (currently supports `daily_briefing`)
3. **Sends results** to Telegram via Bot API
4. **Updates task status** (pending → done or failed)
5. **Handles failures gracefully** with error alerts
6. **Runs on a schedule** via GitHub Actions (daily at 09:00 UTC) or manually

## Architecture

```
┌─────────────────────┐
│  Trigger            │
│  (Cron / Manual)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Agent Main         │
│  (Orchestration)    │
└──────────┬──────────┘
           │
           ├──► Load tasks.json
           │
           ├──► Filter pending tasks
           │
           ├──► Execute each task
           │    └──► Task Runner (dispatches by ID)
           │
           ├──► Send results to Telegram
           │    └──► Telegram (Bot API)
           │
           └──► Save tasks.json
```

## Prerequisites

- **Python 3.11+**
- **requests library** (for HTTP requests)
- **Telegram Bot**: Create one via [@BotFather](https://t.me/botfather) to get:
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_CHAT_ID` (your personal chat or group ID)

## Local Setup and Run

### 1. Clone or create the repository

```bash
git clone <repo-url>
cd agent-mvp
```

### 2. Create and activate virtual environment

**On macOS/Linux:**
```bash
python3.11 -m venv venv
source venv/bin/activate
```

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set environment variables

**On macOS/Linux:**
```bash
export TELEGRAM_BOT_TOKEN="your_bot_token_here"
export TELEGRAM_CHAT_ID="your_chat_id_here"
```

**On Windows (PowerShell):**
```powershell
$env:TELEGRAM_BOT_TOKEN = "your_bot_token_here"
$env:TELEGRAM_CHAT_ID = "your_chat_id_here"
```

**On Windows (Command Prompt):**
```cmd
set TELEGRAM_BOT_TOKEN=your_bot_token_here
set TELEGRAM_CHAT_ID=your_chat_id_here
```

### 5. Run the agent

```bash
python -m agent.main
```

You should see output like:
```
Loading tasks...
Found 1 pending task(s).

Processing task: daily_briefing
Task completed: daily_briefing
Result: Daily Briefing for 2026-02-13...
Notification sent to Telegram.

Saving tasks...
Tasks saved successfully.
```

And you should receive a Telegram message with the briefing result.

## GitHub Actions Setup

### 1. Add repository secrets

Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions** and add:

- **TELEGRAM_BOT_TOKEN**: Your bot token from @BotFather
- **TELEGRAM_CHAT_ID**: Your chat ID

### 2. Verify the workflow

The workflow file is at `.github/workflows/agent.yml` and will:
- Run automatically every day at 09:00 UTC
- Be triggerable manually via **Actions** tab (click **"Run workflow"**)

### 3. Manually run the workflow

1. Go to your GitHub repo → **Actions** tab
2. Select **"Agent MVP Workflow"** on the left
3. Click **"Run workflow"** → **"Run workflow"** again
4. Wait for it to complete
5. Check your Telegram for the result message
6. View logs in GitHub Actions if needed

### 4. Update schedule (timezone)

The schedule is set to **09:00 UTC** via:
```yaml
- cron: '0 9 * * *'
```

To change it:
- Edit `.github/workflows/agent.yml`
- Modify the cron value. Examples:
  - `0 8 * * *` = 08:00 UTC
  - `0 18 * * *` = 18:00 UTC
  - `0 9 * * 1` = Monday at 09:00 UTC
  - More info: [Cron syntax](https://crontab.guru/)
- Commit and push

## Tasks Configuration

### tasks.json Format

```json
[
  {
    "id": "daily_briefing",
    "title": "Generate daily briefing",
    "status": "pending"
  }
]
```

### Task Lifecycle

1. **pending** → Task waits for execution
2. **done** → Task completed successfully; fields added:
   - `last_run_at` (ISO 8601 timestamp)
   - `result_summary` (max 400 chars)
3. **failed** → Task failed; fields added:
   - `last_run_at`
   - `error` (error message)

After execution, tasks.json is automatically updated and committed back to the repo (if using GitHub Actions).

## Adding New Tasks

To add a new task, follow these steps:

### 1. Define the task in `tasks.json`

```json
{
  "id": "my_new_task",
  "title": "Do something cool",
  "status": "pending"
}
```

### 2. Implement the task in `agent/task_runner.py`

Add a function for your task:
```python
def run_my_new_task() -> str:
    """Execute my new task."""
    result = "Task result here"
    return result
```

Update the `run_task()` dispatcher:
```python
def run_task(task: Dict[str, Any]) -> str:
    task_id = task.get("id")
    
    if task_id == "daily_briefing":
        return run_daily_briefing()
    elif task_id == "my_new_task":
        return run_my_new_task()
    else:
        raise ValueError(f"Unknown task ID: {task_id}")
```

### 3. Test locally

```bash
python -m agent.main
```

### 4. Commit and push

```bash
git add tasks.json agent/task_runner.py
git commit -m "feat: add my_new_task"
git push
```

The agent will pick up the new task on the next execution.

## Logs and Debugging

### Local logs
- Run `python -m agent.main` and check console output.
- Check `tasks.json` for execution history (`last_run_at`, `result_summary`, `error`).

### GitHub Actions logs
1. Go to your repo → **Actions** tab
2. Select the workflow run
3. Click the job to view detailed logs

## Error Handling

The agent implements:
- ✅ **HTTP timeouts**: 20-second timeout on Telegram requests
- ✅ **HTTP error handling**: Raises exceptions on non-2xx responses
- ✅ **Task failure handling**: Marks failed tasks with error message
- ✅ **Telegram failure handling**: Attempts to send failure alert; doesn't crash if Telegram is down
- ✅ **Atomic file writes**: Uses temp files to prevent `tasks.json` corruption

## Files Overview

```
agent-mvp/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── tasks.json                         # Task definitions and execution history
├── agent/
│   ├── __init__.py                    # Package marker
│   ├── main.py                        # Orchestration logic
│   ├── task_runner.py                 # Task implementations
│   ├── telegram.py                    # Telegram Bot API integration
│   └── storage.py                     # File persistence (load/save tasks)
└── .github/
    └── workflows/
        └── agent.yml                  # GitHub Actions workflow
```

## Exit Codes

- `0`: Success (all tasks completed or no tasks pending)
- `1`: Fatal error (check logs and Telegram alert)

## Tips

- **Test Telegram token**: Run with a bogus token to verify your setup catches the error.
- **Add logging**: Extend `main.py` to log to a file for auditing.
- **Extend tasks**: New tasks go in `task_runner.py` and `tasks.json`.
- **Manual dispatch**: Use GitHub's "Run workflow" button for ad-hoc runs.

## License

Open source. Use as you wish.

---

**Ready to go!** Add your Telegram secrets, commit this repo, and trigger manually or wait for the daily cron run. 🚀
