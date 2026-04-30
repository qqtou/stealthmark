import os
import subprocess
import re
from ..core.base import BaseHandler, WatermarkData, WatermarkStatus, EmbedResult, ExtractResult, VerifyResult
from ..core.codec import WatermarkCodec

def get_ffmpeg_path() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return 'ffmpeg'

class OGGHandler(BaseHandler):
    SUPPORTED_EXTENSIONS = ('.ogg',)
    HANDLER_NAME = 'ogg'
    
    def __init__(self, config=None):
        super().__init__(config)
        self.codec = WatermarkCodec(password=self.config.get('password'))
        self.ffmpeg_path = get_ffmpeg_path()
    
    def embed(self, file_path, watermark, output_path, **kwargs):
        try:
            data = self.codec.encode(watermark.content)
            if not data:
                return EmbedResult(status=WatermarkStatus.FAILED, message='Codec encode failed', file_path=output_path)
            
            # 用ffmpeg编码为OGG并添加metadata
            cmd = [
                self.ffmpeg_path, '-y',
                '-i', file_path,
                '-c:a', 'libvorbis',
                '-metadata', f'STEALTHMARK={data.hex()}',
                output_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return EmbedResult(
                    status=WatermarkStatus.FAILED,
                    message=f'ffmpeg failed: {result.stderr[-200:]}',
                    file_path=output_path
                )
            
            return EmbedResult(
                status=WatermarkStatus.SUCCESS,
                message='Watermark embedded in OGG metadata',
                file_path=output_path,
                output_path=output_path
            )
        except Exception as e:
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message=f'OGG embed failed: {str(e)}',
                file_path=output_path
            )
    
    def extract(self, file_path, **kwargs):
        try:
            # 用ffmpeg读取metadata（解析stderr输出）
            cmd = [self.ffmpeg_path, '-i', file_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # ffmpeg会在stderr中输出metadata
            stderr = result.stderr
            
            # 查找STEALTHMARK字段（格式：STEALTHMARK     : 534d41524b...）
            pattern = r'STEALTHMARK\s*:\s*([0-9a-fA-F]+)'
            match = re.search(pattern, stderr)
            if not match:
                return ExtractResult(
                    status=WatermarkStatus.FAILED,
                    message='No StealthMark found in OGG metadata',
                    file_path=file_path
                )
            
            data_hex = match.group(1)
            data = bytes.fromhex(data_hex)
            success, content, details = self.codec.decode(data)
            if success:
                return ExtractResult(
                    status=WatermarkStatus.SUCCESS,
                    message='Watermark extracted from OGG metadata',
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
