# StealthMark 隐式水印系统设计方案

## 1. 项目概述

**项目名称**: StealthMark
**项目定位**: 跨格式隐形数字水印工具
**核心功能**: 为31种文档、图片、音频、视频文件添加不可见的数字水印，支持水印提取与验证
**使用方式**: CLI / GUI / Web API

---

## 2. 整体架构

### 2.1 核心流程

```
┌─────────────────────────────────────────────────────────────────┐
│                          水印嵌入流程                            │
│  输入文件 ──▶ 水印编码(CRC32+Base64) ──▶ 嵌入算法 ──▶ 输出文件  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                          水印提取流程                            │
│  含水印文件 ──▶ 提取算法 ──▶ 水印解码 ──▶ 水印内容              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                          水印验证流程                            │
│  提取内容 vs 原始水印 ──▶ CRC校验 ──▶ 一致性比对 ──▶ 结果      │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 模块架构

```
stealthmark/
├── src/stealthmark/                # 标准src布局
│   ├── __init__.py                 # 包入口，导出StealthMark
│   ├── __main__.py                 # python -m stealthmark 入口
│   ├── cli.py                      # CLI（argparse，5个子命令）
│   ├── api.py                      # FastAPI Web API
│   ├── gui.py                      # PyQt6 GUI
│   ├── _logging.py                 # 日志模块
│   ├── core/                       # 核心模块
│   │   ├── base.py                 # 基类、结果数据类
│   │   ├── codec.py                # 编解码（CRC32+Base64+AES-256）
│   │   ├── manager.py              # 门面类（StealthMark主入口，24个Handler）
│   │   └── exceptions.py           # 异常类
│   ├── document/                   # 文档水印（9个Handler）
│   │   ├── pdf_watermark.py        # PDF元数据
│   │   ├── docx_watermark.py       # DOCX零宽字符
│   │   ├── pptx_watermark.py       # PPTX隐藏形状
│   │   ├── xlsx_watermark.py       # XLSX customXml
│   │   ├── odt_watermark.py        # ODT ODF元数据
│   │   ├── ods_watermark.py        # ODS ODF元数据
│   │   ├── odp_watermark.py        # ODP ODF元数据
│   │   ├── epub_watermark.py       # EPUB OPF
│   │   └── rtf_watermark.py        # RTF可忽略控制组
│   ├── image/                      # 图片水印（7个Handler）
│   │   ├── image_watermark.py      # PNG/BMP/JPEG（LSB+DCT）
│   │   ├── tiff_webp_gif_watermark.py  # TIFF/WebP/GIF
│   │   └── heic_handler.py         # HEIC EXIF
│   ├── media/                      # 音视频水印（8个Handler）
│   │   ├── audio_watermark.py      # WAV/MP3扩频水印
│   │   ├── flac_handler.py         # FLAC扩频
│   │   ├── aac_handler.py          # AAC/M4A扩频（输出M4A）
│   │   ├── ogg_handler.py          # OGG元数据
│   │   ├── video_watermark.py      # MP4/AVI/MKV/MOV RGB Blue LSB
│   │   ├── webm_handler.py         # WebM VP9无损
│   │   └── wmv_handler.py          # WMV RGB Blue LSB
│   ├── utils/                      # 工具函数
│   │   └── helpers.py
│   └── static/                     # Web测试前端
│       └── test.html
├── tests/
│   ├── unit/                       # 单元测试（28个文件）
│   ├── scripts/                    # 集成测试脚本
│   └── fixtures/                   # 测试数据（30种格式）
├── skills/stealthmark/             # OpenClaw Skill
│   ├── SKILL.md
│   ├── scripts/                    # embed/extract/verify/batch.py
│   ├── references/                 # formats/algorithms/cli-reference.md
│   └── assets/
├── docs/                           # 设计文档
├── pyproject.toml                  # 项目配置（替代setup.py）
├── requirements.txt
└── README.md
```

---

## 3. 水印编码方案

### 3.1 编码格式

```
[SMARK 5字节][版本 1字节][长度 4字节][内容 N字节][CRC32 4字节]
```

### 3.2 可选加密

AES-256-CBC + PBKDF2-HMAC-SHA256密钥派生（100000迭代）

---

## 4. 各格式水印方案

### 4.1 文档类

| 格式 | 方案 | 关键实现 |
|------|------|---------|
| PDF | 元数据Author字段 | Base64编码写入/SMMark字段 |
| DOCX | 零宽字符 | U+200B=0, U+200C=1，嵌入文本节点 |
| PPTX | 隐藏形状 | 透明不可见形状，名称含水印 |
| XLSX | customXml属性 | customXml/item1.xml中property |
| ODT/ODS/ODP | ODF user-defined | meta.xml中user-defined属性 |
| EPUB | OPF dc:identifier | content.opf中dc:identifier字段 |
| RTF | 可忽略控制组 | `{\*\stealthmark data}` |

### 4.2 图片类

| 格式 | 方案 | 关键实现 |
|------|------|---------|
| PNG/BMP | LSB 3倍冗余 | 每bit重复3次，多数投票提取，RGB三通道 |
| JPEG | DCT域水印 | 8×8分块DCT，修改中频系数 |
| TIFF/WebP | LSB隐写 | 仅限无损版本 |
| GIF | Comment Extension | GIF标准注释块 |
| HEIC | EXIF UserComment | pillow-heif库 |

### 4.3 音频类

| 格式 | 方案 | 关键实现 |
|------|------|---------|
| WAV | 扩频水印 | 自适应alpha（按音频段能量调整），BPS=100 |
| MP3 | 扩频水印 | 继承WAV，librosa读取/soundfile写入 |
| FLAC | 扩频水印 | 继承WAV |
| AAC/M4A | 扩频水印 | 继承WAV，输出为M4A容器（ALAC无损需M4A） |
| OGG | mutagen元数据 | OGG Vorbis COMMENT字段存储 |

### 4.4 视频类

| 格式 | 方案 | 关键实现 |
|------|------|---------|
| MP4/MOV | RGB Blue LSB | 第一帧Blue通道 + libx264rgb CRF0 |
| AVI/MKV | RGB Blue LSB | 第一帧Blue通道 + FFV1无损 |
| WebM | RGB Blue LSB | 第一帧Blue通道 + VP9无损 |
| WMV | RGB Blue LSB | 第一帧Blue通道 |

**视频水印关键决策**：仅修改第一帧Blue通道LSB，避免多帧分散导致的字节对齐问题。必须使用无损编码（有损编码会破坏LSB）。

---

## 5. 接口设计

### 5.1 CLI

```bash
python -m stealthmark embed <file> <watermark> [-o output] [-v] [-q] [-f]
python -m stealthmark extract <file> [-v] [-q]
python -m stealthmark verify <file> [watermark] [-v] [-q]
python -m stealthmark info
python -m stealthmark batch <embed|extract|verify> <dir> [options]
```

batch选项：`--name-pattern`, `--include`, `--exclude`, `--no-recursive`, `--dry-run`, `--workers N`

### 5.2 Python API

```python
from stealthmark import StealthMark

sm = StealthMark(password="optional")
result = sm.embed("doc.pdf", "watermark", "output.pdf")
result = sm.extract("output.pdf")
result = sm.verify("output.pdf", "watermark")
```

### 5.3 Web API

FastAPI，端口8000，文档 http://localhost:8000/docs

端点：/health, /info, /embed, /extract, /verify, /batch, /test

### 5.4 GUI

PyQt6，支持嵌入/提取/验证/批量，拖放+进度条+结果表格

---

## 6. 关键设计决策

| 决策 | 原因 |
|------|------|
| 视频单帧嵌入 | 多帧分散导致per_frame_bits不对齐字节边界，提取时字节错位 |
| AAC输出M4A | ALAC无损编码需要M4A容器，.aac不支持 |
| LSB 3倍冗余 | 单bit LSB易受噪声影响，3次重复+多数投票降低误码率 |
| WAV自适应alpha | 根据音频段能量调整嵌入强度，低能量弱嵌入（不可闻），高能量强嵌入（利用掩蔽效应） |
| OGG用元数据 | OGG有损编码不适合扩频水印，改用元数据存储 |
| src布局 | 标准Python包结构，`pip install -e .` 后可直接 `from stealthmark import StealthMark` |
| colorama | Windows终端GBK不支持特殊符号，用[OK]/[FAIL]替代✓/✗ |

---

## 7. 文件格式支持矩阵

| 格式 | 嵌入方案 | 提取 | 验证 | 备注 |
|------|----------|------|------|------|
| PDF | 元数据（Author字段，Base64） | ✓ | ✓ | 元数据可能被清理 |
| DOCX | 零宽字符 | ✓ | ✓ | 另存为.doc会丢失 |
| PPTX | 隐藏形状 | ✓ | ✓ | 编辑时注意保护 |
| XLSX | customXml属性 | ✓ | ✓ | 最稳定 |
| ODT/ODS/ODP | ODF user-defined | ✓ | ✓ | ODF标准兼容 |
| EPUB | OPF dc:identifier | ✓ | ✓ | 可被手动编辑 |
| RTF | 可忽略控制组 | ✓ | ✓ | 部分编辑器会清理 |
| PNG/BMP | LSB 3倍冗余 | ✓ | ✓ | 缩放/压缩破坏LSB |
| JPEG | DCT域 | ✓ | ✓ | 抗压缩有限 |
| TIFF/WebP | LSB隐写 | ✓ | ✓ | 仅无损版本 |
| GIF | Comment Extension | ✓ | ✓ | 仅支持静态GIF |
| HEIC | EXIF UserComment | ✓ | ✓ | 可选pillow-heif |
| WAV | 扩频（自适应alpha） | ✓ | ✓ | 无损，最稳定 |
| MP3 | 扩频 | ✓ | ✓ | 有损，可能影响精度 |
| FLAC | 扩频 | ✓ | ✓ | 无损 |
| AAC/M4A | 扩频（输出M4A） | ✓ | ✓ | ALAC需M4A容器 |
| OGG | mutagen元数据 | ✓ | ✓ | 有损格式，元数据方案 |
| MP4/MOV | RGB Blue LSB + libx264rgb | ✓ | ✓ | 必须无损编码 |
| AVI/MKV | RGB Blue LSB + FFV1 | ✓ | ✓ | 必须无损编码 |
| WebM | RGB Blue LSB + VP9无损 | ✓ | ✓ | 必须无损编码 |
| WMV | RGB Blue LSB | ✓ | ✓ | 必须无损编码 |

---

*文档版本: 2.0*
*最后更新: 2026-05-01*
