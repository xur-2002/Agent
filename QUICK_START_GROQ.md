# ⚡ 快速上手指南 - Groq Provider 部署 (3 步，5 分钟)

**目标**: 启用 Groq 免费 LLM provider，让 GitHub Actions 自动生成文章

---

## 🚀 第 1 步: 获取 Groq API Key (2 分钟)

### 操作步骤
1️⃣ 访问 https://console.groq.com  
2️⃣ 点击 "Sign up" 或 "Sign in" (支持 Google/GitHub OAuth)  
3️⃣ 创建新的 API Key  
4️⃣ 复制 Key 内容 (格式: `gsk_xxxxxxxxxxxxxxxxxxxxxxxx`)  

### 验证
- 在浏览器中看到 API Key 完整值
- 复制到剪贴板

---

## 🔐 第 2 步: 配置 GitHub Secrets (2 分钟)

### 操作步骤
1️⃣ 进入你的 GitHub 仓库  
2️⃣ 点击 **Settings** 选项卡  
3️⃣ 左侧菜单: **Secrets and variables** → **Actions**  
4️⃣ 点击 **"New repository secret"**  
5️⃣ 填写表单:
   - **Name**: `GROQ_API_KEY`
   - **Secret**: 粘贴 Groq API Key
6️⃣ 点击 **"Add secret"**  

### 验证
- 页面显示 "GROQ_API_KEY" 在 secrets 列表中

---

## ▶️ 第 3 步: 运行 Workflow 验证 (1 分钟)

### 操作步骤
1️⃣ 进入仓库的 **Actions** 选项卡  
2️⃣ 选择 **"Agent MVP Workflow"**  
3️⃣ 点击 **"Run workflow"** 按钮  
4️⃣ 选择分支: `main`  
5️⃣ 点击 **"Run workflow"**  
6️⃣ 等待完成 (~2-3 分钟)  

### 验证检查清单
- [ ] Workflow 状态显示 ✅ (绿色)
- [ ] 点击最新运行，查看日志中：
  - [ ] `LLM_PROVIDER: groq`
  - [ ] `Task result: success` 或 `Task result: skipped`
  - [ ] 无 `NoneType` 错误
- [ ] 收到 Feishu 消息通知
- [ ] 访问 `outputs/articles/2026-02-13/` 看到新生成的文件

---

## 🧪 可选：本地测试 (3 分钟)

```bash
# 进入项目目录
cd agent-mvp

# 保证环境变量正确
export GROQ_API_KEY="gsk_..."
export LLM_PROVIDER="groq"

# 运行测试
python test_groq_provider.py

# 预期输出:
# ✅ PASSED: Groq Missing Key
# ✅ PASSED: DRY_RUN Mode
# ✅ PASSED: Task Runner Skip
# ✅ PASSED: Feishu None Safety
# ✅ PASSED: Syntax Check
# 
# Total: 5/5 passed
# ✅ ALL TESTS PASSED
```

---

## ❓ 常见问题

### Q: 如何切换回 OpenAI?
```
Settings → Variables
- LLM_PROVIDER = openai
同时需要配置 OPENAI_API_KEY secret
```

### Q: Groq 有免费额度吗?
✅ 是的，完全免费，无需信用卡

### Q: Workflow 仍然失败怎么办?
1. 检查 GROQ_API_KEY 是否正确配置
2. 检查 API Key 是否过期 (https://console.groq.com)
3. 查看 Workflow 日志中的具体错误信息

### Q: Feishu 卡片收不到了?
1. 检查 FEISHU_WEBHOOK_URL 是否配置
2. 查看 Workflow 日志中的 "send_article_generation_results" 调用

### Q: 生成的文章在哪里?
在仓库的 `outputs/articles/YYYY-MM-DD/` 目录，例如:
```
outputs/articles/2026-02-13/
├── article1.md
├── article1.json
├── article2.md
└── article2.json
```

---

## 🎉 成功标志

✅ Workflow 执行成功（绿色对勾）  
✅ 收到 Feishu 卡片通知  
✅ 新文章生成在 `outputs/articles/` 目录  
✅ Feishu 卡片显示文章详情（无 NoneType 错误）  

---

## 📚 更多帮助

- **详细指南**: 见 `GROQ_DEPLOYMENT_GUIDE.md`
- **完成摘要**: 见 `DEPLOYMENT_COMPLETE.md`
- **测试脚本**: 见 `test_groq_provider.py`

---

## 🎯 下一步

✅ 完成上述 3 个步骤后，GitHub Actions 会自动：
1. 每天定时运行
2. 使用 Groq (免费) 生成文章
3. 保存到 `outputs/articles/`
4. 发送 Feishu 卡片通知

**成本**: ¥0/月  
**可靠性**: 即使缺 key 也会 gracefully skip，不会 fail  

完成! 🚀
