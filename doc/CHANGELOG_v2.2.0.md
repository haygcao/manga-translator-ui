# v2.2.0 更新日志

发布日期：2026-03-20

## ✨ 新功能

- 新增固定 YOLO 框导入功能：开启后会从 `manga_translator_work/yolo_labels/<图片同名>.txt` 读取标注框。
- 新增“仅翻译（JSON）”模式：直接从已有 JSON 读取原文进行翻译，并把译文回写到 JSON。

## 🐛 修复

- 修复双栏编辑/原图对比模式下，顶部或边缘文本框在禁用换行后文字超出原图范围时，左右两侧画布无法继续对齐和同步移动的问题。
- 修复提示词编辑器部分 UI 显示异常。
- 修复提示词编辑器中 glossary/术语表词条无法上下移动的问题。
- 修复 `render.font_size` 在 `smart_scaling`、`strict`、`balloon_fill` 三种排版模式下未正确作为“固定字体大小”生效的问题；现在会在统一字号出口覆盖布局计算结果。
- 统一 `render.font_size`、`font_size_offset`、`font_scale_ratio`、`font_size_minimum`、`max_font_size` 的字号收口逻辑，三种排版模式行为保持一致，`skip_font_scaling` 分支不受影响。

## 🔧 优化

- 支持在人物词条详情中直接修改分类。

## 📝 说明

- “仅翻译（JSON）”模式需要提前存在 JSON 数据。
- “仅翻译（JSON）”模式完成后会自动删除对应的 `_original.txt`。
