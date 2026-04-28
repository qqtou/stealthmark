# media/aac_handler.py
"""
AAC/M4A音频水印处理器 - 扩频水印

AAC/M4A是有损音频格式。复用WAV的扩频水印方案。
librosa支持加载AAC/M4A格式。

Author: StealthMark Team
Date: 2026-04-28
"""

import logging

from .audio_watermark import WAVHandler

logger = logging.getLogger(__name__)


class AACHandler(WAVHandler):
    """
    AAC/M4A音频水印处理器
    
    复用WAV的扩频水印实现。
    librosa可加载AAC/M4A。
    
    注意: 有损压缩可能影响扩频水印的提取精度。
    """
    
    SUPPORTED_EXTENSIONS = ('.aac', '.m4a')
    HANDLER_NAME = "aac"


logger.info(f"{__name__} module loaded - AAC handler ready")
