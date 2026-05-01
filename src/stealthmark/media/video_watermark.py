"""
视频水印处理器 - 不可见LSB水印

使用 imageio + ffmpeg 无损编码 + RGB空间LSB嵌入

关键设计:
- 嵌入位置: RGB Blue通道LSB (人眼最不敏感)
- 编码方式: libx264rgb -crf 0 (RGB空间无损, 不经YUV转换, 像素级精确)
- 备选编码: ffv1 (无专利无损编解码器)
- 帧选择: 仅修改第一帧(足够容纳水印数据)

Author: StealthMark Team
Date: 2026-04-28
"""

import os
import subprocess
import logging
import tempfile
from typing import Optional, Dict, Any

import numpy as np

from ..core.base import (
    BaseHandler, WatermarkData, WatermarkStatus,
    EmbedResult, ExtractResult, VerifyResult
)
from ..core.codec import WatermarkCodec

logger = logging.getLogger(__name__)


def get_ffmpeg_path() -> str:
    """获取ffmpeg路径"""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return 'ffmpeg'


class VideoHandler(BaseHandler):
    """
    视频水印处理器 - 不可见LSB水印
    
    在RGB Blue通道LSB嵌入数据, 使用无损编码保存.
    libx264rgb -crf 0 在RGB空间工作, 不做YUV转换,
    因此像素值在编码-解码循环中精确保留.
    """
    
    SUPPORTED_EXTENSIONS = ('.mp4', '.avi', '.mkv', '.mov')
    HANDLER_NAME = "video"
    
    # 水印同步头: 0xAA = 10101010, 重复8次（冗余）
    SYNC_PATTERN = bytes([0xAA] * 8)
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.codec = WatermarkCodec(password=self.config.get('password'))
        self.ffmpeg_path = get_ffmpeg_path()
        logger.debug(f"VideoHandler: ffmpeg={self.ffmpeg_path}")
    
    def _prepare_data_bits(self, watermark) -> Optional[list]:
        """
        准备水印数据比特序列
        
        Args:
            watermark: 水印数据
            
        Returns:
            list: 比特列表，失败返回None
        """
        try:
            # 转换水印数据
            if hasattr(watermark, 'content'):
                text = watermark.content
            else:
                text = str(watermark)
            
            # 编码: 同步头 + codec编码数据
            encoded = self.codec.encode(text)
            payload = self.SYNC_PATTERN + encoded
            bits = [int(b) for b in ''.join(format(b, '08b') for b in payload)]
            logger.debug(f"Prepared {len(bits)} bits from watermark")
            return bits
        except Exception as e:
            logger.error(f"Failed to prepare data bits: {e}")
            return None
    
    def embed(self, file_path: str, watermark,
              output_path: str, **kwargs) -> EmbedResult:
        """嵌入不可见水印到视频"""
        logger.info(f"Video embed (LSB): {file_path}")
        
        try:
            # 转换水印数据
            if hasattr(watermark, 'content'):
                text = watermark.content
            else:
                text = str(watermark)
            
            # 编码: 同步头 + codec编码数据
            encoded = self.codec.encode(text)
            payload = self.SYNC_PATTERN + encoded
            bits = ''.join(format(b, '08b') for b in payload)
            logger.debug(f"Payload: {len(payload)} bytes = {len(bits)} bits")
            
            # 用 ffmpeg 将视频解码为原始帧
            import imageio
            reader = imageio.get_reader(file_path)
            meta = reader.get_meta_data()
            fps = meta.get('fps', 30)
            
            frames = []
            for frame in reader:
                frames.append(frame.copy())
            reader.close()
            
            if not frames:
                return EmbedResult(
                    status=WatermarkStatus.FAILED,
                    message="视频无帧数据",
                    file_path=file_path
                )
            
            # 只在第一帧的Blue通道嵌入LSB
            first_frame = frames[0].copy()
            h, w = first_frame.shape[0], first_frame.shape[1]
            capacity = h * w  # Blue通道像素数
            logger.debug(f"Frame 0: {w}x{h}, capacity={capacity} bits, need={len(bits)} bits")
            
            if capacity < len(bits):
                return EmbedResult(
                    status=WatermarkStatus.FAILED,
                    message=f"帧容量不足: {capacity} < {len(bits)}",
                    file_path=file_path
                )
            
            # 单帧嵌入: 只修改第一帧（足够容纳水印数据）
            # 注意: 多帧分散会导致字节边界错位，提取复杂度高
            first_frame = frames[0].copy()
            h, w = first_frame.shape[0], first_frame.shape[1]
            
            # 在第一帧的Blue通道嵌入所有比特
            bit_pos = 0
            for i in range(h):
                for j in range(w):
                    if bit_pos >= len(bits):
                        break
                    first_frame[i, j, 2] = (int(first_frame[i, j, 2]) & 0xFE) | int(bits[bit_pos])
                    bit_pos += 1
                if bit_pos >= len(bits):
                    break
            
            frames[0] = first_frame
            logger.debug(f"Embedded {bit_pos} bits into frame 0 Blue channel")
            
            # 写入: 用ffmpeg无损编码
            # 先写帧序列为PNG
            tmp_dir = tempfile.mkdtemp(prefix='stealthmark_')
            frame_pattern = os.path.join(tmp_dir, 'frame_%08d.png')
            
            import imageio.v3 as iio
            for i, f in enumerate(frames):
                iio.imwrite(frame_pattern % i, f)
            
            # 用 libx264rgb -crf 0 编码 (RGB空间无损)
            temp_video = os.path.join(tmp_dir, 'output.mp4')
            
            # 尝试 libx264rgb (RGB无损)
            cmd_rgb = [
                self.ffmpeg_path, '-y',
                '-framerate', str(fps),
                '-i', frame_pattern,
                '-c:v', 'libx264rgb',
                '-preset', 'ultrafast',
                '-crf', '0',
                temp_video
            ]
            
            result = subprocess.run(cmd_rgb, capture_output=True, text=True)
            
            if result.returncode != 0:
                # fallback: 用 ffv1 编码到 mkv
                logger.warning(f"libx264rgb failed, trying ffv1: {result.stderr[:200]}")
                temp_video = os.path.join(tmp_dir, 'output.mkv')
                cmd_ffv1 = [
                    self.ffmpeg_path, '-y',
                    '-framerate', str(fps),
                    '-i', frame_pattern,
                    '-c:v', 'ffv1',
                    '-level', '3',
                    temp_video
                ]
                result = subprocess.run(cmd_ffv1, capture_output=True, text=True)
                
                if result.returncode != 0:
                    # 最后fallback: copy原视频 + 附加数据
                    logger.warning(f"ffv1 failed: {result.stderr[:200]}")
                    # 清理
                    self._cleanup_tmp(tmp_dir, len(frames))
                    return EmbedResult(
                        status=WatermarkStatus.FAILED,
                        message=f"无损编码失败",
                        file_path=file_path
                    )
            
            # 复制到目标路径
            import shutil
            shutil.copy2(temp_video, output_path)
            
            # 如果输出扩展名和编码不匹配, 尝试重命名
            out_ext = os.path.splitext(output_path)[1].lower()
            vid_ext = os.path.splitext(temp_video)[1].lower()
            if out_ext != vid_ext:
                logger.info(f"Output ext {out_ext} != video ext {vid_ext}, copied as-is")
            
            # 清理临时文件
            self._cleanup_tmp(tmp_dir, len(frames))
            
            logger.info(f"Video embed success: {bit_pos} bits, {len(frames)} frames")
            return self._create_success_result(output_path)
            
        except Exception as e:
            logger.error(f"Video embed failed: {e}")
            import traceback
            traceback.print_exc()
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message=f"嵌入失败: {str(e)}",
                file_path=file_path
            )
    
    def _cleanup_tmp(self, tmp_dir: str, n_frames: int):
        """清理临时文件"""
        frame_pattern = os.path.join(tmp_dir, 'frame_%08d.png')
        for i in range(n_frames + 5):
            try:
                os.remove(frame_pattern % i)
            except OSError:
                pass
        for f in ['output.mp4', 'output.mkv', 'output.avi']:
            try:
                os.remove(os.path.join(tmp_dir, f))
            except OSError:
                pass
        try:
            os.rmdir(tmp_dir)
        except OSError:
            pass
    
    def extract(self, file_path: str, **kwargs) -> ExtractResult:
        """提取视频水印"""
        logger.info(f"Video extract: {file_path}")
        
        try:
            import imageio
            reader = imageio.get_reader(file_path)
            
            # 读取前3帧（与embed一致）
            frames = []
            for i, frame in enumerate(reader):
                if i >= 3:
                    break
                frames.append(frame.copy())
            reader.close()
            
            if not frames:
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message="视频无帧数据",
                    file_path=file_path
                )
            
            # 从所有帧的Blue通道提取LSB并合并
            bits = []
            max_bits = 50000  # 最多读这么多位
            
            for frame in frames:
                h, w = frame.shape[0], frame.shape[1]
                for i in range(h):
                    for j in range(w):
                        if len(bits) >= max_bits:
                            break
                        bits.append(frame[i, j, 2] & 1)
                    if len(bits) >= max_bits:
                        break
                if len(bits) >= max_bits:
                    break
            
            bit_str = ''.join(str(b) for b in bits)
            logger.debug(f"Extracted {len(bits)} bits from {len(frames)} frames Blue channel")
            
            # 查找同步头 (0xAA * 8 = 10101010重复8次)
            sync_bits = '1010101010101010101010101010101010101010101010101010101010101010'
            sync_pos = bit_str.find(sync_bits)
            
            if sync_pos == -1:
                # 尝试短同步头 (4字节)
                sync_bits = '10101010101010101010101010101010'
                sync_pos = bit_str.find(sync_bits)
                if sync_pos == -1:
                    return ExtractResult(
                        status=WatermarkStatus.EXTRACTION_FAILED,
                        message="未找到同步头",
                        file_path=file_path
                    )
            
            # 从同步头后开始, 转为字节
            data_start = sync_pos + len(sync_bits)
            data_bits = bit_str[data_start:]
            
            # 比特转字节
            data_bytes = bytearray()
            for i in range(0, len(data_bits) - 7, 8):
                byte_val = 0
                for j in range(8):
                    byte_val = (byte_val << 1) | int(data_bits[i + j])
                data_bytes.append(byte_val)
            
            logger.debug(f"Data after sync: {len(data_bytes)} bytes, first 10: {data_bytes[:10].hex()}")
            
            # 用codec解码
            success, content, details = self.codec.decode(bytes(data_bytes))
            
            if success:
                logger.info(f"Video extract success: {content[:30]}...")
                return ExtractResult(
                    status=WatermarkStatus.SUCCESS,
                    watermark=WatermarkData(content=content),
                    file_path=file_path
                )
            else:
                logger.warning(f"Decode failed: {details}")
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message=f"解码失败: {details.get('error', '未知')}",
                    file_path=file_path
                )
            
        except Exception as e:
            logger.error(f"Video extract failed: {e}")
            import traceback
            traceback.print_exc()
            return ExtractResult(
                status=WatermarkStatus.EXTRACTION_FAILED,
                message=str(e),
                file_path=file_path
            )
    
    def verify(self, file_path: str, original_watermark: WatermarkData,
               **kwargs) -> VerifyResult:
        """验证视频水印"""
        result = self.extract(file_path)
        if result.status == WatermarkStatus.SUCCESS and result.watermark:
            is_valid = result.watermark.content == original_watermark.content
            return VerifyResult(
                status=WatermarkStatus.SUCCESS if is_valid else WatermarkStatus.VERIFICATION_FAILED,
                is_valid=is_valid,
                is_integrity_ok=is_valid,
                match_score=1.0 if is_valid else 0.0
            )
        return VerifyResult(
            status=result.status,
            is_valid=False,
            is_integrity_ok=False,
            match_score=0.0
        )


class WebMHandler(VideoHandler):
    """
    WebM视频水印处理器
    
    继承VideoHandler的RGB LSB方法，使用WebM特定编码器(vp8/vp9)。
    
    编码器选择:
    - libvpx-vp9: 更好的压缩率
    - libvpx: VP8编码器(备选)
    
    注意: 当前版本直接使用父类embed方法，编码器由imageio自动选择
    """
    
    SUPPORTED_EXTENSIONS = ('.webm',)
    HANDLER_NAME = "webm"


class WMVHandler(VideoHandler):
    """
    WMV视频水印处理器
    
    继承VideoHandler的RGB LSB方法。
    
    注意: WMV是有损格式，水印鲁棒性较差，建议仅用于测试。
    当前版本直接使用父类embed方法。
    """
    
    SUPPORTED_EXTENSIONS = ('.wmv',)
    HANDLER_NAME = "wmv"


logger.info(f"{__name__} module loaded - Video handler (RGB LSB)")
