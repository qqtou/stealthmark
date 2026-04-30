# media/__init__.py
"""音视频水印模块"""
from .audio_watermark import WAVHandler, MP3Handler
from .video_watermark import VideoHandler
from .flac_handler import FLACHandler
from .aac_handler import AACHandler
from .webm_handler import WebMHandler
from .wmv_handler import WMVHandler
from .ogg_handler import OGGHandler

__all__ = [
    'WAVHandler', 'MP3Handler', 'VideoHandler',
    'FLACHandler', 'AACHandler', 'WebMHandler', 'WMVHandler', 'OGGHandler'
]
