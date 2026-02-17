# ⚡ QUICK_VERIFY.md - 5分钟验证指南

## 概述
本指南帮助您在 5 分钟内验证 Article Generation 任务在 GitHub Actions 中的完整端到端运行。

---

## 前置条件

✅ 确保已在 GitHub 仓库中配置 3 个 Secrets:
- **Settings** → **Secrets and variables** → **Actions**
- [ ] `FEISHU_WEBHOOK_URL` ← 必需（用于飞书通知）
- [ ] `OPENAI_API_KEY` ← 必需（用于文章生成）  
  - 从 https://platform.openai.com/api-keys 获取
  - 格式: `sk-proj-xxxxx`
- [ ] `SERPER_API_KEY` ← 可选（用于谷歌搜索）
  - 从 https://serper.dev 获取
  - 如果缺失，程序会使用通用知识模式生成文章

> 注：如果只有 FEISHU_WEBHOOK_URL，文章任务会被标记为 skipped 并继续执行。

---

## 第1步：启用 DRY_RUN 模式（本地快速测试，0 成本）

### 方式 A：本地环境变量

```bash
# Linux / macOS
export DRY_RUN=1
export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/xxxxx"
python -m agent.main

# Windows (PowerShell)
$env:DRY_RUN="1"
$env:FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/xxxxx"
python -m agent.main
```

**预期输出** (日志中会出现):
```
[2026-02-13 10:30:45] [INFO] [article_generate] Starting with 5 keyword(s), DRY_RUN=1
[2026-02-13 10:30:46] [INFO] [article_generate] Processing keyword: artificial intelligence
[DRY_RUN] Generating mock article for keyword: artificial intelligence
[2026-02-13 10:30:47] [INFO] [article_generate] Successfully generated: Understanding AI (850 words)
[2026-02-13 10:30:48] [INFO] article_generator: Saving article to outputs/articles/2026-02-13/understanding-ai.md
```

**检查文件生成**:
```bash
ls -la outputs/articles/2026-02-13/
# 应该看到:
# understanding-ai.md
# understanding-ai.json
```

---

## 第2步：在 GitHub Actions 中运行（完整流程）

### 方式 B：GitHub UI 中手动运行

1. **打开 Actions 页面**
   - 进入您的仓库
   - 点击顶部的 **Actions** 标签页

2. **选择 Workflow**
   - 左侧菜单找到 "Agent MVP Workflow"
   - 点击进入

3. **手动触发运行**
   - 点击 **"Run workflow"** 按钮
   - 选择 branch: **main**
   - （可选）Enable debugging: `persist_state` = `no`（默认）
   - 点击 **"Run workflow"** 按钮

4. **等待完成** (~30-60 秒)
   - 页面会显示正在运行的 job
   - 看到 ✅ 或 ❌ 表示完成

### 预期结果（✅ SUCCESS）

1. **日志中看到安全的环境变量检查**
   ```
   🔍 Checking environment variables...
   SERPER_API_KEY set? True/False
   OPENAI_API_KEY set? True
   FEISHU_WEBHOOK_URL set? True
   ```

2. **看到 article_generate 任务运行日志**
   ```
   [article_generate] Starting with 5 keyword(s), DRY_RUN=0, SERPER=available
   [article_generate] Processing keyword: artificial intelligence
   [article_generate] Successfully generated: Understanding AI (845 words)
   ...
   [2026-02-13 10:30:45] Agent run completed in 24.5s
   ```

3. **在飞书中收到通知卡片**
   ```
   ✅ Agent Run Results
   Status: 🟢 All Pass
   Tasks: 5 ✓ · 0 ✗
   Duration: 24.5s
   Run ID: a1b2c3d4

   ### ✅ Successful Tasks (5)
   **Article Generation - Cheap Mode** (5.2s)
   • Article title 1 (850 words)
   • Article title 2 (823 words)
   ...
   ```

4. **在仓库中找到生成的文件**
   ```
   outputs/articles/2026-02-13/
   ├── understanding-artificial-intelligence.md
   ├── understanding-artificial-intelligence.json
   ├── cloud-computing-trends.md
   ├── cloud-computing-trends.json
   └── ...
   ```
   - 点击 `.md` 文件可以在 GitHub 中预览文章内容
   - `.json` 文件包含元数据 (title, word_count, sources 等)

---

## 第3步：验证不同场景

### 场景 A：所有 keys 都已配置（最好的情况）

**操作**: 运行 workflow（如上步骤 2）

**预期结果**:
- ✅ SERPER_API_KEY set? **True**
- ✅ OPENAI_API_KEY set? **True**
- ✅ 文章基于搜索结果生成（高质量）
- ✅ 飞书卡片显示 5 篇成功的文章
- ✅ outputs/articles/ 中有 10 个文件（5 篇 × 2 个格式）

**成本**: ~$0.005 (5篇文章，每篇成本 ~$0.001)

---

### 场景 B：缺少 SERPER_API_KEY（有 OpenAI）

**操作**:
1. 进入仓库 Settings → Secrets and variables → Actions
2. 删除 `SERPER_API_KEY` secret 或将其值设为空
3. 运行 workflow

**预期结果**:
- ✅ SERPER_API_KEY set? **False**
- ✅ OPENAI_API_KEY set? **True**
- ⚠️ 文章仍然生成（基于通用知识，没有搜索上下文）
- ✅ 飞书卡片显示成功（会标注"无搜索模式"）
- ✅ outputs/articles/ 中有新文件

**成本**: ~$0.004/篇 （文章会短一点）

**日志中会看到**:
```
SERPER_API_KEY set? False
[article_generate] No search provider available - generating article with context-only mode for 'artificial intelligence'
```

---

### 场景 C：缺少 OPENAI_API_KEY（仅有 Feishu）

**操作**:
1. 删除 `OPENAI_API_KEY` secret 或将其值设为空
2. 运行 workflow

**预期结果**:
- ✅ OPENAI_API_KEY set? **False**
- ⊘ article_generate 任务被 **SKIPPED**（不是失败）
- ✅ 其他任务（heartbeat, health_check 等）继续正常运行
- ✅ 飞书卡片会显示「Skipped: OPENAI_API_KEY missing」
- ✅ **Workflow 最终状态: SUCCESS** ✅（不会失败）

**成本**: $0.00

**日志中会看到**:
```
OPENAI_API_KEY set? False
[article_generate] OPENAI_API_KEY not set - task skipped
⊘ [article_generate] SKIPPED: OPENAI_API_KEY missing
```

---

## 故障排除

### 问题 1：Feishu 卡片无法收到

**可能原因**:
- FEISHU_WEBHOOK_URL secret 不存在或值错误

**解决方案**:
1. 检查 secret 是否真的存在：Settings → Secrets and variables → Actions
2. 确认 webhook URL 是完整的，以 `https://open.feishu.cn/open-apis/bot/v2/hook/` 开头
3. 如果 secret 刚添加，可能需要等待几秒钟才能生效
4. 再次运行 workflow

### 问题 2：文件没有出现在 outputs/articles/

**原因分析**:
- 检查日志中 article_generate 是否真的返回了 status="success"
- 可能是 OPENAI_API_KEY 缺失，任务被 skipped

**解决方案**:
1. 检查 Actions 日志中是否有 "Article generation skipped" 消息
2. 确认 OPENAI_API_KEY 已配置
3. 如果在本地 DRY_RUN 模式下可以生成文件，但 GitHub Actions 中生不了，说明 API key 有问题

### 问题 3：看到日志 "SERPER_API_KEY not set" 但希望有搜索结果

**解决方案**:
1. 进入 Settings → Secrets and variables → Actions
2. 添加 SERPER_API_KEY secret，值从 https://serper.dev 获取
3. 再次运行 workflow
4. 文章质量会提升（因为有搜索上下文）

### 问题 4：Workflow 显示 FAILED（红色 ❌）

**可能原因**:
- 缺少必需的 secrets（FEISHU_WEBHOOK_URL 最起码需要）
- Python 依赖没有正确安装

**解决方案**:
1. 检查所有 secrets 都已配置（至少有 FEISHU_WEBHOOK_URL）
2. 检查 workflow 日志中最后的错误消息
3. 如果是 "FEISHU_WEBHOOK_URL environment variable not set"，添加这个 secret
4. 点击 "Re-run failed jobs" 重新运行

---

## 常见问题

**Q: DRY_RUN 模式和真实模式的区别是什么？**

| 方面 | DRY_RUN=1 | 真实模式 |
|------|-----------|---------|
| 调用 OpenAI | ❌ 否 | ✅ 是 |
| 调用 Serper 搜索 | ❌ 否 | ✅ 是（如有 key） |
| 生成文件 | ✅ 是（模拟内容） | ✅ 是（真实内容） |
| 成本 | $0.00 | ~$0.001/篇 |
| 用途 | 本地快速测试 | 真实文章生成 |

**Q: 如果同时缺 SERPER 和 OPENAI 会怎样？**

文章生成任务会被跳过 (skipped)，其他任务继续运行。Workflow 最终状态是 SUCCESS。

**Q: 每 5 分钟运行一次太频繁了吗？**

是的，GitHub Actions 免费计划可能有限制。如果你只是测试，可以：
1. 从 Actions 页面手动运行（不受限）
2. 或者修改 tasks.json 中的 `frequency` 为 `once_per_day`

**Q: 我如何修改文章生成的关键词？**

编辑 `tasks.json`，找到 `"id": "article_generate"` 部分：
```json
"params": {
  "keywords": ["new keyword 1", "new keyword 2", "新关键词"]
  // ... 其他参数
}
```
修改 `keywords` 数组即可。

**Q: 飞书卡片中的"文件路径"是什么意思？**

是仓库中生成的文件的相对路径，例如：
```
outputs/articles/2026-02-13/understanding-artificial-intelligence.md
```
你可以直接点击这个路径在 GitHub 中查看文件。

---

## ✅ 验证检查清单

完成以下所有项即表示部署成功：

- [ ] 三个 Secrets 已在 GitHub 中配置
- [ ] 本地 DRY_RUN 模式可以生成文件
- [ ] GitHub Actions 手动运行完成
- [ ] 日志中看到 env 变量检查输出
- [ ] 飞书收到通知卡片
- [ ] outputs/articles/ 中有日期和文件
- [ ] 文件可以在 GitHub 中预览
- [ ] （可选）测试缺少某个 key 的场景

---

## 🚀 下一步

验证成功后：

1. **自动化运行**: Workflow 已配置为每 5 分钟运行一次
   - 可在 `.github/workflows/agent.yml` 的 `cron` 字段调整频率
   - `'* * * * *'` = 每分钟 (仅用于测试)
   - `'0 */6 * * *'` = 每 6 小时
   - `'0 9 * * *'` = 每天 9:00

2. **监控成本**: 监控 OpenAI 账户使用情况
   - 每篇文章成本 ~$0.001
   - 每月 5 篇 × 30 天 = ~$0.15

3. **自定义关键词**: 修改 tasks.json 中的 keywords 参数

4. **集成其他流程**: 生成的文章可以被其他流程使用（如：发布到社交媒体）

---

**有问题？** 检查日志和[故障排除](#故障排除)部分。

**成功！** 🎉 你现在有一个全自动的文章生成系统了。
