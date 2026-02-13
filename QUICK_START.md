# 🚀 快速部署指南

**当前状态**: ✅ 所有本地检查通过，准备推送到 GitHub

---

## 📋 一键部署命令

### 第 1 步：确认所有检查通过
```bash
python verify_deployment.py
```

**预期输出**: `✅ ALL CHECKS PASSED - Ready for GitHub Actions deployment!`

---

### 第 2 步：提交并推送代码
```bash
git add .
git commit -m "fix: upgrade workflow to v4 and fix tasks.json merge conflicts"
git push origin main
```

---

### 第 3 步：设置 Feishu 密钥（仅首次）

1. 获取飞书机器人 Webhook URL：
   - 进入飞书群 → 设置 → 添加机器人 → 自定义机器人
   - 复制 Webhook URL (格式: `https://open.feishu.cn/open-apis/bot/v2/hook/...`)

2. 在 GitHub 仓库添加 Secret：
   - 进入 Settings → Secrets → New repository secret
   - **Name**: `FEISHU_WEBHOOK_URL`
   - **Value**: 粘贴上面复制的 Webhook URL
   - 点击 "Add secret"

---

### 第 4 步：手动运行工作流

**方法 A: GitHub UI**
1. 进入仓库 → **Actions** 标签页
2. 左侧找到 "Agent MVP Workflow"
3. 点击 "Run workflow" 按钮
4. 选择 `main` 分支，点击 "Run workflow"

**方法 B: 命令行**
```bash
gh workflow run agent.yml --ref main
```

---

### 第 5 步：验证结果（30 秒内）

#### 在 GitHub Actions 中：
1. 刷新 Actions 页面
2. 点击最新的运行记录
3. 检查所有步骤是否为 ✅ 绿色
4. 打开 "Run agent" 步骤，验证输出包含:
   - `Loaded 3 tasks`
   - `Found N eligible tasks`
   - `Agent run completed`

#### 在飞书中：
1. 打开添加了机器人的群聊
2. **应该收到一条卡片消息**，包含：
   ```
   ✅ Agent Run ✅ 2024-01-15 14:30 UTC
   
   Summary
   • Successful: 2
   • Failed: 0
   • Duration: 0.33s
   ```

#### 下载日志：
1. 在 Actions 页面向下滚动到 **Artifacts**
2. 点击 `agent-run-logs` 下载
3. 解压后打开 `run-log.txt` 检查完整日志

---

## ⚠️ 常见问题

| 问题 | 解决方案 |
|------|--------|
| ❌ "All CHECKS FAILED" | 运行 `pip install -r requirements.txt` 并重试 |
| ❌ GitHub Actions 红色失败 | 点击失败的步骤查看错误日志，参考 DEPLOYMENT_CHECKLIST.md |
| ❌ 没有收到飞书消息 | 1) 检查 Secret 名称是否exactly为 `FEISHU_WEBHOOK_URL` 2) 用 curl 测试 Webhook: `curl -X POST "YOUR_WEBHOOK_URL" -H "Content-Type: application/json" -d '{"msg_type":"text","content":{"text":"test"}}'` |
| ❌ 工件上传失败 | 检查工作流中 `tee run-log.txt` 是否成功执行 |

---

## 📞 完整文档

- **详细部署清单**: [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
- **完整修复总结**: [UPGRADE_SUMMARY.md](UPGRADE_SUMMARY.md)
- **项目 README**: [README.md](README.md)
- **自动验证脚本**: `python verify_deployment.py`

---

## ✨ 部署完成标志

```
✅ GitHub Actions: 所有步骤绿色通过
✅ Feishu: 收到卡片消息
✅ Artifacts: agent-run-logs 下载成功
✅ 本地: verify_deployment.py 7/7 通过
```

**完成后**: 工作流将每 5 分钟自动运行一次 (可配置)，每次都会向飞书发送卡片消息。

---

# 🎉 部署成功！

现在您拥有一个完整的、生产级别的任务调度系统，运行在 GitHub Actions 上，每 5 分钟执行一次，结果实时推送到飞书。

