# media/audio_watermark.py
"""
音频水印处理器 - 扩频水印技术

本模块实现音频文件的隐形水印:
- 嵌入方式:扩频水印(Spread Spectrum)
- 原理:将水印信号扩展到宽频带,嵌入音频信号中
- 优点:抗攻击性强,不易被察觉
- 缺点:需要较大音频容量

技术方案:
1. 将水印转换为比特序列
2. 生成伪随机噪声序列(PN序列)
3. 每个比特乘以PN序列,扩展到多个采样点
4. 叠加到音频信号上
5. 提取时使用相关检测

扩频水印原理:
    嵌入: s'(t) = s(t) + α × b × pn(t)
    提取: b = sign(correlate(s'(t), pn(t)))

    其中:
    - s(t): 原始音频
    - α: 嵌入强度
    - b: 比特值 (±1)
    - pn(t): 伪随机序列

使用示例:
    >>> handler = WAVHandler()
    >>>
    >>> # 嵌入水印
    >>> result = handler.embed(
    ...     "audio.wav",
    ...     WatermarkData(content="版权所有"),
    ...     "output.wav"
    ... )
    >>>
    >>> # 提取水印
    >>> result = handler.extract("output.wav")
    >>> print(result.watermark.content)

依赖:
    - librosa: 音频处理
    - soundfile: 音频写入
    - numpy: 数值计算

Author: StealthMark Team
Date: 2026-04-28
"""

import os
import numpy as np
from typing import Optional, Dict, Any
import logging

# 延迟导入
try:
    import librosa
except ImportError:
    librosa = None

from ..core.base import (
    BaseHandler, WatermarkData, WatermarkStatus,
    EmbedResult, ExtractResult, VerifyResult
)
from ..core.codec import WatermarkCodec

# 模块日志
logger = logging.getLogger(__name__)


class AudioSpreadSpectrumHandler(BaseHandler):
    """
    音频扩频水印处理器基类

    实现扩频水印的核心算法。

    扩频水印参数:
        - spread_factor: 扩频因子(每个比特扩展的采样点数)
        - alpha: 嵌入强度(0.001-0.01,越大越明显但越易检测)
        - pn_seed: PN序列种子(用于生成伪随机序列)

    PN序列:
        使用线性同余生成器(LCG)生成伪随机序列:
        x[n+1] = (a × x[n] + c) mod m

        参数: a=1103515245, c=12345, m=2^31

    Attributes:
        codec: WatermarkCodec 实例
        spread_factor: 扩频因子
        alpha: 嵌入强度
        _pn_sequence: 预生成的PN序列
    """

    HANDLER_NAME = "audio_ss"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化音频处理器

        Args:
            config: 配置字典,支持:
                - password: 加密密码
                - spread_factor: 扩频因子(默认31)
                - alpha: 嵌入强度(默认0.005)
                - pn_seed: PN序列种子(默认12345)
        """
        super().__init__(config)
        self.codec = WatermarkCodec(password=self.config.get('password'))
        self.spread_factor = config.get('spread_factor', 31) if config else 31
        self.alpha = config.get('alpha', 0.005) if config else 0.005
        self._pn_sequence = None

        # 预生成PN序列
        self._generate_pn_sequence(1024)

        logger.debug(f"AudioSpreadSpectrumHandler initialized: "
                    f"spread={self.spread_factor}, alpha={self.alpha}")

    def _generate_pn_sequence(self, length: int) -> np.ndarray:
        """
        生成伪随机噪声序列

        使用线性同余生成器(LCG)生成。

        Args:
            length: 序列长度

        Returns:
            np.ndarray: PN序列(值为±1)
        """
        seed = self.config.get('pn_seed', 12345) if self.config else 12345
        sequence = []

        # LCG参数
        a, c, m = 1103515245, 12345, 2**31

        x = seed
        for _ in range(length):
            x = (a * x + c) % m
            sequence.append(1 if (x % 2) else -1)  # 映射到±1

        self._pn_sequence = np.array(sequence)
        return self._pn_sequence

    def _generate_pn(self, length: int) -> np.ndarray:
        """
        生成指定长度的PN序列

        通过重复预生成的序列获得所需长度。

        Args:
            length: 所需长度

        Returns:
            np.ndarray: PN序列
        """
        if self._pn_sequence is None:
            self._generate_pn_sequence(1024)

        # 重复序列直到满足长度
        repeats = (length // len(self._pn_sequence)) + 1
        return np.tile(self._pn_sequence, repeats)[:length]

    def _embed_bit(self, signal: np.ndarray, bit: int, pn: np.ndarray) -> np.ndarray:
        """
        嵌入单个比特

        公式: s' = s + α × b × pn

        Args:
            signal: 音频片段
            bit: 比特值(0或1)
            pn: PN序列

        Returns:
            np.ndarray: 嵌入后的音频片段
        """
        # 比特值映射到±1
        bit_signal = 1.0 if bit == 1 else -1.0

        # 扩频
        spread_signal = bit_signal * pn[:len(signal)]

        # 叠加
        embedded = signal + self.alpha * spread_signal
        return embedded

    def _extract_bit(self, signal: np.ndarray, pn: np.ndarray) -> int:
        """
        提取单个比特(相关检测)

        公式: b = sign(correlate(s', pn))

        Args:
            signal: 含水印音频片段
            pn: PN序列

        Returns:
            int: 提取的比特值(0或1)
        """
        # 计算相关值
        correlation = np.correlate(signal, pn[:len(signal)], mode='valid')

        if len(correlation) == 0:
            return 0

        # 判断符号
        mean_corr = np.mean(correlation)
        return 1 if mean_corr > 0 else 0


class WAVHandler(AudioSpreadSpectrumHandler):
    """
    WAV音频水印处理器

    支持标准WAV格式音频。

    处理流程:
        嵌入:
        1. 使用librosa加载音频
        2. 转换为单声道
        3. 编码水印为比特序列
        4. 分段嵌入每个比特
        5. 使用soundfile保存

        提取:
        1. 加载音频
        2. 分段相关检测
        3. 解码比特序列
    """

    SUPPORTED_EXTENSIONS = ('.wav',)
    HANDLER_NAME = "wav"

    # 固定每个比特占用的采样点数(必须 >= spread_factor 以保证相关检测有效)
    BITS_PER_SAMPLE = 100

    def embed(self, file_path: str, watermark: WatermarkData,
              output_path: str, **kwargs) -> EmbedResult:
        """
        嵌入水印到 WAV 音频

        Args:
            file_path: 原始 WAV 文件路径
            watermark: 水印数据对象
            output_path: 输出文件路径
            **kwargs: 额外参数

        Returns:
            EmbedResult: 嵌入结果
        """
        logger.info(f"WAV embed: {file_path} -> {output_path}")

        # 检查依赖
        if librosa is None:
            logger.error("librosa not installed")
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message="需要安装librosa库: pip install librosa",
                file_path=file_path
            )

        # 验证文件
        error_result = self._validate_file(file_path)
        if error_result:
            return error_result

        try:
            # 加载音频
            signal, sr = librosa.load(file_path, sr=None, mono=False)

            # 转换为单声道
            if len(signal.shape) > 1:
                signal = np.mean(signal, axis=0)

            # 编码水印
            encoded_data = self.codec.encode(watermark.content)

            # 转换为比特序列
            bits = []
            for byte in encoded_data:
                for i in range(7, -1, -1):
                    bits.append((byte >> i) & 1)

            # 添加同步头
            sync = [1, 0, 1, 0, 1, 0, 1, 0]
            bits = sync + bits

            # 使用固定常量,确保embed/extract一致
            bits_per_sample = self.BITS_PER_SAMPLE

            # 检查容量
            max_bits = len(signal) // bits_per_sample
            if len(bits) > max_bits:
                return EmbedResult(
                    status=WatermarkStatus.FAILED,
                    message=f"音频太短: 需要{len(bits)}比特, 容量仅{max_bits}比特",
                    file_path=file_path
                )

            # 嵌入
            embedded = signal.copy()

            for i, bit in enumerate(bits):
                start = i * bits_per_sample
                end = min(start + bits_per_sample, len(signal))

                if start >= len(signal):
                    break

                pn = self._generate_pn(end - start)
                segment = signal[start:end]
                embedded[start:end] = self._embed_bit(segment, bit, pn)

            # 保存
            import soundfile as sf
            sf.write(output_path, embedded, sr)

            logger.info(f"WAV embed success: {len(bits)} bits embedded")
            return self._create_success_result(output_path)

        except Exception as e:
            logger.error(f"WAV embed failed: {e}")
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message=f"嵌入失败: {str(e)}",
                file_path=file_path
            )

    def extract(self, file_path: str, **kwargs) -> ExtractResult:
        """
        从 WAV 音频提取水印

        Args:
            file_path: WAV 文件路径
            **kwargs: 额外参数

        Returns:
            ExtractResult: 提取结果
        """
        logger.info(f"WAV extract: {file_path}")

        # 检查依赖
        if librosa is None:
            logger.error("librosa not installed")
            return ExtractResult(
                status=WatermarkStatus.FAILED,
                message="需要安装librosa库",
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
            # 加载音频
            signal, sr = librosa.load(file_path, sr=None, mono=False)

            if len(signal.shape) > 1:
                signal = np.mean(signal, axis=0)

            # 使用固定常量(与embed一致)
            bits_per_sample = self.BITS_PER_SAMPLE

            # 提取所有比特 - 不需要自行解析长度,codec.decode会处理
            # 先搜索同步头
            sync_pattern = [1, 0, 1, 0, 1, 0, 1, 0]
            sync_found = False
            sync_pos = 0

            # 滑动搜索同步头
            for pos in range(min(1000, len(signal) // bits_per_sample - 8)):
                sync_bits = []
                for j in range(8):
                    start = (pos + j) * bits_per_sample
                    pn = self._generate_pn(bits_per_sample)
                    bit = self._extract_bit(signal[start:start+bits_per_sample], pn) if start + bits_per_sample <= len(signal) else 0
                    sync_bits.append(bit)
                if sync_bits == sync_pattern:
                    sync_found = True
                    sync_pos = pos + 8  # 跳过同步头
                    break

            if not sync_found:
                logger.warning("Sync header not found")
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message="未找到同步头",
                    file_path=file_path
                )

            # 从同步头后提取所有比特,转字节,交给codec.decode
            data_start = sync_pos * bits_per_sample
            max_data_samples = min(len(signal) - data_start, 500 * bits_per_sample)  # 最多读500字节的量

            all_bits = []
            for i in range(sync_pos, sync_pos + max_data_samples // bits_per_sample):
                start = i * bits_per_sample
                end = start + bits_per_sample
                if start + bits_per_sample > len(signal):
                    break
                pn = self._generate_pn(bits_per_sample)
                bit = self._extract_bit(signal[start:end], pn)
                all_bits.append(bit)

            # 比特转字节
            data_bytes = bytearray()
            for i in range(0, len(all_bits) - 7, 8):
                byte = 0
                for j in range(8):
                    byte = (byte << 1) | all_bits[i + j]
                data_bytes.append(byte)

            # 用codec解码(codec内部会解析SMARK头、长度、CRC)
            success, content, details = self.codec.decode(bytes(data_bytes))

            if success:
                logger.info(f"WAV extract success: {content[:30]}...")
                return ExtractResult(
                    status=WatermarkStatus.SUCCESS,
                    message="水印提取成功",
                    file_path=file_path,
                    watermark=WatermarkData(content=content)
                )
            else:
                logger.warning(f"Decode failed: {details}")
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message=f"解码失败: {details.get('error', '未知')}",
                    file_path=file_path
                )

        except Exception as e:
            logger.error(f"WAV extract failed: {e}")
            return ExtractResult(
                status=WatermarkStatus.EXTRACTION_FAILED,
                message=f"提取失败: {str(e)}",
                file_path=file_path
            )

    def verify(self, file_path: str, original_watermark: WatermarkData,
               **kwargs) -> VerifyResult:
        """验证 WAV 水印"""
        logger.info(f"WAV verify: {file_path}")

        extract_result = self.extract(file_path)

        if not extract_result.is_success or not extract_result.watermark:
            return VerifyResult(
                status=extract_result.status,
                is_valid=False,
                is_integrity_ok=False,
                match_score=0.0
            )

        extracted = extract_result.watermark.content
        original = original_watermark.content
        is_match = extracted == original

        result = VerifyResult(
            status=WatermarkStatus.SUCCESS if is_match else WatermarkStatus.VERIFICATION_FAILED,
            is_valid=is_match,
            is_integrity_ok=True,
            match_score=1.0 if is_match else 0.0
        )

        logger.info(f"WAV verify result: valid={is_match}")
        return result


class MP3Handler(BaseHandler):
    """
    MP3 audio watermark handler using ID3 metadata.
    Embeds watermark in TXXX frame (user-defined text).
    Reliable because metadata survives MP3 encoding.
    """

    SUPPORTED_EXTENSIONS = ('.mp3',)
    HANDLER_NAME = 'mp3'
    MAGIC_PREFIX = 'SMARK:'

    def __init__(self, config=None):
        super().__init__(config)
        self.codec = WatermarkCodec(password=self.config.get('password'))
        self._id3_module = None

    def _get_id3(self):
        if self._id3_module is None:
            try:
                import mutagen.id3
                self._id3_module = mutagen.id3
            except ImportError:
                # Fallback: try mutagen directly
                import mutagen
                self._id3_module = mutagen
        return self._id3_module

    def _read_id3_comment(self, file_path):
        """Read TXXX frame from MP3."""
        try:
            from mutagen import File
            audio = File(file_path)
            if audio is None:
                return None
            # Try TXXX frame (user-defined text)
            if hasattr(audio, 'tags') and audio.tags:
                for key, val in audio.tags.items():
                    if 'TXXX' in str(key):
                        return str(val)
            # Try COMM frame (comment)
            if hasattr(audio, 'comments'):
                for comm in audio.comments:
                    return str(comm)
            return None
        except Exception as e:
            return None

    def _write_id3_comment(self, file_path, watermark):
        """Write watermark to TXXX frame in MP3."""
        try:
            from mutagen.id3 import ID3, TXXX

            # Encode watermark with codec
            data = self.codec.encode(watermark.content)
            if not data:
                return False

            # Store as TXXX frame (description='StealthMark')
            encoded = data.hex()

            # Write to ID3 tag
            id3 = ID3(file_path)
            id3.add(TXXX(encoding=3, desc='StealthMark', text=encoded))
            id3.save(v2_version=3)
            return True
        except Exception as e:
            print(f'ID3 write error: {e}')
            return False


    def embed(self, file_path, watermark, output_path, **kwargs):
        import shutil, os

        # Copy to output first
        shutil.copy2(file_path, output_path)

        # Write watermark to ID3
        if self._write_id3_comment(output_path, watermark):
            return EmbedResult(
                status=WatermarkStatus.SUCCESS,
                message='Watermark embedded in ID3 TXXX frame',
                file_path=output_path,
                output_path=output_path
            )

        # Fallback: rename file with watermark in path
        return EmbedResult(
            status=WatermarkStatus.FAILED,
            message='ID3 write failed, fallback not implemented',
            file_path=output_path,
            output_path=output_path
        )

    def extract(self, file_path, **kwargs):
        # Try to read watermark from ID3
        encoded = self._read_id3_comment(file_path)
        if not encoded:
            return ExtractResult(
                status=WatermarkStatus.FAILED,
                message='No ID3 watermark found',
                file_path=file_path
            )

        # Try to decode
        try:
            data = bytes.fromhex(encoded)
            success, content, _ = self.codec.decode(data)
            if success:
                return ExtractResult(
                    status=WatermarkStatus.SUCCESS,
                    watermark=WatermarkData(content=content),
                    file_path=file_path
                )
        except:
            pass

        return ExtractResult(
            status=WatermarkStatus.FAILED,
            message='Invalid watermark format',
            file_path=file_path
        )

    def verify(self, file_path, watermark, **kwargs):
        result = self.extract(file_path, **kwargs)
        if result.is_success:
            match = result.watermark.content == watermark.content
            return VerifyResult(
                is_match=match,
                expected=watermark.content,
                extracted=result.watermark.content,
                file_path=file_path
            )
        return VerifyResult(
            is_match=False,
            expected=watermark.content,
            extracted=None,
            file_path=file_path
        )

