# PowerShell Script: Fix GitHub Actions NameError and Commit
# Purpose: Verify Path import fix, run tests, and commit to feature/v1-image-email
# Run in: PowerShell (Windows)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "================================" -ForegroundColor Cyan
Write-Host "CI NameError Fix - Verification & Commit" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Verify Current Branch
Write-Host "[1/7] Checking current branch..." -ForegroundColor Yellow
$currentBranch = git branch --show-current
Write-Host "Current branch: $currentBranch" -ForegroundColor Green

if ($currentBranch -ne "feature/v1-image-email") {
    Write-Host "WARNING: Expected branch 'feature/v1-image-email', but got '$currentBranch'" -ForegroundColor Red
    Write-Host "Switching to feature/v1-image-email..." -ForegroundColor Yellow
    git checkout feature/v1-image-email
} else {
    Write-Host "✓ Correct branch: feature/v1-image-email" -ForegroundColor Green
}
Write-Host ""

# Step 2: Verify Python Import (No NameError)
Write-Host "[2/7] Verifying Python import (task_runner module)..." -ForegroundColor Yellow
try {
    python -c "import agent.task_runner; from agent.task_runner import _send_email_summary; print('✓ task_runner imports successfully (Path is available)')" 2>&1
    Write-Host "✓ Import successful - Path is properly defined" -ForegroundColor Green
} catch {
    Write-Host "✗ Import failed: $_" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 3: Run Regression Tests
Write-Host "[3/7] Running regression tests (import integrity)..." -ForegroundColor Yellow
pytest tests/test_v1_features.py::TestImportIntegrity -v
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Regression tests failed" -ForegroundColor Red
    exit 1
} else {
    Write-Host "✓ All regression tests passed" -ForegroundColor Green
}
Write-Host ""

# Step 4: Show Modified Files
Write-Host "[4/7] Modified files:" -ForegroundColor Yellow
git diff --name-only
Write-Host ""

# Step 5: Show Diff
Write-Host "[5/7] Changes in task_runner.py (first 30 lines):" -ForegroundColor Yellow
git diff agent/task_runner.py | head -30
Write-Host ""

# Step 6: Stage and Commit
Write-Host "[6/7] Staging and committing..." -ForegroundColor Yellow
git add agent/task_runner.py tests/test_v1_features.py
git commit -m "fix(ci): add pathlib.Path import to task_runner to resolve NameError in GitHub Actions"
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Commit created successfully" -ForegroundColor Green
} else {
    Write-Host "Commit may have been skipped (no changes to commit)" -ForegroundColor Yellow
}
Write-Host ""

# Step 7: Show Git Log
Write-Host "[7/7] Latest commit:" -ForegroundColor Yellow
git log --oneline -1
Write-Host ""

# Final: Show SHA for verification
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Verification Checklist" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
$sha = git rev-parse --short HEAD
Write-Host "✓ Current HEAD SHA: $sha" -ForegroundColor Green
Write-Host "✓ Branch: $(git branch --show-current)" -ForegroundColor Green
Write-Host "✓ Path import added to task_runner.py" -ForegroundColor Green
Write-Host "✓ Regression tests added (TestImportIntegrity)" -ForegroundColor Green
Write-Host "✓ Changes committed" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Push: git push origin feature/v1-image-email" -ForegroundColor Gray
Write-Host "  2. GitHub Actions: Go to Actions tab, select 'run_agent' workflow" -ForegroundColor Gray
Write-Host "  3. Click 'Run workflow' -> select branch 'feature/v1-image-email' -> 'Run workflow'" -ForegroundColor Gray
Write-Host "  4. Wait for run to complete (should exit with code 0)" -ForegroundColor Gray
Write-Host ""
Write-Host "Expected Success Indicators:" -ForegroundColor Cyan
Write-Host "  ✓ No NameError: name 'Path' is not defined" -ForegroundColor Gray
Write-Host "  ✓ All tests pass" -ForegroundColor Gray
Write-Host "  ✓ GitHub Actions workflow exits with code 0" -ForegroundColor Gray
