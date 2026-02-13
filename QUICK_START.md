# Quick Start - Article Generation Closed Loop

## Overview

路线二：最低成本文章生成闭环 - 每次 GitHub Actions 运行时自动生成、保存并通过飞书发送文章。

**特点**：
- ✅ 最低成本：使用 GPT-4o-mini（最便宜的 OpenAI 模型，约 $0.001/篇）
- ✅ 完整闭环：搜索 → 生成 → 保存 → 飞书通知
- ✅ 无图片成本：不调用 DALL-E，节省成本
- ✅ 无邮件成本：不使用 SMTP，仅飞书通知
- ✅ DRY_RUN 模式：本地测试

## 配置步骤

### Step 1: 添加 GitHub Secrets

在 GitHub 仓库的 **Settings > Secrets and variables > Actions** 中添加以下 Secrets：

| 变量名 | 说明 | 获取方式 |
|--------|------|---------|
| `OPENAI_API_KEY` | OpenAI API 密钥 | https://platform.openai.com/api-keys |
| `SERPER_API_KEY` | Serper 搜索 API 密钥 | https://serper.dev |
| `FEISHU_WEBHOOK_URL` | 飞书 Webhook URL | 飞书应用设置 → 机器人 → Webhook URL |

**获取 FEISHU_WEBHOOK_URL 示例**：
```bash
# 在飞书应用中创建机器人，获取 Incoming Webhook URL
# 格式: https://open.feishu.cn/open-apis/bot/v2/hook/xxxxx
```

### Step 2: 修改任务配置（可选）

编辑 `tasks.json`，修改 `article_generate` 任务的 `keywords` 参数：

```json
{
  "id": "article_generate",
  "title": "Article Generation - Cheap Mode",
  "enabled": true,
  "frequency": "every_5_min",
  "params": {
    "keywords": [
      "artificial intelligence",  // 英文关键词
      "云计算",                   // 中文关键词
      "web development"
    ],
    "language": "zh-CN"          // 文章语言
  }
}
```

**支持的语言**：
- `zh-CN` - 中文（默认）
- `en-US` - 英文

### Step 3: 手动运行 Workflow（可选）

在 GitHub 仓库的 **Actions** 标签页，点击 **Agent Workflow** → **Run workflow** 手动触发一次。

## 验证步骤 (5-10 分钟)

### 清单 1: 本地 DRY_RUN 测试

```bash
# 1. 进入项目目录
cd agent-mvp

# 2. 设置环境变量（仅 Secrets，不调用 OpenAI）
export DRY_RUN=1
export FEISHU_WEBHOOK_URL="your-webhook-url-here"
export OPENAI_API_KEY="sk-xxxx"  # 可不填（DRY_RUN 模式不会使用）
export SERPER_API_KEY="xxxxx"

# 3. 运行 Agent
python agent/main.py

# 预期输出：
# ✅ [article_generate] 开始执行
# ✅ 生成模拟文章到 outputs/articles/YYYY-MM-DD/
# ✅ 发送飞书卡片（DRY_RUN 模式仍会尝试）
```

### 清单 2: 检查文件输出

```bash
# 查看生成的文章
ls -la outputs/articles/$(date +%Y-%m-%d)/

# 应看到：
# - article-title-slug.md      (Markdown 文章)
# - article-title-slug.json    (元数据 JSON)
```

**JSON 文件示例**：
```json
{
  "title": "Understanding Artificial Intelligence in 2024",
  "keyword": "artificial intelligence",
  "keywords": ["artificial intelligence"],
  "sources": [
    {"title": "Source 1", "link": "https://example1.com"},
    {"title": "Source 2", "link": "https://example2.com"}
  ],
  "created_at": "2024-02-13T10:30:45.123456",
  "word_count": 750,
  "file_path": "outputs/articles/2024-02-13/understanding-artificial-intelligence.md"
}
```

### 清单 3: 飞书卡片验证

在飞书群组中应该看到：
```
✅ Article Generation Results

📊 Summary
• ✅ Successful: 1
• ❌ Failed: 0
• ⏱️ Time: 5.2s

### ✅ Successful Articles (1)
**Understanding AI in 2024**
📌 Keyword: `artificial intelligence`
📝 Words: 750
📚 Sources: 3
📄 File: `outputs/articles/2024-02-13/understanding-ai.md`
```

### 清单 4: 实时 Workflow 运行（GitHub Actions）

1. 进入 **GitHub 仓库** → **Actions** 标签
2. 看到 **Agent Workflow** 的运行记录
3. 点击最新的运行，查看日志：

```log
[2024-02-13 10:30:45] [INFO] [article_generate] Starting with 3 keyword(s), DRY_RUN=0
[2024-02-13 10:30:46] [INFO] [article_generate] Processing keyword: artificial intelligence
[2024-02-13 10:30:50] [INFO] [article_generate] Found 5 search results for artificial intelligence
[2024-02-13 10:30:55] [INFO] Calling OpenAI API for keyword: artificial intelligence
[2024-02-13 10:31:05] [INFO] Article generated for keyword: artificial intelligence
[2024-02-13 10:31:05] [INFO] Saved article markdown: outputs/articles/2024-02-13/understanding-ai.md
[2024-02-13 10:31:05] [INFO] Saved article metadata: outputs/articles/2024-02-13/understanding-ai.json
[2024-02-13 10:31:05] [INFO] ✓ [article_generate] SUCCESS (20.50s)
```

### 清单 5: 检查仓库文件

在 GitHub 仓库网页中：
1. 进入 **outputs/articles/** 文件夹
2. 根据日期查看各个日期的文件夹
3. 看到 `.md` 和 `.json` 文件对应生成

## 成本说明

### 每篇文章的成本

**使用 GPT-4o-mini**：
- 输入 Token: ~500-800（搜索结果 + 提示）
- 输出 Token: ~800-1000（文章内容）
- **单价**: $0.15/100K input + $0.60/100K output
- **单篇成本**: 约 **$0.0008-0.001** ≈ **0.5-1 分人民币**

**每月成本估算**（假设每天生成 5 篇）：
- 5 篇 × 30 天 × $0.001 = **$0.15/月** ≈ **1 元/月**

## 故障排除

### 问题 1: "OPENAI_API_KEY not set"
- 检查 GitHub Secrets 是否正确配置
- Settings → Secrets and variables → Actions → OPENAI_API_KEY

### 问题 2: "No search results found"
- 确认 SERPER_API_KEY 正确
- 确认 Serper 账户有可用配额
- 尝试更通用的关键词

### 问题 3: 飞书卡片未收到
- 测试 Webhook URL：`curl -X POST "YOUR_URL" -d "{...}"`
- 确认群组已添加机器人
- 检查飞书应用日志

### 问题 4: DRY_RUN 模式生成的文件不是真实文章
- DRY_RUN=1 是预期行为，用于测试
- 设置 DRY_RUN=0 使用真实的 OpenAI 调用

## 进阶配置

### 修改生成频率
```json
{
  "frequency": "every_5_min"   // 当前：每 5 分钟
  "frequency": "hourly"         // 改为：每小时一次
  "frequency": "once_per_day"   // 改为：每天一次
}
```

### 支持多语言
```json
{
  "language": "en-US"  // 改为英文
  "language": "zh-CN"  // 中文（默认）
}
```

### 修改 OpenAI 参数
编辑 `agent/article_generator.py` 中的 generate_article 函数：
- `model="gpt-4o-mini"` - 改为其他模型
- `max_tokens=1200` - 改变文章长度
- `temperature=0.7` - 改变创意度

---

**祝您使用愉快！** 🚀