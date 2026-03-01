# 命令行模式使用指南

本文档详细介绍如何使用命令行模式进行漫画翻译。

---

## ⚠️ 重要提示

使用命令行前，请先在项目目录激活虚拟环境：

```bash
# Windows / Linux / macOS
conda activate manga-env
```

---

## 📋 目录

- [快速开始](#快速开始)
- [基本用法](#基本用法)
- [配置文件](#配置文件)
- [输入输出](#输入输出)
- [常用参数](#常用参数)
- [使用示例](#使用示例)
- [Web模式](#web-模式---web服务器api--web界面)

---

## 快速开始

### 运行模式

本程序支持两种运行模式：

1. **Local 模式**（推荐）- 命令行翻译模式，功能完整
2. **Web 模式** - Web服务器，提供 HTTP REST API 和 Web界面

### Local 模式

```bash
# 翻译单个图片（自动使用配置文件）
python -m manga_translator local -i manga.jpg

# 翻译整个文件夹
python -m manga_translator local -i ./manga_folder/

# 简写方式（默认使用 Local 模式）
python -m manga_translator -i manga.jpg
```

就这么简单！程序会自动：
- 加载 `examples/config.json` 配置文件
- 使用配置文件中的所有设置（翻译器、OCR、渲染等）
- 输出到同目录（文件名加 `-translated` 后缀）

---

## 基本用法

### 命令格式

```bash
# Local 模式
python -m manga_translator local -i <输入> [选项]

# 或简写（默认 Local 模式）
python -m manga_translator -i <输入> [选项]
```

### 必需参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `-i`, `--input` | 输入图片或文件夹 | `-i manga.jpg` |

### 可选参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-o`, `--output` | 输出路径 | 同目录 |
| `--config` | 配置文件路径 | 自动查找 |
| `-v`, `--verbose` | 详细日志 | 关闭 |
| `--overwrite` | 覆盖已存在文件 | 关闭 |
| `--use-gpu` | 使用 GPU 加速 | 配置文件 |
| `--format` | 输出格式（png/jpg/webp） | 配置文件 |
| `--batch-size` | 批量处理大小 | 配置文件 |
| `--attempts` | 翻译失败重试次数（-1=无限） | 配置文件 |

### 内存管理参数（子进程模式）

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--subprocess` | 启用子进程模式（支持内存管理） | 关闭 |
| `--memory-limit` | 进程内存限制（MB），超过后自动重启子进程，0表示不限制 | 0 |
| `--memory-percent` | 系统内存百分比限制，系统总内存使用率超过此值时重启，0表示不限制 | 0 |
| `--batch-per-restart` | 每处理N张图片后重启子进程释放内存，0表示不限制 | 0 |

**子进程模式说明**：
- 翻译任务在独立子进程中运行，内存可以真正释放
- 当进程内存或系统内存超过限制时，子进程结束，主进程启动新的子进程继续
- 需要安装 `psutil` 来监控内存：`pip install psutil`

**注意**：命令行参数会覆盖配置文件中的对应设置。

---

## 配置文件

### 自动加载

命令行模式会自动按以下优先级查找配置文件：

1. **`examples/config.json`** （用户配置，优先）
2. `examples/config-example.json` （模板配置）

### 指定配置文件

```bash
python -m manga_translator -i manga.jpg --config my_config.json
```

### 配置文件内容

配置文件包含所有翻译设置。完整的配置示例请参考 `examples/config-example.json`。

**基本配置示例**：

```json
{
  "translator": {
    "translator": "openai_hq",
    "target_lang": "CHS",
    "no_text_lang_skip": false,
    "high_quality_prompt_path": "dict/prompt_example.yaml",
    "max_requests_per_minute": 0
  },
  "detector": {
    "detector": "default",
    "detection_size": 2048,
    "text_threshold": 0.5,
    "box_threshold": 0.5,
    "unclip_ratio": 2.5,
    "use_yolo_obb": true,
    "min_box_area_ratio": 0.0008
  },
  "ocr": {
    "ocr": "48px",
    "use_hybrid_ocr": false,
    "secondary_ocr": "mocr",
    "min_text_length": 0,
    "prob": 0.1
  },
  "inpainter": {
    "inpainter": "lama_large",
    "inpainting_size": 2048,
    "inpainting_precision": "fp32"
  },
  "render": {
    "renderer": "default",
    "alignment": "auto",
    "direction": "auto",
    "font_path": "Arial-Unicode-Regular.ttf",
    "layout_mode": "smart_scaling",
    "disable_font_border": false,
    "font_size_offset": 0,
    "stroke_width": 0.07,
    "check_br_and_retry": false
  },
  "upscale": {
    "upscaler": "realcugan",
    "upscale_ratio": null,
    "realcugan_model": null,
    "tile_size": 600
  },
  "colorizer": {
    "colorizer": "none",
    "colorization_size": 2048,
    "denoise_sigma": 30
  },
  "cli": {
    "use_gpu": true,
    "verbose": false,
    "attempts": -1,
    "ignore_errors": false,
    "context_size": 3,
    "format": "不指定",
    "overwrite": true,
    "skip_no_text": false,
    "save_text": false,
    "load_text": false,
    "template": false,
    "save_quality": 100,
    "batch_size": 3
  },
  "filter_text": null,
  "kernel_size": 3,
  "mask_dilation_offset": 70
}
```

**配置说明**：
- 完整的配置结构请参考 `examples/config-example.json`
- 所有参数的详细说明请参考 [设置说明文档](SETTINGS.md)
- 可以只配置需要修改的部分，其他使用默认值

### 命令行参数优先级

**命令行参数 > 配置文件**

```bash
# 命令行参数会覆盖配置文件中的设置
python -m manga_translator -i manga.jpg -v
```

---

## 输入输出

### 输入类型

#### 1. 单个图片

```bash
python -m manga_translator -i manga.jpg
```

支持格式：`.png`, `.jpg`, `.jpeg`, `.bmp`, `.webp`

#### 2. 多个图片

```bash
python -m manga_translator -i page1.jpg page2.jpg page3.jpg
```

#### 3. 文件夹

```bash
python -m manga_translator -i ./manga_folder/
```

会递归处理所有子文件夹中的图片。

### 输出规则

#### 不指定输出路径

```bash
python -m manga_translator -i manga.jpg
```

**输出：** `manga-translated.jpg` （同目录）

```bash
python -m manga_translator -i ./manga_folder/
```

**输出：** `./manga_folder-translated/` （新文件夹）

#### 指定输出文件

```bash
python -m manga_translator -i manga.jpg -o translated.jpg
```

**输出：** `translated.jpg`

#### 指定输出文件夹

```bash
python -m manga_translator -i manga.jpg -o ./output/
```

**输出：** `./output/manga.jpg`

```bash
python -m manga_translator -i ./manga_folder/ -o ./output/
```

**输出：** `./output/` （保持原有目录结构）

---

## 常用参数

### 详细日志

```bash
# 显示详细日志和中间结果
python -m manga_translator -i manga.jpg -v
```

会在 `result/` 目录保存调试图片：
- `bboxes.png` - 检测框
- `mask.png` - 文本蒙版
- `inpainted.png` - 修复后的图片

### 覆盖已存在文件

```bash
python -m manga_translator -i manga.jpg --overwrite
```

### 输出格式

```bash
# 输出为 PNG
python -m manga_translator -i manga.jpg --format png

# 输出为 JPEG（指定质量）
python -m manga_translator -i manga.jpg --format jpg
```

---

## 使用示例

### 示例 1：翻译单个图片

```bash
python -m manga_translator -i manga.jpg
```

**结果：** `manga-translated.jpg`

### 示例 2：翻译文件夹到指定目录

```bash
python -m manga_translator -i ./raw/ -o ./translated/
```

**结果：** 所有图片翻译后保存到 `./translated/`

### 示例 3：使用自定义配置

```bash
python -m manga_translator -i manga.jpg --config my_config.json
```

### 示例 4：详细日志

```bash
python -m manga_translator -i manga.jpg -v
```

### 示例 5：批量翻译多个文件

```bash
python -m manga_translator -i page1.jpg page2.jpg page3.jpg -o ./output/
```

### 示例 6：使用子进程模式（内存管理）

```bash
# 启用子进程模式（不设置限制则不会自动重启）
python -m manga_translator local -i ./manga_folder/ --subprocess

# 使用进程内存限制（进程内存超过6GB时重启）
python -m manga_translator local -i ./manga_folder/ --subprocess --memory-limit 6000

# 使用系统内存百分比限制（系统总内存使用率超过80%时重启）
python -m manga_translator local -i ./manga_folder/ --subprocess --memory-percent 80

# 每处理20张图片后强制重启子进程
python -m manga_translator local -i ./manga_folder/ --subprocess --batch-per-restart 20

# 组合使用：进程内存超过6GB 或 每处理50张图片后重启
python -m manga_translator local -i ./manga_folder/ --subprocess --memory-limit 6000 --batch-per-restart 50
```

---

## 高级用法

### 批量处理

```bash
# 设置批量大小（一次处理多张图片）
python -m manga_translator -i ./folder/
```

批量大小在配置文件中设置（`cli.batch_size`）。

### 子进程模式（内存管理）

子进程模式适用于大批量翻译任务，可以有效管理内存：

```bash
# 基本用法（进程内存超过6GB时重启）
python -m manga_translator local -i ./manga_folder/ --subprocess --memory-limit 6000

# 完整参数示例
python -m manga_translator local -i ./manga_folder/ -o ./output/ \
    --subprocess \
    --memory-limit 6000 \
    --verbose \
    --overwrite
```

**工作原理**：
1. 主进程负责任务调度和进度管理
2. 子进程执行实际翻译任务
3. 当进程内存或系统内存超过限制时，子进程结束
4. 主进程启动新的子进程继续处理（内存已释放）
5. 直到所有文件处理完成

**内存限制说明**：
- `--memory-limit`：监控翻译进程自身的内存使用
- `--memory-percent`：监控系统总内存使用率（包括所有进程）
- 两个参数可以同时使用，任一条件触发都会重启子进程

---

## Web 模式 - Web服务器（API + Web界面）

Web 模式启动一个功能完整的Web服务器，通过浏览器访问，提供专业的漫画翻译服务：

```bash
# 启动 Web API 服务器
python -m manga_translator web --host 127.0.0.1 --port 8000

# 使用 GPU
python -m manga_translator web --host 0.0.0.0 --port 8000 --use-gpu

# 设置模型 TTL（模型在最后一次使用后 300 秒后卸载）
python -m manga_translator web --models-ttl 300

# 强制重试次数（忽略 API 传入的配置）
python -m manga_translator web --retry-attempts 3
```

### 环境变量配置

**管理员密码自动设置**

首次启动 Web 服务器时，可以通过环境变量自动设置管理员密码，无需手动在界面中设置：

```bash
# Windows (CMD)
set MANGA_TRANSLATOR_ADMIN_PASSWORD=your_password_here
python -m manga_translator web --host 127.0.0.1 --port 8000

# Windows (PowerShell)
$env:MANGA_TRANSLATOR_ADMIN_PASSWORD="your_password_here"
python -m manga_translator web --host 127.0.0.1 --port 8000

# Linux / macOS
export MANGA_TRANSLATOR_ADMIN_PASSWORD=your_password_here
python -m manga_translator web --host 127.0.0.1 --port 8000

# Docker 部署
docker run -e MANGA_TRANSLATOR_ADMIN_PASSWORD=your_password_here ...
```

**说明**：
- 密码至少需要 6 位字符
- 只在首次启动且未设置密码时生效
- 密码会自动保存到 `manga_translator/server/admin_config.json`
- 后续启动会使用保存的密码，不再读取环境变量
- 如需修改密码，请在管理面板中使用"更改管理员密码"功能

**核心功能**：

**1. Web用户界面**
- 🌐 **浏览器访问** - 无需安装客户端，任何设备都能使用
- 📁 **拖拽上传** - 支持拖拽上传图片和文件夹
- 🗂️ **批量处理** - 一次上传多张图片，自动批量翻译
- 📊 **实时进度** - 翻译进度实时显示，支持查看详细日志
- 🖼️ **结果预览** - 翻译完成后直接在浏览器中预览和下载

**2. 管理后台**
- ⚙️ **服务器配置** - GPU设置、模型TTL、重试次数等
- 👥 **用户管理** - 访问密码、权限控制
- 🔐 **API密钥策略** - 强制用户提供密钥、允许服务器密钥等
- 📊 **参数可见性** - 控制用户可见的配置选项
- 🔒 **管理员登录** - 独立的管理员密码保护

**3. 翻译配置**
- 🔧 **翻译器选择** - OpenAI、Gemini、Sakura等
- 🎯 **目标语言** - 支持中文、英文、日文、韩文等多种语言
- 🔍 **检测器配置** - 文本检测参数、YOLO OBB等
- 👁️ **OCR配置** - OCR引擎选择、混合OCR等
- 🎨 **渲染配置** - 字体、对齐、布局模式等
- 🖌️ **修复器配置** - 图片修复参数
- 📈 **超分配置** - 图片超分辨率设置

**4. API密钥管理**
- 🔑 **可视化配置** - 在Web界面直接输入API密钥
- 🔐 **并发隔离** - 多用户同时使用不同API密钥互不干扰
- 💾 **持久化存储** - 密钥保存到localStorage，页面刷新不丢失
- 🔄 **实时生效** - 修改密钥后立即生效，无需重启服务器
- 🛡️ **安全保护** - 使用线程锁保护并发访问

**5. 资源管理**
- 📝 **字体管理** - 上传、删除、查看可用字体
- 📄 **提示词管理** - 上传、删除、编辑高质量翻译提示词
- 🗑️ **文件清理** - 清理临时文件和翻译结果
- 📦 **批量操作** - 支持批量上传和删除

**6. REST API**
- 🔌 **完整API** - 提供完整的HTTP REST API
- 📡 **远程调用** - 支持通过网络远程调用
- 🔄 **任务队列** - 自动管理并发请求
- 📊 **API文档** - 自动生成Swagger文档
- 🎯 **多种端点** - 翻译、导出、导入、超分、上色等

**7. 实时日志**
- 📊 **日志查看** - 实时查看翻译日志
- 🔍 **级别过滤** - 按日志级别过滤（INFO、WARNING、ERROR）
- 📈 **进度追踪** - 追踪每个处理步骤
- 🔄 **自动刷新** - 支持轮询自动刷新

**8. 多语言支持**
- 🌍 **界面多语言** - 支持中文、英文、日文、韩文等
- 🔄 **动态切换** - 无需刷新页面即可切换语言
- 📝 **完整翻译** - 所有界面文本都支持多语言

**9. 权限控制**
- 🔐 **用户密码** - 可设置用户访问密码
- 👑 **管理员权限** - 独立的管理员密码和权限
- 🚫 **功能限制** - 控制用户可上传字体、删除文件等
- 📊 **上传限制** - 限制文件大小和数量

**访问方式**：
- 🏠 **用户界面**：`http://127.0.0.1:8000/`
- ⚙️ **管理后台**：`http://127.0.0.1:8000/admin`
- 📚 **API文档**：`http://127.0.0.1:8000/docs`
- 📊 **实时日志**：`http://127.0.0.1:8000/logs`

**适用场景**：
- ✅ **个人使用** - 通过浏览器随时随地访问
- ✅ **团队协作** - 多人共享服务器，各自使用自己的API密钥
- ✅ **远程访问** - 部署在服务器上，通过网络访问
- ✅ **移动设备** - 手机、平板也能通过浏览器使用
- ✅ **API集成** - 作为后端服务集成到其他应用
- ✅ **自动化脚本** - 通过API实现自动化翻译

**优势**：
- 🌐 跨平台访问，无需安装客户端
- 👥 多用户支持，API密钥隔离
- 🔐 完善的权限控制和安全保护
- 📊 实时日志和进度显示
- 🔌 完整的REST API支持
- ⚙️ 灵活的配置管理
- 🌍 多语言界面支持

**参数说明**：
- `--host` - 服务器主机（默认：127.0.0.1，设置为0.0.0.0允许外网访问）
- `--port` - 服务器端口（默认：8000）
- `--use-gpu` - 使用 GPU 加速
- `--models-ttl` - 模型在内存中的保留时间（秒，0 表示永远，默认：0）
- `--retry-attempts` - 翻译失败时的重试次数（-1 表示无限重试，None 表示使用 API 传入的配置，默认：None）
- `-v, --verbose` - 显示详细日志



---

## Web 模式 API 端点

以下API端点在 **Web模式** 中可用：

### 基础端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 服务器信息 |
| `/docs` | GET | API 文档（Swagger UI） |
| `/translate/queue-size` | POST | 获取任务队列大小 |

### 认证端点 (`/auth`)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/auth/login` | POST | 用户登录 |
| `/auth/logout` | POST | 用户注销 |
| `/auth/register` | POST | 用户注册（需管理员开启） |
| `/auth/change-password` | POST | 修改密码 |
| `/auth/check` | GET | 检查会话状态 |
| `/auth/status` | GET | 获取认证系统状态 |
| `/auth/setup` | POST | 初始设置（创建首个管理员） |

### 配置管理端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/config` | GET | 获取配置结构（支持 mode 参数：user/authenticated/admin） |
| `/config/defaults` | GET | 获取服务器默认配置 |
| `/config/structure` | GET | 获取完整配置结构（管理员） |
| `/config/options` | GET | 获取配置选项（翻译器、语言等） |
| `/translator-config/{translator}` | GET | 获取指定翻译器的配置信息 |

### 元数据端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/fonts` | GET | 获取可用字体列表 |
| `/translators` | GET | 获取可用翻译器列表（支持 mode 参数） |
| `/languages` | GET | 获取可用目标语言列表（支持 mode 参数） |
| `/workflows` | GET | 获取可用工作流列表（支持 mode 参数） |

### 用户设置端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/user/settings` | GET | 获取用户设置（包含用户组配额） |

### 管理员端点 (`/admin`)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/admin/need-setup` | GET | 检查是否需要首次设置 |
| `/admin/setup` | POST | 首次设置管理员密码 |
| `/admin/login` | POST | 管理员登录（旧版，建议用 /auth/login） |
| `/admin/change-password` | POST | 修改管理员密码 |
| `/admin/settings` | GET/POST/PUT | 获取/更新管理员设置 |
| `/admin/settings/parameter-visibility` | POST | 更新参数可见性设置 |
| `/admin/server-config` | GET/POST | 获取/更新服务器配置 |
| `/admin/announcement` | PUT | 更新公告 |
| `/admin/tasks` | GET | 获取所有活动任务 |
| `/admin/tasks/{task_id}/cancel` | POST | 取消指定任务（支持 force 参数） |
| `/admin/logs` | GET | 获取日志（支持筛选和分页） |
| `/admin/logs/export` | GET | 导出日志为文本文件 |
| `/admin/env-vars` | GET/POST | 获取/保存环境变量 |
| `/admin/storage/info` | GET | 获取存储使用情况 |
| `/admin/cleanup/{target}` | POST | 清理指定目录（uploads/results/cache/all） |

### 用户管理端点 (`/api/admin/users`)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/admin/users` | GET | 列出所有用户 |
| `/api/admin/users` | POST | 创建新用户 |
| `/api/admin/users/{username}` | GET | 获取用户信息 |
| `/api/admin/users/{username}` | PUT | 更新用户信息 |
| `/api/admin/users/{username}` | DELETE | 删除用户 |
| `/api/admin/users/{username}/permissions` | PUT | 更新用户权限 |

### 用户组管理端点 (`/api/admin/groups`)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/admin/groups` | GET | 获取所有用户组 |
| `/api/admin/groups` | POST | 创建新用户组 |
| `/api/admin/groups/{group_id}` | GET | 获取指定用户组 |
| `/api/admin/groups/{group_id}` | DELETE | 删除用户组 |
| `/api/admin/groups/{group_id}/rename` | PUT | 重命名用户组 |
| `/api/admin/groups/{group_id}/config` | PUT | 更新用户组配置 |

### 会话管理端点 (`/sessions`)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/sessions/` | GET | 列出当前用户的会话 |
| `/sessions/` | POST | 创建新会话 |
| `/sessions/{session_token}` | GET | 获取会话详情 |
| `/sessions/{session_token}` | DELETE | 删除会话 |
| `/sessions/{session_token}/status` | PUT | 更新会话状态 |
| `/sessions/access-log` | GET | 获取访问日志（管理员） |
| `/sessions/access-log/unauthorized` | GET | 获取未授权访问记录（管理员） |

### 资源管理端点 (`/api/resources`)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/resources/prompts` | GET | 获取用户的提示词列表 |
| `/api/resources/prompts` | POST | 上传提示词文件 |
| `/api/resources/prompts/{resource_id}` | DELETE | 删除提示词 |
| `/api/resources/prompts/by-name/{filename}` | DELETE | 按文件名删除提示词 |
| `/api/resources/fonts` | GET | 获取用户的字体列表 |
| `/api/resources/fonts` | POST | 上传字体文件 |
| `/api/resources/fonts/{resource_id}` | DELETE | 删除字体 |
| `/api/resources/fonts/by-name/{filename}` | DELETE | 按文件名删除字体 |
| `/api/resources/stats` | GET | 获取资源统计信息 |

### 历史记录端点 (`/api/history`)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/history` | GET | 获取用户翻译历史（支持筛选） |
| `/api/history/search` | GET | 搜索翻译历史 |
| `/api/history/admin/all` | GET | 管理员查看所有历史（支持分页） |
| `/api/history/{session_token}` | GET | 获取会话详情 |
| `/api/history/{session_token}` | DELETE | 删除翻译会话 |
| `/api/history/{session_token}/download` | GET | 下载会话结果（ZIP） |
| `/api/history/{session_token}/file/{filename}` | GET | 获取历史记录中的单个文件 |
| `/api/history/batch-download` | POST | 批量下载多个会话 |

### 配额管理端点 (`/api`)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/quota/stats` | GET | 获取当前用户配额统计 |
| `/api/admin/quota/stats` | GET | 获取所有用户配额统计（管理员） |
| `/api/admin/quota/user/{user_id}` | GET | 获取指定用户配额（管理员） |
| `/api/admin/quota/reset` | POST | 重置配额（管理员） |
| `/api/admin/quota/set-limits` | POST | 设置配额限制（管理员） |

### 清理管理端点 (`/api/admin/cleanup`)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/admin/cleanup/rules` | GET | 获取所有清理规则 |
| `/api/admin/cleanup/rules` | POST | 创建清理规则 |
| `/api/admin/cleanup/rules/{rule_id}` | DELETE | 删除清理规则 |
| `/api/admin/cleanup/manual` | POST | 执行手动清理 |
| `/api/admin/cleanup/preview` | POST | 预览清理结果 |
| `/api/admin/cleanup/auto/status` | GET | 获取自动清理状态 |
| `/api/admin/cleanup/auto/trigger` | POST | 手动触发自动清理 |
| `/api/admin/cleanup/auto/history` | GET | 获取自动清理历史 |

### 日志端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/logs` | GET | 获取实时日志（旧版） |

### 翻译端点 (`/translate`)

**JSON Body 端点**（接收 JSON 格式的请求）：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/translate/json` | POST | 翻译图片，返回 JSON |
| `/translate/bytes` | POST | 翻译图片，返回自定义字节格式 |
| `/translate/image` | POST | 翻译图片，返回图片 |
| `/translate/json/stream` | POST | 流式翻译，返回 JSON（支持进度） |
| `/translate/bytes/stream` | POST | 流式翻译，返回字节格式（支持进度） |
| `/translate/image/stream` | POST | 流式翻译，返回图片（支持进度） |

**Form 表单端点**（接收 multipart/form-data）：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/translate/with-form/json` | POST | 翻译图片，返回 JSON |
| `/translate/with-form/bytes` | POST | 翻译图片，返回字节格式 |
| `/translate/with-form/image` | POST | 翻译图片，返回图片 |
| `/translate/with-form/json/stream` | POST | 流式翻译，返回 JSON（支持进度） |
| `/translate/with-form/bytes/stream` | POST | 流式翻译，返回字节格式（支持进度） |
| `/translate/with-form/image/stream` | POST | 流式翻译，返回图片（推荐，适合脚本） |
| `/translate/with-form/image/stream/web` | POST | 流式翻译，返回图片（Web 前端优化） |

**批量翻译端点**：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/translate/batch/json` | POST | 批量翻译，返回 JSON 数组 |
| `/translate/batch/images` | POST | 批量翻译，返回 ZIP 压缩包 |

> ⚠️ **重要**：批量端点使用 JSON 格式请求，图片需要 base64 编码，不是 multipart/form-data 格式！

**批量翻译示例**：
```python
import requests
import base64
import json

# 读取图片并编码为 base64
with open('image1.jpg', 'rb') as f:
    img1_b64 = base64.b64encode(f.read()).decode('utf-8')
with open('image2.jpg', 'rb') as f:
    img2_b64 = base64.b64encode(f.read()).decode('utf-8')

# 准备请求数据
data = {
    "images": [
        f"data:image/jpeg;base64,{img1_b64}",
        f"data:image/jpeg;base64,{img2_b64}"
    ],
    "config": {},  # 使用默认配置
    "batch_size": 2
}

# 发送请求（注意是 json=data，不是 files=）
response = requests.post(
    'http://127.0.0.1:8200/translate/batch/json',
    json=data,
    timeout=600
)

# 处理结果
if response.status_code == 200:
    results = response.json()
    print(f"成功翻译 {len(results)} 张图片")
```

**导出端点**（导出翻译结果）：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/translate/export/original` | POST | 导出原文（ZIP：JSON + TXT） |
| `/translate/export/original/stream` | POST | 导出原文（流式，支持进度） |
| `/translate/export/translated` | POST | 导出译文（ZIP：JSON + TXT） |
| `/translate/export/translated/stream` | POST | 导出译文（流式，支持进度） |

**处理端点**（图片处理）：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/translate/upscale` | POST | 仅超分（返回高清图片） |
| `/translate/upscale/stream` | POST | 仅超分（流式，支持进度） |
| `/translate/colorize` | POST | 仅上色（返回彩色图片） |
| `/translate/colorize/stream` | POST | 仅上色（流式，支持进度） |
| `/translate/inpaint` | POST | 仅修复（检测文字并修复图片） |
| `/translate/inpaint/stream` | POST | 仅修复（流式，支持进度） |

**导入端点**（导入翻译并渲染）：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/translate/import/json` | POST | 导入 JSON + 图片，返回渲染后的图片 |
| `/translate/import/json/stream` | POST | 导入 JSON + 图片（流式，支持进度） |
| `/translate/import/txt` | POST | 导入 TXT + JSON + 图片，返回渲染后的图片 |
| `/translate/import/txt/stream` | POST | 导入 TXT + JSON + 图片（流式，支持进度） |

**其他端点**：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/translate/complete` | POST | 翻译图片，返回完整结果（JSON + 图片，multipart 格式） |

**结果管理端点**：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/results/list` | GET | 列出所有结果目录 |
| `/result/{folder_name}/final.png` | GET | 获取指定结果图片 |
| `/results/{folder_name}` | DELETE | 删除指定结果目录 |
| `/results/clear` | DELETE | 清空所有结果目录 |

**维护端点**：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/cleanup/temp` | POST | 清理临时文件（默认清理24小时前的文件） |

---

## 功能说明

所有端点都已经内置了对应的功能，无需额外参数指定工作模式。

> ⚠️ **重要**：API 端点会**忽略** config 中的 `cli` 工作流程设置（如 `load_text`、`template`、`generate_and_export` 等），完全由端点本身控制工作流程。这些 `cli` 设置仅用于命令行模式。

### 翻译端点

#### 翻译并返回图片
完整的翻译流程，返回渲染后的图片。

**流程**：
```
输入图片 → 文本检测 → OCR识别 → 机器翻译 → 图片修复 → 文字渲染 → 输出图片
```

**API 端点**：
```python
POST /translate/image                    # 返回图片
POST /translate/image/stream             # 流式，支持进度
POST /translate/with-form/image          # 表单方式
POST /translate/with-form/image/stream   # 表单方式，流式
```

#### 翻译并返回 JSON
完整的翻译流程，但不渲染图片，直接返回翻译数据（更快）。

**流程**：
```
输入图片 → 文本检测 → OCR识别 → 机器翻译 → 输出 JSON（跳过渲染）
```

**优势**：
- 跳过图片修复和渲染步骤，速度更快
- 适合只需要翻译文本的场景
- 可以后续使用导入端点重新渲染

**API 端点**：
```python
POST /translate/json                     # 返回 JSON
POST /translate/json/stream              # 流式，支持进度
POST /translate/with-form/json           # 表单方式
POST /translate/with-form/json/stream    # 表单方式，流式
```

### 导出端点

#### 导出原文
只执行检测和 OCR，不进行翻译，用于提取原文。

**流程**：
```
输入图片 → 文本检测 → OCR识别 → 生成 ZIP（JSON + TXT）
```

**返回内容**：
- `translation.json` - 包含文本框位置、原文等信息
- `original.txt` - 纯文本原文（每行一个文本框）

**使用场景**：
- 需要手动翻译
- 需要校对原文
- 批量提取文本

**API 端点**：
```python
POST /translate/export/original          # 普通版本
POST /translate/export/original/stream   # 流式版本（支持进度）
```

**示例**：
```python
with open('manga.jpg', 'rb') as f:
    files = {'image': f}
    response = requests.post('http://localhost:8000/translate/export/original', files=files)
    with open('original_export.zip', 'wb') as out:
        out.write(response.content)
```

#### 导出译文
执行完整翻译，并导出 JSON 和 TXT 文件。

**流程**：
```
输入图片 → 完整翻译流程 → 生成 ZIP（JSON + TXT）
```

**返回内容**：
- `translation.json` - 包含原文、译文、位置信息
- `translated.txt` - 纯文本译文

**使用场景**：
- 需要保存翻译数据用于后续编辑
- 需要导出译文文本
- 需要重新渲染

**API 端点**：
```python
POST /translate/export/translated          # 普通版本
POST /translate/export/translated/stream   # 流式版本（支持进度）
```

**示例**：
```python
with open('manga.jpg', 'rb') as f:
    files = {'image': f}
    response = requests.post('http://localhost:8000/translate/export/translated', files=files)
    with open('translated_export.zip', 'wb') as out:
        out.write(response.content)
```

### 导入端点

#### 导入 JSON
从 JSON 文件加载翻译数据，跳过检测、OCR、翻译步骤，直接渲染。

**流程**：
```
输入图片 + JSON文件 → 从JSON加载文本框和翻译 → 图片修复 → 文字渲染 → 输出图片
```

**使用场景**：
- 手动编辑了 JSON 中的翻译后重新渲染
- 更换字体或渲染参数后重新渲染
- 使用不同的翻译版本

**API 端点**：
```python
POST /translate/import/json          # 普通版本
POST /translate/import/json/stream   # 流式版本（支持进度）
```

#### 导入 TXT
从 TXT 文件导入翻译，支持模板解析和模糊匹配。

**流程**：
```
输入图片 + TXT + JSON → 将TXT合并到JSON → 图片修复 → 文字渲染 → 输出图片
```

**使用场景**：
- 手动翻译后导入
- 使用外部翻译工具的结果
- 批量导入翻译

**API 端点**：
```python
POST /translate/import/txt          # 普通版本
POST /translate/import/txt/stream   # 流式版本（支持进度）
```

### 处理端点

#### 仅超分
只执行图片超分辨率，不进行翻译。

**流程**：
```
输入图片 → 超分辨率处理 → 输出高清图片
```

**使用场景**：
- 提升图片质量
- 放大图片
- 图片增强

**API 端点**：
```python
POST /translate/upscale          # 普通版本
POST /translate/upscale/stream   # 流式版本（支持进度）
```

**示例**：
```python
with open('manga.jpg', 'rb') as f:
    files = {'image': f}
    data = {'config': json.dumps({'upscale': {'upscaler': 'waifu2x', 'upscale_ratio': 2}})}
    response = requests.post('http://localhost:8000/translate/upscale', files=files, data=data)
    with open('upscaled.png', 'wb') as out:
        out.write(response.content)
```

#### 仅上色
只执行黑白图片上色，不进行翻译。

**流程**：
```
输入黑白图片 → AI上色 → 输出彩色图片
```

**使用场景**：
- 为黑白漫画上色
- 老照片上色

**API 端点**：
```python
POST /translate/colorize          # 普通版本
POST /translate/colorize/stream   # 流式版本（支持进度）
```

**示例**：
```python
with open('manga.jpg', 'rb') as f:
    files = {'image': f}
    data = {'config': json.dumps({'colorizer': {'colorizer': 'mc2'}})}
    response = requests.post('http://localhost:8000/translate/colorize', files=files, data=data)
    with open('colorized.png', 'wb') as out:
        out.write(response.content)
```

### TXT 导入端点说明

`/translate/import/txt` 端点使用与 UI 相同的导入逻辑，支持：

1. **模板解析** - 支持带格式的 TXT 文件
2. **模糊匹配** - 通过原文匹配，即使有细微差异也能匹配
3. **自定义模板** - 可以指定自定义模板文件

**参数**：
- `image` - 原始图片文件
- `txt_file` - TXT 翻译文件
- `json_file` - JSON 文件（包含文本框位置和原文）
- `config` - 配置 JSON 字符串（可选）
- `template` - 模板文件（可选，不提供则使用默认模板）

**默认模板格式**：
```
原文: <original>
译文: <translated>
```

**TXT 文件格式示例**：
```
原文: こんにちは
译文: 你好

原文: ありがとう
译文: 谢谢
```

**或简单格式**（每行一个翻译，按顺序匹配）：
```
你好
谢谢
```

### 手动翻译工作流示例

完整的手动翻译流程：

```python
import requests

# 步骤1：导出原文
with open('manga.jpg', 'rb') as f:
    files = {'image': f}
    response = requests.post('http://localhost:8000/translate/export/original',
                            files=files)
    with open('export.zip', 'wb') as out:
        out.write(response.content)

# 步骤2：解压 export.zip，得到 translation.json 和 original.txt

# 步骤3：手动翻译 original.txt，保存为 translated.txt
# 可以保持原有格式，或使用简单格式（每行一个翻译）

# 步骤4：导入翻译并渲染
with open('manga.jpg', 'rb') as img, \
     open('translated.txt', 'rb') as txt, \
     open('translation.json', 'rb') as json_file:
    files = {
        'image': img,
        'txt_file': txt,
        'json_file': json_file
    }
    # 可选：提供自定义模板
    # with open('my_template.txt', 'rb') as template:
    #     files['template'] = template
    
    response = requests.post('http://localhost:8000/translate/import/txt',
                            files=files)
    with open('result.png', 'wb') as out:
        out.write(response.content)
```

**导入逻辑说明**：
1. API 使用与 UI 相同的 `safe_update_large_json_from_text` 函数
2. 通过原文（`text` 字段）匹配对应的文本框
3. 支持模糊匹配（标准化后匹配）
4. 更新 `translation` 字段

### 临时文件清理

流式端点（`/stream`）会在 `result` 目录中生成临时文件。为了避免磁盘空间占用，建议定期清理。

**清理端点**：
```python
POST /cleanup/temp?max_age_hours=24
```

**参数**：
- `max_age_hours` - 清理多少小时前的临时文件（默认：24小时）

**返回示例**：
```json
{
  "deleted": 15,
  "message": "Successfully cleaned up 15 temporary files older than 24 hours"
}
```

**使用示例**：
```python
import requests

# 清理24小时前的临时文件（默认）
response = requests.post('http://localhost:8000/cleanup/temp')
result = response.json()
print(f"已清理 {result['deleted']} 个临时文件")

# 清理1小时前的临时文件
response = requests.post('http://localhost:8000/cleanup/temp?max_age_hours=1')
result = response.json()
print(f"已清理 {result['deleted']} 个临时文件")
```

**建议**：
- 在生产环境中，建议使用定时任务（如 cron）定期调用清理端点
- 开发环境可以设置较短的清理时间（如 1 小时）
- 生产环境建议设置较长的清理时间（如 24-48 小时）

**注意**：
- 只会清理 `result` 目录中以 `temp_` 开头的文件和文件夹
- 正在使用的文件会被跳过（Windows 文件锁定）
- 清理操作是安全的，不会影响正在进行的翻译任务
- `DELETE /results/clear` - 清空所有结果目录

**支持的工作流程**：
- `normal` - 正常翻译（默认）
- `export_original` - 导出原文（只检测和 OCR，生成 JSON + TXT 文件）
- `save_json` - 保存 JSON（正常翻译 + 保存 JSON + TXT 文件）
- `load_text` - 导入翻译并渲染（从 JSON 文件加载翻译）
- `upscale_only` - 仅超分
- `colorize_only` - 仅上色

**文件生成位置**：
- JSON 文件：`manga_translator_work/json/图片名_translations.json`
- 原文 TXT：`manga_translator_work/originals/图片名_original.txt`
- 翻译 TXT：`manga_translator_work/translations/图片名_translated.txt`
- 翻译结果：`manga_translator_work/result/图片名.png`（开启 `--save-to-source-dir` 时）

**工作流程说明**：
1. `export_original` - 导出原文用于手动翻译
   - 生成 JSON 文件（包含原文和文本框信息）
   - 生成 TXT 文件（纯文本原文）
   - 可以编辑 TXT 文件进行手动翻译

2. `save_json` - 保存翻译结果
   - 生成 JSON 文件（包含翻译和文本框信息）
   - 生成 TXT 文件（纯文本翻译）
   - 用于后续编辑或重新渲染

3. `load_text` - 导入翻译并渲染
   - 从 JSON 文件加载翻译
   - 重新渲染图片
   - 用于手动翻译后的渲染

**流式响应格式**：
```
[1字节状态码][4字节数据长度][N字节数据]

状态码：
- 0: 结果数据（图片）
- 1: 进度更新
- 2: 错误信息
- 3: 队列位置
- 4: 等待翻译实例
```

**使用示例**：

```python
import requests
import io

# 方式1：正常翻译
with open('manga.jpg', 'rb') as f:
    files = {'image': f}
    data = {'config': '{}'}  # JSON 配置
    response = requests.post('http://localhost:8000/translate/with-form/image', 
                            files=files, data=data)
    
    # 保存结果
    with open('result.png', 'wb') as out:
        out.write(response.content)

# 方式2：翻译并返回 JSON（更快，跳过渲染）
with open('manga.jpg', 'rb') as f:
    files = {'image': f}
    data = {'config': '{}'}
    response = requests.post('http://localhost:8000/translate/with-form/json',
                            files=files, data=data)
    
    # 获取 JSON 结果
    result = response.json()
    print(f"成功: {result['success']}")
    print(f"文本区域数量: {len(result['text_regions'])}")
    for region in result['text_regions']:
        print(f"原文: {region['text']}")
        print(f"译文: {region['translation']}")

# 方式3：导出原文（只检测和 OCR，返回 ZIP：JSON + TXT）
with open('manga.jpg', 'rb') as f:
    files = {'image': f}
    response = requests.post('http://localhost:8000/translate/export/original',
                            files=files)
    
    # 保存 ZIP 文件
    with open('original_export.zip', 'wb') as out:
        out.write(response.content)
    
    # ZIP 包含：translation.json 和 original.txt

# 方式5：仅超分
with open('manga.jpg', 'rb') as f:
    files = {'image': f}
    data = {
        'config': json.dumps({'upscale': {'upscaler': 'waifu2x', 'upscale_ratio': 2}})
    }
    response = requests.post('http://localhost:8000/translate/upscale',
                            files=files, data=data)
    
    with open('upscaled.png', 'wb') as out:
        out.write(response.content)

# 方式6：流式翻译（支持进度）
with open('manga.jpg', 'rb') as f:
    files = {'image': f}
    data = {'config': '{}'}
    response = requests.post('http://localhost:8000/translate/with-form/image/stream',
                            files=files, data=data, stream=True)
    
    # 解析流式响应
    buffer = io.BytesIO(response.content)
    while True:
        status_byte = buffer.read(1)
        if not status_byte:
            break
        status = int.from_bytes(status_byte, 'big')
        size = int.from_bytes(buffer.read(4), 'big')
        data = buffer.read(size)
        
        if status == 0:  # 结果数据
            with open('result.png', 'wb') as out:
                out.write(data)
        elif status == 1:  # 进度更新
            print(f"进度: {data.decode('utf-8')}")
        elif status == 2:  # 错误
            print(f"错误: {data.decode('utf-8')}")
```

**使用场景**：
- 提供 HTTP API 服务
- 集成到其他应用
- 远程翻译服务
- 需要任务队列管理
- 需要负载均衡

### 模型内存管理

`--models-ttl` 参数控制模型在内存中的保留时间，用于优化内存使用：

```bash
# 模型永远保留在内存中（默认，适合高频使用）
python -m manga_translator web --models-ttl 0

# 模型在最后一次使用后 5 分钟后卸载（适合低频使用）
python -m manga_translator web --models-ttl 300

# 模型在最后一次使用后 30 分钟后卸载
python -m manga_translator web --models-ttl 1800
```

**使用建议**：
- **高频使用**（如生产环境）：设置为 `0`（永远保留），避免重复加载模型
- **低频使用**（如个人服务器）：设置为 `300-1800` 秒，节省内存
- **内存受限**：设置较短的时间（如 `300` 秒），及时释放内存

**注意**：
- 模型卸载后，下次请求会重新加载，可能需要几秒到几十秒
- 该参数同样适用于 `ws` 和 `shared` 模式

### 重试次数控制

`--retry-attempts` 参数控制翻译失败时的重试行为：

```bash
# 不指定（使用 API 传入的 config.translator.attempts）
python -m manga_translator web

# 强制无限重试（忽略 API 配置）
python -m manga_translator web --retry-attempts -1

# 强制最多重试 3 次（忽略 API 配置）
python -m manga_translator web --retry-attempts 3

# 强制不重试（忽略 API 配置）
python -m manga_translator web --retry-attempts 0
```

**优先级**：
1. **命令行 `--retry-attempts`**（如果指定）：最高优先级，会覆盖 API 传入的配置
2. **API 传入的 `config.translator.attempts`**：次优先级
3. **默认值 -1**（无限重试）：最低优先级

**使用建议**：
- **生产环境**：建议设置为固定值（如 `3`），避免无限重试导致资源浪费
- **开发测试**：可以使用默认值（`None`），允许 API 灵活控制
- **稳定性优先**：设置为 `-1`（无限重试），确保翻译最终成功

### WebSocket 模式和 Shared 模式

这两种模式也支持 `--models-ttl` 和 `--retry-attempts` 参数：

```bash
# WebSocket 模式
python -m manga_translator ws --models-ttl 300 --retry-attempts 3

# Shared 模式（API 实例）
python -m manga_translator shared --models-ttl 300 --retry-attempts 3
```

**参数说明**：
- `--nonce` - 用于保护内部通信的 Nonce
- `--models-ttl` - 模型在内存中的保留时间（秒，0 表示永远）
- `--retry-attempts` - 翻译失败时的重试次数（-1 表示无限重试，None 表示使用 API 传入的配置）

**使用场景**：
- 作为 Web 服务器的后端翻译实例
- 提供 HTTP API 服务

---

## CLI 参数说明

配置文件中的 `cli` 部分包含以下参数：

### 工作流程参数（仅命令行）
- `load_text` - 导入翻译并渲染
- `template` - 导出原文（生成 JSON 模板）
- `generate_and_export` - 导出翻译（翻译后导出到 TXT）
- `upscale_only` - 仅超分
- `colorize_only` - 仅上色

### 运行参数（仅命令行）
- `use_gpu` - 使用 GPU 加速
- `retry_attempts` - 翻译失败重试次数

> ⚠️ **重要**：这些参数**仅在命令行模式下有效**。在 API 模式下，这些设置会被**自动忽略**：
> - 工作流程由 API 端点控制
> - GPU 设置由服务器启动参数（`--use-gpu`）控制
> - 重试次数使用默认值

---

## 用户认证与权限系统

Web 模式支持完整的用户认证和权限管理系统。

### 初始设置

首次启动服务器时，需要创建管理员账户：

```bash
# 方式1：通过环境变量自动设置
set MANGA_TRANSLATOR_ADMIN_PASSWORD=your_password_here
python -m manga_translator web

# 方式2：通过 Web 界面设置
# 访问 http://127.0.0.1:8000/admin 进行初始设置

# 方式3：通过 API 设置
curl -X POST http://127.0.0.1:8000/auth/setup \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}'
```

### 用户登录

```python
import requests

# 登录获取 token
response = requests.post('http://localhost:8000/auth/login', json={
    'username': 'your_username',
    'password': 'your_password'
})
data = response.json()
token = data['token']

# 后续请求携带 token
headers = {'X-Session-Token': token}
response = requests.get('http://localhost:8000/api/history', headers=headers)
```

### 用户组与权限

系统支持基于用户组的权限管理：

- **admin** - 管理员组，拥有所有权限
- **default** - 默认用户组
- **guest** - 访客组（受限权限）

**权限类型**：
- `allowed_translators` - 允许使用的翻译器（白名单）
- `denied_translators` - 禁止使用的翻译器（黑名单）
- `allowed_workflows` - 允许使用的工作流
- `allowed_parameters` - 允许调整的参数
- `max_concurrent_tasks` - 最大并发任务数
- `daily_quota` - 每日翻译配额（-1 表示无限制）
- `can_upload_files` - 是否可以上传文件
- `can_delete_files` - 是否可以删除文件

### 配额管理

```python
# 获取当前用户配额
response = requests.get('http://localhost:8000/api/quota/stats', headers=headers)
quota = response.json()
print(f"今日已用: {quota['used_today']}/{quota['daily_limit']}")
```

### 历史记录管理

```python
# 获取翻译历史
response = requests.get('http://localhost:8000/api/history', headers=headers)
history = response.json()

# 下载历史记录
response = requests.get(
    f'http://localhost:8000/api/history/{session_token}/download',
    headers=headers
)
with open('history.zip', 'wb') as f:
    f.write(response.content)
```

---

## 常见问题

### Q: 如何查看所有可用参数？

```bash
python -m manga_translator --help
```

### Q: 配置文件在哪里？

默认位置：`examples/config.json`

如果不存在，会使用 `examples/config-example.json`

### Q: 如何修改翻译器？

编辑 `examples/config.json`：

```json
{
  "translator": {
    "translator": "openai_hq",
    "target_lang": "CHS"
  }
}
```

或使用 Qt 界面修改配置。

### Q: 如何使用 CPU 模式？

编辑配置文件：

```json
{
  "cli": {
    "use_gpu": false
  }
}
```

### Q: 翻译速度慢怎么办？

1. 启用 GPU：在配置文件中设置 `cli.use_gpu: true`
2. 减小检测尺寸：配置文件中 `detector.detection_size: 1536`
3. 增加批量大小：配置文件中 `cli.batch_size: 3`

---

## 相关文档

- [安装指南](INSTALLATION.md)
- [使用教程](USAGE.md)
- [API 配置](API_CONFIG.md)
- [设置说明](SETTINGS.md)

---

**生成时间**: 2025-12-07
