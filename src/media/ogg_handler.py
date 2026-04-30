import os
import subprocess
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
                '-c:a', 'libvorbis',  # OGG必须用libvorbis编码
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
            # 用ffprobe读取metadata
            ffprobe = self.ffmpeg_path.replace('ffmpeg', 'ffprobe')
            if not os.path.exists(ffprobe):
                ffprobe = 'ffprobe'  # 尝试系统PATH
            
            cmd = [
                ffprobe,
                '-v', 'quiet',
                '-show_entries', 'format_tags=STEALTHMARK',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0 or not result.stdout.strip():
                return ExtractResult(
                    status=WatermarkStatus.FAILED,
                    message='No StealthMark found in OGG metadata',
                    file_path=file_path
                )
            
            data_hex = result.stdout.strip()
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
                    message=f'Decode failed: {details.get("error", "未知")}',
                    file_path=file_path
                )
        except Exception as e:
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
