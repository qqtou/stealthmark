# image/__init__.py
"""图片水印模块"""
from .image_watermark import PNGHandler, BMPHandler, JPEGHandler
from .heic_handler import HEICHandler

# TIFF, WebP, GIF 处理器
try:
    from .tiff_webp_gif_watermark import TIFFHandler, WebPHandler, GIFHandler
except ImportError:
    # 如果文件不存在，暂时使用基类占位
    from .image_watermark import JPEGHandler as TIFFHandler
    from .image_watermark import PNGHandler as WebPHandler
    from .image_watermark import PNGHandler as GIFHandler

__all__ = [
    'PNGHandler', 'BMPHandler', 'JPEGHandler',
    'TIFFHandler', 'WebPHandler', 'GIFHandler', 'HEICHandler'
]
