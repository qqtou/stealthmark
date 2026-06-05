# StealthMark

> ⚠️ **AI-Generated Project** — 本项目由 AI（Claude / OpenClaw）参与设计与实现。

隐形数字水印工具。为 PDFs、Word、PowerPoint、图片、音视频添加人不可见的隐形水印，用于版权保护、溯源、文件鉴权。

## 功能特点

- **多格式支持**：31种文档、图片、音频、视频格式
- **隐形嵌入**：水印对用户不可见，不影响原文件内容
- **完整生命周期**：嵌入 → 提取 → 验证
- **可选加密**：支持 AES-256 加密水印内容
- **完整性校验**：CRC32 校验确保数据完整
- **三种使用方式**：CLI / GUI / Web API

## 支持格式

| 类型 | 格式 | 技术方案 |
|------|------|---------|
| 文档 | `.pdf` | PDF元数据嵌入 |
| 文档 | `.docx` | 零宽字符隐写 |
| 文档 | `.pptx` | 隐藏形状标记 |
| 文档 | `.xlsx` | 自定义XML属性 |
| 文档 | `.odt` / `.ods` / `.odp` | ODF元数据 |
| 文档 | `.epub` | OPF dc:identifier |
| 文档 | `.rtf` | 可忽略控制组 |
| 图片 | `.png` / `.bmp` | LSB隐写（3倍冗余） |
| 图片 | `.jpg` / `.jpeg` | DCT域水印 |
| 图片 | `.tiff` | LSB隐写 |
| 图片 | `.webp` | LSB隐写（无损） |
| 图片 | `.gif` | Comment Extension |
| 图片 | `.heic` | EXIF UserComment |
| 音频 | `.wav` | 扩频水印（自适应alpha） |
| 音频 | `.mp3` / `.flac` / `.m4a` | 扩频水印 |
| 音频 | `.aac` | 扩频水印（输出 `.m4a`，ALAC 无损需 M4A 容器） |
| 音频 | `.ogg` | mutagen 元数据 |
| 视频 | `.mp4` / `.mov` | RGB Blue通道LSB + libx264rgb 无损 |
| 视频 | `.avi` / `.mkv` | RGB Blue通道LSB + FFV1 无损 |
| 视频 | `.webm` | RGB Blue通道LSB + VP9 无损 |
| 视频 | `.wmv` | RGB Blue通道LSB |

## 安装

```bash
# 克隆项目
git clone https://github.com/qqtou/stealthmark.git
cd stealthmark

# 安装（可编辑模式）
pip install -e .
```

依赖：
- PyPDF2, python-docx, python-pptx, openpyxl
- Pillow, opencv-python, numpy
- librosa, soundfile, imageio-ffmpeg, mutagen
- cryptography, colorama, tqdm
- 可选：PyQt6（GUI）, FastAPI + uvicorn（Web API）

## 快速开始

### Python API

```python
from stealthmark import StealthMark

# 初始化（可选传入 password 启用 AES-256 加密）
sm = StealthMark()

# 嵌入水印
result = sm.embed("document.pdf", "版权所有 2026", "output.pdf")
print(f"嵌入结果: {result.is_success}")

# 提取水印
result = sm.extract("output.pdf")
print(f"水印内容: {result.watermark.content}")

# 验证水印
result = sm.verify("output.pdf", "版权所有 2026")
print(f"验证结果: {result.is_valid}")

# 加密模式
sm_secure = StealthMark(password="secret123")
result = sm_secure.embed("doc.pdf", "机密", "secure.pdf")
```

## 水印容量与限制

| 格式类型 | 最大水印长度 | 典型限制 |
|----------|-------------|----------|
| 文档（PDF/DOCX/PPTX） | ~1000 字符 | PDF 元数据可能被工具清理 |
| 文档（XLSX/ODF/EPUB） | ~500 字符 | 编辑器保留元数据 |
| 图片（PNG/BMP） | ~1000 字符 | LSB 对压缩/缩放敏感 |
| 图片（JPEG） | ~500 字符 | DCT 抗压缩有限 |
| 音频（WAV/FLAC） | ~50 字符 | 依赖音频时长 |
| 音频（MP3/AAC） | ~30 字符 | 有损编码影响精度 |
| 视频（MP4/MOV/AVI） | ~100 字符 | 需无损编码 |


**通用限制**：
- 水印文本最长 1024 字符
- 加密模式下所有 Handler 统一使用 AES-256-CBC
- 有损格式（MP3/OGG/HEIC）提取失败为预期行为
- 视频仅修改第一帧，避免多帧分散导致字节对齐问题

## 命令行

```bash
# 嵌入水印
python -m stealthmark embed document.pdf "水印内容" -o output.pdf

# 提取水印
python -m stealthmark extract document.pdf

# 验证水印
python -m stealthmark verify document.pdf "水印内容"

# 查看支持的格式
python -m stealthmark info

# 批量处理
python -m stealthmark batch embed ./input_dir -o ./output_dir --watermark "水印"
python -m stealthmark batch embed ./input_dir --include .pdf .docx --workers 4
python -m stealthmark batch embed ./input_dir --dry-run

# 输出控制
python -m stealthmark embed file.pdf "wm" -v    # 详细日志
python -m stealthmark embed file.pdf "wm" -q    # 静默模式
python -m stealthmark embed file.pdf "wm" -f    # 强制覆盖
```

## GUI 图形界面

需要 PyQt6：`pip install PyQt6`

```bash
python -m stealthmark.gui
```

功能：文件/文件夹选择 + 拖放、嵌入/提取/验证三种模式、批量处理 + 进度条、结果表格、可选加密、自定义输出命名

## Web API

需要 FastAPI + Uvicorn：`pip install fastapi uvicorn`

```bash
# 从项目根目录启动
cd D:\work\code\stealthmark
uvicorn src.stealthmark.api:app --reload --port 8000
```

交互式文档（Swagger UI）：http://localhost:8000/docs  
ReDoc 文档：http://localhost:8000/redoc

### 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 首页（API 信息） |
| `/health` | GET | 健康检查，返回 handlers 数量 |
| `/info` | GET | 支持格式列表（按 document/image/audio/video 分组） |
| `/embed` | POST | 嵌入水印（multipart/form-data） |
| `/extract` | POST | 提取水印 |
| `/verify` | POST | 验证水印 |
| `/batch` | POST | 批量处理（支持 embed/extract/verify） |

### 请求格式

所有 POST 端点接受 `multipart/form-data`：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` / `files` | File | 是 | 输入文件 |
| `watermark` | string | embed/verify 必填 | 水印文本 |
| `password` | string | 否 | 加密密码 |
| `action` | string | batch 必填 | `embed`\|`extract`\|`verify` |

### 示例

**启动服务**
```bash
cd D:\work\code\stealthmark
uvicorn src.stealthmark.api:app --reload --port 8000
```

**查看支持的格式**
```bash
curl http://localhost:8000/info
```

**嵌入水印**
```bash
curl -X POST http://localhost:8000/embed \
  -F "file=@document.pdf" \
  -F "watermark=版权所有 2026"
```

**提取水印**
```bash
curl -X POST http://localhost:8000/extract \
  -F "file=@output.pdf"
```

**验证水印**
```bash
curl -X POST http://localhost:8000/verify \
  -F "file=@output.pdf" \
  -F "watermark=版权所有 2026"
```

**批量嵌入**
```bash
curl -X POST http://localhost:8000/batch \
  -F "files=@file1.pdf" \
  -F "files=@file2.png" \
  -F "watermark=版权所有 2026" \
  -F "action=embed"
```

## 水印内容格式

StealthMark 支持通用水印内容格式，适用于版权保护、来源溯源、品牌保护等多种场景。

### 格式规范

```json
{
  "v": 1,
  "type": "copyright",
  "issuer": "did:example:123abc",
  "timestamp": "2026-05-05T10:34:00Z",
  "payload": "任意内容",
  "nonce": "a1b2c3d4"
}
```

### 字段定义

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `v` | int | 是 | 格式版本号，当前为 `1` |
| `type` | string | 是 | 水印类型，见下表 |
| `issuer` | string | 是 | 签发者标识（DID/URI/UUID） |
| `timestamp` | string | 是 | ISO 8601 时间戳 |
| `payload` | string | 否 | 自定义内容 |
| `nonce` | string | 是 | 随机数（防重放，8-16字节hex） |

### 水印类型

| type | 用途 |
|------|------|
| `copyright` | 版权声明 |
| `provenance` | 来源溯源 |
| `watermark` | 通用水印 |
| `brand` | 品牌保护 |
| `tracking` | 泄露追踪 |

### 使用示例

**版权保护场景**

```json
{
  "v": 1,
  "type": "copyright",
  "issuer": "did:web:copyright.example.com",
  "timestamp": "2026-05-05T10:34:00Z",
  "payload": "work_id:ABC123",
  "nonce": "f3e2d1c0"
}
```

**个人水印**

```json
{
  "v": 1,
  "type": "watermark",
  "issuer": "did:key:z6MkhaXgPB...",
  "timestamp": "2026-05-05T10:34:00Z",
  "nonce": "12345678"
}
```

**品牌保护**

```json
{
  "v": 1,
  "type": "brand",
  "issuer": "https://brand.example.com",
  "timestamp": "2026-05-05T10:34:00Z",
  "payload": "official",
  "nonce": "abcdef12"
}
```

### 设计原则

1. **通用性**：不绑定特定业务，`payload` 可放任意内容
2. **可扩展**：`v` 字段支持未来版本演进
3. **简洁性**：核心字段仅6个，控制在100字节内
4. **标准化**：时间戳用 ISO 8601，标识符用 DID/URI

### JSON Schema 验证

水印格式定义见 `schemas/watermark.schema.json`，可用于：

**Python 验证**

```python
import json
from jsonschema import validate, ValidationError

with open('schemas/watermark.schema.json') as f:
    schema = json.load(f)

watermark = {"v": 1, "type": "copyright", ...}
try:
    validate(instance=watermark, schema=schema)
    print("格式有效")
except ValidationError as e:
    print(f"格式错误: {e.message}")
```

**命令行验证**

```bash
# 安装 jsonschema CLI
pip install jsonschema[format]

# 验证水印 JSON 文件
jsonschema -i watermark.json schemas/watermark.schema.json
```

**约束检查**

| 字段 | 约束 |
|------|------|
| `v` | 1-99 |
| `type` | 必须为5种类型之一 |
| `issuer` | DID/URI/UUID格式，最长256字符 |
| `timestamp` | ISO 8601格式 |
| `payload` | 字符串最长1024字符 |
| `nonce` | 16-32字符hex（8-16字节） |

## 水印格式

编码流程：原文 → UTF-8 → CRC32 → 格式封装

```
[SMARK 5字节][版本 1字节][长度 4字节][内容 N字节][CRC32 4字节]
```

可选加密：AES-256-CBC（设置password参数启用）

## 注意事项

- **JPEG**：有损压缩，可能影响水印提取
- **DOCX**：另存为 .doc 可能丢失零宽字符
- **PNG/BMP**：LSB 对压缩敏感
- **音频/视频**：处理时间随文件长度增加
- **PDF**：元数据可能被专业工具清理
- **视频**：输出为无损编码，文件较大；有损转码会破坏水印
- **AAC**：输出为 `.m4a` 格式（ALAC 无损编码需 M4A 容器，无法写入原生 `.aac`）
- **有损格式**：MP3/OGG/HEIC等有损格式水印提取失败为预期行为

## 项目结构

```
stealthmark/
├── src/stealthmark/       # 核心源码（标准src布局）
│   ├── core/              # 基类、编解码、管理器
│   ├── document/          # 9个文档Handler
│   ├── image/             # 7个图片Handler
│   ├── media/             # 8个音视频Handler
│   ├── cli.py             # 命令行
│   ├── api.py             # Web API
│   ├── gui.py             # GUI
│   └── static/            # Web静态资源
│       ├── test.html      # 测试前端页面
│       └── file/          # 文件存储目录
│           └── YYYY/M/    # 按年月归档
├── tests/                 # 单元测试 + 集成测试 + 测试数据
├── skills/stealthmark/    # OpenClaw Skill
├── docs/                  # 设计文档
├── pyproject.toml         # 项目配置
└── README.md
```

## 许可证

MIT License