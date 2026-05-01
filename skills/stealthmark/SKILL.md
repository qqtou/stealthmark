# StealthMark Skill

## 简介

StealthMark 跨格式隐形数字水印工具，支持 30+ 种格式：PDF/DOCX/PPTX/XLSX/ODT/ODS/ODP/EPUB/RTF, PNG/JPEG/BMP/GIF/TIFF/WebP/HEIC, WAV/MP3/FLAC/AAC/OGG, MP4/AVI/MKV/MOV/WebM/WMV。

## 使用方法

### 首次安装
```bash
pip install -e D:/work/code/stealthmark
# 或从 GitHub:
pip install git+https://github.com/qqtou/stealthmark.git
```

### Python 调用

```python
from skills.stealthmark.scripts.embed import embed
result = embed(
    input_file="report.pdf",
    watermark="CONFIDENTIAL",
    output_file="report_wm.pdf",
    force=True
)
# result['success'], result['output_path']

from skills.stealthmark.scripts.extract import extract
result = extract(file_path="report_wm.pdf")
# result['success'], result['watermark']

from skills.stealthmark.scripts.verify import verify
result = verify(file_path="report_wm.pdf", original_watermark="CONFIDENTIAL")
# result['success'], result['match'], result['score']
```

### CLI 直接调用

```bash
python -m stealthmark embed input.pdf "WM" -o output.pdf -f
python -m stealthmark extract output.pdf
python -m stealthmark verify output.pdf "WM"
python -m stealthmark batch embed ./dir --watermark "WM" --workers 4
python -m stealthmark info
```

## 返回格式

```python
# embed
{'success': True, 'output_path': '...', 'message': '...', 'format': '.pdf', 'handler': None}

# extract  
{'success': True, 'watermark': 'WM', 'message': '...', 'format': '.pdf'}

# verify
{'success': True, 'match': True, 'score': 1.0, 'message': '...', 'details': {...}}

# batch
{'success': True, 'total': 100, 'processed': 98, 'failed': 2, 'errors': [...]}
```

## 注意事项

- **有损格式**：MP3/HEIC 等有损压缩格式水印提取失败为预期行为
- **安装依赖**：必须先 `pip install -e D:/work/code/stealthmark`
- **工作目录**：脚本会自动尝试多个工作目录确保 CLI 正常运行
- **并行批处理**：batch 支持 `--workers N` 并行（默认 4）

## 参考

- 格式说明：`references/formats.md`
- 算法原理：`references/algorithms.md`
- CLI 参数：`references/cli-reference.md`