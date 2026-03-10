# v2.1.5 更新日志

发布日期：2026-03-01

## ✨ 新增

- 提示词支持 YAML 格式（优先于 JSON）
- 新增统一提示词加载模块 `prompt_loader.py`
- Web 端支持上传/管理 YAML 提示词文件
- 新增字间距倍率 `letter_spacing`：支持全局设置、区域设置和编辑器区域属性；默认值 `1.0` 与旧行为一致，并统一作用于排版计算、文本框尺寸计算和最终渲染。
- 新增禁用 ONNX GPU 加速开关 `disable_onnx_gpu`：可在 ONNX Runtime 的 GPU 兼容性不佳时强制切换到 `CPUExecutionProvider`。
- 新增 API OCR：`openai_ocr` 与 `gemini_ocr`，支持逐框调用多模态接口识别文本，识别完成后继续使用本地 `48px` 模型提取文字颜色。
- 新增 API 上色器：`openai_colorizer` 与 `gemini_colorizer`，支持整页调用 OpenAI / Gemini 图像接口进行漫画上色。
- 新增 API 渲染器：`openai_renderer` 与 `gemini_renderer`，支持整页调用 OpenAI / Gemini 图像接口进行漫画渲染；会自动把清图画上编号框，并将对应编号的翻译文本一起组合进提示词，拟声词 / 音效也会一并发送。
- 新增独立的 AI OCR / AI 上色 / AI 渲染固定提示词文件：
  - `dict/ai_ocr_prompt.yaml`
  - `dict/ai_colorizer_prompt.yaml`
  - `dict/ai_renderer_prompt.yaml`
- 新增 AI OCR / AI 上色 / AI 渲染并发配置项，支持分别限制 API 请求并发数。

## 🐛 修复

- 修复翻译错误提示框中长原始错误信息显示不全的问题：原始错误现在会自动换行，支持完整查看与复制，并移除了冗余分隔线。
- 修复网络错误识别不完整的问题：“测试连接”和翻译错误提示现在都能识别连接错误、超时以及 Host / DNS 解析失败，并提示检查网络及尝试开启 TUN（虚拟网卡模式）。
- 修复编辑器与工作目录协作逻辑：
  - 上色/超分后的编辑器底图现在统一保存到 `manga_translator_work/editor_base/`
  - 修复图继续保存到 `manga_translator_work/inpainted/`，`保存 JSON` 会直接更新这张图，不再额外调用后端修复
  - `导入翻译并渲染` 检测到已有修复图时会直接复用，不再重复跑修复
  - `导出图片` 不再重复执行上色/超分，优先直接使用编辑器当前修复图进行渲染
  - PSD 导出现在会优先使用 `editor_base` 作为原图层底图，并优先使用当前会话修复图作为修复图层

## 🔧 优化

- 更新了新的 UI，统一了桌面端主界面、设置页和编辑器的整体风格。
- 更新 YOLO OBB 辅助检测器为原生 PyTorch 版本：模型切换为 `ysgyolo_yolo26_2.0.pt`，直接加载 checkpoint 推理，并统一设备选择与模型加载链路。
- 更新 MangaLens 气泡检测模型为 PyTorch 版本：`mangalens_detector.py` 现直接加载 `mangalens.pt` checkpoint 推理，并兼容旧 `best.pt` 文件自动迁移。
- `_build_system_prompt` 和 `_flatten_prompt_data` 统一到基类，消除约 320 行重复代码
- 优化 HQ 系统提示词结构：基础系统提示与输出格式要求拆分，自动术语提取按开关追加术语提取规则，并统一在末尾输出格式要求。
- 优化历史上下文附加逻辑：上下文改为以消息形式注入对话，Gemini 使用 `systemInstruction` 承载系统提示，高质量翻译的历史上下文不再携带图片。
- 优化 Gemini 空响应诊断：日志会输出 `finish_reason`、`block_reason` 和 `safetyRatings`，并结合诊断结果调整重试策略。
- 清理 `common.py` 死代码，从 2890 行精简至约 2436 行
- 优化 Qt 设置页提示词编辑入口：AI OCR / AI 上色 / AI 渲染统一改为固定文件的简化编辑器，不再显示路径输入框，也不再提供另存为。
- 优化 API 预设与 `.env` 管理：预设现在会统一纳入 OCR / 上色 / 渲染三组 API 环境变量，切换预设时可一起保存和加载。
- 优化服务端配置输出：Web / 服务器端不再暴露 `openai_ocr`、`gemini_ocr`、`openai_colorizer`、`gemini_colorizer`、`openai_renderer`、`gemini_renderer` 以及对应 AI 并发参数。

## 🗑️ 移除

- 旧版 JSON 系统提示词（已有 YAML 替代）
