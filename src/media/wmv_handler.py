# media/wmv_handler.py
"""
WMV视频水印处理器 - ASF元数据嵌入

技术方案:
1. WMV/ASF容器不支持无损编码，LSB方案不可行
2. 使用ASF元数据（Content Description）嵌入水印
3. ffmpeg可读写ASF元数据

Author: StealthMark Team
Date: 2026-04-28
"""

import os
import subprocess
import json
import logging
import tempfile
from typing import Optional, Dict, Any

from ..core.base import (
    BaseHandler, WatermarkData, WatermarkStatus,
    EmbedResult, ExtractResult, VerifyResult
)
from ..core.codec import WatermarkCodec
from .video_watermark import get_ffmpeg_path

logger = logging.getLogger(__name__)


class WMVHandler(BaseHandler):
    """
    WMV视频水印处理器
    
    WMV不支持无损编码，使用ASF元数据嵌入水印。
    通过ffmpeg的-metadata参数写入/读取元数据。
    """
    
    SUPPORTED_EXTENSIONS = ('.wmv',)
    HANDLER_NAME = "wmv"
    META_KEY = "SMMark"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.codec = WatermarkCodec(password=self.config.get('password'))
        self.ffmpeg_path = get_ffmpeg_path()
    
    def embed(self, file_path: str, watermark,
              output_path: str, **kwargs) -> EmbedResult:
        logger.info(f"WMV embed: {file_path}")
        
        error_result = self._validate_file(file_path)
        if error_result:
            return error_result
        
        try:
            if hasattr(watermark, 'content'):
                text = watermark.content
            else:
                text = str(watermark)
            
            encoded_data = self.codec.encode(text)
            encoded_b64 = self.codec.to_base64(encoded_data)
            
            # Use ffmpeg to copy video + add metadata
            cmd = [
                self.ffmpeg_path, '-y',
                '-i', file_path,
                '-c', 'copy',
                '-metadata', f'{self.META_KEY}={encoded_b64}',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning(f"ffmpeg metadata embed failed, trying re-encode: {result.stderr[:200]}")
                # Fallback: re-encode with metadata
                cmd = [
                    self.ffmpeg_path, '-y',
                    '-i', file_path,
                    '-c:v', 'wmv2',
                    '-q:v', '1',  # High quality
                    '-c:a', 'wmav2',
                    '-metadata', f'{self.META_KEY}={encoded_b64}',
                    output_path
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    return EmbedResult(
                        status=WatermarkStatus.FAILED,
                        message=f"ffmpeg执行失败: {result.stderr[:100]}",
                        file_path=file_path
                    )
            
            return self._create_success_result(output_path)
            
        except Exception as e:
            logger.error(f"WMV embed failed: {e}")
            return EmbedResult(status=WatermarkStatus.FAILED, message=f"嵌入失败: {str(e)}", file_path=file_path)
    
    def extract(self, file_path: str, **kwargs) -> ExtractResult:
        logger.info(f"WMV extract: {file_path}")
        
        error_result = self._validate_file(file_path)
        if error_result:
            return ExtractResult(status=error_result.status, message=error_result.message, file_path=file_path)
        
        try:
            # Use ffprobe to read metadata
            cmd = [
                self.ffmpeg_path.replace('ffmpeg', 'ffprobe'),
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message="ffprobe执行失败",
                    file_path=file_path
                )
            
            probe = json.loads(result.stdout)
            tags = probe.get('format', {}).get('tags', {})
            
            # Search for SMMark in tags (case-insensitive)
            smmark = None
            for key, value in tags.items():
                if key.lower() == self.META_KEY.lower():
                    smmark = value
                    break
            
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
                message="未找到水印元数据",
                file_path=file_path
            )
            
        except Exception as e:
            logger.error(f"WMV extract failed: {e}")
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


logger.info(f"{__name__} module loaded - WMV handler ready")
