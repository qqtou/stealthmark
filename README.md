# StealthMark

隐形数字水印工具。为 PDFs、Word、PowerPoint、图片、音视频添加人不可见的隐形水印，用于版权保护、溯源、文件鉴权。

## 功能特点

- **多格式支持**：30种文档、图片、音频、视频格式
- **隐形嵌入**：水印对用户不可见，不影响原文件内容
- **完整生命周期**：嵌入 → 提取 → 验证
- **可选加密**：支持 AES-256 加密水印内容
- **完整性校验**：CRC32 校验确保数据完整

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
| 图片 | `.png` / `.bmp` | LSB隐写 |
| 图片 | `.jpg` / `.jpeg` | DCT域水印 |
| 图片 | `.tiff` | LSB隐写 |
| 图片 | `.webp` | LSB隐写（无损） |
| 图片 | `.gif` | Comment Extension |
| 图片 | `.heic` | EXIF UserComment |
| 音频 | `.wav` / `.mp3` | 扩频水印 |
| 音频 | `.flac` | 扩频水印 |
| 音频 | `.aac` / `.m4a` | 扩频水印 |
| 视频 | `.mp4` / `.avi` / `.mkv` / `.mov` | RGB Blue通道LSB + 无损编码 |
| 视频 | `.webm` | RGB Blue通道LSB + VP9无损 |
| 视频 | `.wmv` | RGB Blue通道LSB |

## 水印容量限制

水印内容经 codec 编码后有 14 字节固定开销（魔术5 + 版本1 + 长度4 + CRC4），再加上原始文件的 UTF-8 字节数。各格式容量取决于载体大小：

| 格式 | 容量计算 | 典型容量（参考） | 限制因素 |
|------|----------|-----------------|---------|
| `.pdf` | 无损型限制 | 几乎无限（受PDF文件规范限制） | 元数据域可能被清理 |
| `.docx` | 取决于文档字符密度 | 一般文档可嵌数千字符 | 另存为.doc时会丢失字符 |
| `.pptx` | 取决于幻灯片张数 | 数百~数千字符 | 编辑时水印标记可擦 |
| `.png` / `.bmp` | (宽 × 高 × 通道数 - 32) ÷ 8 字节 | 1920×1080 RGB ≈ 777 KB | 缩放/压缩会破坏LSB |
| `.jpg` / `.jpeg` | (宽/8 × 高/8 - 8) ÷ 8 字节 | 1920×1080 ≈ 31 KB | 有损压缩影响提取精度 |
| `.tiff` / `.webp` | (宽 × 高 × 通道数 - 32) ÷ 8 字节 | 1920×1080 RGB ≈ 777 KB | 仅限无损版本 |
| `.gif` | 取决于Comment Extension长度 | 数KB | 仅支持静态GIF |
| `.heic` | 取决于EXIF字段 | 约1-4 KB | 有损压缩影响精度 |
| `.wav` | 采样点数 ÷ 100 - 8 bits | 44.1kHz/5min ≈ 1.3 KB | 音频太短容量不足 |
| `.mp3` | 同WAV | 取决于音频时长 | 有损压缩可能影响水印强度 |
| `.flac` | (采样点数 ÷ 100 - 32) ÷ 8 字节 | 44.1kHz/5min ≈ 55 KB | 无损，LSB安全 |
| `.aac` / `.m4a` | 同WAV扩频 | 取决于音频时长 | 有损编码 |
| `.mp4` 等 | 第一帧宽 × 高 - 32 bits ÷ 8 字节 | 1920×1080 ≈ 259 KB | 仅用第一帧；必须无损编码 |
| `.webm` / `.wmv` | 同上 | 1920×1080 ≈ 259 KB | 必须无损编码 |

**容量计算示例**：

```
水印文本 "StealthMark-Test-2026"（22字符）
  → UTF-8: 22字节 → 编码后: 36字节（含14字节开销）
  → PNG 800×600: 容量 1,440,000字节 → 轻松容纳
  → WAV 44.1kHz/10秒: 容量 44,100 / 100 = 441 bits → 可嵌入
  → WAV 44.1kHz/1秒:  容量 441 / 100 = 4 bits → 无法嵌入
```

**建议**：水印内容尽量简短，推荐 100 字符以内。音视频媒体建议不超过 50 字符。

## 安装

```bash
# 克隆项目
git clone https://github.com/your-repo/stealthmark.git
cd stealthmark

# 安装依赖
pip install -r requirements.txt
```

依赖：
- PyPDF2
- python-docx
- python-pptx
- openpyxl
- Pillow
- opencv-python
- librosa
- soundfile
- imageio-ffmpeg
- cryptography

## 快速开始

```python
from src.core.manager import StealthMark
from src.core.base import WatermarkData

# 初始化
wm = StealthMark()

# 嵌入水印
result = wm.embed("document.pdf", "版权所有 2026", "output.pdf")
print(f"嵌入结果: {result.status}")


# 提取水印
result = wm.extract("output.pdf")
print(f"水印内容: {result.watermark.content}")


# 验证水印
result = wm.verify("output.pdf", "原始水印")
print(f"验证结果: {result.is_valid}")
```

## 命令行

```bash
# 嵌入水印
python -m stealthmark embed document.pdf "水印内容" output.pdf

# 提取水印
python -m stealthmark extract document.pdf

# 验证水印
python -m stealthmark verify document.pdf "原始水印"
```

## 水印格式

编码流程：原文 → UTF-8 → CRC32 → 格式封装

```
[魔术数: 5字节][版本: 1字节][长度: 4字节][内容: N字节][CRC32: 4字节]
```

可选加密：AES-256-CBC（设置password参数即可启用）

## API

```python
# 基本用法
wm = StealthMark()
wm.embed(input_file, watermark_text, output_file) → EmbedResult
wm.extract(file_path) → ExtractResult
wm.verify(file_path, original_text) → VerifyResult

# 加密用法（需要设置密码）
wm = StealthMark(config={'password': 'secret123'})
wm.embed("doc.pdf", "机密内容", "out.pdf")  # 自动加密

# 批量处理
wm.batch_embed(directory, watermark_text)
wm.batch_extract(directory)
```

## 注意事项

- **JPEG**：有损压缩，只可能影响水印提取
- **DOCX**：另存为 .doc 可能丢失字符
- **PNG/BMP**：LSB 对压缩敏感
- **音频/视频**：处理时间随文件长度增加
- **PDF**：元数据可能被专业工具清理
- **视频**：输出为无损编码，文件较大

## 许可证

MIT License
