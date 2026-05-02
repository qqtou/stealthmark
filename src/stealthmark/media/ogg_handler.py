import logging
import os
from ..core.base import BaseHandler, WatermarkData, WatermarkStatus, EmbedResult, ExtractResult, VerifyResult
from ..core.codec import WatermarkCodec

logger = logging.getLogger(__name__)


class OGGHandler(BaseHandler):
    """
    OGG Vorbis 音频水印处理器

    使用 OGG 元数据字段（Vorbis Comment）存储水印。

    技术方案:
        嵌入: 将水印编码后转为十六进制字符串，写入 'STEALTHMARK' 标签
        提取: 读取 'STEALTHMARK' 标签，十六进制解码后送入 codec 解码

    依赖:
        mutagen: OGG Vorbis 元数据读写

    优点: 元数据方式，音频质量零损失
    缺点: 元数据可被工具清除
    """

    SUPPORTED_EXTENSIONS = ('.ogg',)
    HANDLER_NAME = 'ogg'

    def __init__(self, config=None):
        super().__init__(config)
        self.codec = WatermarkCodec(password=self.config.get('password'))
        logger.debug("OGGHandler initialized")
    
    def embed(self, file_path, watermark, output_path, **kwargs):
        """
        嵌入水印到 OGG 文件

        将编码后的水印以十六进制字符串形式写入 Vorbis Comment 的 'STEALTHMARK' 字段。
        """
        logger.info(f"OGG embed: {file_path} -> {output_path}")

        error_result = self._validate_file(file_path)
        if error_result:
            return error_result

        try:
            import shutil
            shutil.copy2(file_path, output_path)

            from mutagen.oggvorbis import OggVorbis
            audio = OggVorbis(output_path)
            data = self.codec.encode(watermark.content)
            if not data:
                logger.error("OGG embed: codec encode returned empty data")
                return EmbedResult(status=WatermarkStatus.FAILED, message='Codec encode failed', file_path=output_path, output_path=output_path)

            audio['STEALTHMARK'] = data.hex()
            audio.save()
            logger.info(f"OGG embed success: {output_path}")

            return EmbedResult(
                status=WatermarkStatus.SUCCESS,
                message='Watermark embedded in OGG Vorbis Comment',
                file_path=output_path,
                output_path=output_path
            )
        except Exception as e:
            import traceback
            logger.error(f"OGG embed failed: {e}\n{traceback.format_exc()}")
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message=f'OGG embed failed: {str(e)}',
                file_path=file_path,
                output_path=output_path
            )
    
    def extract(self, file_path, **kwargs):
        """
        从 OGG 文件提取水印

        读取 Vorbis Comment 的 'STEALTHMARK' 字段，十六进制解码后送入 codec 解码。
        """
        logger.info(f"OGG extract: {file_path}")

        error_result = self._validate_file(file_path)
        if error_result:
            return ExtractResult(status=error_result.status, message=error_result.message, file_path=file_path)

        try:
            from mutagen.oggvorbis import OggVorbis
            audio = OggVorbis(file_path)

            if 'STEALTHMARK' not in audio:
                logger.warning(f"OGG extract: STEALTHMARK tag not found in {file_path}")
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message='No StealthMark found in OGG metadata',
                    file_path=file_path
                )

            data_hex = audio['STEALTHMARK'][0]
            data = bytes.fromhex(data_hex)
            success, content, details = self.codec.decode(data)

            if success:
                logger.info(f"OGG extract success: {content[:30]}...")
                return ExtractResult(
                    status=WatermarkStatus.SUCCESS,
                    message='Watermark extracted from OGG',
                    file_path=file_path,
                    watermark=WatermarkData(content=content)
                )
            else:
                logger.warning(f"OGG decode failed: {details}")
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message=f'Decode failed: {details.get("error", "Unknown")}',
                    file_path=file_path
                )
        except Exception as e:
            import traceback
            logger.error(f"OGG extract failed: {e}\n{traceback.format_exc()}")
            return ExtractResult(
                status=WatermarkStatus.EXTRACTION_FAILED,
                message=f'OGG extract failed: {str(e)}',
                file_path=file_path
            )
    
    def verify(self, file_path, watermark, **kwargs):
        """
        验证 OGG 水印

        Args:
            file_path: 含水印文件路径
            watermark: 原始水印数据

        Returns:
            VerifyResult: 验证结果
        """
        logger.info(f"OGG verify: {file_path}")

        extract_result = self.extract(file_path)
        if not extract_result.is_success or not extract_result.watermark:
            return VerifyResult(
                status=extract_result.status,
                message=extract_result.message,
                file_path=file_path,
                is_valid=False,
                is_integrity_ok=False,
                match_score=0.0
            )
        is_valid = extract_result.watermark.content == watermark.content
        return VerifyResult(
            status=WatermarkStatus.SUCCESS if is_valid else WatermarkStatus.VERIFICATION_FAILED,
            message='Verify success' if is_valid else 'Content mismatch',
            file_path=file_path,
            is_valid=is_valid,
            is_integrity_ok=True,
            match_score=1.0 if is_valid else 0.0
        )


logger.info(f"{__name__} module loaded - OGG handler ready")
