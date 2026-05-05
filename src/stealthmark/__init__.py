# StealthMark - 隐式水印系统
"""
StealthMark — 跨格式隐式数字水印工具包

支持 31 种文件格式的水印嵌入、提取与验证：
- 文档：PDF, DOCX, PPTX, XLSX, ODT, ODS, ODP, EPUB, RTF
- 图片：PNG, JPEG, BMP, TIFF, WebP, GIF, HEIC
- 音频：WAV, MP3, FLAC, AAC/M4A, OGG
- 视频：MP4, AVI, MKV, MOV, WebM, WMV

三种使用方式：
- CLI: python -m stealthmark embed/extract/verify/batch
- GUI: python -m stealthmark.gui
- Web API: uvicorn stealthmark.api:app

示例:
    >>> from stealthmark import StealthMark
    >>> sm = StealthMark()
    >>> result = sm.embed("photo.png", "copyright 2026", "photo_wm.png")
    >>> print(result.is_success)
"""
try:
    from importlib.metadata import version as _pkg_version
    __version__ = _pkg_version("stealthmark")
except Exception:
    __version__ = "0.1.0"

from .core.manager import StealthMark
from .core.base import (
    WatermarkData,
    WatermarkStatus,
    WatermarkType,
    EmbedResult,
    ExtractResult,
    VerifyResult,
)

__all__ = [
    "StealthMark",
    "WatermarkData",
    "WatermarkStatus",
    "WatermarkType",
    "EmbedResult",
    "ExtractResult",
    "VerifyResult",
]
