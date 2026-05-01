# core/manager.py
"""
StealthMark 门面类 - 统一的水印操作入口

设计模式：门面模式（Facade Pattern）
- 为子系统中的一组接口提供一个统一的高层接口
- 简化客户端使用，隐藏内部复杂性

Author: StealthMark Team
Date: 2026-04-28
"""

from typing import Optional, Dict, List, Type
from pathlib import Path
import logging

from .base import (
    BaseHandler, WatermarkData, WatermarkType, WatermarkStatus,
    EmbedResult, ExtractResult, VerifyResult
)
from .codec import WatermarkCodec

logger = logging.getLogger(__name__)


class StealthMark:
    """
    StealthMark 门面类
    
    支持的文件格式：
    - 文档：PDF, DOCX, PPTX, XLSX, ODT, ODS, ODP, EPUB, RTF
    - 图片：PNG, JPEG, BMP, TIFF, WebP, GIF, HEIC
    - 音频：WAV, MP3, FLAC, AAC/M4A
    - 视频：MP4, AVI, MKV, MOV, WebM, WMV
    """
    
    def __init__(self, password: Optional[str] = None):
        self.password = password
        self.codec = WatermarkCodec(password=password)
        self._handlers: Dict[str, BaseHandler] = {}
        self._handler_registry: List[Type[BaseHandler]] = []
        self._register_builtin_handlers()
        
        logger.info(f"StealthMark initialized: {len(self._handler_registry)} handlers, "
                    f"encryption={'enabled' if password else 'disabled'}")
    
    def _register_builtin_handlers(self) -> None:
        """注册所有内置处理器"""
        from ..document import (
            PDFHandler, DOCXHandler, PPTXHandler,
            XLSXHandler, ODTHandler, ODSHandler, ODPHandler,
            EPUBHandler, RTFHandler
        )
        from ..image import (
            PNGHandler, BMPHandler, JPEGHandler,
            TIFFHandler, WebPHandler, GIFHandler, HEICHandler
        )
        from ..media import (
            WAVHandler, MP3Handler, VideoHandler,
            FLACHandler, AACHandler, WebMHandler, WMVHandler, OGGHandler
        )
        
        handler_classes = [
            # 文档处理器
            PDFHandler, DOCXHandler, PPTXHandler,
            XLSXHandler, ODTHandler, ODSHandler, ODPHandler,
            EPUBHandler, RTFHandler,
            # 图片处理器
            PNGHandler, BMPHandler, JPEGHandler,
            TIFFHandler, WebPHandler, GIFHandler, HEICHandler,
            # 音频处理器
            WAVHandler, MP3Handler, FLACHandler, AACHandler, OGGHandler,
            # 视频处理器
            VideoHandler, WebMHandler, WMVHandler,
        ]
        
        for handler_class in handler_classes:
            self.register_handler(handler_class)
        
        logger.debug(f"Builtin handlers registered: {len(self._handler_registry)}")
    
    def register_handler(self, handler_class: Type[BaseHandler]) -> None:
        """注册水印处理器"""
        try:
            handler = handler_class()
            for ext in handler.SUPPORTED_EXTENSIONS:
                self._handlers[ext.lower()] = handler
            self._handler_registry.append(handler_class)
            logger.debug(f"Handler registered: {handler.HANDLER_NAME} -> {handler.SUPPORTED_EXTENSIONS}")
        except Exception as e:
            logger.error(f"Failed to register handler {handler_class.__name__}: {e}")
    
    def _get_handler(self, file_path: str) -> Optional[BaseHandler]:
        """获取文件对应的处理器"""
        ext = Path(file_path).suffix.lower()
        handler = self._handlers.get(ext)
        if handler:
            logger.debug(f"Handler for {ext}: {handler.HANDLER_NAME}")
        else:
            logger.debug(f"No handler for {ext}")
        return handler
    
    # ==================== 核心操作 ====================
    
    def embed(self, file_path: str, watermark: str, 
              output_path: Optional[str] = None, **kwargs) -> EmbedResult:
        """嵌入水印到文件"""
        logger.info(f"Embed request: {file_path}")
        
        path = Path(file_path)
        if not path.exists():
            return EmbedResult(status=WatermarkStatus.FILE_NOT_FOUND, message=f"文件不存在: {file_path}", file_path=file_path)
        
        handler = self._get_handler(file_path)
        if not handler:
            return EmbedResult(status=WatermarkStatus.UNSUPPORTED_FORMAT, message=f"不支持的文件格式: {path.suffix}", file_path=file_path)
        
        if output_path is None:
            output_path = file_path
        
        watermark_data = WatermarkData(content=watermark)
        result = handler.embed(file_path, watermark_data, output_path, **kwargs)
        
        # 兜底：部分 handler 未设置 output_path，用调用参数补全
        if result.is_success and result.output_path is None:
            result = EmbedResult(
                status=result.status,
                message=result.message,
                file_path=result.file_path,
                output_path=output_path,
                watermark_id=result.watermark_id
            )
        
        return result
    
    def extract(self, file_path: str, **kwargs) -> ExtractResult:
        """从文件中提取水印"""
        logger.info(f"Extract request: {file_path}")
        
        handler = self._get_handler(file_path)
        if not handler:
            return ExtractResult(status=WatermarkStatus.UNSUPPORTED_FORMAT, message=f"不支持的文件格式: {Path(file_path).suffix}", file_path=file_path)
        
        result = handler.extract(file_path, **kwargs)
        return result
    
    def verify(self, file_path: str, original_watermark: str,
               **kwargs) -> VerifyResult:
        """验证文件中的水印"""
        logger.info(f"Verify request: {file_path}")
        
        extract_result = self.extract(file_path, **kwargs)
        
        if not extract_result.is_success or not extract_result.watermark:
            return VerifyResult(
                status=extract_result.status,
                message=f"提取失败: {extract_result.message}",
                is_valid=False, is_integrity_ok=False, match_score=0.0
            )
        
        extracted = extract_result.watermark.content
        original = original_watermark
        
        if extracted == original:
            match_score = 1.0
        else:
            match_score = self._calculate_similarity(extracted, original)
        
        is_integrity_ok = extract_result.status == WatermarkStatus.SUCCESS
        is_valid = match_score >= 0.8 and is_integrity_ok
        
        return VerifyResult(
            status=WatermarkStatus.SUCCESS if is_valid else WatermarkStatus.VERIFICATION_FAILED,
            message="验证通过" if is_valid else "验证失败",
            is_valid=is_valid, is_integrity_ok=is_integrity_ok,
            match_score=match_score,
            details={"extracted": extracted, "original": original, "similarity": f"{match_score * 100:.1f}%"}
        )
    
    # ==================== 辅助方法 ====================
    
    def _calculate_similarity(self, s1: str, s2: str) -> float:
        """Levenshtein距离相似度"""
        if s1 == s2:
            return 1.0
        if not s1 or not s2:
            return 0.0
        
        len1, len2 = len(s1), len(s2)
        max_len = max(len1, len2)
        
        if len1 > 100 or len2 > 100:
            import hashlib
            return 1.0 if hashlib.sha256(s1.encode()).hexdigest() == hashlib.sha256(s2.encode()).hexdigest() else 0.0
        
        dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]
        for i in range(len1 + 1):
            dp[i][0] = i
        for j in range(len2 + 1):
            dp[0][j] = j
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                if s1[i-1] == s2[j-1]:
                    dp[i][j] = dp[i-1][j-1]
                else:
                    dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
        
        return 1.0 - (dp[len1][len2] / max_len)
    
    def is_supported(self, file_path: str) -> bool:
        ext = Path(file_path).suffix.lower()
        return ext in self._handlers
    
    def supported_formats(self) -> List[str]:
        return list(self._handlers.keys())


logger.info(f"{__name__} module loaded - StealthMark facade ready")
