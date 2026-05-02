# StealthMark - 隐式水印系统
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
