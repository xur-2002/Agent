# ========================================
# GitHub Actions NameError 修复
# 完整 PowerShell 命令序列
# ========================================

# 前置条件：
#   - 已在 VS Code 中修改 agent/task_runner.py（添加了 from pathlib import Path）
#   - 已在 VS Code 中修改 tests/test_v1_features.py（添加了 TestImportIntegrity）
#   - 当前目录：agent-mvp（sln root）
#   - PowerShell 版本：5.0 或更高（Windows 10+）

# ========================================
# Step 1: 验证 Python 导入（无 NameError）
# ========================================

cd 'c:\Users\徐大帅\Desktop\新建文件夹\agent-mvp'

# 测试 task_runner 导入
python -c "import agent.task_runner; from agent.task_runner import _send_email_summary; print('✓ Import OK: Path is available')"

# 如果显示 "✓ Import OK: Path is available"，说明修复成功
# 如果显示 NameError: name 'Path' is not defined，说明修复未生效


# ========================================
# Step 2: 运行回归测试（确保导入测试通过）
# ========================================

# 确保 venv 已安装依赖
python -m venv venv
& "venv\Scripts\Activate.ps1"
pip install -r requirements.txt

# 运行新增的导入完整性测试
pytest tests/test_v1_features.py::TestImportIntegrity -v

# 预期结果：
#   PASSED tests/test_v1_features.py::TestImportIntegrity::test_task_runner_imports_without_errors
#   PASSED tests/test_v1_features.py::TestImportIntegrity::test_all_v1_modules_import


# ========================================
# Step 3: 运行全部 V1 测试
# ========================================

pytest tests/test_v1_features.py -v

# 预期结果：所有 15+ 个测试都应该通过（PASSED）


# ========================================
# Step 4: 查看修改的文件
# ========================================

git diff agent/task_runner.py

# 你应该看到：
#   +from pathlib import Path

git diff tests/test_v1_features.py | head -50

# 你应该看到：
#   +class TestImportIntegrity:
#   +    """Test: Verify all modules import without NameError..."""


# ========================================
# Step 5: 检查当前分支
# ========================================

git branch --show-current

# 预期输出：feature/v1-image-email


# ========================================
# Step 6: 提交修改
# ========================================

git add agent/task_runner.py tests/test_v1_features.py

git commit -m "fix(ci): add pathlib.Path import to task_runner to resolve NameError in GitHub Actions

- Added 'from pathlib import Path' to agent/task_runner.py imports
- Added TestImportIntegrity regression test to ensure no import-time NameError
- Verified all V1 feature modules import successfully"

# 预期输出：
#   [feature/v1-image-email xxx] fix(ci): add pathlib.Path import...
#   2 files changed, X insertions(+), Y deletions(-)


# ========================================
# Step 7: 查看最新提交
# ========================================

git log --oneline -1

# 预期输出：
#   <short-sha> fix(ci): add pathlib.Path import to task_runner to resolve NameError in GitHub Actions

# 获取完整 SHA
$sha = git rev-parse HEAD
Write-Host "Full SHA: $sha"


# ========================================
# Step 8: 推送到远端
# ========================================

git push origin feature/v1-image-email

# 预期：no error，remote 应该接到新 commit


# ========================================
# 验证清单
# ========================================

$branch = git rev-parse --abbrev-ref HEAD
$sha = git rev-parse --short HEAD
Write-Host "✓ Current branch: $branch" -ForegroundColor Green
Write-Host "✓ Current SHA: $sha" -ForegroundColor Green

# 验证文件内容
$hasPathImport = Select-String -Path "agent/task_runner.py" -Pattern "from pathlib import Path" | Measure-Object | Select-Object -ExpandProperty Count
Write-Host "✓ Path import present: $hasPathImport times" -ForegroundColor Green

$hasTestImportIntegrity = Select-String -Path "tests/test_v1_features.py" -Pattern "class TestImportIntegrity" | Measure-Object | Select-Object -ExpandProperty Count
Write-Host "✓ TestImportIntegrity class present: $hasTestImportIntegrity times" -ForegroundColor Green

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "✓ 本地修复完成！" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "接下来在 GitHub Actions 验证：" -ForegroundColor Yellow
Write-Host "  1. 访问 https://github.com/<your>/Agent/actions" -ForegroundColor Gray
Write-Host "  2. 选择 'run_agent' workflow" -ForegroundColor Gray
Write-Host "  3. 点击 'Run workflow' -ForegroundColor Gray
Write-Host "  4. 选择分支：feature/v1-image-email" -ForegroundColor Gray
Write-Host "  5. 点击 'Run workflow' 按钮" -ForegroundColor Gray
Write-Host ""
Write-Host "预期 GitHub Actions 结果：" -ForegroundColor Cyan
Write-Host "  ✓ 无 NameError: name 'Path' is not defined" -ForegroundColor Gray
Write-Host "  ✓ 所有测试通过（至少 15 个测试）" -ForegroundColor Gray
Write-Host "  ✓ Workflow 完成，exit code 0（成功）" -ForegroundColor Gray
