# v2.0.3 更新日志

发布日期：2026-01-03

## ⚡ 性能优化

### YOLO OBB 检测器优化
- **提升输入分辨率**：将 YOLO OBB 检测器的输入图像分辨率从 640 提升到 1280，提高小文本框的检测精度

### 特殊模式内存和显存管理优化
- **新增统一清理方法**：添加 `_cleanup_context_memory()` 方法，用于清理单个上下文的所有中间数据
- **所有特殊模式内存清理**：为 9 个特殊模式添加完整的内存和显存清理
  - 仅上色模式（colorize_only）
  - 仅超分模式（upscale_only）
  - 仅修复模式（inpaint_only）
  - 导入翻译并渲染（load_text）
  - 导出原文（template + save_text）
  - 导出翻译（generate_and_export）
  - 替换翻译（replace_translation）
- **循环内清理优化**：循环处理模式（load_text、导出原文、导出翻译、替换翻译）在每张图片处理完后立即清理，避免内存累积
- **超分推理显存优化**：
  - RealCUGAN 推理后立即删除中间张量并清理显存
  - MangaJaNai 推理后立即删除中间张量并清理显存
- **清理内容**：自动清理 input、img_rgb、img_colorized、upscaled、img_inpainted、img_rendered、img_alpha、mask、mask_raw 等中间数据
- **效果**：修复内存泄漏，批量处理时内存占用更稳定，显存释放更及时

## 🐛 修复

### OCR 模块 GPU 清理重构
- **重构 GPU 显存清理逻辑**：将 `model_32px.py` 和 `model_48px.py` 中神经网络类内部的 GPU 清理代码移除，改为在外层模型类的 `_infer` 方法中使用统一的 `_cleanup_ocr_memory` 方法
- 删除 OCR 神经网络类中直接调用 `torch.cuda.empty_cache()` 的代码，避免神经网络类关心 GPU 管理细节
- 统一使用 `common.py` 中的 `_cleanup_ocr_memory` 方法，该方法会自动检查 `use_gpu` 标志，确保只在使用 GPU 时才清理显存
