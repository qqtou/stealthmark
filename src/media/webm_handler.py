# media/webm_handler.py
"""
WebM视频水印处理器 - VP9无损编码 + LSB

WebM使用VP9编解码器。VP9支持无损模式 (-lossless 1)。
在无损模式下，像素值精确保留，LSB隐写可行。

Author: StealthMark Team
Date: 2026-04-28
"""

import os
import subprocess
import tempfile
import shutil
import logging
from typing import Optional, Dict, Any

import numpy as np

from ..core.base import (
    BaseHandler, WatermarkData, WatermarkStatus,
    EmbedResult, ExtractResult, VerifyResult
)
from ..core.codec import WatermarkCodec
from .video_watermark import get_ffmpeg_path

logger = logging.getLogger(__name__)


class WebMHandler(BaseHandler):
    """
    WebM视频水印处理器
    
    使用VP9无损编码 + RGB Blue通道LSB嵌入。
    VP9无损模式在RGB空间工作，像素级精确。
    """
    
    SUPPORTED_EXTENSIONS = ('.webm',)
    HANDLER_NAME = "webm"
    
    SYNC_PATTERN = bytes([0xAA] * 4)
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.codec = WatermarkCodec(password=self.config.get('password'))
        self.ffmpeg_path = get_ffmpeg_path()
    
    def embed(self, file_path: str, watermark,
              output_path: str, **kwargs) -> EmbedResult:
        logger.info(f"WebM embed: {file_path}")
        
        try:
            if hasattr(watermark, 'content'):
                text = watermark.content
            else:
                text = str(watermark)
            
            encoded = self.codec.encode(text)
            payload = self.SYNC_PATTERN + encoded
            bits = ''.join(format(b, '08b') for b in payload)
            
            import imageio
            reader = imageio.get_reader(file_path)
            meta = reader.get_meta_data()
            fps = meta.get('fps', 30)
            
            frames = []
            for frame in reader:
                frames.append(frame.copy())
            reader.close()
            
            if not frames:
                return EmbedResult(status=WatermarkStatus.FAILED, message="视频无帧数据", file_path=file_path)
            
            # Embed in first frame Blue channel
            first_frame = frames[0].copy()
            h, w = first_frame.shape[0], first_frame.shape[1]
            capacity = h * w
            
            if capacity < len(bits):
                return EmbedResult(status=WatermarkStatus.FAILED, message=f"帧容量不足: {capacity} < {len(bits)}", file_path=file_path)
            
            bit_idx = 0
            for i in range(h):
                for j in range(w):
                    if bit_idx >= len(bits):
                        break
                    first_frame[i, j, 2] = (int(first_frame[i, j, 2]) & 0xFE) | int(bits[bit_idx])
                    bit_idx += 1
                if bit_idx >= len(bits):
                    break
            
            frames[0] = first_frame
            
            # Write frames as PNG sequence
            tmp_dir = tempfile.mkdtemp(prefix='stealthmark_')
            frame_pattern = os.path.join(tmp_dir, 'frame_%08d.png')
            
            import imageio.v3 as iio
            for i, f in enumerate(frames):
                iio.imwrite(frame_pattern % i, f)
            
            # Encode with VP9 lossless
            temp_video = os.path.join(tmp_dir, 'output.webm')
            cmd = [
                self.ffmpeg_path, '-y',
                '-framerate', str(fps),
                '-i', frame_pattern,
                '-c:v', 'libvpx-vp9',
                '-lossless', '1',
                '-pix_fmt', 'rgb24',
                temp_video
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.warning(f"VP9 lossless failed: {result.stderr[:200]}")
                # Cleanup and fail
                self._cleanup_tmp(tmp_dir, len(frames))
                return EmbedResult(
                    status=WatermarkStatus.FAILED,
                    message=f"VP9无损编码失败: {result.stderr[:100]}",
                    file_path=file_path
                )
            
            shutil.copy2(temp_video, output_path)
            self._cleanup_tmp(tmp_dir, len(frames))
            
            return self._create_success_result(output_path)
            
        except Exception as e:
            logger.error(f"WebM embed failed: {e}")
            return EmbedResult(status=WatermarkStatus.FAILED, message=f"嵌入失败: {str(e)}", file_path=file_path)
    
    def _cleanup_tmp(self, tmp_dir, n_frames):
        frame_pattern = os.path.join(tmp_dir, 'frame_%08d.png')
        for i in range(n_frames + 5):
            try:
                os.remove(frame_pattern % i)
            except OSError:
                pass
        for f in ['output.webm']:
            try:
                os.remove(os.path.join(tmp_dir, f))
            except OSError:
                pass
        try:
            os.rmdir(tmp_dir)
        except OSError:
            pass
    
    def extract(self, file_path: str, **kwargs) -> ExtractResult:
        logger.info(f"WebM extract: {file_path}")
        
        try:
            import imageio
            reader = imageio.get_reader(file_path)
            
            first_frame = None
            for frame in reader:
                first_frame = frame.copy()
                break
            reader.close()
            
            if first_frame is None:
                return ExtractResult(status=WatermarkStatus.EXTRACTION_FAILED, message="视频无帧数据", file_path=file_path)
            
            # Extract from Blue channel LSB
            h, w = first_frame.shape[0], first_frame.shape[1]
            bits = []
            max_bits = min(h * w, 50000)
            
            for i in range(h):
                for j in range(w):
                    if len(bits) >= max_bits:
                        break
                    bits.append(first_frame[i, j, 2] & 1)
                if len(bits) >= max_bits:
                    break
            
            bit_str = ''.join(str(b) for b in bits)
            
            # Find sync header
            sync_bits = '10101010101010101010101010101010'
            sync_pos = bit_str.find(sync_bits)
            
            if sync_pos == -1:
                sync_bits = '1010101010101010'
                sync_pos = bit_str.find(sync_bits)
                if sync_pos == -1:
                    return ExtractResult(status=WatermarkStatus.EXTRACTION_FAILED, message="未找到同步头", file_path=file_path)
            
            data_start = sync_pos + len(sync_bits)
            data_bits = bit_str[data_start:]
            
            data_bytes = bytearray()
            for i in range(0, len(data_bits) - 7, 8):
                byte_val = 0
                for j in range(8):
                    byte_val = (byte_val << 1) | int(data_bits[i + j])
                data_bytes.append(byte_val)
            
            success, content, details = self.codec.decode(bytes(data_bytes))
            if success:
                return ExtractResult(
                    status=WatermarkStatus.SUCCESS,
                    watermark=WatermarkData(content=content),
                    file_path=file_path
                )
            return ExtractResult(status=WatermarkStatus.EXTRACTION_FAILED, message=f"解码失败: {details.get('error', '未知')}", file_path=file_path)
            
        except Exception as e:
            logger.error(f"WebM extract failed: {e}")
            return ExtractResult(status=WatermarkStatus.EXTRACTION_FAILED, message=str(e), file_path=file_path)
    
    def verify(self, file_path, original_watermark, **kwargs):
        result = self.extract(file_path)
        if result.status == WatermarkStatus.SUCCESS and result.watermark:
            is_valid = result.watermark.content == original_watermark.content
            return VerifyResult(
                status=WatermarkStatus.SUCCESS if is_valid else WatermarkStatus.VERIFICATION_FAILED,
                is_valid=is_valid, is_integrity_ok=is_valid,
                match_score=1.0 if is_valid else 0.0
            )
        return VerifyResult(status=result.status, is_valid=False, is_integrity_ok=False, match_score=0.0)


logger.info(f"{__name__} module loaded - WebM handler ready")
