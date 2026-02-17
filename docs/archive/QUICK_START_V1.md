# V1 Feature - Quick Start Guide (Windows)

## 🚀 Quickest Way to Test V1

### 1. Create & Activate Virtual Environment
```powershell
python -m venv venv
& "venv\Scripts\Activate.ps1"
```

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Run Tests (5 min)
```powershell
pytest tests/test_v1_features.py -v
```

### 4. Manual Test Run (5 min)
```powershell
$env:TOP_N = "2"
$env:LLM_PROVIDER = "dry_run"

python -m agent.task_runner
# OR directly:
python -c "
from agent.task_runner import run_daily_content_batch
from agent.models import Task
task = Task(id='daily_content_batch', params={'daily_quota': 2})
result = run_daily_content_batch(task)
print('Generated:', result.metrics.get('generated_count'))
"
```

### 5. Check Output Files
```powershell
# Should contain: wechat.md, xiaohongshu.md, images/, metadata.json
ls outputs/articles -Recurse -File
```

---

## 🎯 Feature Summary (30 seconds)

**A. Hot Topics (TOP_N)**
- Fetches trending topics; controllable via `TOP_N` env var
- Fallback to seed keywords if Trends not available
- Example: `$env:TOP_N = "5"` generates 5 topics

**B. Dual Versions**
- **WeChat** (wechat.md): 800-1200 words, structured
- **Xiaohongshu** (xiaohongshu.md): 300-600 words, casual
- Both saved to: `outputs/articles/YYYY-MM-DD/<topic>/`

**C. Images**
- Priority: Search Bing/Unsplash → Download → Placeholder PNG
- Includes: url, source_url, site_name, license_note
- File: `outputs/articles/YYYY-MM-DD/<topic>/images/<topic>.png`

**D. Feishu Card**
- Shows article versions (copyable content)
- Shows image with source attribution
- Includes execution summary

**E. Email (Optional)**
- Only sends if SMTP configured
- Supports multiple env var names (SMTP_USER/SMTP_USERNAME, etc.)
- Gracefully skips if missing

---

## 📁 Output Structure

```
outputs/articles/2026-02-14/
├── ai/
│   ├── wechat.md              # 800-1200 words
│   ├── xiaohongshu.md         # 300-600 words  
│   ├── metadata.json          # ← Includes style, word_count, provider
│   └── images/
│       └── ai.png             # Real image or placeholder
├── cloud-computing/
│   └── ...
└── index.json                 # Daily summary
```

---

## 🧪 Test Commands

```powershell
# All V1 tests
pytest tests/test_v1_features.py -v

# Specific test class
pytest tests/test_v1_features.py::TestTopicSelection -v
pytest tests/test_v1_features.py::TestDualVersionGeneration -v
pytest tests/test_v1_features.py::TestImageSearch -v
pytest tests/test_v1_features.py::TestEmailDelivery -v

# With coverage
pytest tests/test_v1_features.py --cov=agent --cov-report=term-missing
```

---

## 🔧 Environment Variables

| Var | Default | Purpose |
|-----|---------|---------|
| `TOP_N` | 3 | Number of topics to select |
| `WECHAT_WORDS_MIN` | 800 | Minimum WeChat article words |
| `WECHAT_WORDS_MAX` | 1200 | Maximum WeChat article words |
| `XHS_WORDS_MIN` | 300 | Minimum Xiaohongshu words |
| `XHS_WORDS_MAX` | 600 | Maximum Xiaohongshu words |
| `LLM_PROVIDER` | groq | groq / openai / dry_run |
| `IMAGE_SEARCH_PROVIDER` | bing | bing / google |
| `BING_SEARCH_SUBSCRIPTION_KEY` | *empty* | If set, uses Bing for images |
| `SMTP_HOST` | *empty* | SMTP server (enable email) |
| `SMTP_USER` | *empty* | SMTP username |
| `SMTP_PASS` | *empty* | SMTP password |
| `FEISHU_WEBHOOK_URL` | *empty* | Feishu webhook (enable Feishu) |

### Example: Full Test with All Features
```powershell
$env:TOP_N = "3"
$env:LLM_PROVIDER = "dry_run"          # Free mode
$env:FEISHU_WEBHOOK_URL = "https://..."  # Your webhook
$env:SMTP_HOST = "smtp.gmail.com"        # Email (optional)
$env:SMTP_USER = "your@gmail.com"
$env:SMTP_PASS = "your_app_password"
$env:BING_SEARCH_SUBSCRIPTION_KEY = "your_key"  # Image search (optional)

python -m agent.task_runner
```

---

## ✅ Verification Checklist

- [ ] `pytest tests/test_v1_features.py` passes (15+ tests green)
- [ ] `outputs/articles/YYYY-MM-DD/` directory created
- [ ] Each topic has: `wechat.md`, `xiaohongshu.md`, `metadata.json`
- [ ] `metadata.json` contains: style, word_count, provider, image info
- [ ] `.gitignore` correctly ignores outputs/ and state.json
- [ ] `git status` shows no unwanted changes

---

## 🐛 Troubleshooting

**Q: Tests fail with "import error"**
- → Check: `pip install -r requirements.txt` completed
- → Check: Virtual environment activated

**Q: "No outputs directory created"**
- → Likely error in run_daily_content_batch
- → Check: logs for actual error message
- → Verify seed_keywords not empty

**Q: "Image_provider.py not found"**
- → Ensure you're in agent-mvp root directory
- → Check: `ls agent/image_provider.py` exists

**Q: Email not sending**
- → Expected if SMTP env vars not set
- → Check logs: "SMTP not fully configured; skipping email send"
- → This is NOT an error; graceful skip

---

## 📝 Next Steps

1. **Local Test** (5 min): Run this Quick Start
2. **Verify Output** (2 min): Check outputs/articles/ structure
3. **All Tests** (5 min): `pytest tests/ -v`
4. **Commit** (2 min): `git add ...` → `git commit -m "feat(v1): ..."`
5. **Push to feature/v1-image-email**: `git push origin feature/v1-image-email`
6. **GitHub Actions** (5-10 min): Wait for CI to pass
7. **Create PR**: `feature/v1-image-email` → `main`

---

**Estimated Total Time:** 20-30 minutes  
**Status:** Ready to deploy 🚀
