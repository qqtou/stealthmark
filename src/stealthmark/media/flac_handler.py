# media/flac_handler.py
"""
FLAC音频水印处理器 - 扩频水印

FLAC是无损音频格式。复用WAV的扩频水印方案。
librosa + soundfile 原生支持FLAC。

Author: StealthMark Team
Date: 2026-04-28
"""

import logging

from .audio_watermark import WAVHandler

logger = logging.getLogger(__name__)


class FLACHandler(WAVHandler):
    """
    FLAC音频水印处理器
    
    复用WAV的扩频水印实现。
    librosa可加载FLAC，soundfile可写入FLAC。
    """
    
    SUPPORTED_EXTENSIONS = ('.flac',)
    HANDLER_NAME = "flac"


logger.info(f"{__name__} module loaded - FLAC handler ready")
