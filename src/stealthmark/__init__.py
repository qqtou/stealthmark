# StealthMark - 隐式水印系统
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
