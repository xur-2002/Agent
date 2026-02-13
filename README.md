# Agent MVP - Autonomous Task Automation for Content & Monitoring

A **production-ready Python agent** that automatically runs monitoring and content generation tasks every minute, executes them concurrently, and sends real-time updates to Feishu via rich interactive cards.

**Core Mission:** Zero-cost article generation + multi-source monitoring + real-time notifications = fully autonomous content production pipeline.

---

## 🎯 What You Get (In 30 Seconds)

### 1. Add GitHub Secrets

Go to repo **Settings → Secrets and variables → Actions**, add these:

| Secret Name | Value | Required |
|---|---|---|
| `FEISHU_WEBHOOK_URL` | Your Feishu webhook URL | ✅ Yes |
| `GROQ_API_KEY` | Free LLM API key from https://console.groq.com | (if using article_generate) |
| `SERPER_API_KEY` | Search enhancement (optional) | ❌ No |
| `OPENAI_API_KEY` | Fallback LLM provider (optional) | ❌ No |

### 2. Trigger Manually (or wait for automatic run)

- **Manual:** Go to **Actions → Agent MVP Workflow → Run workflow**
- **Automatic:** Workflow runs **every minute** via GitHub Actions cron (`* * * * *`)

### 3. View Results

- **Feishu:** Check your Feishu group for the result card
- **Articles:** Generated articles appear in `outputs/articles/YYYY-MM-DD/*.md` and `*.json`
- **Logs:** View in GitHub Actions workflow run details

---

## What This Agent Does

1. **Schedules tasks** with flexible frequency (every_minute, hourly, daily, weekly)
2. **Executes concurrently** using ThreadPoolExecutor for efficiency
3. **Supports 9+ task types** with configurable parameters
4. **Sends Feishu cards** with task results and failure alerts
5. **Persists state** in `state.json` (local) or optional Feishu Bitable database
6. **Runs every minute** via GitHub Actions cron (`* * * * *`)
7. **Supports external triggers** via GitHub API dispatch (workflow_dispatch, repository_dispatch)
8. **Generates articles** with Groq LLM (free) or OpenAI (paid), saves to `outputs/articles/`
9. **Provides detailed logging** for observability and debugging

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                           TRIGGERS                               │
├──────────────────────────────────────────────────────────────────┤
│ • GitHub Actions Cron (every minute: * * * * *)                 │
│ • Manual dispatch (workflow_dispatch from Actions tab)          │
│ • External cron (Vercel/Cloudflare) → GitHub API dispatch       │
└─────────────────────┬────────────────────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────────────┐
│              AGENT MAIN ORCHESTRATION                            │
├──────────────────────────────────────────────────────────────────┤
│ 1. Load tasks from storage (state.json or optional Bitable)      │
│ 2. Filter eligible tasks (enabled + should_run)                  │
│ 3. Execute concurrently (ThreadPoolExecutor, max 5 workers)      │
│ 4. Collect results & update task status                          │
│ 5. Send failure alerts immediately                               │
│ 6. Save updated tasks to storage                                 │
│ 7. Send consolidated Feishu card                                 │
│ 8. Commit generated articles to repo (if any)                    │
└─────────────────────┬────────────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────────────────┐
        │             │                         │
        ▼             ▼                         ▼
┌─────────────┐ ┌──────────────┐ ┌──────────────────┐
│ Health      │ │ RSS Watch    │ │ Article Gen      │
│ Check       │ │ / Trending   │ │ (Groq/OpenAI)    │
└─────────────┘ └──────────────┘ │ → outputs/...    │
        │             │         │ (auto-commit)    │
        └─────────────┼─────────┘ └──────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────────────┐
│        STORAGE & NOTIFICATIONS                                   │
├──────────────────────────────────────────────────────────────────┤
│ • Storage: state.json (local) + optional Feishu Bitable         │
│ • Outputs: outputs/articles/YYYY-MM-DD/*.md + *.json            │
│ • Notify: Feishu webhook bot (card format)                      │
│ • VCS: Auto-commit to main branch if enabled                     │
└──────────────────────────────────────────────────────────────────┘
```

## Task Types

The agent supports 9+ built-in task types. All support the common task schema below:

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
- `frequency`: `every_minute` | `hourly` | `daily` | `weekly` | `once_per_day` | `every_5_min`
- `timezone`: IANA timezone (currently UTC only)
- `params`: Task-specific parameters (dict)
- `status`: Current status (scheduled | running | ok | failed)
- `last_run_at`: ISO 8601 timestamp of last execution
- `next_run_at`: ISO 8601 timestamp of next scheduled run
- `last_result_summary`: Result summary from last run (≤400 chars)
- `last_error`: Error message if last run failed (≤400 chars)

### Built-in Tasks

#### 1. `heartbeat`
System heartbeat (auto-run every minute, no configuration needed).

**Result:** Heartbeat timestamp

---

#### 2. `daily_briefing`
Generates a timestamped briefing.

**Frequency:** every_minute, hourly, daily, etc.  
**Params:** (none)  
**Result:** Timestamped briefing message

---

#### 3. `health_check_url`
Checks HTTP endpoint availability.

**Params:**
- `url` (required): URL to check
- `timeout_sec` (default 10): HTTP timeout
- `expected_status` (default 200): Expected HTTP status

**Result:** Response time, status, pass/fail

---

#### 4. `rss_watch`
Monitors an RSS feed for new items.

**Params:**
- `feed_url` (required): URL to RSS feed
- `max_items` (default 3): Number of items to check
- `last_seen_guid` (auto-managed): GUID of last seen item

**Result:** Count of new items, feed title

---

#### 5. `github_trending_watch`
Monitors trending repositories on GitHub by language.

**Params:**
- `language` (default python): GitHub language filter
- `since` (default daily): daily | weekly | monthly

**Result:** Top 5 trending repos with star growth

---

#### 6. `github_repo_watch`
Watches a specific GitHub repository for releases and activity.

**Params:**
- `owner` (required): GitHub username
- `repo` (required): Repository name
- `watch_type` (default releases): releases | commits | discussions

**Result:** Latest release/activity info

---

#### 7. `keyword_trend_watch`
Monitors keyword trends using search API (Serper).

**Params:**
- `keywords` (required): Array of keywords to watch
- `region` (default zh-CN): Region/language code
- `search_provider` (default serper): serper | google

**Result:** Search volume and trend change

---

#### 8. `article_generate`
Generates articles using LLM (Groq/OpenAI) based on keywords.

**Frequency:** every_minute, hourly, daily, etc.  
**Params:**
- `keywords` (required): Array of keywords to write about
- `language` (default zh-CN): Output language (zh-CN | en-US)

**Flow for each keyword:**
1. **Search** (optional): If SERPER_API_KEY is set, search for keyword context
2. **Generate**: Call LLM API with search results + prompt (Groq/OpenAI/DRY_RUN)
3. **Save**: Write both `.md` (content) and `.json` (metadata) to `outputs/articles/YYYY-MM-DD/`
4. **Notify**: Send Feishu card with article title, word count, provider, model

**Error Handling** (6 exception types):
- `MissingAPIKeyError` (non-retriable): No API key configured → **skip** remaining keywords
- `InsufficientQuotaError` (non-retriable): Billing/quota issue → **skip** remaining keywords
- `RateLimitError` (retriable): API throttled → **fail** this keyword, **continue** with others
- `TransientError` (retriable): Network timeout → **fail** this keyword, **continue** with others
- `LLMProviderError` (retriable/non-retriable flag): Generic provider error
- Generic `Exception`: **fail** this keyword, **continue** with others

**Task Status Logic:**
- ✅ `success`: At least 1 keyword generated successfully
- ⊘ `skipped`: All keywords skipped (due to missing key/quota)
- ❌ `failed`: Some keywords failed (can be retried in next run)

**Result:** 
- Generated articles in `outputs/articles/YYYY-MM-DD/` with metadata
- Feishu card with: successful ✅ + failed ❌ + skipped ⊘ breakdown
- Auto-commit articles to repo (if enabled via PERSIST_STATE=repo)

**Environment:**
- `LLM_PROVIDER`: groq (free, default) | openai (paid) | dry_run (mock)
- `GROQ_API_KEY`: Get from https://console.groq.com (free, no credit card)
- `GROQ_MODEL`: llama-3.1-8b-instant (default)
- `OPENAI_API_KEY`: Optional fallback (requires paid plan)
- `OPENAI_MODEL`: gpt-4o-mini (default)
- `SERPER_API_KEY`: For search enrichment (optional)

---

#### 9. `publish_kit_build`
Builds publish kits for content distribution platforms.

**Params:**
- `hour` (default 18): Hour to run (UTC)
- `platforms` (optional): Target platforms list

**Result:** Generate publish kits for WeChat, Xiaohongshu, etc.

## Scheduling & Frequency

### Frequency Options

| Frequency | Interval | Typical Use |
|-----------|----------|-------------|
| `every_minute` | 60 seconds | Real-time monitoring, polling |
| `every_5_min` | 5 minutes | Frequent checks with less overhead |
| `hourly` | 1 hour | Regular checks, feeds, trends |
| `once_per_day` | 1 day at specified hour | Daily reports, article generation |
| `daily` | 1 day | Daily task execution |
| `weekly` | 7 days | Weekly summaries |

### GitHub Actions Cron

The workflow runs on **GitHub Actions cron schedule: `* * * * *`** (every minute).

- **Actual run interval:** Every minute (GitHub now supports this with standard runners)
- **Agent behavior:** Each run checks task frequency and skips if not due
- **Example:** A task with `frequency: "daily"` will only execute when `should_run()` returns true

### State Persistence

State is persisted to **`state.json`** in the repository root:
- **Format:** JSON with task execution history and metadata
- **Auto-updated:** After each agent run
- **Manual persistence:** Set `PERSIST_STATE=repo` in workflow to commit state.json to repo

### Optional: True "Every Minute" via External Cron

If you use the built-in GitHub Actions cron (`* * * * *`), you're already getting every-minute triggering. 

For even more frequent triggering or outside GitHub infrastructure, you can use external cron:
- **Vercel Cron** (recommended for ease)
- **Cloudflare Workers** (advanced)
- **Your own server** with cron job

See [Achieving True "Every Minute" Triggering](#achieving-true-every-minute-triggering) section below.

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

### Step 1: Add Required Secrets

Go to your GitHub repo → **Settings** → **Secrets and variables** → **Actions**

Add these secrets:

| Secret Name | Details | Required |
|---|---|---|
| `FEISHU_WEBHOOK_URL` | Your Feishu bot webhook URL | ✅ Required |
| `GROQ_API_KEY` | Free LLM API from https://console.groq.com | For article_generate task |
| `OPENAI_API_KEY` | OpenAI API key (fallback LLM) | Optional |
| `SERPER_API_KEY` | Search enrichment API | Optional |

**Note:** All other env vars (LLM_PROVIDER, etc.) have sensible defaults and can be set as **Variables** if you want to change them per environment.

### Step 2: Verify the Workflow

The workflow file is `.github/workflows/agent.yml`:
- **Name:** Agent MVP Workflow
- **Triggers:** 
  - Cron: `* * * * *` (every minute)
  - Manual: `workflow_dispatch` (run from Actions tab)
  - GitHub API: `repository_dispatch` (external HTTP triggers)

### Step 3: Manual Trigger (First Test)

1. Go to your repo → **Actions** tab
2. Select **"Agent MVP Workflow"** on the left
3. Click **"Run workflow"** button
4. Click **"Run workflow"** again to confirm
5. Wait ~30-60 seconds for completion
6. Check your Feishu group for the result card

### Step 4: Automatic Runs

Once configured, the workflow runs automatically every minute. Check:
- **GitHub Actions logs:** Actions tab → latest run
- **Feishu cards:** Should arrive in your workspace every minute (or per task frequency)
- **Generated articles:** If `article_generate` is enabled, check `outputs/articles/YYYY-MM-DD/` in the repo

### Step 5: View Generated Content

Generated articles from the `article_generate` task are saved to:

```
outputs/
  articles/
    2026-02-13/
      article-title.md       # Markdown content
      article-title.json     # Metadata (title, keywords, word_count, etc.)
```

Files are automatically committed to the repo if git operations succeed.

---

## Achieving Sub-Minute Triggering (Optional)

The built-in GitHub Actions cron supports **every minute triggering** (`* * * * *`). If you need **more frequent execution** (e.g., every 30 seconds), use external cron services:

### Option A: Vercel Cron (Recommended for ease)

Vercel offers free cron jobs that can call external URLs.

**Setup:**

1. Create `vercel.json` in your repo root (if not exists):
```json
{
  "crons": [
    {
      "path": "/api/trigger-agent",
      "schedule": "*/1 * * * *"
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
triggers.crons = ["*/1 * * * *"]

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

The agent uses a two-file approach:

1. **`tasks.json`** - Task definitions (static, rarely changes)
   - Loaded on each run
   - Contains task configuration, parameters, frequency, etc.
   - Edit manually to add/remove tasks

2. **`state.json`** - Task execution state (dynamic, auto-updated)
   - Saved after each run
   - Contains last_run_at, next_run_at, status, last_error, etc.
   - Tracks task execution history
   - Optional: commit to repo via `PERSIST_STATE=repo`

**Best for:** Small teams, simple setups, CI/CD friendly, no additional credentials

### Optional: Feishu Bitable Storage

Instead of (or in addition to) JSON files, tasks can be stored in a Feishu Bitable (multi-dimensional table):

**Advantages:**
- Centralized task management
- Web UI for editing
- No repo clutter from frequent state commits
- Shared access across team

**Setup:**

1. Create a Feishu App (if not exists)
2. Create a Bitable with columns: id, title, enabled, frequency, timezone, params, status, last_run_at, etc.
3. Add GitHub Secrets for app credentials
4. Agent auto-detects and uses Bitable if env vars are set

**Best for:** Large teams, avoid repo clutter, centralized management

**Note:** Currently using local JSON storage. Bitable support available via optional env vars.

## Configuration Options

### Environment Variables (from .env.example)

| Variable | Purpose | Default | Example | Required |
|----------|---------|---------|---------|----------|
| `FEISHU_WEBHOOK_URL` | Feishu bot webhook | (none) | `https://open.feishu.cn/...` | ✅ Yes |
| `FEISHU_MENTION` | User ID to mention on failures | (none) | `ou_xxx` | ❌ No |
| `LLM_PROVIDER` | Which LLM to use | groq | groq \| openai \| dry_run | For article_generate |
| `GROQ_API_KEY` | Groq API key (free) | (none) | `gsk_...` | For groq provider |
| `GROQ_MODEL` | Groq model to use | llama-3.1-8b-instant | llama-3.1-8b-instant | Auto |
| `OPENAI_API_KEY` | OpenAI API key (paid) | (none) | `sk_...` | For openai provider |
| `OPENAI_MODEL` | OpenAI model to use | gpt-4o-mini | gpt-4o-mini | Auto |
| `SERPER_API_KEY` | Search enrichment API | (none) | `xxx` | For keyword searches |
| `PERSIST_STATE` | Save state to repo | local | local \| repo \| bitable | Auto |
| `STATE_FILE` | Where to save state | state.json | state.json | Auto |
| `MAX_CONCURRENCY` | Max concurrent tasks | 5 | 1-10 | Auto |
| `RETRY_BACKOFF` | Retry backoff times | 1s,3s,7s | Comma-separated delays | Auto |

### LLM Provider Setup (for article_generate task)

**Option A: Use free Groq (recommended)**
1. Go to https://console.groq.com
2. Sign up (free, no credit card needed)
3. Create API key
4. Add `GROQ_API_KEY` to GitHub Secrets

**Option B: Use paid OpenAI (optional fallback)**
1. Go to https://platform.openai.com
2. Add payment method
3. Create API key
4. Add `OPENAI_API_KEY` to GitHub Secrets
5. (Optional) Set `LLM_PROVIDER=openai` in GitHub Variables

**Fallback behavior:** If LLM_PROVIDER is groq but GROQ_API_KEY is missing, automatically tries openai (if available), then dry_run (mock).

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

Open source. No LICENSE file currently. Use as you wish. Consider adding a LICENSE file (MIT, Apache 2.0, etc.) if publishing.

---

## Changelog (README only)

**Changes made to align with actual repo behavior:**
- ✅ Added Quick Start section (3 steps) at top
- ✅ Fixed cron schedule: `* * * * *` (every minute), not `*/5` (every 5 min)
- ✅ Expanded task list from 3 to 9 types (added heartbeat, github_trending_watch, github_repo_watch, keyword_trend_watch, article_generate, publish_kit_build)
- ✅ Documented article generation output path: `outputs/articles/YYYY-MM-DD/*.md + *.json`
- ✅ Clarified state persistence: uses `state.json` + `tasks.json`, not just `tasks.json`
- ✅ Updated env variables table with actual LLM_PROVIDER, GROQ_API_KEY, OPENAI_API_KEY, SERPER_API_KEY from workflow and .env.example
- ✅ Documented Groq free LLM provider setup (new feature)
- ✅ Removed "5-minute minimum" claim (GitHub now supports 1-minute cron)
- ✅ Updated architecture diagram to show article generation pipeline and outputs commit
