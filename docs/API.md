# StealthMark API 文档

---

## 1. Python API

### 1.1 StealthMark 主类

```python
from stealthmark import StealthMark

sm = StealthMark(password="optional")  # password启用AES-256加密
```

### 1.2 核心方法

| 方法 | 签名 | 返回 |
|------|------|------|
| embed | `embed(file_path, watermark, output_path=None, **kwargs)` | EmbedResult |
| extract | `extract(file_path, **kwargs)` | ExtractResult |
| verify | `verify(file_path, original_watermark, **kwargs)` | VerifyResult |
| is_supported | `is_supported(file_path)` | bool |
| supported_formats | `supported_formats()` | List[str] |

### 1.3 结果类

```python
@dataclass
class EmbedResult:
    status: WatermarkStatus
    message: str = ""
    output_path: Optional[str] = None

    @property
    def is_success(self) -> bool: ...

@dataclass
class ExtractResult:
    status: WatermarkStatus
    message: str = ""
    watermark: Optional[WatermarkData] = None

    @property
    def is_success(self) -> bool: ...

@dataclass
class VerifyResult:
    status: WatermarkStatus
    is_valid: bool = False
    is_integrity_ok: bool = False
    match_score: float = 0.0
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
```

### 1.4 WatermarkStatus

| 值 | 含义 |
|----|------|
| SUCCESS (0) | 成功 |
| FAILED (1) | 通用失败 |
| FILE_NOT_FOUND (2) | 文件不存在 |
| FILE_CORRUPTED (3) | 文件损坏 |
| UNSUPPORTED_FORMAT (4) | 不支持格式 |
| INVALID_WATERMARK (5) | 无效水印 |
| EXTRACTION_FAILED (6) | 提取失败 |
| VERIFICATION_FAILED (7) | 验证失败 |
| ENCRYPTION_FAILED (8) | 加密失败 |
| DECRYPTION_FAILED (9) | 解密失败 |

### 1.5 使用示例

```python
from stealthmark import StealthMark

sm = StealthMark()

# 嵌入
result = sm.embed("doc.pdf", "版权所有 2026", "output.pdf")
if result.is_success:
    print(f"输出: {result.output_path}")

# 提取
result = sm.extract("output.pdf")
if result.is_success:
    print(f"水印: {result.watermark.content}")

# 验证
result = sm.verify("output.pdf", "版权所有 2026")
print(f"匹配: {result.is_valid}, 分数: {result.match_score}")

# 加密水印
sm = StealthMark(password="secret")
sm.embed("doc.pdf", "机密内容", "output.pdf")  # 自动加密
result = sm.extract("output.pdf")  # 自动解密

# 自定义Handler
class MyHandler(BaseHandler):
    SUPPORTED_EXTENSIONS = ('.myformat',)
    HANDLER_NAME = "myformat"
    def embed(self, file_path, watermark, output_path, **kwargs): ...
    def extract(self, file_path, **kwargs): ...
    def verify(self, file_path, original_watermark, **kwargs): ...

sm = StealthMark()
sm.register_handler(MyHandler)
```

---

## 2. CLI

```bash
python -m stealthmark <command> [options]
```

### 2.1 子命令

| 命令 | 说明 |
|------|------|
| `embed <file> <watermark> [-o output]` | 嵌入水印 |
| `extract <file>` | 提取水印 |
| `verify <file> [watermark]` | 验证水印 |
| `info` | 显示支持的格式 |
| `batch <embed\|extract\|verify> <dir>` | 批量处理 |

### 2.2 通用选项

| 选项 | 说明 |
|------|------|
| `-v, --verbose` | 详细日志 |
| `-q, --quiet` | 仅显示错误 |
| `-f, --force` | 强制覆盖（embed） |
| `--show-errors` | 显示失败详情 |
| `-p, --password` | 加密密码 |

### 2.3 batch 选项

| 选项 | 说明 |
|------|------|
| `-o, --output-dir` | 输出目录 |
| `--watermark` | 水印文本 |
| `-n, --name-pattern` | 输出命名：`{name}` `{ext}` `{date}` `{time}` |
| `--include` | 只处理指定扩展名 |
| `--exclude` | 排除指定扩展名 |
| `--no-recursive` | 不扫描子目录 |
| `--dry-run` | 模拟运行 |
| `--workers N` | 并行线程数（默认4） |

### 2.4 示例

```bash
# 基础操作
python -m stealthmark embed doc.pdf "版权所有"
python -m stealthmark extract doc.pdf
python -m stealthmark verify doc.pdf "版权所有"

# 批量嵌入
python -m stealthmark batch embed ./files -o ./out --watermark "版权"

# 只处理PDF和Word
python -m stealthmark batch embed ./files --include .pdf .docx

# 模拟运行
python -m stealthmark batch embed ./files --dry-run

# 自定义输出命名
python -m stealthmark batch embed ./files -n "{name}_marked{ext}"

# 4线程并行
python -m stealthmark batch embed ./files --workers 4
```

---

## 3. Web API

### 3.1 启动

```bash
uvicorn stealthmark.api:app --reload --port 8000
```

文档：http://localhost:8000/docs

### 3.2 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查，返回handler数量 |
| `/info` | GET | 支持格式列表（按分类） |
| `/embed` | POST | 嵌入水印（multipart/form-data） |
| `/extract` | POST | 提取水印 |
| `/verify` | POST | 验证水印 |
| `/batch` | POST | 批量处理 |
| `/test` | GET | 测试前端页面 |
| `/test-templates` | GET | 测试文件列表 |
| `/test-template/{ext}` | GET | 下载测试文件 |
| `/output-file` | GET | 下载最近嵌入的输出文件 |

### 3.3 请求示例

```bash
# 嵌入
curl -X POST http://localhost:8000/embed \
  -F "file=@document.pdf" \
  -F "watermark=版权所有 2026"

# 提取
curl -X POST http://localhost:8000/extract \
  -F "file=@watermarked.pdf"

# 验证
curl -X POST http://localhost:8000/verify \
  -F "file=@watermarked.pdf" \
  -F "watermark=版权所有 2026"

# 加密嵌入
curl -X POST http://localhost:8000/embed \
  -F "file=@document.pdf" \
  -F "watermark=机密" \
  -F "password=secret"
```

---

## 4. 24个Handler

| Handler | 格式 | 模块 |
|---------|------|------|
| PDFHandler | .pdf | document.pdf_watermark |
| DOCXHandler | .docx | document.docx_watermark |
| PPTXHandler | .pptx | document.pptx_watermark |
| XLSXHandler | .xlsx | document.xlsx_watermark |
| ODTHandler | .odt | document.odt_watermark |
| ODSHandler | .ods | document.ods_watermark |
| ODPHandler | .odp | document.odp_watermark |
| EPUBHandler | .epub | document.epub_watermark |
| RTFHandler | .rtf | document.rtf_watermark |
| PNGHandler | .png | image.image_watermark |
| BMPHandler | .bmp | image.image_watermark |
| JPEGHandler | .jpg/.jpeg | image.image_watermark |
| TIFFHandler | .tiff/.tif | image.tiff_webp_gif_watermark |
| WebPHandler | .webp | image.tiff_webp_gif_watermark |
| GIFHandler | .gif | image.tiff_webp_gif_watermark |
| HEICHandler | .heic | image.heic_handler |
| WAVHandler | .wav | media.audio_watermark |
| MP3Handler | .mp3 | media.audio_watermark |
| FLACHandler | .flac | media.flac_handler |
| AACHandler | .aac/.m4a | media.aac_handler |
| OGGHandler | .ogg | media.ogg_handler |
| VideoHandler | .mp4/.avi/.mkv/.mov | media.video_watermark |
| WebMHandler | .webm | media.webm_handler |
| WMVHandler | .wmv | media.wmv_handler |

---

*API版本: 2.0*
*最后更新: 2026-05-01*
