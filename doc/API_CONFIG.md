# API 配置教程

本文档提供常用在线翻译 API 的申请和配置教程。

---

## 📋 目录

- [通用 API 配置说明](#通用-api-配置说明)
- [DeepSeek API 配置](#deepseek-api-配置)
- [Google Gemini API 配置](#google-gemini-api-配置)
- [其他 API 配置](#其他-api-配置)

---

## 通用 API 配置说明

### 翻译器类型

程序提供了两类翻译器，它们的区别只是**接口不同**：

#### 普通翻译器（OpenAI / Gemini）
- 使用纯文本 API
- 只发送识别出的文字
- 翻译速度快，消耗少
- 适合简单场景

#### 高质量翻译器（高质量翻译 OpenAI / 高质量翻译 Gemini）
- 使用多模态 API（支持图片）
- 发送图片 + 文字
- AI 可以"看到"图片，理解场景
- 翻译更准确，但消耗较多
- **需要模型支持多模态**（如 GPT-4o、Gemini）

> 💡 **提示**：如果你的模型支持多模态，强烈推荐使用"高质量翻译器"获得最佳效果！

### API 地址填写规范

#### OpenAI 兼容接口

OpenAI 翻译器**几乎支持市面上所有模型**，因为几乎所有的 AI 平台都提供 OpenAI 兼容接口。

- **一般情况**：API 地址以 `/v1` 结尾
  - 例如：`https://api.openai.com/v1`
  - 例如：`https://api.deepseek.com/v1`
  - 支持：DeepSeek、Groq、Together AI、OpenRouter、**硅基流动**、**火山引擎**等
- **例外情况**：某些服务商可能使用其他版本号
  - 例如：火山引擎使用 `/v3` 结尾

> 💡 **提示**：只要你的 API 提供商支持 OpenAI 兼容接口，就可以使用 OpenAI 翻译器！

#### Gemini 接口
- **无需添加版本号**：直接填写基础地址即可
  - 填写：`https://generativelanguage.googleapis.com`
  - 程序会自动添加 `/v1beta`
- **使用 AI Studio 官方 key**：无需填写 API 地址（自动使用默认地址）

---

## DeepSeek API 配置

DeepSeek 提供高质量、低成本的 AI 翻译服务，非常适合漫画翻译使用。

> ⚠️ **注意**：DeepSeek 不支持多模态，无法使用"高质量翻译器"。为了获得最佳翻译效果，建议使用支持多模态的模型（如 OpenAI GPT-4o、Google Gemini）。

### 1. 注册账号

1. 访问 [DeepSeek 开放平台](https://platform.deepseek.com/)
2. 点击"注册"按钮，使用邮箱或手机号注册
3. 完成邮箱验证

### 2. 充值

1. 登录后，点击右上角头像 → "充值"
2. 选择充值金额（建议最低 10 元起）
3. 使用支付宝或微信支付

### 3. 创建 API Key

1. 点击左侧菜单"API Keys"
2. 点击"创建 API Key"按钮
3. 输入名称（如"漫画翻译"）
4. 复制生成的 API Key（格式：`sk-xxxxxxxxxxxxxxxx`）
5. ⚠️ **重要**：立即保存 API Key，关闭窗口后无法再次查看

### 4. 配置到程序中

1. 打开程序
2. 在"基础设置"→"翻译器"中选择"OpenAI"
3. 在"高级设置"中填写：
   - **API Key**：填入你的 DeepSeek API Key（`sk-xxxxxxxxxxxxxxxx`）
   - **Base URL**：填入 `https://api.deepseek.com/v1`
   - **模型**：选择以下两种之一：
     - `deepseek-chat`：不思考，速度快，**但可能导致 AI 断句不生效**
     - `deepseek-reasoner`：有思考，速度慢，**但断句稳定可靠** ⭐ 推荐

> 💡 **提示**：AI 断句功能可以智能拆分长文本，避免气泡溢出。如果需要最佳翻译效果，建议使用 `deepseek-reasoner`。

---

## Google Gemini API 配置

Google Gemini 是 Google 最新的多模态 AI 模型，性能强劲。

### 1. 获取 API Key

1. 访问 [Google AI Studio](https://makersuite.google.com/app/apikey)
2. 登录 Google 账号
3. 点击"Create API Key"
4. 选择 Google Cloud 项目（或创建新项目）
5. 复制生成的 API Key

> 💡 **优势**：Gemini 提供每日免费额度，适合测试使用

### 2. 模型选择

Gemini 提供多种模型，各有不同的免费额度（每天）：

| 模型 | 每分钟请求数 | 上下文长度 | 每日免费次数 | 推荐度 |
|------|-------------|-----------|-------------|--------|
| **gemini-2.5-pro** | 2 | 125,000 tokens | 50 | ⭐⭐⭐ 推荐，断句稳定 |
| **gemini-2.5-flash** | 10 | 250,000 tokens | 250 | ⭐⭐ 推荐，速度快 |
| gemini-2.5-flash-preview | 10 | 250,000 tokens | 250 | 预览版 |
| gemini-2.5-flash-lite | 15 | 250,000 tokens | 1000 | 轻量版 |
| gemini-2.5-flash-lite-preview | 15 | 250,000 tokens | 1000 | 轻量版预览 |
| gemini-2.0-flash | 15 | 1,000,000 tokens | 200 | - |
| gemini-2.0-flash-lite | 30 | 1,000,000 tokens | 200 | - |

> ⚠️ **重要提示**：除了 `gemini-2.5-pro` 之外，其他模型的 **AI 断句可能不稳定**。如果需要稳定的断句效果，建议使用 Pro 模型。

### 3. 配置到程序中

1. 打开程序
2. 在"基础设置"→"翻译器"中选择"高质量翻译 Gemini"或"Gemini"
3. 在"高级设置"中填写：
   - **API Key**：你的 Gemini API Key
   - **Base URL**：如果使用 AI Studio 的官方 key，**无需填写**（自动使用默认地址）
   - **模型**：
     - `gemini-2.5-pro`：断句稳定，质量最高 ⭐ 强烈推荐
     - `gemini-2.5-flash`：速度快，免费次数多 ⭐ 推荐

---

## 其他 API 配置

### DeepL API

**特点**：专业翻译服务，质量高

1. 访问 [DeepL API](https://www.deepl.com/pro-api)
2. 注册账号并充值
3. 获取 API Key
4. 配置：

```yaml
deepl:
  api_key: "your-deepl-api-key-here"
```

### 百度翻译 API

**特点**：中文友好，价格便宜

1. 访问 [百度翻译开放平台](https://fanyi-api.baidu.com/)
2. 注册账号
3. 创建应用，获取 APP ID 和密钥
4. 在程序中选择"百度翻译"

### 有道翻译 API

**特点**：中文友好，有免费额度

1. 访问 [有道智云](https://ai.youdao.com/)
2. 注册账号
3. 创建应用，获取应用 ID 和密钥
4. 在程序中选择"有道翻译"

---

## 常见问题

### Q1：哪个 API 最推荐？

**回答**：
- **性价比最高**：DeepSeek（国内用户推荐）
- **质量最高**：OpenAI GPT-4o
- **免费试用**：Google Gemini

### Q2：API Key 泄露怎么办？

**回答**：
1. 立即到对应平台删除泄露的 API Key
2. 创建新的 API Key
3. 检查账户余额是否异常

### Q3：提示"API Key 无效"怎么办？

**回答**：
1. 检查 API Key 是否完整复制
2. 检查 Base URL 是否正确
3. 确认账户余额充足
4. 检查网络连接（国外 API 可能需要科学上网）

---

返回 [主页](../README.md) | 返回 [使用教程](USAGE.md)

