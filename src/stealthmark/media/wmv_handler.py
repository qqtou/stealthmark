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
import logging
import tempfile
from typing import Optional, Dict, Any

import av

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
        """初始化WMV处理器。

        Args:
            config: 可选配置字典，支持 'password' 键指定加密密码。
        """
        super().__init__(config)
        self.codec = WatermarkCodec(password=self.config.get('password'))
        self.ffmpeg_path = get_ffmpeg_path()
        logger.debug("WMVHandler initialized")

    def embed(self, file_path: str, watermark,
              output_path: str, **kwargs) -> EmbedResult:
        """
        嵌入水印到 WMV 文件

        使用 ffmpeg 将编码后的水印写入 ASF 元数据字段。

        Args:
            file_path (str): 源 WMV 文件路径
            watermark (WatermarkData): 水印数据
            output_path (str): 输出文件路径
            **kwargs: 其他参数

        Returns:
            EmbedResult: 嵌入结果
        """
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

            logger.debug(f"Running ffmpeg: {' '.join(cmd)}")
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
        """
        从 WMV 文件提取水印

        使用 PyAV 读取 ASF 元数据，查找 SMMark 字段后解码。

        Args:
            file_path (str): WMV 文件路径
            **kwargs: 其他参数

        Returns:
            ExtractResult: 提取结果
        """
        logger.info(f"WMV extract: {file_path}")

        error_result = self._validate_file(file_path)
        if error_result:
            return ExtractResult(status=error_result.status, message=error_result.message, file_path=file_path)

        try:
            # Use PyAV to read metadata (no ffprobe needed)
            with av.open(file_path) as container:
                tags = container.metadata or {}

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
                    logger.info(f"WMV extract success: {content[:30]}...")
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
        """
        验证 WMV 水印

        Args:
            file_path: 含水印文件路径
            original_watermark: 原始水印数据

        Returns:
            VerifyResult: 验证结果
        """
        logger.info(f"WMV verify: {file_path}")

        extract_result = self.extract(file_path)
        if not extract_result.is_success or not extract_result.watermark:
            return VerifyResult(status=extract_result.status, is_valid=False, is_integrity_ok=False, match_score=0.0)
        is_match = extract_result.watermark.content == original_watermark.content
        return VerifyResult(
            status=WatermarkStatus.SUCCESS if is_match else WatermarkStatus.VERIFICATION_FAILED,
            is_valid=is_match, is_integrity_ok=True, match_score=1.0 if is_match else 0.0
        )


logger.info(f"{__name__} module loaded - WMV handler ready")