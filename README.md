# Agent MVP - Production-Grade Task Scheduler

A production-ready Python agent that runs tasks on a schedule (every minute to daily), executes them concurrently, and sends rich notifications to Feishu.

## What This Agent Does

1. **Schedules tasks** with flexible frequency (every_minute, hourly, daily, weekly)
2. **Executes concurrently** using ThreadPoolExecutor for efficiency
3. **Supports multiple task types** with configurable parameters
4. **Sends Feishu cards** with task results and failure alerts
5. **Persists state** in tasks.json or optional Feishu Bitable database
6. **Runs every 5 minutes** via GitHub Actions (minimum allowed granularity)
7. **Supports true "every minute"** via external cron calling GitHub API
8. **Provides detailed logging** for observability and debugging

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                           TRIGGERS                               │
├──────────────────────────────────────────────────────────────────┤
│ • GitHub Actions Cron (*/5 min)                                  │
│ • Manual dispatch (workflow_dispatch)                            │
│ • External cron (Vercel/Cloudflare) → GitHub API dispatch       │
└─────────────────────┬────────────────────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────────────┐
│              AGENT MAIN ORCHESTRATION                            │
├──────────────────────────────────────────────────────────────────┤
│ 1. Load tasks from storage (JSON or Bitable)                     │
│ 2. Filter eligible tasks (enabled + should_run)                  │
│ 3. Execute concurrently (ThreadPoolExecutor, max 4 workers)      │
│ 4. Collect results & update task status                          │
│ 5. Send failure alerts immediately                               │
│ 6. Save updated tasks to storage                                 │
│ 7. Send consolidated Feishu card                                 │
└─────────────────────┬────────────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
┌─────────────┐ ┌──────────┐ ┌──────────────┐
│ Task 1      │ │ Task 2   │ │ Task 3       │
│ (Briefing)  │ │ (Health) │ │ (RSS Watch)  │
└─────────────┘ └──────────┘ └──────────────┘
        │             │             │
        └─────────────┼─────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────────────┐
│        STORAGE & NOTIFICATIONS                                   │
├──────────────────────────────────────────────────────────────────┤
│ • Storage: tasks.json (local) or Feishu Bitable (if env vars)   │
│ • Notify: Feishu webhook bot (card format)                      │
└──────────────────────────────────────────────────────────────────┘
```

## Task Types

The agent includes three built-in task types. All support the common schema:

### Task Schema

```json
{
  "id": "task_id",
  "title": "Task Display Name",
  "enabled": true,
  "frequency": "every_minute",
  "timezone": "UTC",
  "params": { "custom": "parameters" },
  "status": "scheduled",
  "last_run_at": null,
  "next_run_at": null,
  "last_result_summary": null,
  "last_error": null
}
```

**Fields:**
- `id`: Unique task identifier (used to dispatch to task_runner)
- `title`: Human-readable name
- `enabled`: Whether task should run
- `frequency`: `every_minute` | `hourly` | `daily` | `weekly`
- `timezone`: IANA timezone (currently UTC only)
- `params`: Task-specific parameters (dict)
- `status`: Current status (scheduled | running | ok | failed)
- `last_run_at`: ISO 8601 timestamp of last execution
- `next_run_at`: ISO 8601 timestamp of next scheduled run
- `last_result_summary`: Result summary from last run (≤400 chars)
- `last_error`: Error message if last run failed (≤400 chars)

### Built-in Tasks

#### 1. `daily_briefing`
Generates a timestamped briefing. Useful for testing and periodic reports.

**Frequency:** every_minute, hourly, daily, etc.  
**Params:** (none)  
**Result:** Brief status message with timestamp

**Example tasks.json entry:**
```json
{
  "id": "daily_briefing",
  "title": "Daily Briefing",
  "enabled": true,
  "frequency": "every_minute",
  "timezone": "UTC",
  "params": {}
}
```

#### 2. `health_check_url`
Checks HTTP endpoint availability and response status.

**Frequency:** every_minute, hourly, daily, etc.  
**Params:**
- `url` (required): URL to check
- `timeout_sec` (default 10): HTTP request timeout
- `expected_status` (default 200): Expected HTTP status code

**Result:** Response time, actual status code, pass/fail

**Example tasks.json entry:**
```json
{
  "id": "health_check_url",
  "title": "Health Check - GitHub",
  "enabled": true,
  "frequency": "every_minute",
  "timezone": "UTC",
  "params": {
    "url": "https://github.com",
    "timeout_sec": 10,
    "expected_status": 200
  }
}
```

#### 3. `rss_watch`
Monitors an RSS feed for new items.

**Frequency:** hourly, daily, etc.  
**Params:**
- `feed_url` (required): URL to RSS feed
- `max_items` (default 3): Number of recent items to check
- `last_seen_guid` (auto-managed): GUID of last seen item

**Result:** Count of new items, feed title

**Example tasks.json entry:**
```json
{
  "id": "rss_watch",
  "title": "RSS Monitor",
  "enabled": true,
  "frequency": "hourly",
  "timezone": "UTC",
  "params": {
    "feed_url": "https://news.ycombinator.com/rss",
    "max_items": 3
  }
}
```

## Scheduling & Frequency

### Frequency Options

| Frequency | Minimum interval | Use case |
|-----------|------------------|----------|
| `every_minute` | 60 seconds | Real-time monitoring, polling |
| `hourly` | 1 hour | Regular checks |
| `daily` | 1 day | Daily reports, once-per-day jobs |
| `weekly` | 7 days | Weekly summaries |

### GitHub Actions Limits

**GitHub Actions minimum cron granularity is 5 minutes.** Therefore:

- **Agent runs every 5 minutes** via `cron: '*/5 * * * *'`
- **Each task checks its own frequency** (if last run was < 60 seconds ago for every_minute, it skips)
- **To achieve true every-minute triggering**, use external cron (see below)

## Running Locally

### 1. Clone & Setup

```bash
cd agent-mvp
python3.11 -m venv venv

# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Environment Variable

```bash
# macOS/Linux
export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook-id"

# Windows PowerShell
$env:FEISHU_WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook-id"

# Windows CMD
set FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook-id
```

### 4. Run the Agent

```bash
python -m agent.main
```

You should see:
```
Loading tasks from storage...
Loaded 3 tasks
Found 2 eligible tasks to run
Starting concurrent execution with 2 worker(s)
[daily_briefing] Starting task execution
[health_check_url] Starting task execution
[daily_briefing] Task completed: ok (0.02s)
[health_check_url] Task completed: ok (0.45s)
...
Agent run completed in 0.48s
✓ All systems operational
```

## GitHub Actions Setup

### 1. Add Secrets to Repository

1. Go to your GitHub repo → **Settings** → **Secrets and variables** → **Actions**
2. Add new secret:
   - **Name:** `FEISHU_WEBHOOK_URL`
   - **Value:** `https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook-id`

### 2. Trigger Agent Manually

1. Go to **Actions** tab
2. Select **"Agent MVP Workflow"** on the left
3. Click **"Run workflow"**
4. (Optional) Check "Persist state to repo" → Set to "yes" if you want tasks.json updated in repo
5. Click **"Run workflow"** again
6. Workflow should complete in ~10 seconds
7. Check your Feishu group for result card

### 3. View Logs

- Click the completed workflow run
- Click "run_agent" job
- Scroll to see detailed logs

## Achieving True "Every Minute" Triggering

GitHub Actions only supports **5-minute minimum** for scheduled workflows. To trigger the agent every minute:

### Option A: Vercel Cron (Recommended for ease)

Vercel offers free cron jobs that can call external URLs.

**Setup:**

1. Create `vercel.json` in your repo root (if not exists):
```json
{
  "crons": [
    {
      "path": "/api/trigger-agent",
      "schedule": "* * * * *"
    }
  ]
}
```

2. Create `api/trigger-agent.js` or `.py`:
```javascript
// api/trigger-agent.js
export default async (req, res) => {
  const token = process.env.GH_DISPATCH_TOKEN;
  const owner = "your-username";
  const repo = "agent-mvp";
  
  const response = await fetch(
    `https://api.github.com/repos/${owner}/${repo}/dispatches`,
    {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Accept": "application/vnd.github.v3+json"
      },
      body: JSON.stringify({
        "event_type": "agent-trigger"
      })
    }
  );
  
  return res.status(response.status).json({
    message: "Agent trigger dispatched"
  });
};
```

3. Create a GitHub PAT:
   - Go to GitHub → Settings → **Developer settings** → **Personal access tokens** → **Fine-grained tokens**
   - Click **"Generate new token"**
   - Name: `GH_DISPATCH_TOKEN`
   - Repository access: Select your `agent-mvp` repo
   - Permissions: Check `Contents: read` and `Actions: read & write`
   - Generate and copy token

4. Add to Vercel project:
   - Go to Vercel project Settings → **Environment Variables**
   - Add: `GH_DISPATCH_TOKEN = <your-token>`
   - Redeploy

5. Test:
```bash
curl https://your-vercel-app.vercel.app/api/trigger-agent
```

### Option B: Cloudflare Workers (Advanced)

Create a Cloudflare Worker with cron trigger:

```javascript
// wrangler.toml
[env.production]
triggers.crons = ["* * * * *"]

// src/index.js
export default {
  async scheduled(event, env, ctx) {
    const token = env.GH_DISPATCH_TOKEN;
    const owner = "your-username";
    const repo = "agent-mvp";
    
    await fetch(
      `https://api.github.com/repos/${owner}/${repo}/dispatches`,
      {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "User-Agent": "Cloudflare-Worker"
        },
        body: JSON.stringify({
          event_type: "agent-trigger"
        })
      }
    );
  }
};
```

Deploy: `wrangler deploy --env production`

### Option C: External Webhook Server

If you have a server with cron capabilities (cPanel, VPS, etc.):

```bash
# Cron job running every minute
* * * * * curl -X POST -H "Authorization: Bearer YOUR_GITHUB_PAT" \
  -H "Accept: application/vnd.github.v3+json" \
  -d '{"event_type":"agent-trigger"}' \
  https://api.github.com/repos/your-username/agent-mvp/dispatches
```

## Adding New Tasks

### 1. Define Task in tasks.json

```json
{
  "id": "my_new_task",
  "title": "My Custom Task",
  "enabled": true,
  "frequency": "daily",
  "timezone": "UTC",
  "params": {
    "param1": "value1"
  }
}
```

### 2. Implement Task Handler in agent/task_runner.py

```python
def run_my_new_task(task: Task) -> TaskResult:
    """Execute my custom task.
    
    Args:
        task: Task object with id, params, etc.
    
    Returns:
        TaskResult with status, summary, metrics, optional error.
    """
    params = task.params
    param1 = params.get("param1")
    
    try:
        # Do your work here
        result = f"Done with {param1}"
        
        return TaskResult(
            status="ok",
            summary=result,
            metrics={"custom_metric": 42}
        )
    except Exception as e:
        return TaskResult(
            status="failed",
            summary="Task failed",
            error=str(e)
        )
```

### 3. Register in run_task Dispatcher

In `agent/task_runner.py`, update `run_task()`:

```python
def run_task(task: Task) -> TaskResult:
    ...
    if task_id == "daily_briefing":
        result = run_daily_briefing(task)
    elif task_id == "health_check_url":
        result = run_health_check_url(task)
    elif task_id == "rss_watch":
        result = run_rss_watch(task)
    elif task_id == "my_new_task":
        result = run_my_new_task(task)  # ADD THIS
    else:
        raise ValueError(f"Unknown task ID: {task_id}")
    ...
```

### 4. Test Locally

```bash
export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/..."
python -m agent.main
```

## Storage Backends

### Default: JSON File Storage

**How it works:**
- Tasks stored in `tasks.json` in repo root
- Loaded on every run
- Atomic writes prevent corruption (write to temp file, then replace)
- No credentials needed

**Best for:** Small teams, simple setups, CI/CD friendly

### Optional: Feishu Bitable Storage

**How it works:**
- Tasks stored in a Feishu Bitable (multi-dimensional table)
- Avoids repo commits on every run
- Requires Feishu App credentials

**Setup:**

1. Create a Feishu App:
   - Go to [Feishu Developer Console](https://open.feishu.cn/app)
   - Create new app
   - Copy **App ID** and **App Secret**

2. Create a Bitable:
   - Go to Feishu desktop app
   - Create new Bitable
   - Add columns: id, title, enabled, frequency, timezone, params, status, last_run_at, next_run_at, last_result_summary, last_error

3. Grant API permissions to your app

4. Add GitHub Secrets:
   - `FEISHU_APP_ID`: Your app ID
   - `FEISHU_APP_SECRET`: Your app secret
   - `FEISHU_BITABLE_APP_TOKEN`: From Bitable sharing link
   - `FEISHU_BITABLE_TABLE_ID`: From Bitable dashboard

5. Agent will automatically detect and use Bitable

**Best for:** Large teams, avoid repo clutter, centralized task management

## Configuration Options

### Environment Variables

| Variable | Purpose | Default | Example |
|----------|---------|---------|---------|
| `FEISHU_WEBHOOK_URL` | Webhook for notifications | (required) | `https://open.feishu.cn/...` |
| `PERSIST_STATE` | Save tasks to repo | `none` | `repo` or `none` |
| `FEISHU_APP_ID` | Bitable app ID | (optional) | `cli_xxx` |
| `FEISHU_APP_SECRET` | Bitable app secret | (optional) | `xxx` |
| `FEISHU_BITABLE_APP_TOKEN` | Bitable token | (optional) | `xxx` |
| `FEISHU_BITABLE_TABLE_ID` | Bitable table ID | (optional) | `tblxxx` |

## Logging & Observability

The agent produces structured logs to stdout:

```
2026-02-13 07:25:00 [INFO] ============================================================
2026-02-13 07:25:00 [INFO] Agent run started
2026-02-13 07:25:00 [INFO] Loading tasks from storage...
2026-02-13 07:25:00 [INFO] Loaded 3 tasks
2026-02-13 07:25:00 [INFO] Found 2 eligible tasks to run
2026-02-13 07:25:00 [INFO] Starting concurrent execution with 2 worker(s)
2026-02-13 07:25:00 [INFO] [daily_briefing] Starting task execution
2026-02-13 07:25:00 [INFO] [health_check_url] Starting task execution
2026-02-13 07:25:00 [INFO] [daily_briefing] ✓ OK: Daily Briefing for 2026-02-13...
2026-02-13 07:25:00 [INFO] [health_check_url] ✓ OK: ✓ https://github.com returned 200 (0.48s)
2026-02-13 07:25:00 [INFO] Saving tasks to storage...
2026-02-13 07:25:00 [INFO] Saved 3 tasks
2026-02-13 07:25:00 [INFO] ============================================================
2026-02-13 07:25:00 [INFO] Agent run completed in 0.48s
2026-02-13 07:25:00 [INFO] ✓ All systems operational
```

### Artifact Logs

In GitHub Actions, logs are automatically uploaded as artifacts. Download from the workflow run summary.

## Exit Codes

- `0`: All tasks succeeded or skipped
- `1`: One or more tasks failed, or Feishu notification failed

## Troubleshooting

### Agent not running every minute locally

**Issue:** You're running locally but only see runs on 5-minute boundaries.  
**Reason:** You're probably using GitHub Actions cron. Local execution should run every time.  
**Solution:** Run `python -m agent.main` directly; it doesn't have the 5-minute limit.

### Feishu message not received

**Issues & fixes:**
1. **Webhook URL wrong**: Check `FEISHU_WEBHOOK_URL` is correct and still active
2. **Network timeout**: Webhook takes >20 seconds to respond
3. **Frequency too high**: If running every minute, you might miss some due to Feishu rate limits

### Task marked as "failed" but no error shown

**Check:** Look at `last_error` field in tasks.json or Feishu card. Usually a network/timeout issue.

### Bitable storage not being used

**Check:** Verify all 4 Bitable env vars are set in GitHub Secrets. Agent will log at startup if using Bitable.

## Development

### Project Structure

```
agent-mvp/
├── agent/
│   ├── __init__.py
│   ├── main.py             # Orchestration, concurrency
│   ├── task_runner.py      # Task implementations
│   ├── feishu.py           # Webhook notifications
│   ├── storage.py          # JSON & Bitable backends
│   ├── scheduler.py        # Frequency logic (should_run)
│   ├── models.py           # Task & TaskResult dataclasses
│   └── utils.py            # Helpers (retry, json, time)
├── .github/
│   └── workflows/
│       └── agent.yml       # GitHub Actions workflow
├── tasks.json              # Task definitions
├── requirements.txt        # Dependencies
└── README.md               # This file
```

### Running Tests Locally

```bash
python -c "
from agent.models import Task
from agent.scheduler import should_run
from agent.utils import now_utc

task = Task(id='test', title='Test', frequency='every_minute')
task.last_run_at = (now_utc() - __import__('datetime').timedelta(seconds=61)).isoformat()
print('Should run:', should_run(task))  # Should print True
"
```

## Performance Notes

- **Concurrency:** Max 4 workers (ThreadPoolExecutor), easily adjustable in main.py
- **Network:** Each webhook call has 20-second timeout
- **Storage:** JSON writes are atomic (temp file then replace)
- **Memory:** Minimal (all tasks kept in memory during run)

## License

Open source. Use as you wish.

---

## Quick Reference Checklist

- [ ] Set `FEISHU_WEBHOOK_URL` secret in GitHub
- [ ] Test locally: `export FEISHU_WEBHOOK_URL=...; python -m agent.main`
- [ ] Verify Feishu card received
- [ ] (Optional) Set `PERSIST_STATE=repo` if you want tasks.json committed
- [ ] (Optional) Set up external cron for true every-minute triggering
- [ ] Add new tasks to tasks.json and implement handlers in task_runner.py
- [ ] Monitor logs in GitHub Actions

---

**Ready to go!** The agent runs every 5 minutes via GitHub Actions, supports every-minute via external cron, and scales to dozens of concurrent tasks. 🚀
