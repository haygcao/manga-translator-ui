# v2.1.2 更新日志

发布日期：2026-02-26

## ✨ 新增

- 新增 PaddleOCR-VL OCR 提示词配置能力（语言下拉 + 自定义提示词）：
  - 支持 `ocr.ocr_vl_language_hint` 语言下拉（常用语言英文全称），自动生成 `OCR: Extract all <Language> text.` 风格提示词。
  - 支持 `ocr.ocr_vl_custom_prompt` 自定义提示词输入；填写后优先使用自定义提示词。
  - Web 首页参数面板新增以上两项并支持多语言文案显示。
  - 管理端权限编辑器（参数权限）新增以上两项，可按用户组进行显示/禁用/默认值控制。
  - Qt UI 首页 OCR 参数区新增以上两项；优化长语言名称下拉宽度并补充自定义提示词输入框（含占位示例）。
- 新增“智能气泡缩字”能力（`layout_mode=balloon_fill`）：
  - 使用 MangaLens 全图完整蒙版（含分割掩码）驱动排版，不再按区域重复检测。
  - 原始 OCR `line` 完全被气泡蒙版包裹时：
    - `has_br`：直接二分法锁定可放入蒙版的最大字号。
    - `no_br`：先用 `solve_no_br_layout` 断句，再二分法锁字。
  - 未被完整包裹时：自动回退到 `smart_scaling` 分支，避免错误缩字。
  - `dst_points` 随最终字号实时重算，保持中心点与旋转角度语义不变。
- 新增统一气泡蒙版能力：将模型检测结果统一转换为可复用的气泡蒙版，同步服务 OCR 过滤、修复范围扩展和排版，保证三处判断口径一致。
- 新增 MangaLens 检测结果缓存：`detect_bubbles_with_mangalens(...)` 增加缓存，减少 OCR 过滤/修复范围扩展/渲染阶段的重复推理开销。
- 新增 OCR 模型气泡“像素级重叠过滤”策略：由框重叠阈值升级为文本框与模型蒙版像素重叠阈值，过滤结果更稳定。
- 编辑器 OCR 新增 YOLO OBB 辅助拆分：裁剪大框区域后发送给 YOLO OBB 检测文本行，`_split_polygon_by_yolo()` 过滤重叠文本行（overlap >= 30%），排除 `other` 标签。
- 编辑器 OCR 新增方向感知排序：`_sort_quads_by_direction()` 按多数投票判断方向，水平按 y 上到下、竖直按 -(x+w) 右到左排序后再拼接文本。

## 🐛 修复

- 修复 YOLO `other` 检测框在 OCR / 常规渲染链路中误参与的问题：检测结果改为“全量检测框”与“下游处理框”分离。
- 修复 `other` 标签在后续流程中身份丢失导致过滤失效的问题：`other` 不再进入 mOCR 合并输入，避免因新建四边形未继承标签而漏过滤。
- 修复模型辅助合并与常规合并输入边界不清晰的问题：仅“模型辅助合并”可读取 `other` 检测框，mOCR 合并明确不可读取。
- 修复开启模型辅助合并后发送给翻译器的文本顺序不一致问题：统一合并结果排序规则，保证输入顺序稳定。
- 修复编辑器 OCR 拆分仅对 ocr32px/48px/48px_ctc 生效的问题：移除 OCR 模型白名单限制，PaddleOCR 等模型均可受益于 YOLO 拆分（`mocr` 和 `paddleocr_vl`等多行模型除外）。

## 🔧 优化

- 优化“启用模型气泡过滤盒 / 扩大气泡修复范围”链路：统一使用同一模型蒙版构建逻辑，减少重复实现与行为偏差。
- 优化 Qt UI 多语言与环境变量交互体验：
  - API Key 全空时“开始翻译”拦截弹窗改为完整 i18n（含“文件列表为空/未设置输出目录”短提示键补齐）。
  - API/模型输入框改为“有值显示真实值，空值显示占位符”；占位符文案及常用地址/模型默认值统一并支持多语言。
  - 统一补齐各语言包 OCR 语言下拉项（`ocr_lang_*`），并移除不再使用的 `ocr_prompt_mode_*` 文案键，避免显示不一致。

- 新增检测阶段上下文缓存：
  - `ctx.all_detected_textlines`：保存全量检测框（用于调试/追踪）。
  - `ctx.model_assisted_other_textlines`：仅保存 `other`，供模型辅助合并按需使用。
- 优化文本线合并入口：按配置动态拼接模型辅助输入，默认下游 OCR 链路只处理非 `other` 文本框。
- 优化 YOLO OBB（`yolo26obb`）后处理链路：仅保留 end-to-end 输出格式解析（`[cx, cy, w, h, conf, class_id, angle]`）；移除单 patch 内部二次去重，保留长图合并后的跨 patch 去重。
- 清理无效配置项：移除 `detector.yolo_obb_iou`（`yolo26obb` 现为 end-to-end 后处理，不再使用该参数）。
- 编辑器 OCR 移除旧 canny_flood 切割逻辑（约 250 行）：删除 `_build_text_mask_canny_flood()`、`_split_spans_from_mask()`、`_split_single_polygon()` 及其 fallback 分支，统一使用 YOLO OBB。
