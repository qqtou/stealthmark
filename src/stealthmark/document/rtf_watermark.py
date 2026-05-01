# document/rtf_watermark.py
"""
RTF文档水印处理器 - 隐藏控制组嵌入

技术方案:
1. RTF支持{\\*\\keyword ...}格式，标记为"可忽略目标"
2. 不识别该目标的RTF阅读器会自动跳过
3. 将水印Base64编码嵌入到{\\*\\smark ...}组中

依赖: 无特殊依赖 (仅使用标准库)
"""

import os
import re
from typing import Optional, Dict, Any
import logging

from ..core.base import (
    BaseHandler, WatermarkData, WatermarkStatus,
    EmbedResult, ExtractResult, VerifyResult
)
from ..core.codec import WatermarkCodec

logger = logging.getLogger(__name__)


class RTFHandler(BaseHandler):
    """
    RTF文档水印处理器
    
    使用RTF可忽略目标组{\\*\\smark ...}嵌入水印。
    RTF阅读器会自动跳过不认识的目标，不影响文档显示。
    """
    
    SUPPORTED_EXTENSIONS = ('.rtf',)
    HANDLER_NAME = "rtf"
    MARKER_BEGIN = r'{\*\smark '
    MARKER_END = '}'
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.codec = WatermarkCodec(password=self.config.get('password'))
    
    def embed(self, file_path: str, watermark: WatermarkData,
              output_path: str, **kwargs) -> EmbedResult:
        logger.info(f"RTF embed: {file_path} -> {output_path}")
        
        error_result = self._validate_file(file_path)
        if error_result:
            return error_result
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            encoded_data = self.codec.encode(watermark.content)
            encoded_b64 = self.codec.to_base64(encoded_data)
            
            # Remove existing watermark
            content = re.sub(r'\{\\\*\\smark [^}]*\}', '', content)
            
            # Insert watermark before closing brace of header or at beginning
            # Find the first \rtf1 group
            rtf_match = re.search(r'\{\\rtf1', content)
            if rtf_match:
                # Insert after the header area (before first \par or text content)
                # Find end of font/color table definitions
                insert_pos = rtf_match.end()
                # Skip past header tables
                for table_pattern in [r'\\fonttbl[^}]*\}', r'\\colortbl[^}]*\}']:
                    table_match = re.search(table_pattern, content[insert_pos:])
                    if table_match:
                        insert_pos += table_match.end()
                
                watermark_block = f'\n{self.MARKER_BEGIN}{encoded_b64}{self.MARKER_END}\n'
                content = content[:insert_pos] + watermark_block + content[insert_pos:]
            else:
                # Not a valid RTF, just append
                watermark_block = f'\n{self.MARKER_BEGIN}{encoded_b64}{self.MARKER_END}\n'
                content += watermark_block
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return self._create_success_result(output_path)
            
        except Exception as e:
            logger.error(f"RTF embed failed: {e}")
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message=f"嵌入失败: {str(e)}",
                file_path=file_path
            )
    
    def extract(self, file_path: str, **kwargs) -> ExtractResult:
        logger.info(f"RTF extract: {file_path}")
        
        error_result = self._validate_file(file_path)
        if error_result:
            return ExtractResult(status=error_result.status, message=error_result.message, file_path=file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            match = re.search(r'\{\\\*\\smark ([^}]*)\}', content)
            if match:
                b64_data = match.group(1).strip()
                encoded_data = self.codec.from_base64(b64_data)
                success, text, details = self.codec.decode(encoded_data)
                if success:
                    return ExtractResult(
                        status=WatermarkStatus.SUCCESS,
                        message="水印提取成功",
                        file_path=file_path,
                        watermark=WatermarkData(content=text)
                    )
            
            return ExtractResult(
                status=WatermarkStatus.EXTRACTION_FAILED,
                message="未找到水印",
                file_path=file_path
            )
            
        except Exception as e:
            logger.error(f"RTF extract failed: {e}")
            return ExtractResult(
                status=WatermarkStatus.EXTRACTION_FAILED,
                message=f"提取失败: {str(e)}",
                file_path=file_path
            )
    
    def verify(self, file_path, original_watermark, **kwargs):
        extract_result = self.extract(file_path)
        if not extract_result.is_success or not extract_result.watermark:
            return VerifyResult(
                status=extract_result.status,
                is_valid=False, is_integrity_ok=False, match_score=0.0
            )
        is_match = extract_result.watermark.content == original_watermark.content
        return VerifyResult(
            status=WatermarkStatus.SUCCESS if is_match else WatermarkStatus.VERIFICATION_FAILED,
            is_valid=is_match, is_integrity_ok=True,
            match_score=1.0 if is_match else 0.0
        )


logger.info(f"{__name__} module loaded - RTF handler ready")
