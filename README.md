# StealthMark

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
| 音频 | `.aac` | 扩频水印（输出M4A） |
| 音频 | `.ogg` | mutagen元数据 |
| 视频 | `.mp4` / `.mov` | RGB Blue通道LSB + libx264rgb无损 |
| 视频 | `.avi` / `.mkv` | RGB Blue通道LSB + FFV1无损 |
| 视频 | `.webm` | RGB Blue通道LSB + VP9无损 |
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

```python
from stealthmark import StealthMark

# 初始化
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
```

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
uvicorn stealthmark.api:app --reload --port 8000
```

交互式文档：http://localhost:8000/docs

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/info` | GET | 支持格式列表 |
| `/embed` | POST | 嵌入水印（multipart/form-data） |
| `/extract` | POST | 提取水印 |
| `/verify` | POST | 验证水印 |
| `/batch` | POST | 批量处理 |
| `/test` | GET | 测试前端页面 |

```bash
# 嵌入水印
curl -X POST http://localhost:8000/embed \
  -F "file=@document.pdf" \
  -F "watermark=版权所有 2026"

# 验证水印
curl -X POST http://localhost:8000/verify \
  -F "file=@output.pdf" \
  -F "watermark=版权所有 2026"
```

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
- **AAC**：输出为 .m4a 格式（ALAC无损需M4A容器）
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
│   └── gui.py             # GUI
├── tests/                 # 单元测试 + 集成测试 + 测试数据
├── skills/stealthmark/    # OpenClaw Skill
├── docs/                  # 设计文档
├── pyproject.toml         # 项目配置
└── README.md
```

## 许可证

MIT License
