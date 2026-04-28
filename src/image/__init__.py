# image/__init__.py
"""图片水印模块"""
from .image_watermark import PNGHandler, BMPHandler, JPEGHandler
from .tiff_webp_gif_watermark import TIFFHandler, WebPHandler, GIFHandler
from .heic_handler import HEICHandler

__all__ = [
    'PNGHandler', 'BMPHandler', 'JPEGHandler',
    'TIFFHandler', 'WebPHandler', 'GIFHandler', 'HEICHandler'
]
