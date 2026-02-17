# Route 2 最小验证步骤清单 (5 分钟)

快速验证"路线二：最低成本文章生成闭环"已成功实现

---

## ✅ 前置检查

- [ ] 已在 GitHub Secrets 添加 3 个密钥：
  - `OPENAI_API_KEY`
  - `SERPER_API_KEY`
  - `FEISHU_WEBHOOK_URL`

---

## 步骤 1: 本地 DRY_RUN 模式验证 (2 分钟)

在项目目录运行：

```bash
export DRY_RUN=1
export FEISHU_WEBHOOK_URL="https://xxx"  # 你的飞书 webhook URL
python agent/main.py
```

**预期结果**：
- ✅ 看到日志 `[article_generate] Starting with N keyword(s), DRY_RUN=1`
- ✅ 看到日志 `Article generated for keyword: ...`
- ✅ 看到日志 `Saved article markdown: outputs/articles/YYYY-MM-DD/...`
- ✅ 看到日志 `Saved article metadata: outputs/articles/YYYY-MM-DD/...`

---

## 步骤 2: 检查文件生成 (1 分钟)

```bash
# 检查今天的文章目录
ls outputs/articles/$(date +%Y-%m-%d)/

# 应看到文件：
# - xxxxxxx.md       (Markdown 文章)
# - xxxxxxx.json     (元数据)
```

**检查清单**：
- [ ] Markdown 文件 (.md) 存在
- [ ] JSON 文件 (.json) 存在
- [ ] JSON 包含：title, keyword, sources, word_count, created_at

```bash
# 查看 JSON 内容
cat outputs/articles/$(date +%Y-%m-%d)/*.json
```

**预期结构**：
```json
{
  "title": "文章标题",
  "keyword": "关键词",
  "keywords": ["关键词"],
  "sources": [
    {"title": "来源1", "link": "URL1"},
    {"title": "来源2", "link": "URL2"}
  ],
  "created_at": "2024-02-13T10:30:45.123456",
  "word_count": 750,
  "file_path": "outputs/articles/2024-02-13/xxx.md"
}
```

---

## 步骤 3: GitHub Actions 运行 (1 分钟)

1. 进入 GitHub 仓库 → **Actions** 标签
2. 看到 **Agent MVP Workflow** 的最新运行
3. 点击进入查看日志

**检查清单**：
- [ ] Workflow 状态为 ✅ 绿色
- [ ] 看到日志包含 `[article_generate] Starting with`
- [ ] 看到日志包含 `Article generated for`
- [ ] 看到日志包含 `Saved article markdown`

---

## 步骤 4: 飞书卡片验证 (30 秒)

在飞书群组中查看是否收到卡片消息

**预期卡片内容**：
```
✅ Article Generation Results

📊 Summary
• ✅ Successful: 1
• ❌ Failed: 0
• ⏱️ Time: 5.2s

### ✅ Successful Articles (1)
**文章标题**
📌 Keyword: `关键词`
📝 Words: 750
📚 Sources: 3
📄 File: `outputs/articles/2024-02-13/xxx.md`
```

**检查清单**：
- [ ] 收到飞书卡片消息
- [ ] 卡片显示成功的文章数量
- [ ] 卡片显示文章标题、关键词、字数
- [ ] 卡片显示文件路径

---

## 步骤 5: GitHub 仓库检查 (1 分钟)

在 GitHub 网页中：

1. 进入仓库
2. 点击 **Code** 标签
3. 进入 **outputs/articles/** 文件夹

**检查清单**：
- [ ] 看到按日期创建的文件夹 (如 2024-02-13/)
- [ ] 文件夹中有 .md 和 .json 文件
- [ ] 文件名是 URL-safe slug (小写、去特殊字符)

---

## 🎉 验证完成！

如果所有 5 个步骤都完成，恭喜您！

✅ 路线二已成功实现  
✅ 最低成本文章生成闭环正在运行  
✅ 每次 Workflow 运行都会自动生成文章  
✅ 文章已保存到仓库  
✅ 飞书已接收通知  

---

## 故障排除快速指南

| 症状 | 原因 | 解决 |
|------|------|------|
| DRY_RUN 报错 "Config.validate() failed" | 缺少必需的 env var | 设置 `export FEISHU_WEBHOOK_URL="xxx"` |
| 没看到文件生成 | 权限问题或文件夹不存在 | 运行 `mkdir -p outputs/articles` |
| 飞书没收到卡片 | Webhook URL 错误 | 测试: `curl -X POST "YOUR_URL" -H "Content-Type: application/json" -d '{"msg_type":"text","content":{"text":"test"}}'` |
| 文章质量很差 | 搜索结果不佳 | 修改 keywords 为更通用的词汇 |
| OpenAI API 错误 | API 配额用尽或密钥错误 | 检查 `OPENAI_API_KEY` 是否正确 |

---

## 下一步

- 📖 阅读完整的 [QUICK_START.md](QUICK_START.md) 获取详细配置
- 🔧 根据需要修改 `tasks.json` 中的关键词
- 📊 监控 GitHub Actions，看自动化流程运行
- 💬 遇到问题？查看 Actions 日志中的错误信息

---

**预计总耗时**: 5 分钟  
**成本**: 〜 $0.001/篇 (gpt-4o-mini)  
**频率**: 每 5 分钟自动运行（可配置）
