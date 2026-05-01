import os
from ..core.base import BaseHandler, WatermarkData, WatermarkStatus, EmbedResult, ExtractResult, VerifyResult
from ..core.codec import WatermarkCodec

class OGGHandler(BaseHandler):
    SUPPORTED_EXTENSIONS = ('.ogg',)
    HANDLER_NAME = 'ogg'
    
    def __init__(self, config=None):
        super().__init__(config)
        self.codec = WatermarkCodec(password=self.config.get('password'))
    
    def embed(self, file_path, watermark, output_path, **kwargs):
        try:
            # 复制文件到输出路径
            import shutil
            shutil.copy2(file_path, output_path)
            
            # 用mutagen写入metadata
            from mutagen.oggvorbis import OggVorbis
            audio = OggVorbis(output_path)
            data = self.codec.encode(watermark.content)
            if not data:
                return EmbedResult(status=WatermarkStatus.FAILED, message='Codec encode failed', file_path=output_path)
            
            audio['STEALTHMARK'] = data.hex()
            audio.save()
            
            return EmbedResult(
                status=WatermarkStatus.SUCCESS,
                message='Watermark embedded in OGG Vorbis Comment',
                file_path=output_path,
                output_path=output_path
            )
        except Exception as e:
            import traceback
            logger = __import__('logging').getLogger(__name__)
            logger.error(f"OGG embed exception: {e}")
            logger.error(traceback.format_exc())
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message=f'OGG embed failed: {str(e)}',
                file_path=output_path
            )
    
    def extract(self, file_path, **kwargs):
        try:
            from mutagen.oggvorbis import OggVorbis
            audio = OggVorbis(file_path)
            
            if 'STEALTHMARK' not in audio:
                return ExtractResult(
                    status=WatermarkStatus.FAILED,
                    message='No StealthMark found in OGG metadata',
                    file_path=file_path
                )
            
            data_hex = audio['STEALTHMARK'][0]  # mutagen returns list
            data = bytes.fromhex(data_hex)
            success, content, details = self.codec.decode(data)
            
            if success:
                return ExtractResult(
                    status=WatermarkStatus.SUCCESS,
                    message='Watermark extracted from OGG',
                    file_path=file_path,
                    watermark=WatermarkData(content=content)
                )
            else:
                return ExtractResult(
                    status=WatermarkStatus.FAILED,
                    message=f'Decode failed: {details.get("error", "Unknown")}',
                    file_path=file_path
                )
        except Exception as e:
            import traceback
            logger = __import__('logging').getLogger(__name__)
            logger.error(f"OGG extract exception: {e}")
            logger.error(traceback.format_exc())
            return ExtractResult(
                status=WatermarkStatus.FAILED,
                message=f'OGG extract failed: {str(e)}',
                file_path=file_path
            )
    
    def verify(self, file_path, watermark, **kwargs):
        extract_result = self.extract(file_path)
        if not extract_result.is_success or not extract_result.watermark:
            return VerifyResult(
                status=extract_result.status,
                message=extract_result.message,
                file_path=file_path,
                is_valid=False
            )
        is_valid = extract_result.watermark.content == watermark.content
        return VerifyResult(
            status=WatermarkStatus.SUCCESS if is_valid else WatermarkStatus.VERIFICATION_FAILED,
            message='Verify success' if is_valid else 'Content mismatch',
            file_path=file_path,
            is_valid=is_valid
        )
