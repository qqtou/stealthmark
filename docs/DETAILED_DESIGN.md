# StealthMark 详细设计说明书

---

## 文档信息

| 属性 | 内容 |
|------|------|
| 项目名称 | StealthMark |
| 文档版本 | 2.0 |
| 关联文档 | SRS.md, DESIGN.md, API.md |
| 创建日期 | 2026-04-28 |
| 最后更新 | 2026-05-01 |

---

## 1. 系统架构

### 1.1 整体架构图

```
┌──────────────────────────────────────────────────────────────────────┐
│                            使用接口                                  │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │   CLI     │    │   Python API │    │   GUI (PyQt6) │              │
│  │  cli.py   │    │  StealthMark │    │   gui.py      │              │
│  └─────┬────┘    └──────┬───────┘    └──────┬───────┘              │
│        └────────────────┼───────────────────┘                       │
│                         ▼                                            │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                     StealthMark 核心引擎                     │    │
│  │  ┌───────────────┐  ┌───────────────┐  ┌──────────────┐   │    │
│  │  │  Manager      │  │    Codec      │  │  Exceptions  │   │    │
│  │  │ (24 Handlers) │  │ (CRC+Base64   │  │              │   │    │
│  │  │               │  │  +AES-256)    │  │              │   │    │
│  │  └───────┬───────┘  └───────────────┘  └──────────────┘   │    │
│  └──────────┼─────────────────────────────────────────────────┘    │
│             │                                                       │
│  ┌──────────┼─────────────────────────────────────────────────┐    │
│  │          ▼         Handler 分层                             │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │    │
│  │  │  Document    │  │    Image     │  │    Media     │    │    │
│  │  │  (9 handlers) │  │  (7 handlers)│  │  (8 handlers)│    │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘    │    │
│  └────────────────────────────────────────────────────────────┘    │
│                         ▼                                            │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    第三方依赖                                │    │
│  │  PyPDF2 | python-docx | python-pptx | openpyxl | Pillow    │    │
│  │  opencv-python | librosa | soundfile | mutagen | ffmpeg     │    │
│  └─────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.2 模块职责

| 模块 | 职责 | 关键文件 |
|------|------|---------|
| core/manager.py | 门面类，统一入口，注册和路由24个Handler | manager.py |
| core/codec.py | 水印编解码（CRC32+Base64+AES-256） | codec.py |
| core/base.py | 基类、结果数据类、状态枚举 | base.py |
| core/exceptions.py | 异常类定义 | exceptions.py |
| document/ | 9个文档Handler（PDF/DOCX/PPTX/XLSX/ODT/ODS/ODP/EPUB/RTF） | 9个文件 |
| image/ | 7个图片Handler（PNG/BMP/JPEG/TIFF/WebP/GIF/HEIC） | 3个文件 |
| media/ | 8个音视频Handler（WAV/MP3/FLAC/AAC/OGG/Video/WebM/WMV） | 7个文件 |
| cli.py | argparse命令行，5个子命令 | cli.py |
| api.py | FastAPI Web API，10个端点 | api.py |
| gui.py | PyQt6 GUI | gui.py |
| _logging.py | 日志模块 | _logging.py |

---

## 2. 水印编解码设计

### 2.1 编码格式

```
[SMARK 5B][VERSION 1B][LENGTH 4B][PAYLOAD NB][CRC32 4B]
```

- **SMARK**: 魔数 `b"SMARK"`，5字节，用于识别水印数据
- **VERSION**: 格式版本号，1字节，当前为1
- **LENGTH**: 载荷长度（大端序），4字节
- **PAYLOAD**: UTF-8编码的水印文本，N字节
- **CRC32**: 载荷的CRC32校验（大端序），4字节

### 2.2 可选加密

AES-256-CBC加密流程：

```
密码 → PBKDF2-HMAC-SHA256(100000次迭代, salt) → 32字节密钥
数据 → PKCS7填充 → AES-CBC加密(随机IV) → IV(16B) + 密文
```

### 2.3 有损格式宽松校验

MP3/HEIC/OGG等有损格式，CRC校验可能失败。宽松策略：只要魔术数`SMARK`匹配即接受提取结果。

---

## 3. Handler 详细设计

### 3.1 Handler 注册机制

```python
class StealthMark:
    def _register_builtin_handlers(self):
        # 24个Handler按类型分组注册
        # document: PDF, DOCX, PPTX, XLSX, ODT, ODS, ODP, EPUB, RTF
        # image: PNG, BMP, JPEG, TIFF, WebP, GIF, HEIC
        # media: WAV, MP3, FLAC, AAC, OGG, Video, WebM, WMV
        
        for handler_class in handler_classes:
            handler = handler_class()
            for ext in handler.SUPPORTED_EXTENSIONS:
                self._handlers[ext.lower()] = handler
```

文件扩展名 → Handler 映射，查找时取 `Path(file_path).suffix.lower()`。

### 3.2 文档 Handler 详细方案

#### PDFHandler (.pdf)

- **嵌入**: 将编码后数据Base64写入PDF元数据 `/SMMark` 字段
- **提取**: 读取 `/SMMark` 字段 → Base64解码 → codec.decode()
- **注意**: 元数据可能被PDF编辑器清理

#### DOCXHandler (.docx)

- **嵌入**: 将水印转为零宽字符序列（U+200B=0, U+200C=1），追加到文档文本节点
- **提取**: 解析document.xml → 遍历所有w:t元素 → 过滤零宽字符 → 二进制重组
- **注意**: 另存为.doc会丢失零宽字符

#### PPTXHandler (.pptx)

- **嵌入**: 创建不可见形状（hidden_前缀，透明填充），形状名称含水印数据
- **提取**: 遍历slide XML → 查找hidden_前缀形状 → 提取名称中的水印

#### XLSXHandler (.xlsx)

- **嵌入**: 将数据写入 customXml/item1.xml 的 property 属性
- **提取**: 解压ZIP → 读取 customXml/item1.xml → 解析属性

#### ODT/ODS/ODP (.odt/.ods/.odp)

- **嵌入**: 写入 meta.xml 的 user-defined 元数据属性
- **提取**: 解压ZIP → 读取 meta.xml → 解析 user-defined

#### EPUBHandler (.epub)

- **嵌入**: 写入 content.opf 的 dc:identifier 字段
- **提取**: 解压ZIP → 读取 content.opf → 解析 dc:identifier

#### RTFHandler (.rtf)

- **嵌入**: 插入 `{\*\stealthmark base64data}` 可忽略控制组
- **提取**: 正则匹配 `\stealthmark` 控制字 → 提取Base64数据

### 3.3 图片 Handler 详细方案

#### PNGHandler / BMPHandler (.png / .bmp)

- **嵌入**: LSB 3倍冗余 — 每个bit重复3次嵌入RGB三通道LSB，提取时多数投票
- **数据格式**: 4字节长度前缀 + codec编码数据
- **容量**: (宽 × 高 × 3 - 32) ÷ 8 字节

#### JPEGHandler (.jpg / .jpeg)

- **嵌入**: DCT域水印 — 8×8分块DCT，修改中频系数(2,3)编码0/1
- **提取**: DCT → 读取中频系数符号 → 重组
- **容量**: (宽/8 × 高/8 - 8) ÷ 8 字节

#### TIFFHandler / WebPHandler (.tiff / .webp)

- **嵌入**: LSB隐写（同PNG），仅限无损版本
- **提取**: 读取LSB → 重组

#### GIFHandler (.gif)

- **嵌入**: 写入GIF Comment Extension块 (`0x21 0xFE [len] [data]`)
- **提取**: 扫描GIF扩展块 → 读取Comment数据

#### HEICHandler (.heic)

- **嵌入**: 写入EXIF UserComment字段（pillow-heif库）
- **提取**: 读取EXIF UserComment

### 3.4 音频 Handler 详细方案

#### WAVHandler (.wav)

- **算法**: 扩频水印（Direct Sequence Spread Spectrum）
- **嵌入**:
  1. 编码水印为二进制流
  2. 每bit分配BPS=100个采样点
  3. 生成LCG伪随机PN序列
  4. 水印bit × PN序列 × alpha → 叠加到音频信号
  5. **自适应alpha**: 按音频段能量调整嵌入强度（低能量→弱，高能量→强）
- **提取**: 相关检测 — 计算信号与PN序列的相关值，>0→1, ≤0→0
- **容量**: 采样点数 ÷ 100 - 开销

#### MP3Handler / FLACHandler (.mp3 / .flac)

- **继承**: WAVHandler扩频方案
- **读取**: librosa.load() 解码为PCM
- **写入**: soundfile.write() 输出

#### AACHandler (.aac / .m4a)

- **继承**: WAVHandler扩频方案
- **关键**: 输出为M4A容器（ALAC无损编码需要M4A，.aac不支持ALAC）
- **API注意**: embed返回的output_path为.m4a而非.aac

#### OGGHandler (.ogg)

- **方案**: mutagen库读写OGG Vorbis COMMENT字段
- **原因**: OGG有损编码不适合扩频水印，改用元数据存储

### 3.5 视频 Handler 详细方案

#### VideoHandler (.mp4 / .avi / .mkv / .mov)

- **算法**: RGB Blue通道LSB
- **嵌入**:
  1. ffmpeg解码视频为RGB帧序列
  2. 仅修改**第一帧**的Blue通道LSB
  3. 同步头: 8个0xAA字节（原4个，后增强为8个）
  4. 数据: codec编码后的二进制流
  5. 无损编码输出:
     - MP4/MOV: libx264rgb CRF 0（RGB空间无损）
     - AVI/MKV: FFV1（纯无损）
- **提取**:
  1. ffmpeg解码为RGB帧
  2. 读取第一帧Blue通道LSB
  3. 搜索同步头0xAA×8
  4. 提取比特流 → codec.decode()
- **关键决策**: 单帧嵌入（避免多帧分散导致per_frame_bits不对齐字节边界）

**为什么不用libx264（YUV空间）**：YUV420转换会破坏Blue通道LSB数据。libx264rgb在RGB空间内编码，像素值精确保留。

#### WebMHandler (.webm)

- **同VideoHandler**，编码器改为VP9无损（`-lossless 1`）

#### WMVHandler (.wmv)

- **同VideoHandler**，编码器改为WMV默认编码

---

## 4. CLI 设计

### 4.1 命令结构

```
python -m stealthmark
├── embed <file> <watermark> [-o output] [-v] [-q] [-f]
├── extract <file> [-v] [-q]
├── verify <file> [watermark] [-v] [-q]
├── info
└── batch
    ├── embed <dir> [-o dir] [--watermark] [-n pattern]
    │           [--include] [--exclude] [--no-recursive]
    │           [--dry-run] [--workers N]
    ├── extract <dir> [options]
    └── verify <dir> [options]
```

### 4.2 输出格式

- 彩色输出: colorama（[OK]绿色 / [FAIL]红色 / [WARN]黄色）
- 进度条: tqdm
- GBK兼容: 不使用✓/✗等特殊符号

### 4.3 退出码

- 0: 全部成功
- 1: 有失败项

---

## 5. Web API 设计

### 5.1 技术栈

- FastAPI + uvicorn
- 静态文件服务: /test 测试前端

### 5.2 端点详细设计

| 端点 | 方法 | 输入 | 输出 |
|------|------|------|------|
| /health | GET | - | {status, handlers} |
| /info | GET | - | {document: [...], image: [...], ...} |
| /embed | POST | file + watermark + password? | {success, output_path} |
| /extract | POST | file + password? | {success, watermark} |
| /verify | POST | file + watermark + password? | {success, is_valid, match_score} |
| /batch | POST | files[] + watermark + operation | {results: [...]} |
| /test | GET | - | HTML测试页面 |
| /test-templates | GET | - | {formats: [...]} |
| /test-template/{ext} | GET | - | 文件流 |
| /output-file | GET | - | 最近嵌入的输出文件 |

---

## 6. 目录结构

```
stealthmark/
├── src/stealthmark/               # 标准src布局
│   ├── __init__.py                # 包入口
│   ├── __main__.py                # python -m 入口
│   ├── cli.py                     # CLI
│   ├── api.py                     # FastAPI Web API
│   ├── gui.py                     # PyQt6 GUI
│   ├── _logging.py                # 日志
│   ├── core/
│   │   ├── __init__.py
│   │   ├── base.py                # 基类、数据类
│   │   ├── codec.py               # 编解码
│   │   ├── manager.py             # 管理器（24个Handler）
│   │   └── exceptions.py          # 异常
│   ├── document/                  # 9个文档Handler
│   │   ├── pdf_watermark.py
│   │   ├── docx_watermark.py
│   │   ├── pptx_watermark.py
│   │   ├── xlsx_watermark.py
│   │   ├── odt_watermark.py
│   │   ├── ods_watermark.py
│   │   ├── odp_watermark.py
│   │   ├── epub_watermark.py
│   │   └── rtf_watermark.py
│   ├── image/                     # 7个图片Handler
│   │   ├── image_watermark.py     # PNG/BMP/JPEG
│   │   ├── tiff_webp_gif_watermark.py  # TIFF/WebP/GIF
│   │   └── heic_handler.py        # HEIC
│   ├── media/                     # 8个音视频Handler
│   │   ├── audio_watermark.py     # WAV/MP3
│   │   ├── flac_handler.py        # FLAC
│   │   ├── aac_handler.py         # AAC/M4A
│   │   ├── ogg_handler.py         # OGG
│   │   ├── video_watermark.py     # MP4/AVI/MKV/MOV
│   │   ├── webm_handler.py        # WebM
│   │   └── wmv_handler.py         # WMV
│   ├── utils/
│   │   └── helpers.py
│   └── static/
│       └── test.html              # Web测试前端
├── tests/
│   ├── unit/                      # 28个单元测试文件
│   ├── scripts/                   # 集成测试脚本
│   └── fixtures/                  # 30种格式测试数据
├── skills/stealthmark/            # OpenClaw Skill
│   ├── SKILL.md
│   ├── scripts/
│   ├── references/
│   └── assets/
├── docs/
│   ├── SRS.md
│   ├── DESIGN.md
│   ├── DETAILED_DESIGN.md
│   └── API.md
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## 7. 依赖关系

```
StealthMark
├── core/codec.py → zlib, cryptography, base64
├── document/
│   ├── pdf_watermark.py → PyPDF2
│   ├── docx_watermark.py → python-docx, zipfile
│   ├── pptx_watermark.py → python-pptx
│   ├── xlsx_watermark.py → openpyxl, zipfile
│   └── odt/ods/odp/epub/rtf → zipfile, xml.etree
├── image/
│   ├── image_watermark.py → Pillow, numpy, opencv-python
│   ├── tiff_webp_gif_watermark.py → Pillow
│   └── heic_handler.py → pillow-heif
├── media/
│   ├── audio_watermark.py → librosa, soundfile, numpy
│   ├── flac/aac_handler.py → librosa, soundfile
│   ├── ogg_handler.py → mutagen
│   └── video/webm/wmv_handler.py → imageio-ffmpeg, numpy
├── cli.py → argparse, colorama, tqdm
├── api.py → FastAPI, uvicorn
└── gui.py → PyQt6
```

---

*文档版本: 2.0*
*最后更新: 2026-05-01*
