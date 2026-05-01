# document/__init__.py
"""文档水印模块"""
from .pdf_watermark import PDFHandler
from .docx_watermark import DOCXHandler
from .pptx_watermark import PPTXHandler
from .xlsx_watermark import XLSXHandler
from .odt_watermark import ODTHandler, ODSHandler, ODPHandler
from .epub_watermark import EPUBHandler
from .rtf_watermark import RTFHandler

__all__ = [
    'PDFHandler', 'DOCXHandler', 'PPTXHandler',
    'XLSXHandler', 'ODTHandler', 'ODSHandler', 'ODPHandler',
    'EPUBHandler', 'RTFHandler'
]
