# image/heic_handler.py
"""
HEIC/HEIF图片水印处理器 - EXIF UserComment嵌入

技术方案:
1. HEIC是有损格式，LSB/DCT域方法复杂度极高且不可靠
2. 使用EXIF元数据UserComment标签存储水印（最可靠的方案）
3. 依赖 pillow-heif 读写HEIC + piexif 读写EXIF

Author: StealthMark Team
Date: 2026-04-28 (revised 2026-04-29)
"""

import os
import base64
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

# EXIF UserComment 编码标识前缀 (8字节)
_UC_PREFIX = b'ASCII\x00\x00'


def _check_piexif():
    """检查 piexif 是否可用"""
    try:
        import piexif
        return True
    except ImportError:
        return False


def _build_exif_with_watermark(watermark_bytes: bytes) -> bytes:
    """
    构造包含水印的EXIF数据。

    将 base64 编码的水印写入 EXIF UserComment 标签 (tag 0x9286)。

    Args:
        watermark_bytes: 水印原始二进制数据

    Returns:
        bytes: 完整的EXIF字节流

    Raises:
        RuntimeError: piexif 未安装时抛出
    """
    import piexif
    # UserComment 格式: [8字节编码描述符] + 数据
    user_comment = _UC_PREFIX + base64.b64encode(watermark_bytes)
    exif_dict = {'Exif': {piexif.ExifIFD.UserComment: user_comment}}
    return piexif.dump(exif_dict)


def _extract_watermark_from_exif(exif_data: bytes) -> Optional[bytes]:
    """
    从EXIF数据中提取水印。

    Args:
        exif_data: EXIF字节数据

    Returns:
        Optional[bytes]: 解码后的水印二进制数据，未找到返回 None
    """
    import piexif
    try:
        exif_dict = piexif.load(exif_data)
    except Exception as e:
        logger.warning(f"Failed to parse EXIF data: {e}")
        return None

    user_comment = exif_dict.get('Exif', {}).get(piexif.ExifIFD.UserComment)
    if not user_comment or not isinstance(user_comment, bytes):
        return None

    if not user_comment.startswith(_UC_PREFIX):
        logger.debug("UserComment has unexpected prefix, skipping")
        return None

    encoded_b64 = user_comment[len(_UC_PREFIX):]
    return base64.b64decode(encoded_b64)


class HEICHandler(BaseHandler):
    """
    HEIC/HEIF图片水印处理器

    使用 EXIF UserComment 标签嵌入水印。
    原因：Pillow 的 PngInfo 方式对 HEIC 格式无效，
          HEIC 保存时不保留 PngInfo 中的自定义文本字段。

    依赖:
        - pillow-heif: HEIC 文件读写
        - piexif: EXIF 元数据构造与解析

    限制:
        - EXIF 元数据可能被图片编辑器清理
        - 需要安装 piexif 库
    """

    SUPPORTED_EXTENSIONS = ('.heic', '.heif')
    HANDLER_NAME = "heic"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.codec = WatermarkCodec(password=self.config.get('password'))

    def _check_heif_support(self) -> bool:
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

        if not _check_piexif():
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message="需要安装piexif库来写入EXIF元数据: pip install piexif",
                file_path=file_path
            )

        if Image is None:
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message="需要Pillow库",
                file_path=file_path
            )

        error_result = self._validate_file(file_path)
        if error_result:
            return error_result

        try:
            image = Image.open(file_path)

            # 编码水印为二进制
            encoded_data = self.codec.encode(watermark.content)

            # 构造含水印的EXIF数据，通过 exif= 参数传入 save()
            exif_bytes = _build_exif_with_watermark(encoded_data)
            image.save(output_path, format='HEIF', exif=exif_bytes, lossless=True)

            logger.info(f"HEIC embed success: {output_path}")
            return self._create_success_result(output_path)

        except RuntimeError as e:
            logger.error(f"HEIC embed failed (dependency): {e}")
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message=str(e),
                file_path=file_path
            )
        except Exception as e:
            logger.error(f"HEIC embed failed: {e}")
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message=f"嵌入失败: {str(e)}",
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

        if not _check_piexif():
            return ExtractResult(
                status=WatermarkStatus.FAILED,
                message="需要安装piexif库来读取EXIF元数据: pip install piexif",
                file_path=file_path
            )

        if Image is None:
            return ExtractResult(status=WatermarkStatus.FAILED, message="需要Pillow库", file_path=file_path)

        error_result = self._validate_file(file_path)
        if error_result:
            return ExtractResult(
                status=error_result.status,
                message=error_result.message,
                file_path=file_path
            )

        try:
            image = Image.open(file_path)

            # 从 image.info 中获取 EXIF 字节数据
            exif_data = image.info.get('exif')
            if not exif_data:
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message="文件中未找到EXIF元数据",
                    file_path=file_path
                )

            # 从 EXIF 中提取水印
            watermark_bytes = _extract_watermark_from_exif(exif_data)
            if watermark_bytes is None:
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message="EXIF中未找到水印数据",
                    file_path=file_path
                )

            # 用 codec 解码
            success, content, details = self.codec.decode(watermark_bytes)
            if success:
                return ExtractResult(
                    status=WatermarkStatus.SUCCESS,
                    message="水印提取成功",
                    watermark=WatermarkData(content=content),
                    file_path=file_path
                )
            else:
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message=f"解码失败: {details.get('error', '未知')}",
                    file_path=file_path
                )

        except Exception as e:
            logger.error(f"HEIC extract failed: {e}")
            return ExtractResult(
                status=WatermarkStatus.FAILED,
                message=f"提取失败: {str(e)}",
                file_path=file_path
            )

    def verify(self, file_path: str, original_watermark: WatermarkData,
               **kwargs) -> VerifyResult:
        extract_result = self.extract(file_path)
        if not extract_result.is_success or not extract_result.watermark:
            return VerifyResult(
                status=extract_result.status,
                is_valid=False,
                is_integrity_ok=False,
                match_score=0.0,
                message=f"提取失败: {extract_result.message}"
            )
        is_match = extract_result.watermark.content == original_watermark.content
        return VerifyResult(
            status=WatermarkStatus.SUCCESS if is_match else WatermarkStatus.VERIFICATION_FAILED,
            is_valid=is_match,
            is_integrity_ok=True,
            match_score=1.0 if is_match else 0.0,
            message="验证通过" if is_match else "水印不匹配"
        )


logger.info(f"{__name__} module loaded - HEIC handler ready (EXIF mode)")
