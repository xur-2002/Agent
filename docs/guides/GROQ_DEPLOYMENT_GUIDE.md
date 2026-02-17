# Article Generation - Groq Provider Deployment Guide

**Date**: 2026-02-13  
**Status**: ✅ 完成  
**Commit**: Latest (LLM Provider refactoring)

## 📋 问题修复总结

### 问题 1: OpenAI API 额度用尽导致业务中断
**症状**: GitHub Actions 定时任务因 OpenAI HTTP 429 (额度不足) 导致整个 workflow failed  
**根本原因**: 无备用 LLM provider，依赖单一厂商  
**解决方案**: 实现 Groq 作为默认免费 provider，异常分类 + graceful skip  

### 问题 2: Feishu 卡片 NoneType 崩溃
**症状**: `TypeError: object of type 'NoneType' has no len()`  
**根本原因**: 部分字段为 None 时直接调用 `len()` 或未检查访问  
**解决方案**: 所有输入参数加 safe defaults + None 检查

### 问题 3: 缺 API Key 导致任务 Failed
**症状**: GROQ_API_KEY 未配置时，任务被标记为 failed  
**根本原因**: MissingAPIKey 异常未分类处理  
**解决方案**: 异常分类 + skip 状态支持

---

## 🔧 技术变更详情

### 1️⃣ Groq LLM Provider (新增)
```python
# LLM_PROVIDER=groq 时的行为
client = OpenAI(
    api_key=Config.GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)
model = Config.GROQ_MODEL  # llama-3.1-8b-instant (免费)
```

**优势**:
- ✅ 完全免费 (vs OpenAI 付费)
- ✅ 兼容 OpenAI SDK
- ✅ 速度快 (推理快)
- ✅ 无需信用卡配置

### 2️⃣ 异常分类系统 (重新设计)
```python
class MissingAPIKeyError(LLMProviderError):
    retriable = False  # 不重试，直接 skip 所有剩余 keyword
    
class InsufficientQuotaError(LLMProviderError):
    retriable = False  # 不重试
    
class RateLimitError(LLMProviderError):
    retriable = True   # 重试，或继续下一个 keyword
    
class TransientError(LLMProviderError):
    retriable = True   # 临时错误，可重试
```

### 3️⃣ 任务状态管理 (新增)
任务不再只有 success/failed，现在支持三状态：

| 状态 | 条件 | 重试 | 示例 |
|------|------|------|------|
| `success` | 至少有 1 个 keyword 成功 | ✅ 不重试 (已成功) | 生成 1 篇文章成功 |
| `skipped` | 所有 keyword 都 skip，无 failed | ❌ 不重试 | 所有 keyword 因缺 key 而 skip |
| `failed` | 有 keyword 失败 (retriable error) | ✅ 重试 | RateLimit 导致失败 |

### 4️⃣ Feishu 卡片安全性 (完整重写)
```python
# 所有输入参数加 safe default
successful_articles = successful_articles or []
failed_articles = failed_articles or []
skipped_articles = skipped_articles or []
total_time = total_time or 0
provider = provider or "unknown"

# 卡片生成前检查 None
for article in successful_articles:
    if not article:
        continue
    title = article.get('title') or 'Untitled'
    word_count = article.get('word_count') or 0
    
# 异常处理：log 不 raise
try:
    ...
except Exception as e:
    logger.error(f"Feishu send failed: {e}")
    # 不 crash，继续执行
```

---

## 🚀 部署步骤

### 步骤 1: 获取 Groq API Key (免费)
1. 访问 https://console.groq.com
2. 注册账号 (支持 Google/GitHub OAuth)
3. 创建新 API Key
4. 复制 Key 内容

预期 Key 格式: `gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxx`

### 步骤 2: 配置 GitHub Secrets
1. 进入仓库 Settings → Secrets and variables → Actions
2. 点 "New repository secret"
3. 添加以下 Secrets:

| Name | Value | 必须 |
|------|-------|------|
| `GROQ_API_KEY` | 从 console.groq.com 复制 | ✅ 是 |
| `OPENAI_API_KEY` | (可选，作备用) | ❌ 否 |
| `SERPER_API_KEY` | (可选，搜索增强) | ❌ 否 |

### 步骤 3: 配置 GitHub Variables (可选)
1. 进入仓库 Settings → Variables
2. 添加环境变量:

| Name | Value | 默认 | 说明 |
|------|-------|------|------|
| `LLM_PROVIDER` | groq \| openai \| dry_run | groq | LLM 提供商 |

### 步骤 4: 本地测试 (可选)
```bash
# 设置本地环境变量
export GROQ_API_KEY="gsk_..."
export LLM_PROVIDER="groq"

# 运行测试
cd agent-mvp
python test_groq_provider.py

# 预期输出:
# ✅ PASSED: Groq Missing Key
# ✅ PASSED: DRY_RUN Mode
# ✅ PASSED: Task Runner Skip
# ✅ PASSED: Feishu None Safety
# ✅ PASSED: Syntax Check
# 
# Total: 5/5 passed
```

### 步骤 5: 首次 GitHub Actions 运行
1. 进入 Actions 选项卡
2. 选择 "Agent MVP Workflow"
3. 点 "Run workflow" → 选 Branch: main
4. 等待运行完成 (~2-3 分钟)

**验证检查清单**:
- [ ] Workflow 状态为 ✅ (绿色)
- [ ] 日志中看到 `LLM_PROVIDER: groq`
- [ ] 日志中看到 "Task result: success" 或 "Task result: skipped"
- [ ] 日志中**看不到** `NoneType` 错误
- [ ] Feishu 卡片收到消息
- [ ] `outputs/articles/2026-02-13/` 目录有新文件

---

## 📊 工作流示例

### 场景 A: Groq 成功生成文章
```
1. GitHub Actions 触发
2. 读取环境变量: LLM_PROVIDER=groq, GROQ_API_KEY=gsk_...
3. 对每个 keyword 调用 generate_article()
   ├─ _get_llm_client("groq") 返回 OpenAI SDK with groq base_url
   ├─ 调用 Groq API
   ├─ 成功返回文章 (metadata: provider=groq, model=llama-3.1-8b-instant)
   └─ save_article() 保存到 outputs/articles/2026-02-13/
4. 任务状态: success
5. run_article_generate() 返回:
   {
     "status": "success",
     "metrics": {
       "successful_articles": [{"keyword": "ai", "title": "..."}],
       "failed_articles": [],
       "skipped_articles": [],
       "total_time": 12.5
     }
   }
6. main.py 调用 send_article_generation_results(...) → Feishu 卡片展示成功
```

**Feishu 卡片内容**:
```
✅ Article Generation Results
• ✅ Successful: 2
• ❌ Failed: 0
• ⊘ Skipped: 0
• 🤖 Provider: groq

✅ Successful Articles (2)
• Understanding AI (750 words)
• Cloud Computing (820 words)
```

### 场景 B: GROQ_API_KEY 缺失
```
1. 环境变量: GROQ_API_KEY= (空或未设置)
2. run_article_generate() 中:
   ├─ generate_article("ai", ...)
   ├─ _get_llm_client("groq")
   └─ 抛出 MissingAPIKeyError(provider="groq", retriable=False)
3. Exception 处理（task_runner.py）:
   ├─ 捕获 MissingAPIKeyError
   ├─ 将所有剩余 keyword 标记为 skipped
   └─ break (不继续尝试)
4. 任务状态: skipped (不是 failed)
5. main.py send_article_generation_results():
   ├─ skipped_articles = [{"keyword": "ai", "reason": "missing_groq_api_key"}, ...]
   └─ 发送 Feishu 卡片（skipped 分组）
```

**Feishu 卡片内容**:
```
⊘ Article Generation Results
• ✅ Successful: 0
• ❌ Failed: 0
• ⊘ Skipped: 2
• 🤖 Provider: groq

⊘ Skipped Articles (2)
• artificial intelligence (missing_groq_api_key)
• cloud computing (missing_groq_api_key)
```

### 场景 C: Groq 额度不足 → 降级到 OpenAI → 仍然不足
```
1. generate_article() with provider="groq"
2. Groq API 返回 "exceeded token quota"
3. 抛出 InsufficientQuotaError(provider="groq", retriable=False)
4. task_runner 捕获: 中止 Groq，尝试降级
5. 尝试 provider="openai" (如果配置了 OPENAI_API_KEY)
6. 同样收到 429 错误 → InsufficientQuotaError(provider="openai")
7. 最后降级 provider="dry_run" → 生成 mock 文章
```

---

## 🧪 测试覆盖清单

测试脚本: `test_groq_provider.py`

| # | 测试路径 | 覆盖场景 | 状态 |
|----|---------|--------|------|
| 1 | 缺 Groq Key | MissingAPIKeyError → skip | ✅ |
| 2 | DRY_RUN 模式 | 生成 mock 文章 (零成本) | ✅ |
| 3 | TaskRunner Skip | 所有 keyword skip → status=skipped | ✅ |
| 4 | Feishu None Safety | None 值不崩溃，safe rendering | ✅ |
| 5 | Python 语法 | 所有 .py 文件通过 py_compile | ✅ |

**运行测试**:
```bash
cd agent-mvp
python test_groq_provider.py
```

**预期输出**:
```
✅ PASSED: Groq Missing Key
✅ PASSED: DRY_RUN Mode
✅ PASSED: Task Runner Skip
✅ PASSED: Feishu None Safety
✅ PASSED: Syntax Check

Total: 5/5 passed
✅ ALL TESTS PASSED
```

---

## 📝 修改文件清单

### A. 配置文件
- **`.env.example`** (+4 行)
  - 新增 LLM_PROVIDER, GROQ_API_KEY, GROQ_MODEL, OPENAI_MODEL
  
- **`agent/config.py`** (+8 行)
  - LLM_PROVIDER, GROQ_API_KEY, GROQ_MODEL, OPENAI_API_KEY, OPENAI_MODEL
  
- **`requirements.txt`** (+1 行)
  - `openai>=1.5.0` (兼容 Groq API)

### B. 核心逻辑
- **`agent/article_generator.py`** (~150 行新增)
  - 6 个异常类型定义
  - `_get_llm_client()` factory 函数
  - `generate_article()` 重构 (支持 provider + 异常分类)
  - `save_article()` 添加 provider/model metadata
  
- **`agent/task_runner.py`** (~200 行改动)
  - `run_article_generate()` 完全重写
  - 三状态支持 (success/skipped/failed)
  - Per-keyword 追踪
  
- **`agent/feishu.py`** (~150 行改动)
  - `send_article_generation_results()` 重写
  - Safe defaults 对所有参数
  - skipped_articles 参数新增
  
- **`agent/main.py`** (~35 行改动)
  - 更新 `send_article_generation_results()` 调用
  - 传递 skipped_articles 和 provider

### C. CI/CD
- **`.github/workflows/agent.yml`** (+8 行)
  - `LLM_PROVIDER` 环境变量注入
  - `GROQ_API_KEY` secret 注入
  - 增强环保量检查

### D. 测试
- **`test_groq_provider.py`** (新增，~270 行)
  - 5 条测试路径覆盖

**总计**: ~600 行代码改动

---

## 🔍 故障排查

### Q1: Workflow 仍然失败，日志显示 "GROQ_API_KEY not set"
**原因**: GitHub Secrets 未配置  
**解决**:
1. Settings → Secrets and variables → Actions
2. 确认 `GROQ_API_KEY` 存在
3. 重新运行 Workflow

### Q2: Feishu 卡片仍然出现 NoneType 错误
**原因**: 代码更新后未重新部署  
**解决**:
1. 确认使用最新 commit
2. 手动触发 Workflow: Actions → "Run workflow"
3. 检查日志中 "LLM Provider refactoring commit" 是否包含

### Q3: 生成的文章质量下降 (Groq vs OpenAI)
**原因**: Groq 使用 llama-3.1-8b，比 GPT-4o-mini 小  
**解决方案**:
- 方案 A: 调整 prompt 优化 Groq 输出
- 方案 B: 切换到 openai provider 并配置 OPENAI_API_KEY
- 方案 C: 增加 prompt word count 让 Groq 输出更长

**配置切换**:
```bash
# 方案 B: 使用 OpenAI (需付费)
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk_...
```

### Q4: 昨天还正常，今天 Workflow 全 skip 了
**原因**: 可能 Groq/OpenAI quota 被消耗完毕  
**解决**:
1. 检查 Groq 使用量 (https://console.groq.com) 
2. 如果额度用尽，等待月度重置或升级计划
3. 临时解决: 切换到 `LLM_PROVIDER=dry_run` (mock 生成)

### Q5: 测试运行失败，说 "ImportError: No module named 'agent'"
**原因**: 未在 agent-mvp 目录下运行  
**解决**:
```bash
cd agent-mvp
python test_groq_provider.py
```

---

## 💡 最佳实践

### 1. 监控 Groq Quota
定期检查 https://console.groq.com/admin/usage

### 2. 设置 Fallback Provider
在 GitHub Variables 中配置:
```
LLM_PROVIDER=groq    # 主
OPENAI_API_KEY=sk_...  # 备
```

代码会自动在 groq 额度不足时降级到 openai

### 3. 定期测试
每月至少一次手动触发 Workflow:
```
Actions → "Agent MVP Workflow" → "Run workflow"
```

### 4. 监控 Feishu 卡片
确保每次 Workflow 运行都能收到卡片，检查是否有异常

---

## 📞 联系与反馈

- **Issue**: 提交 GitHub Issue
- **Logs**: 查看 GitHub Actions 日志
- **Groq 支持**: https://support.groq.com

---

## ✅ 验收清单（部署前）

- [ ] GROQ_API_KEY 已从 console.groq.com 获取
- [ ] GitHub Secrets 已配置 (Settings → Secrets)
- [ ] GitHub Variables 已配置 (可选)
- [ ] 本地测试通过: `python test_groq_provider.py` → 5/5 passed
- [ ] Git commit 已提交: `git log --oneline -1`
- [ ] 首次 Workflow 运行成功 (Actions 页面显示 ✅)
- [ ] Feishu 卡片正常收到 (无 NoneType 错误)
- [ ] outputs/articles/2026-02-13/ 有新生成文件

---

**部署完成日期**: 2026-02-13  
**最终状态**: ✅ 就绪  
**下一步**: 运行 GitHub Actions Workflow 验证
