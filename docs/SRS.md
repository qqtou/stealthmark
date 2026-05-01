# StealthMark 隐式水印系统需求规格说明书

---

## 1. 文档信息

| 属性 | 内容 |
|------|------|
| 项目名称 | StealthMark |
| 文档版本 | 2.0 |
| 创建日期 | 2026-04-28 |
| 最后更新 | 2026-05-01 |
| 文档类型 | 需求规格说明书（SRS） |

---

## 2. 概述

### 2.1 项目背景

随着数字内容的广泛传播，文档、图片、音频、视频等数字资产面临被非法复制、篡改和传播的风险。数字水印技术作为一种有效的数字内容保护手段，可以在不影响原始文件质量的前提下，将版权信息、身份标识等隐蔽地嵌入到数字内容中。

### 2.2 项目目标

开发一套通用的隐式水印系统，实现以下目标：

1. **水印嵌入**: 向各类文档、图片、音频、视频文件中嵌入不可见的数字水印
2. **水印提取**: 从含水印文件中准确提取嵌入的水印信息
3. **水印验证**: 验证文件的完整性和水印的一致性
4. **多格式支持**: 支持31种主流的文档、图片、音频、视频格式
5. **多接口支持**: 提供 CLI、GUI、Web API 三种使用方式

### 2.3 术语定义

| 术语 | 定义 |
|------|------|
| 隐式水印 | 人眼/耳不可感知的技术性标记，嵌入到数字内容中 |
| 嵌入 | 将水印信息转换为特定格式并写入目标文件的过程 |
| 提取 | 从含水印文件中还原出水印信息的过程 |
| 验证 | 检查水印完整性及与原始水印一致性的过程 |
| 鲁棒性 | 水印抵抗各种攻击（如压缩、裁剪、滤波）的能力 |
| 扩频水印 | 将水印信号扩展到宽频带，利用伪随机序列实现低能量嵌入 |
| LSB隐写 | 修改像素/采样最低有效位来嵌入信息的技术 |

---

## 3. 功能需求

### 3.1 总体功能列表

| 编号 | 功能 | 优先级 | 描述 | 状态 |
|------|------|--------|------|------|
| F01 | 水印嵌入 | P0 | 向文件中嵌入水印信息 | ✅ 已实现 |
| F02 | 水印提取 | P0 | 从含水印文件中提取水印信息 | ✅ 已实现 |
| F03 | 水印验证 | P0 | 验证水印的完整性和一致性 | ✅ 已实现 |
| F04 | 水印编码 | P0 | 将水印文本编码为可嵌入格式 | ✅ 已实现 |
| F05 | 水印解码 | P0 | 将提取的数据解码为水印文本 | ✅ 已实现 |
| F06 | 水印加密 | P1 | 使用AES-256加密水印内容 | ✅ 已实现 |
| F07 | 批量处理 | P2 | 支持批量文件的水印操作 | ✅ 已实现 |
| F08 | CLI增强 | P2 | verbose/quiet/batch/彩色输出 | ✅ 已实现 |
| F09 | GUI界面 | P3 | PyQt6图形界面 | ✅ 已实现 |
| F10 | Web API | P3 | FastAPI RESTful接口 | ✅ 已实现 |

### 3.2 文档水印功能

| 编号 | 功能 | 优先级 | 描述 | 状态 |
|------|------|--------|------|------|
| PDF01 | PDF元数据嵌入 | P0 | 将水印写入PDF元数据字段 | ✅ |
| PDF02 | PDF水印提取/验证 | P0 | 从PDF中提取和验证水印 | ✅ |
| DOC01 | DOCX零宽字符嵌入 | P0 | 使用零宽Unicode字符编码水印 | ✅ |
| DOC02 | DOCX提取/验证 | P0 | 从Word文档中提取和验证水印 | ✅ |
| PPT01 | PPTX隐藏形状嵌入 | P0 | 插入不可见的透明形状存储水印 | ✅ |
| XLS01 | XLSX自定义XML属性 | P0 | customXml/item1.xml属性存储 | ✅ |
| ODF01 | ODT/ODS/ODP ODF元数据 | P0 | user-defined元数据属性 | ✅ |
| EPUB01 | EPUB OPF嵌入 | P0 | OPF dc:identifier元数据 | ✅ |
| RTF01 | RTF可忽略控制组 | P0 | 可忽略控制组嵌入 | ✅ |

### 3.3 图片水印功能

| 编号 | 功能 | 优先级 | 描述 | 状态 |
|------|------|--------|------|------|
| IMG01 | PNG/BMP LSB嵌入 | P0 | RGB三通道LSB隐写，3倍冗余 | ✅ |
| IMG02 | JPEG DCT嵌入 | P0 | DCT域水印 | ✅ |
| IMG03 | TIFF/WebP LSB嵌入 | P0 | LSB隐写（无损） | ✅ |
| IMG04 | GIF Comment Extension | P0 | GIF注释扩展块 | ✅ |
| IMG05 | HEIC EXIF嵌入 | P1 | EXIF UserComment字段 | ✅ |
| IMG06 | 图片水印提取/验证 | P0 | 通用提取和验证 | ✅ |

### 3.4 音视频水印功能

| 编号 | 功能 | 优先级 | 描述 | 状态 |
|------|------|--------|------|------|
| AUD01 | WAV扩频水印 | P0 | 自适应alpha嵌入强度 | ✅ |
| AUD02 | MP3扩频水印 | P0 | 继承WAV扩频方案 | ✅ |
| AUD03 | FLAC扩频水印 | P0 | 继承WAV扩频方案 | ✅ |
| AUD04 | AAC/M4A扩频水印 | P0 | 输出为M4A容器（ALAC无损） | ✅ |
| AUD05 | OGG元数据水印 | P1 | mutagen库OGG Vorbis元数据 | ✅ |
| AUD06 | 音频水印提取/验证 | P0 | 通用提取和验证 | ✅ |
| VID01 | MP4/AVI/MKV/MOV RGB Blue LSB | P0 | 第一帧Blue通道LSB + libx264rgb/FFV1无损编码 | ✅ |
| VID02 | WebM RGB Blue LSB | P0 | 第一帧Blue通道LSB + VP9无损 | ✅ |
| VID03 | WMV RGB Blue LSB | P0 | 第一帧Blue通道LSB | ✅ |
| VID04 | 视频水印提取/验证 | P0 | 通用提取和验证 | ✅ |

### 3.5 接口功能

| 编号 | 功能 | 优先级 | 描述 | 状态 |
|------|------|--------|------|------|
| CLI01 | 基础命令 | P0 | embed/extract/verify/info | ✅ |
| CLI02 | 批量处理 | P2 | batch embed/extract/verify + 过滤/并行/dry-run | ✅ |
| CLI03 | 输出控制 | P2 | -v/--verbose, -q/--quiet, 彩色输出 | ✅ |
| GUI01 | PyQt6界面 | P3 | 拖放/进度条/结果表格 | ✅ |
| API01 | RESTful接口 | P3 | /embed /extract /verify /batch /health /info | ✅ |
| API02 | 测试前端 | P3 | Web测试页面，全流程测试 | ✅ |

---

## 4. 数据格式需求

### 4.1 水印编码格式

```
┌──────────────────────────────────────────────────────────┐
│                     水印数据格式                          │
├──────────────────────────────────────────────────────────┤
│ [魔术数: SMARK 5字节][版本: 1字节][长度: 4字节][内容: N字节][CRC32: 4字节] │
└──────────────────────────────────────────────────────────┘
```

可选加密：AES-256-CBC（PBKDF2-HMAC-SHA256密钥派生）

### 4.2 支持的文件格式

| 类别 | 格式 | 扩展名 | 算法 | 状态 |
|------|------|--------|------|------|
| 文档 | PDF | .pdf | 元数据（Author字段，Base64） | ✅ |
| 文档 | Word | .docx | 零宽字符（U+200B=0, U+200C=1） | ✅ |
| 文档 | PowerPoint | .pptx | 隐藏形状（hidden_前缀） | ✅ |
| 文档 | Excel | .xlsx | customXml/item1.xml属性 | ✅ |
| 文档 | ODF文本 | .odt | ODF user-defined元数据 | ✅ |
| 文档 | ODF表格 | .ods | ODF user-defined元数据 | ✅ |
| 文档 | ODF演示 | .odp | ODF user-defined元数据 | ✅ |
| 文档 | EPUB | .epub | OPF dc:identifier | ✅ |
| 文档 | RTF | .rtf | 可忽略控制组 | ✅ |
| 图片 | PNG | .png | LSB 3倍冗余嵌入 | ✅ |
| 图片 | JPEG | .jpg/.jpeg | DCT域水印 | ✅ |
| 图片 | BMP | .bmp | LSB 3倍冗余嵌入 | ✅ |
| 图片 | TIFF | .tiff/.tif | LSB隐写 | ✅ |
| 图片 | WebP | .webp | LSB隐写（无损） | ✅ |
| 图片 | GIF | .gif | Comment Extension块 | ✅ |
| 图片 | HEIC | .heic | EXIF UserComment | ✅ |
| 音频 | WAV | .wav | 扩频水印（自适应alpha） | ✅ |
| 音频 | MP3 | .mp3 | 扩频水印 | ✅ |
| 音频 | FLAC | .flac | 扩频水印 | ✅ |
| 音频 | AAC/M4A | .aac/.m4a | 扩频水印（输出M4A） | ✅ |
| 音频 | OGG | .ogg | mutagen元数据 | ✅ |
| 视频 | MP4 | .mp4 | RGB Blue LSB + libx264rgb CRF0 | ✅ |
| 视频 | AVI | .avi | RGB Blue LSB + FFV1无损 | ✅ |
| 视频 | MKV | .mkv | RGB Blue LSB + FFV1无损 | ✅ |
| 视频 | MOV | .mov | RGB Blue LSB + libx264rgb CRF0 | ✅ |
| 视频 | WebM | .webm | RGB Blue LSB + VP9无损 | ✅ |
| 视频 | WMV | .wmv | RGB Blue LSB | ✅ |

---

## 5. 水印算法需求

### 5.1 文档水印算法

| 文件类型 | 算法 | 描述 |
|----------|------|------|
| PDF | 元数据写入 | 将Base64编码的水印写入Author字段（/SMMark） |
| DOCX | 零宽字符 | U+200B=0, U+200C=1，嵌入文档文本节点 |
| PPTX | 隐藏形状 | 插入透明不可见形状，名称含水印数据 |
| XLSX | customXml属性 | customXml/item1.xml中property属性 |
| ODT/ODS/ODP | ODF user-defined | ODF标准自定义元数据字段 |
| EPUB | OPF dc:identifier | 电子书元数据字段 |
| RTF | 可忽略控制组 | `{\*\stealthmark base64encoded}` |

### 5.2 图片水印算法

| 文件类型 | 算法 | 描述 |
|----------|------|------|
| PNG/BMP | LSB 3倍冗余 | 每bit重复3次，提取时多数投票，RGB三通道 |
| JPEG | DCT域 | 在DCT系数中嵌入水印 |
| TIFF/WebP | LSB隐写 | 最低有效位隐写（仅无损版本） |
| GIF | Comment Extension | GIF标准注释扩展块 |
| HEIC | EXIF UserComment | EXIF UserComment字段（pillow-heif） |

### 5.3 音视频水印算法

| 文件类型 | 算法 | 描述 |
|----------|------|------|
| WAV | 扩频水印 | 自适应alpha（根据音频段能量调整），BPS=100 |
| MP3/FLAC/AAC | 扩频水印 | 继承WAV方案 |
| AAC/M4A | 输出M4A | ALAC无损编码需M4A容器 |
| OGG | mutagen元数据 | OGG Vorbis COMMENT字段 |
| MP4/AVI/MKV/MOV | RGB Blue LSB | **第一帧**Blue通道LSB + 无损编码 |
| WebM | RGB Blue LSB | **第一帧**Blue通道LSB + VP9无损 |
| WMV | RGB Blue LSB | **第一帧**Blue通道LSB |

---

## 6. 接口需求

### 6.1 命令行接口

```bash
# 基础操作
python -m stealthmark embed <input_file> <watermark> [-o <output>]
python -m stealthmark extract <file>
python -m stealthmark verify <file> <original_watermark>
python -m stealthmark info

# 批量处理
python -m stealthmark batch embed <input_dir> [-o <output_dir>] [options]
python -m stealthmark batch extract <input_dir> [options]
python -m stealthmark batch verify <input_dir> [options]

# 输出控制
python -m stealthmark embed <file> <wm> -v    # 详细日志
python -m stealthmark embed <file> <wm> -q    # 静默模式
python -m stealthmark embed <file> <wm> -f    # 强制覆盖
```

### 6.2 编程接口

```python
from stealthmark import StealthMark

sm = StealthMark()
sm.embed(file_path, watermark, output_path) -> EmbedResult
sm.extract(file_path) -> ExtractResult
sm.verify(file_path, original_watermark) -> VerifyResult
sm.is_supported(file_path) -> bool
sm.supported_formats() -> List[str]
```

### 6.3 Web API

```bash
# 启动
uvicorn stealthmark.api:app --reload --port 8000

# 端点
GET  /health          # 健康检查
GET  /info            # 支持格式
POST /embed           # 嵌入水印
POST /extract         # 提取水印
POST /verify          # 验证水印
POST /batch           # 批量处理
GET  /test            # 测试前端页面
```

### 6.4 GUI

```bash
python -m stealthmark.gui
```

---

## 7. 性能需求

| 指标 | 要求 | 说明 |
|------|------|------|
| 嵌入速度 | < 10秒/文件 | 对于100MB以内的文件 |
| 提取速度 | < 5秒/文件 | 对于100MB以内的文件 |
| 文件大小变化 | < 1% | 嵌入水印后文件大小变化 |
| 内存占用 | < 500MB | 处理过程中最大内存使用 |

---

## 8. 质量需求

### 8.1 准确性

| 指标 | 要求 |
|------|------|
| 水印提取准确率 | ≥ 99%（无损格式） |
| 水印验证准确率 | ≥ 99% |
| 编码解码错误率 | < 0.1% |

### 8.2 隐蔽性

| 指标 | 要求 |
|------|------|
| 视觉不可见 | 水印嵌入后文件外观无变化 |
| 听觉不可见 | 音频水印不可被人耳察觉 |
| 统计不可检测 | 不引入明显的统计异常 |

---

## 9. 安全需求

| 编号 | 需求 | 优先级 | 描述 | 状态 |
|------|------|--------|------|------|
| SEC01 | 水印加密 | P1 | AES-256-CBC加密水印 | ✅ |
| SEC02 | 密钥派生 | P1 | PBKDF2-HMAC-SHA256从密码派生密钥 | ✅ |
| SEC03 | 密钥分离 | P0 | 密钥不存储在文件中 | ✅ |
| SEC04 | CRC校验 | P0 | CRC32检测篡改 | ✅ |

---

## 10. 运行环境需求

### 10.1 软件依赖

| 组件 | 版本要求 | 用途 |
|------|----------|------|
| Python | ≥ 3.9 | 运行环境 |
| PyPDF2 | ≥ 3.0 | PDF处理 |
| python-docx | ≥ 0.8 | Word处理 |
| python-pptx | ≥ 0.6 | PPT处理 |
| openpyxl | ≥ 3.0 | Excel处理 |
| Pillow | ≥ 9.0 | 图片处理 |
| opencv-python | ≥ 4.7 | 图像处理 |
| numpy | ≥ 1.24 | 数值计算 |
| librosa | ≥ 0.10 | 音频处理 |
| soundfile | ≥ 0.12 | 音频读写 |
| imageio-ffmpeg | ≥ 0.4 | 视频编解码 |
| mutagen | ≥ 1.46 | OGG元数据 |
| cryptography | ≥ 41.0 | 加密 |
| colorama | ≥ 0.4 | 彩色输出 |
| tqdm | ≥ 4.0 | 进度条 |
| PyQt6 | ≥ 6.0 | GUI（可选） |
| FastAPI | ≥ 0.100 | Web API（可选） |
| uvicorn | ≥ 0.20 | ASGI服务器（可选） |

---

## 11. 约束条件

| 编号 | 约束 | 说明 |
|------|------|------|
| CON01 | 格式约束 | 仅支持指定的31种文件格式 |
| CON02 | 大小约束 | 单文件建议不超过500MB |
| CON03 | 水印长度 | 单条水印建议不超过1KB |
| CON04 | 视频约束 | 视频必须使用无损编码，有损转码会破坏水印 |
| CON05 | 有损格式 | MP3/HEIC等有损格式水印提取可能失败为预期行为 |

---

*文档版本: 2.0*
*创建日期: 2026-04-28*
*最后更新: 2026-05-01*
