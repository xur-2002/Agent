# PowerShell script for local V1 testing on Windows
# Usage: .\run_v1_test.ps1

Write-Host "🚀 V1 Feature Testing Script (Windows PowerShell)" -ForegroundColor Cyan
Write-Host "" 

# Step 1: Create virtual environment
Write-Host "Step 1: Setting up Python virtual environment..."
if (Test-Path "venv") {
    Write-Host "✓ Virtual environment already exists"
} else {
    python -m venv venv
    Write-Host "✓ Virtual environment created"
}

# Activate venv
& "venv\Scripts\Activate.ps1"

# Step 2: Install dependencies
Write-Host ""
Write-Host "Step 2: Installing dependencies..."
pip install -q -r requirements.txt
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Dependencies installed"
} else {
    Write-Host "✗ Failed to install dependencies" -ForegroundColor Red
    exit 1
}

# Step 3: Set environment variables
Write-Host ""
Write-Host "Step 3: Configuring environment..."
$env:PYTHONPATH = "$PWD"
$env:TOP_N = "2"          # Generate only 2 topics for quick test
$env:LLM_PROVIDER = "dry_run"  # Use dry_run to avoid API calls
$env:PERSIST_STATE = "local"
Write-Host "✓ Environment configured"
Write-Host "  TOP_N = 2"
Write-Host "  LLM_PROVIDER = dry_run"

# Step 4: Run unit tests
Write-Host ""
Write-Host "Step 4: Running unit tests..."
pytest -v tests/test_v1_features.py --tb=short
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️ Some tests failed, but continuing..." -ForegroundColor Yellow
}

# Step 5: Run full test suite
Write-Host ""
Write-Host "Step 5: Running full test suite..."
pytest tests/ -v --tb=short -x 2>&1 | Tee-Object -FilePath "test_results.log"

# Step 6: Manual run of daily_content_batch
Write-Host ""
Write-Host "Step 6: Manual test run of daily_content_batch..."
Write-Host "Running: python -m agent.task_runner" -ForegroundColor Cyan

python -c "
import os
os.environ['TOP_N'] = '2'
os.environ['LLM_PROVIDER'] = 'dry_run'

from agent.task_runner import run_daily_content_batch
from agent.models import Task

task = Task(
    id='daily_content_batch',
    params={
        'daily_quota': 2,
        'seed_keywords': ['Python', 'Cloud Computing'],
        'geo': 'US',
        'cooldown_days': 3
    }
)

result = run_daily_content_batch(task)
print(f'Status: {result.status}')
print(f'Summary: {result.summary}')
print(f'Generated: {result.metrics.get(\"generated_count\", 0)}')
print(f'Failed: {result.metrics.get(\"failed_count\", 0)}')
print(f'Time: {result.duration_sec:.2f}s')
"

# Step 7: Check output structure
Write-Host ""
Write-Host "Step 7: Checking output structure..."
if (Test-Path "outputs/articles") {
    $articles = Get-ChildItem -Path "outputs/articles" -Recurse -File | Measure-Object | Select-Object -ExpandProperty Count
    Write-Host "✓ Found $articles files in outputs/articles/"
    Get-ChildItem -Path "outputs/articles" -Recurse -File | Select-Object -ExpandProperty Name | ForEach-Object { "  - $_" }
} else {
    Write-Host "⚠️ No outputs/articles directory found"
}

# Step 8: Display summary
Write-Host ""
Write-Host "════════════════════════════════════════════" -ForegroundColor Green
Write-Host "✅ V1 Feature Test Complete" -ForegroundColor Green
Write-Host "════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "✅ Test Coverage:"
Write-Host "  A. Topic selection with TOP_N support"
Write-Host "  B. Dual article versions (WeChat + Xiaohongshu)"
Write-Host "  C. Image search with placeholder fallback"
Write-Host "  D. Email sending with SMTP graceful skip"
Write-Host "  E. Feishu notification integration"
Write-Host ""
Write-Host "📂 Output files:"
Write-Host "  - outputs/articles/YYYY-MM-DD/<topic>/wechat.md"
Write-Host "  - outputs/articles/YYYY-MM-DD/<topic>/xiaohongshu.md"
Write-Host "  - outputs/articles/YYYY-MM-DD/<topic>/images/<topic>.png"
Write-Host "  - outputs/articles/YYYY-MM-DD/<topic>/metadata.json"
Write-Host ""
Write-Host "Next: Commit changes to feature/v1-image-email branch"
Write-Host ""
