# V1 Product Feature - Acceptance Checklist

**Project:** agent-mvp  
**Branch:** feature/v1-image-email  
**Version:** 1.0  
**Date:** 2026-02-13

---

## ✅ Feature A: Hot Topic Selection (TOP_N)

- [ ] **A.1** Topics selection fetches at least 30 candidates from Google Trends RSS
- [ ] **A.2** Select Top N topics (default 3, controllable via `TOP_N` env var)
- [ ] **A.3** Store recent topics in state.json (not committed to git)
- [ ] **A.4** Respect cooldown_days: Skip topics generated in last N days
- [ ] **A.5** Graceful fallback: If trends fetch fails, use seed keywords
- [ ] **A.6** Last resort fallback: If seed keywords exhausted, allow recent repetition
- [ ] **Test:** `pytest tests/test_v1_features.py::TestTopicSelection -v`
- [ ] **Manual:** `python -c "from agent.trends import select_topics; topics = select_topics(['AI', 'Cloud'], 3); print(len(topics))"`

---

## ✅ Feature B: Dual Article Versions

- [ ] **B.1** Generate WeChat version: 800-1200 words, structured (title/intro/body/conclusion)
  - File: `outputs/articles/YYYY-MM-DD/<slug>/wechat.md`
- [ ] **B.2** Generate Xiaohongshu version: 300-600 words, casual tone (hook/points/suggestion)
  - File: `outputs/articles/YYYY-MM-DD/<slug>/xiaohongshu.md`
- [ ] **B.3** Both versions saved to separate files with metadata
- [ ] **B.4** Metadata contains: word_count, provider, fallback_used, version type
  - File: `outputs/articles/YYYY-MM-DD/<slug>/metadata.json`
- [ ] **B.5** LLM failure gracefully falls back to template (marked fallback_used=true)
- [ ] **B.6** Word count and style tracked in metadata
- [ ] **Test:** `pytest tests/test_v1_features.py::TestDualVersionGeneration -v`
- [ ] **Manual:** `python -c "from agent.article_generator import generate_article_in_style; a = generate_article_in_style('AI', {}, 'wechat'); print(len(a['body'].split()))"`

---

## ✅ Feature C: Image Search with Fallback

- [ ] **C.1** Try to search images using Bing Image Search API (if configured) or Unsplash
- [ ] **C.2** If real image found and downloadable, save as `images/<slug>.png` (binary)
- [ ] **C.3** Image metadata: url, source_url, site_name, license_note
- [ ] **C.4** If image search fails or no results, gracefully fallback to placeholder PNG
- [ ] **C.5** Placeholder PNG is base64-encoded or read from assets/placeholder.png
- [ ] **C.6** No images written to git; all in outputs/ (gitignored)
- [ ] **C.7** Image info included in metadata.json: status, path, source_url, license_note
- [ ] **Test:** `pytest tests/test_v1_features.py::TestImageSearch -v`
- [ ] **Manual:** `python -c "from agent.image_provider import image_search; images = image_search('Python', 1); print(len(images))"`

---

## ✅ Feature D: Feishu Card with Copyable Content

- [ ] **D.1** Feishu card includes article title and both versions (wechat + xiaohongshu)
- [ ] **D.2** Content is formatted as copyable Markdown blocks (not just file paths)
- [ ] **D.3** Image links clickable: [View Source](url) with site_name attribution
- [ ] **D.4** License note clearly shown: "Photo by X on Platform - License"
- [ ] **D.5** Summary: count of successful/failed/image status per topic
- [ ] **D.6** If image skipped, show reason: "no_sources", "search_failed", etc.
- [ ] **D.7** Card includes total execution time
- [ ] **Test:** Manual - configure FEISHU_WEBHOOK_URL and run daily_content_batch
- [ ] **Manual Check:**
  ```powershell
  $env:FEISHU_WEBHOOK_URL = "your_webhook_url"
  python -m agent.task_runner  # Run via workflow_dispatch
  ```

---

## ✅ Feature E: Email Delivery (Optional)

- [ ] **E.1** Email sends summarizing all topics (title, version links, image source)
- [ ] **E.2** Attachments: markdown files of both versions (if enabled)
- [ ] **E.3** If SMTP not configured (missing SMTP_HOST/USER/PASS), gracefully skip
- [ ] **E.4** Support multiple env var names: SMTP_USER or SMTP_USERNAME, SMTP_PASS or SMTP_PASSWORD
- [ ] **E.5** No exception thrown if email fails; logged as warning instead
- [ ] **E.6** Email result returned as {'status': 'sent'|'skipped', 'reason': optional}
- [ ] **Test:** `pytest tests/test_v1_features.py::TestEmailDelivery -v`
- [ ] **Manual:** Verify by checking logs: `Email send result: skipped - smtp_not_configured`

---

## ✅ CI/CD & Git Constraints

- [ ] **CI.1** .gitignore includes: state.json, outputs/, drafts/, publish_kits/
- [ ] **CI.2** GitHub Actions workflow does NOT commit/push state.json or outputs/
- [ ] **CI.3** Workflow uses `upload-artifact` v4 to store daily outputs
- [ ] **CI.4** `git status` after agent run shows: no unstaged changes (except maybe logs)
- [ ] **CI.5** Workflow exit code = 0 (success) even if SMTP/Feishu not configured
- [ ] **CI.6** Run task_runner.py --once works locally without git errors
- [ ] **Test:** 
  ```powershell
  git status  # Should show clean
  python -m agent.main --once 2>&1 | grep -i "error"  # Should be minimal
  ```

---

## ✅ Test Coverage Requirements

- [ ] **T.1** Unit tests for select_topics with TOP_N env var override
- [ ] **T.2** Unit tests for dual article generation (wechat + xiaohongshu)
- [ ] **T.3** Unit tests for image_search returning empty results gracefully
- [ ] **T.4** Unit tests for provide_cover_image writing placeholder without crash
- [ ] **T.5** Unit tests for email_sender skip when SMTP missing
- [ ] **T.6** Integration test: run_daily_content_batch produces correct file structure
- [ ] **T.7** All tests pass on Windows + Linux (GitHub Actions)
- [ ] **Run All Tests:**
  ```powershell
  pytest tests/test_v1_features.py -v --tb=short
  ```

---

## ✅ Local Verification Checklist (Windows PowerShell)

Execute on Windows PowerShell before submitting PR:

```powershell
# 1. Setup
python -m venv venv
& "venv\Scripts\Activate.ps1"
pip install -r requirements.txt

# 2. Run tests
pytest tests/test_v1_features.py -v

# 3. Manual run (dry_run mode, no real APIs)
$env:TOP_N = '2'
$env:LLM_PROVIDER = 'dry_run'
python -c "
from agent.task_runner import run_daily_content_batch
from agent.models import Task
task = Task(id='daily_content_batch', params={'daily_quota': 2, 'seed_keywords': ['AI']})
result = run_daily_content_batch(task)
print(f'✓ Status: {result.status}, Generated: {result.metrics.get(\"generated_count\")}')
"

# 4. Check outputs
ls outputs/articles/*/* -Recurse | Select-Object Name

# 5. Verify .gitignore
git status  # Should show no outputs/ or state.json changes
```

---

## ✅ Code Quality Requirements

- [ ] **Code.1** All new functions have docstrings with Args/Returns
- [ ] **Code.2** Error handling: All external API calls have try/except with graceful fallback
- [ ] **Code.3** Logging: All major steps logged with logger.info/warning/error
- [ ] **Code.4** No hardcoded paths; use Path() and relative paths
- [ ] **Code.5** Config all exposed via Config class (agent/config.py)
- [ ] **Code.6** Env var supported: TOP_N, WECHAT_WORDS_MIN/MAX, XHS_WORDS_MIN/MAX, IMAGE_SEARCH_PROVIDER, BING_SEARCH_SUBSCRIPTION_KEY
- [ ] **Check:** `grep -r "TODO\|FIXME\|XXX" agent/ | wc -l` → Should be 0

---

## ✅ Files Modified & Created

### Modified Files:
- [x] `agent/config.py` - Added TOP_N, WECHAT_WORDS_*, XHS_WORDS_*, IMAGE_SEARCH_PROVIDER, BING_SEARCH_SUBSCRIPTION_KEY
- [x] `agent/trends.py` - Added TOP_N env var support, improved fallback logic
- [x] `agent/article_generator.py` - Added generate_article_in_style() for dual versions
- [x] `agent/image_provider.py` - Added image_search(), download_image(), enhanced provide_cover_image()
- [x] `agent/email_sender.py` - Enhanced multi-env-var support, better error handling
- [x] `agent/task_runner.py` - Completely rewrote run_daily_content_batch() and added _send_feishu_summary(), _send_email_summary()

### New Files:
- [x] `tests/test_v1_features.py` - Comprehensive test suite for V1 features
- [x] `run_v1_test.ps1` - PowerShell script for local testing
- [x] `.github/workflows/agent.yml` - Already updated: no git commits of ignored files

### Unchanged:
- [x] `.gitignore` - Already correct (includes state.json, outputs/, etc.)
- [x] `requirements.txt` - All dependencies already present

---

## ✅ Commit Message Template

```
feat(v1): Complete article dual-version + image search + email/Feishu integration

- A. Hot topic selection: Support TOP_N env var, graceful Trends RSS fallback
- B. Dual versions: Generate WeChat (800-1200 words) + Xiaohongshu (300-600 words)
- C. Image search: Try Bing/Unsplash → download → fallback placeholder PNG
- D. Feishu: Copyable article content + image/source links + metadata
- E. Email: Optional, graceful SMTP skip, multi-env-var support
- Tests: 15+ unit/integration tests covering all features
- CI: No git commits of outputs/state.json (upload-artifact only)
- Verified on Windows PowerShell + GitHub Actions

Closes: #V1-DELIVERY
```

---

## ✅ Sign-Off Checklist

- [ ] **Developer:** All tests pass locally (pytest)
- [ ] **Developer:** Manual verification on Windows + 2 topics generated successfully
- [ ] **Developer:** `git status` shows no unwanted changes; only modified source files
- [ ] **Developer:** Code follows project style and docstring conventions
- [ ] **Code Review:** Features A-E all implemented and tested
- [ ] **Code Review:** No blocking issues in CI (GitHub Actions workflow succeeds)
- [ ] **Product:** All acceptance criteria in sections A-E met
- [ ] **Product:** File structure outputs/articles/YYYY-MM-DD/<slug>/{wechat.md, xiaohongshu.md, images/<slug>.png, metadata.json} correct
- [ ] **QA:** End-to-end test on staging branch successful
- [ ] **Ready to Merge:** feature/v1-image-email → main

---

**Target Completion Date:** 2026-02-14  
**Status:** Ready for PR Review
