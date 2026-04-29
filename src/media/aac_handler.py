# media/aac_handler.py
"""
AAC/M4A音频水印处理器 - 扩频水印

AAC/M4A是有损音频格式，复用WAV的扩频水印方案。
使用 PyAV 读取（支持所有音频格式），ffmpeg subprocess 写入。

Author: StealthMark Team
Date: 2026-04-28
"""

import logging
import os
import subprocess
import tempfile
import numpy as np

from .audio_watermark import WAVHandler

logger = logging.getLogger(__name__)

# 全局 ffmpeg 路径缓存
_ffmpeg_path = None


def _get_ffmpeg():
    """获取 ffmpeg 可执行文件路径（优先 imageio-ffmpeg）"""
    global _ffmpeg_path
    if _ffmpeg_path:
        return _ffmpeg_path
    try:
        import imageio_ffmpeg
        _ffmpeg_path = str(imageio_ffmpeg.get_ffmpeg_exe())
        return _ffmpeg_path
    except ImportError:
        pass
    # 降级：从 PATH 找
    import shutil
    for name in ('ffmpeg', 'ffmpeg.exe'):
        p = shutil.which(name)
        if p:
            _ffmpeg_path = p
            return _ffmpeg_path
    raise RuntimeError("需要安装 imageio-ffmpeg: pip install imageio-ffmpeg")


def _av_read_audio(file_path: str):
    """用 PyAV 读取任意音频文件，返回 (samples, sr, channels)"""
    import av
    container = av.open(file_path)
    stream = next((s for s in container.streams if s.type == 'audio'), None)
    if stream is None:
        raise ValueError(f"No audio stream in {file_path}")

    sr = stream.codec_context.sample_rate
    channels = stream.codec_context.channels

    # 解码所有帧
    frames = []
    for packet in container.demux(stream):
        for frame in packet.decode():
            frames.append(frame.to_ndarray())

    container.close()

    if not frames:
        raise ValueError(f"No audio frames decoded from {file_path}")

    # 合并帧 (shape: [channels, samples] 或 [samples])
    audio = np.concatenate(frames, axis=-1)

    # 转 float64，范围 [-1, 1]
    if audio.dtype == np.int16:
        audio = audio.astype(np.float64) / 32768.0
    elif audio.dtype == np.int32:
        audio = audio.astype(np.float64) / 2147483648.0
    elif audio.dtype == np.uint8:
        audio = (audio.astype(np.float64) - 128.0) / 128.0
    else:
        audio = audio.astype(np.float64)

    # 合并多声道 → 单声道
    if audio.ndim > 1:
        audio = np.mean(audio, axis=0)

    return audio, sr, channels


def _ffmpeg_encode_m4a(samples: np.ndarray, sr: int, channels: int, output_path: str):
    """用 ffmpeg subprocess 将音频数组编码为 M4A (Apple Lossless ALAC)

    注意：使用 ALAC 无损编码，不使用 AAC 有损编码。
    原因：扩频水印信号极其微弱（alpha=0.005），AAC 有损压缩会完全抹除水印。
    ALAC 完全无损，能保留扩频水印信号。
    """
    ffmpeg = _get_ffmpeg()

    import tempfile as _tf
    with _tf.NamedTemporaryFile(suffix='.wav', delete=False) as wf:
        tmp_wav = wf.name

    # soundfile 写临时 WAV（soundfile 需要 shape=(N,) + channels 参数）
    try:
        import soundfile as sf
        _samples = samples
        if _samples.ndim == 1:
            _samples = _samples.reshape(-1, 1)  # shape → (N, 1)
        sf.write(tmp_wav, _samples, sr)
        tmp_raw = None  # soundfile 成功，不用 raw fallback
    except Exception:
        # soundfile 写不了就走 wav 库 fallback
        import wave
        import tempfile as _tf2
        tmp_raw = _tf2.NamedTemporaryFile(suffix='.raw', delete=False)
        tmp_raw.close()
        data = (samples * 32767).astype(np.int16).tobytes()
        with wave.open(tmp_raw.name, 'wb') as wh:
            wh.setnchannels(1)
            wh.setsampwidth(2)
            wh.setframerate(sr)
            wh.writeframes(data)

    try:
        if tmp_raw is None:
            sub = subprocess.run(
                [ffmpeg, '-y',
                 '-i', tmp_wav,
                 '-ar', str(sr), '-ac', '1',
                 '-c:a', 'alac',
                 output_path],
                capture_output=True, text=True
            )
        else:
            sub = subprocess.run(
                [ffmpeg, '-y',
                 '-f', 's16le', '-ar', str(sr), '-ac', '1',
                 '-i', tmp_raw.name,
                 '-c:a', 'alac',
                 output_path],
                capture_output=True, text=True
            )
        if sub.returncode != 0:
            raise RuntimeError(f"ffmpeg ALAC encode failed (code {sub.returncode}): {sub.stderr[:300]}")
    finally:
        if tmp_wav and os.path.exists(tmp_wav):
            os.unlink(tmp_wav)
        if tmp_raw and os.path.exists(tmp_raw.name):
            os.unlink(tmp_raw.name)


class AACHandler(WAVHandler):
    """
    AAC/M4A音频水印处理器

    复用WAV的扩频水印实现（AudioSpreadSpectrumHandler）。

    读取路径：PyAV（支持所有音频格式，包括 AAC/MP4 容器）
    写入路径：ffmpeg subprocess（WAV → AAC/M4A）
    """

    SUPPORTED_EXTENSIONS = ('.aac', '.m4a')
    HANDLER_NAME = "aac"

    def embed(self, file_path: str, watermark, output_path: str, **kwargs):
        """重写 embed：用 PyAV 读取 + ffmpeg 写入"""
        from src.core.base import EmbedResult, WatermarkStatus

        logger.info(f"AAC embed: {file_path} -> {output_path}")

        # 依赖检查
        if not self._check_dependency('av', 'pyav'):
            try:
                import av
            except ImportError:
                return EmbedResult(
                    status=WatermarkStatus.FAILED,
                    message="需要安装 PyAV: pip install av",
                    file_path=file_path
                )

        try:
            # 用 PyAV 读取（兼容所有音频格式）
            signal, sr, channels = _av_read_audio(file_path)

            # 复用父类 WAVHandler 的水印嵌入逻辑
            # 父类 embed 用 librosa 读，但 embed 核心只需要 signal/sr/np.ndarray
            # 所以我们手动走一遍 WAVHandler.embed 中的核心处理流程
            # 但更好的方式是直接调用父类——需要先 patch signal/sr

            # 编码水印
            encoded_data = self.codec.encode(watermark.content)
            bits = []
            for byte in encoded_data:
                for i in range(7, -1, -1):
                    bits.append((byte >> i) & 1)
            bits = [1, 0, 1, 0, 1, 0, 1, 0] + bits  # 同步头

            # 检查容量
            bits_per_sample = self.BITS_PER_SAMPLE
            max_bits = len(signal) // bits_per_sample
            if len(bits) > max_bits:
                return EmbedResult(
                    status=WatermarkStatus.FAILED,
                    message=f"音频太短: 需要{len(bits)}比特, 容量仅{max_bits}比特",
                    file_path=file_path
                )

            # 扩频嵌入
            embedded = signal.copy()
            for i, bit in enumerate(bits):
                start = i * bits_per_sample
                end = min(start + bits_per_sample, len(signal))
                if start >= len(signal):
                    break
                pn = self._generate_pn(end - start)
                segment = signal[start:end]
                embedded[start:end] = self._embed_bit(segment, bit, pn)

            # 用 ffmpeg 写入 M4A
            _ffmpeg_encode_m4a(embedded, sr, channels, output_path)

            logger.info(f"AAC embed success: {len(bits)} bits, {output_path}")
            return self._create_success_result(output_path)

        except Exception as e:
            logger.error(f"AAC embed failed: {e}")
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message=f"嵌入失败: {str(e)}",
                file_path=file_path
            )

    def extract(self, file_path: str, **kwargs):
        """重写 extract：用 PyAV 读取"""
        from src.core.base import ExtractResult, WatermarkStatus

        logger.info(f"AAC extract: {file_path}")

        if not self._check_dependency('av', 'pyav'):
            try:
                import av
            except ImportError:
                return ExtractResult(
                    status=WatermarkStatus.FAILED,
                    message="需要安装 PyAV: pip install av",
                    file_path=file_path
                )

        # 验证文件
        error_result = self._validate_file(file_path)
        if error_result:
            return ExtractResult(
                status=error_result.status,
                message=error_result.message,
                file_path=file_path
            )

        try:
            # 用 PyAV 读取
            signal, sr, channels = _av_read_audio(file_path)

            # 复用父类提取逻辑（父类从 signal/sr 开始处理，不需要 librosa）
            # WAVHandler.extract 前半部分用 librosa.load，后半部分是纯 numpy
            # 所以这里手动跑提取核心
            bits_per_sample = self.BITS_PER_SAMPLE
            sync_pattern = [1, 0, 1, 0, 1, 0, 1, 0]

            # 搜索同步头（直接用 _extract_bit 判决，与WAV保持一致）
            sync_found = False
            sync_pos = 0
            search_limit = min(len(signal) // bits_per_sample - 8, 500)
            for pos in range(search_limit):
                found_sync = True
                for j, expected in enumerate(sync_pattern):
                    s = (pos + j) * bits_per_sample
                    e = min(s + bits_per_sample, len(signal))
                    if s >= len(signal):
                        found_sync = False
                        break
                    pn_j = self._generate_pn(e - s)
                    bit_j = self._extract_bit(signal[s:e], pn_j)  # 与WAV一致
                    if bit_j != expected:
                        found_sync = False
                        break
                if found_sync:
                    sync_found = True
                    sync_pos = pos
                    break

            if not sync_found:
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message="Sync header not found",
                    file_path=file_path
                )

            # 提取数据位（用 _extract_bit 判决，与WAV一致）
            data_bits = []
            data_start = sync_pos + len(sync_pattern)
            max_data = min(len(signal) // bits_per_sample - data_start, 500)

            for i in range(max_data):
                pos = data_start + i
                start = pos * bits_per_sample
                end = min(start + bits_per_sample, len(signal))
                if start >= len(signal):
                    break
                pn = self._generate_pn(end - start)
                bit = self._extract_bit(signal[start:end], pn)
                data_bits.append(bit)

            # 解码
            byte_data = []
            for byte_idx in range(0, len(data_bits) - (len(data_bits) % 8), 8):
                byte = 0
                for bit in data_bits[byte_idx:byte_idx + 8]:
                    byte = (byte << 1) | bit
                byte_data.append(byte)

            content = self.codec.decode(bytes(byte_data))
            return ExtractResult(
                status=WatermarkStatus.SUCCESS,
                message="提取成功",
                watermark=content,
                file_path=file_path
            )

        except Exception as e:
            logger.error(f"AAC extract failed: {e}")
            return ExtractResult(
                status=WatermarkStatus.FAILED,
                message=f"提取失败: {str(e)}",
                file_path=file_path
            )

    def _check_dependency(self, name: str, pip_name: str):
        """检查依赖是否安装（stub，av 导入失败会抛 ImportError）"""
        try:
            __import__(name)
            return True
        except ImportError:
            return False


logger.info(f"{__name__} module loaded - AAC handler ready (PyAV + ffmpeg)")
