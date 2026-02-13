# 🚀 部署检查清单

此清单用于验证 Agent MVP 从本地到 GitHub Actions 再到飞书的端到端配置。

## ✅ 本地验证（已完成）

- [x] **JSON 格式修复**: tasks.json 不再包含合并冲突标记
  - 运行: `python -m json.tool tasks.json`
  - 预期: ✅ 有效的 JSON 输出

- [x] **Task 实例化**: 所有 3 个示例任务可加载
  - 运行: `python test_tasks.py`  
  - 预期: ✅ "Loaded 3 tasks, all instantiated successfully"

- [x] **Agent 执行**: 并发运行成功，状态保存完整
  - 运行: `$env:FEISHU_WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"; python -m agent.main`
  - 预期: ✅ 2个任务在 ~0.3s 内完成，tasks.json 更新

- [x] **工作流升级**: 
  - `actions/upload-artifact@v3` → `@v4` ✅
  - 日志捕获 via `tee run-log.txt` ✅

---

## 📋 GitHub Actions 验证清单（下一步）

### 1️⃣ 代码推送
```bash
# 根目录运行
git status                           # 检查更改
git add .
git commit -m "fix: upgrade workflow to v4 and fix tasks.json merge conflicts"
git push origin main
```

**验证点**:
- [ ] 没有推送错误
- [ ] 远程 GitHub 显示新的提交

---

### 2️⃣ 设置 Feishu 密钥（仅首次）

1. 去飞书开放平台创建一个自定义机器人 → 获得 Webhook URL
2. 前往 GitHub 仓库设置 → Secrets → 新建 Secret:
   - **Name**: `FEISHU_WEBHOOK_URL`
   - **Value**: `https://open.feishu.cn/open-apis/bot/v2/hook/your-token`

**验证点**:
- [ ] Secret 已创建（GitHub Actions 页面可见）
- [ ] Secret name 必须完全匹配: `FEISHU_WEBHOOK_URL`

---

### 3️⃣ 手动运行工作流

**方法 A: GitHub UI**
1. 前往 GitHub 仓库 → **Actions** 标签页
2. 左侧列表找到 "Agent MVP Workflow"
3. 点击 "Run workflow" 按钮
4. 选择 main 分支，点击 "Run workflow"

**方法 B: 本地 GitHub CLI**
```bash
gh workflow run agent.yml --ref main
```

**验证点**:
- [ ] 工作流开始运行（Actions 页面显示黄色待执行状态）

---

### 4️⃣ 监控工作流执行（30 秒内）

**在 GitHub Actions 页面**:
1. 刷新 Actions 页面，最新的运行应该显示
2. 点击最新的运行条目查看详情
3. 等待所有步骤完成（预计 20-30 秒）

**预期步骤顺序**:
```
✅ Checkout code
✅ Set up Python 3.11
✅ Install dependencies
✅ Run agent              ← 这里应该看到 "Loaded 3 tasks"
✅ Commit and push changes (如果启用)
✅ Upload run logs
```

**验证点**:
- [ ] 所有步骤以绿色 ✅ 完成
- [ ] 最后一个 "Upload run logs" 成功
- [ ] 没有红色 ❌ 错误

---

### 5️⃣ 检查日志

**在 GitHub Actions 页面**:
1. 在最新运行中打开 "Run agent" 步骤
2. 查看输出日志，应该显示:
   ```
   Loading tasks from storage...
   Loaded 3 tasks
   Found N eligible tasks to run
   Starting concurrent execution...
   [task-id] Task completed: ok (X.XXs)
   ...
   All 3 tasks saved to storage
   Agent run completed in X.XXs
   ✓ All systems operational
   ```

**验证点**:
- [ ] 看到 "Loaded 3 tasks"
- [ ] 看到 "Agent run completed"
- [ ] 没有异常堆栈跟踪或错误日志

---

### 6️⃣ 下载运行日志工件

1. 在最新运行详情页面，向下滚动到 "Artifacts" 部分
2. 点击 "agent-run-logs" 下载 zip
3. 解压并打开 `run-log.txt`
4. 检查内容是否与步骤 5 中的日志一致

**验证点**:
- [ ] 工件存在且可下载
- [ ] `run-log.txt` 包含完整的执行日志
- [ ] 文件大小 > 0 KB

---

## 🚀 飞书验证（关键步骤）

### 7️⃣ 检查飞书消息

**在飞书中**:
1. 打开与机器人相同的群聊天
2. **工作流执行 30 秒内**应该收到一条新的卡片消息
3. 卡片应包含:
   ```
   ✅ Agent Run ✅ 2024-01-15 14:30 UTC
   
   Summary
   • Successful: 2
   • Failed: 0
   • Duration: 0.33s
   
   Successful Tasks
   ✓ daily_briefing (0.01s)
     Generated briefing for today
   
   ✓ health_check_url (0.32s)
     Status OK: https://example.com
   ```

**验证点**:
- [ ] 收到飞书卡片消息（不是纯文本，是"卡片"格式）
- [ ] 卡片显示 "✅ Agent Run"（绿色成功状态）
- [ ] 卡片包含 Summary、执行时间 & 任务列表
- [ ] 时间戳与 GitHub Actions 运行时间匹配（允许 ±1 分钟）

**如果没有收到消息**:
- [ ] 检查飞书 Webhook URL 是否正确
- [ ] 在 Actions 日志中查找 "Feishu" 错误
- [ ] 确认 Secret `FEISHU_WEBHOOK_URL` 已正确设置
- [ ] 手动测试 Webhook (使用 curl 或 Postman)

```bash
# 示例: 测试飞书 Webhook
curl -X POST "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"msg_type":"text","content":{"text":"Test message"}}'
```

---

## 🔄 故障排诊表

| 症状 | 原因 | 解决方案 |
|------|------|--------|
| ❌ "Loaded 3 tasks" 不显示 | tasks.json 损坏 或 JSON 解析失败 | 运行 `python -m json.tool tasks.json` 验证格式 |
| ❌ 工作流跳过 "Run agent" 步骤 | Python 依赖缺失 | 检查 `pip install -r requirements.txt` 输出 |
| ❌ 没有收到飞书卡片 | Secret 未设置 或 Webhook URL 错误 | 验证 Secret 名称及值，测试 curl 请求 |
| ❌ 工件上传失败 | run-log.txt 文件名不匹配 | 检查 `tee run-log.txt` 执行是否成功 |
| ⚠️ 仅收到文本消息，不是卡片 | send_consolidated_card() 失败，回退到 send_text() | 检查 Feishu 响应；验证 requests 库版本 |

---

## ✨ 完全成功标志

当以下**所有**条件满足时，部署完成 ✅:

```
✅ GitHub Actions 工作流：绿色（所有步骤通过）
✅ 飞书卡片消息：在 30 秒内收到
✅ Feishu 卡片格式：包含 Summary + Successful Tasks
✅ 执行时间：显示 < 1 秒
✅ run-log.txt 工件：已上传 & 可下载
✅ tasks.json：更新了 status/last_run_at/next_run_at 时期中的字段
```

---

## 📝 事后总结

完成所有验证后，更新 README.md 添加：

1. **最终 tasks.json 架构文档**
2. **GitHub Actions 故障排诊指南**
3. **飞书集成测试步骤**
4. **生产环境推荐设置**（cron 频率、超时等）

---

## 🔗 有用的链接

- 飞书开放平台: https://open.feishu.cn
- GitHub Actions 文档: https://docs.github.com/en/actions
- 飞书机器人卡片格式: https://open.feishu.cn/document/server-docs/bot-v3/add-custom-bot
- 本项目 README: [README.md](README.md)

---

**最后检查人**: 您 👤  
**检查日期**: ___________  
**所有项目已验证**: ☐ 是 ☐ 否

