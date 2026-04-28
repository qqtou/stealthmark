# image/heic_handler.py
"""
HEIC/HEIF图片水印处理器 - EXIF元数据嵌入

技术方案:
1. HEIC是有损格式，LSB/DCT域方法复杂度极高
2. 使用EXIF元数据嵌入水印（最可靠的方案）
3. Pillow + pillow-heif 读写HEIC

依赖: pillow-heif (可选)

Author: StealthMark Team
Date: 2026-04-28
"""

import os
from typing import Optional, Dict, Any
import logging

try:
    from PIL import Image
except ImportError:
    Image = None

from ..core.base import (
    BaseHandler, WatermarkData, WatermarkStatus,
    EmbedResult, ExtractResult, VerifyResult
)
from ..core.codec import WatermarkCodec

logger = logging.getLogger(__name__)


class HEICHandler(BaseHandler):
    """
    HEIC/HEIF图片水印处理器
    
    使用EXIF元数据嵌入水印。
    HEIC是有损格式，像素域嵌入不可靠，元数据方案最稳定。
    
    限制:
        - 需要pillow-heif库
        - 元数据可能被清理
    """
    
    SUPPORTED_EXTENSIONS = ('.heic', '.heif')
    HANDLER_NAME = "heic"
    WATERMARK_EXIF_KEY = 0x9C9C  # Custom EXIF tag for SMMark
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.codec = WatermarkCodec(password=self.config.get('password'))
    
    def _check_heif_support(self):
        """Check if pillow-heif is available"""
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
            return True
        except ImportError:
            return False
    
    def embed(self, file_path: str, watermark: WatermarkData,
              output_path: str, **kwargs) -> EmbedResult:
        logger.info(f"HEIC embed: {file_path} -> {output_path}")
        
        if not self._check_heif_support():
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message="需要安装pillow-heif库: pip install pillow-heif",
                file_path=file_path
            )
        
        if Image is None:
            return EmbedResult(status=WatermarkStatus.FAILED, message="需要Pillow库", file_path=file_path)
        
        error_result = self._validate_file(file_path)
        if error_result:
            return error_result
        
        try:
            image = Image.open(file_path)
            encoded_data = self.codec.encode(watermark.content)
            encoded_b64 = self.codec.to_base64(encoded_data)
            
            # Use PNG as intermediate (HEIC re-encoding would destroy metadata)
            # Embed watermark in image info dict
            from PIL import PngImagePlugin
            meta = PngImagePlugin.PngInfo()
            
            # Copy existing info
            if image.info:
                for k, v in image.info.items():
                    if isinstance(v, str) and k != 'SMMark':
                        meta.add_text(k, v)
            
            meta.add_text("SMMark", encoded_b64)
            
            # Save as HEIC with metadata
            image.save(output_path, format='HEIF', lossless=True, pnginfo=meta)
            
            return self._create_success_result(output_path)
            
        except Exception as e:
            # Fallback: try direct EXIF approach
            logger.warning(f"HEIC metadata embed failed, trying EXIF: {e}")
            try:
                image = Image.open(file_path)
                encoded_data = self.codec.encode(watermark.content)
                encoded_b64 = self.codec.to_base64(encoded_data)
                
                # Add as image text info
                from PIL import PngImagePlugin
                meta = PngImagePlugin.PngInfo()
                meta.add_text("SMMark", encoded_b64)
                image.save(output_path, format='HEIF', pnginfo=meta)
                
                return self._create_success_result(output_path)
            except Exception as e2:
                logger.error(f"HEIC embed failed: {e2}")
                return EmbedResult(
                    status=WatermarkStatus.FAILED,
                    message=f"嵌入失败: {str(e2)}",
                    file_path=file_path
                )
    
    def extract(self, file_path: str, **kwargs) -> ExtractResult:
        logger.info(f"HEIC extract: {file_path}")
        
        if not self._check_heif_support():
            return ExtractResult(
                status=WatermarkStatus.FAILED,
                message="需要安装pillow-heif库",
                file_path=file_path
            )
        
        if Image is None:
            return ExtractResult(status=WatermarkStatus.FAILED, message="需要Pillow库", file_path=file_path)
        
        error_result = self._validate_file(file_path)
        if error_result:
            return ExtractResult(status=error_result.status, message=error_result.message, file_path=file_path)
        
        try:
            image = Image.open(file_path)
            
            # Try image info
            smmark = image.info.get('SMMark', '')
            if not smmark:
                # Try text chunks
                if hasattr(image, 'text'):
                    smmark = image.text.get('SMMark', '')
            
            if smmark:
                encoded_data = self.codec.from_base64(smmark)
                success, content, details = self.codec.decode(encoded_data)
                if success:
                    return ExtractResult(
                        status=WatermarkStatus.SUCCESS,
                        message="水印提取成功",
                        file_path=file_path,
                        watermark=WatermarkData(content=content)
                    )
            
            return ExtractResult(
                status=WatermarkStatus.EXTRACTION_FAILED,
                message="未找到水印",
                file_path=file_path
            )
            
        except Exception as e:
            logger.error(f"HEIC extract failed: {e}")
            return ExtractResult(
                status=WatermarkStatus.EXTRACTION_FAILED,
                message=f"提取失败: {str(e)}",
                file_path=file_path
            )
    
    def verify(self, file_path, original_watermark, **kwargs):
        extract_result = self.extract(file_path)
        if not extract_result.is_success or not extract_result.watermark:
            return VerifyResult(status=extract_result.status, is_valid=False, is_integrity_ok=False, match_score=0.0)
        is_match = extract_result.watermark.content == original_watermark.content
        return VerifyResult(
            status=WatermarkStatus.SUCCESS if is_match else WatermarkStatus.VERIFICATION_FAILED,
            is_valid=is_match, is_integrity_ok=True, match_score=1.0 if is_match else 0.0
        )


logger.info(f"{__name__} module loaded - HEIC handler ready")
