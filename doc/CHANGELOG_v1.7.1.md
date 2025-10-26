# 更新日志 v1.7.1

## 功能增强

### ✨ 编辑器单文本框独立字体设置功能

**新增功能**：
- 支持在编辑器中为每个文本框独立设置字体
- 每个文本框的字体设置互不影响
- 未设置字体的文本框使用全局默认字体

**实现内容**：

1. **添加 font_path 参数传递支持** (`desktop_qt_ui/services/render_parameter_service.py`)
   - 在 `get_region_parameters` 方法中添加对 `font_path` 字段的读取
   - 确保文本框的字体路径正确传递到渲染参数

2. **TextBlock 字体路径属性支持** (`manga_translator/utils/textblock.py`)
   - 在 `TextBlock.__init__` 中添加 `font_path` 属性
   - 从 `kwargs` 中读取并保存 `font_path`，支持桌面UI的单文本框字体设置

3. **修复字体污染问题** (`manga_translator/rendering/__init__.py`)
   - 保存全局默认字体路径
   - 每个文本框渲染前检查并设置正确的字体：
     - 有设置 `font_path` → 使用文本框指定的字体
     - 无设置 `font_path` → 恢复UI配置的全局默认字体
   - 防止单个文本框的字体设置影响其他文本框

4. **配置文件清理** (`examples/config-example.json`)
   - 移除示例配置文件中的绝对路径
   - 将 `last_open_dir` 和 `last_output_path` 设置为空字符串

## 影响范围

- 桌面UI编辑器导出功能
- 文本渲染引擎
- 字体处理逻辑

## 测试建议

1. 在编辑器中为不同文本框设置不同字体
2. 导出图片并验证每个文本框使用了正确的字体
3. 验证未设置字体的文本框使用UI全局配置的默认字体

