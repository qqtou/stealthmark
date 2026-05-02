# image/tiff_webp_gif_watermark.py
"""
TIFF/WebP/GIF图片水印处理器

技术方案:
- TIFF: LSB隐写 (无损格式, 同PNG)
- WebP: LSB隐写 (无损模式, 需保存为lossless)
- GIF: 扩展块嵌入 (GIF Comment Extension, 不修改图像数据)

依赖:
- Pillow: 图片处理
- numpy: 数值计算

Author: StealthMark Team
Date: 2026-04-28
"""

import os
import struct
from typing import Optional, Dict, Any
import logging

try:
    from PIL import Image
    import numpy as np
except ImportError:
    Image = None
    np = None

from ..core.base import (
    BaseHandler, WatermarkData, WatermarkStatus,
    EmbedResult, ExtractResult, VerifyResult
)
from ..core.codec import WatermarkCodec

logger = logging.getLogger(__name__)


class TIFFHandler(BaseHandler):
    """
    TIFF图片水印处理器 - LSB隐写

    TIFF是无损格式，支持多种色彩空间和压缩方式。
    使用LSB隐写方案：每像素存储1bit水印数据。

    格式: [长度(32bit)][编码数据]
    容量: 宽×高×通道数 bits

    依赖:
        Pillow: TIFF读写
        numpy: 数值处理
    """

    SUPPORTED_EXTENSIONS = ('.tiff', '.tif')
    HANDLER_NAME = "tiff"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.codec = WatermarkCodec(password=self.config.get('password'))
        logger.debug("TIFFHandler initialized")

    def _bytes_to_bits(self, data: bytes) -> list:
        """字节序列转比特列表（高位在前）"""
        bits = []
        for byte in data:
            for i in range(7, -1, -1):
                bits.append((byte >> i) & 1)
        return bits

    def _bits_to_bytes(self, bits: list) -> bytes:
        """比特列表转字节序列（高位在前）"""
        while len(bits) % 8 != 0:
            bits.append(0)
        result = bytearray()
        for i in range(0, len(bits), 8):
            byte = 0
            for j, bit in enumerate(bits[i:i+8]):
                byte |= (bit << (7 - j))
            result.append(byte)
        return bytes(result)

    def embed(self, file_path: str, watermark: WatermarkData,
              output_path: str, **kwargs) -> EmbedResult:
        """
        嵌入水印到 TIFF

        将水印编码后嵌入像素LSB，保存为无损TIFF。
        """
        logger.info(f"TIFF embed: {file_path} -> {output_path}")
        
        if Image is None:
            return EmbedResult(status=WatermarkStatus.FAILED, message="需要Pillow库", file_path=file_path)
        
        error_result = self._validate_file(file_path)
        if error_result:
            return error_result
        
        try:
            image = Image.open(file_path)
            encoded_data = self.codec.encode(watermark.content)
            
            length_bits = self._bytes_to_bits(len(encoded_data).to_bytes(4, 'big'))
            data_bits = self._bytes_to_bits(encoded_data)
            all_bits = length_bits + data_bits
            
            img_array = np.array(image)
            flat = img_array.flatten()
            
            if len(all_bits) > len(flat):
                return EmbedResult(
                    status=WatermarkStatus.FAILED,
                    message=f"图片容量不足", file_path=file_path
                )
            
            for i, bit in enumerate(all_bits):
                if bit == 1:
                    flat[i] = flat[i] | 1
                else:
                    flat[i] = flat[i] & 0xFE
            
            embedded = flat.reshape(img_array.shape)
            result_img = Image.fromarray(embedded.astype(np.uint8), mode=image.mode)
            result_img.save(output_path, format='TIFF')
            
            return self._create_success_result(output_path)
            
        except Exception as e:
            logger.error(f"TIFF embed failed: {e}")
            return EmbedResult(status=WatermarkStatus.FAILED, message=f"嵌入失败: {str(e)}", file_path=file_path)
    
    def extract(self, file_path: str, **kwargs) -> ExtractResult:
        """
        从 TIFF 提取水印

        读取像素LSB，解析长度前缀后解码水印。
        """
        logger.info(f"TIFF extract: {file_path}")
        
        if Image is None:
            return ExtractResult(status=WatermarkStatus.FAILED, message="需要Pillow库", file_path=file_path)
        
        error_result = self._validate_file(file_path)
        if error_result:
            return ExtractResult(status=error_result.status, message=error_result.message, file_path=file_path)
        
        try:
            image = Image.open(file_path)
            img_array = np.array(image)
            flat = img_array.flatten()
            
            # Read length (first 32 bits)
            length_bits = [flat[i] & 1 for i in range(32)]
            length_bytes = self._bits_to_bytes(length_bits)
            data_length = int.from_bytes(length_bytes, 'big')
            
            if data_length <= 0 or data_length > 10 * 1024 * 1024:
                return ExtractResult(status=WatermarkStatus.EXTRACTION_FAILED, message="无效长度", file_path=file_path)
            
            # Read data
            data_bits = [flat[i] & 1 for i in range(32, 32 + data_length * 8)]
            data_bytes = self._bits_to_bytes(data_bits)
            
            success, content, details = self.codec.decode(data_bytes)
            if success:
                return ExtractResult(
                    status=WatermarkStatus.SUCCESS,
                    message="水印提取成功",
                    file_path=file_path,
                    watermark=WatermarkData(content=content)
                )
            return ExtractResult(status=WatermarkStatus.EXTRACTION_FAILED, message="解码失败", file_path=file_path)
            
        except Exception as e:
            logger.error(f"TIFF extract failed: {e}")
            return ExtractResult(status=WatermarkStatus.EXTRACTION_FAILED, message=f"提取失败: {str(e)}", file_path=file_path)
    
    def verify(self, file_path, original_watermark, **kwargs):
        """验证 TIFF 水印完整性"""
        extract_result = self.extract(file_path)
        if not extract_result.is_success or not extract_result.watermark:
            return VerifyResult(status=extract_result.status, is_valid=False, is_integrity_ok=False, match_score=0.0)
        is_match = extract_result.watermark.content == original_watermark.content
        return VerifyResult(
            status=WatermarkStatus.SUCCESS if is_match else WatermarkStatus.VERIFICATION_FAILED,
            is_valid=is_match, is_integrity_ok=True, match_score=1.0 if is_match else 0.0
        )


class WebPHandler(BaseHandler):
    """
    WebP图片水印处理器 - LSB隐写（无损模式）

    WebP支持有损和无损两种模式。
    在无损模式下，像素值精确保留，LSB隐写可行。

    限制:
        - 必须保存为无损WebP才能保证水印可提取
        - 有损WebP会破坏LSB信息

    依赖:
        Pillow: WebP读写（需8.0+版本）
    """

    SUPPORTED_EXTENSIONS = ('.webp',)
    HANDLER_NAME = "webp"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.codec = WatermarkCodec(password=self.config.get('password'))
        logger.debug("WebPHandler initialized")

    def _bytes_to_bits(self, data: bytes) -> list:
        """字节序列转比特列表（高位在前）"""
        bits = []
        for byte in data:
            for i in range(7, -1, -1):
                bits.append((byte >> i) & 1)
        return bits

    def _bits_to_bytes(self, bits: list) -> bytes:
        """比特列表转字节序列（高位在前）"""
        while len(bits) % 8 != 0:
            bits.append(0)
        result = bytearray()
        for i in range(0, len(bits), 8):
            byte = 0
            for j, bit in enumerate(bits[i:i+8]):
                byte |= (bit << (7 - j))
            result.append(byte)
        return bytes(result)

    def embed(self, file_path: str, watermark: WatermarkData,
              output_path: str, **kwargs) -> EmbedResult:
        """
        嵌入水印到 WebP（无损模式）

        强制使用 lossless=True 保存，确保LSB数据精确保留。
        """
        logger.info(f"WebP embed: {file_path} -> {output_path}")
        
        if Image is None:
            return EmbedResult(status=WatermarkStatus.FAILED, message="需要Pillow库", file_path=file_path)
        
        error_result = self._validate_file(file_path)
        if error_result:
            return error_result
        
        try:
            image = Image.open(file_path).convert('RGB')
            encoded_data = self.codec.encode(watermark.content)
            
            length_bits = self._bytes_to_bits(len(encoded_data).to_bytes(4, 'big'))
            data_bits = self._bytes_to_bits(encoded_data)
            all_bits = length_bits + data_bits
            
            img_array = np.array(image)
            flat = img_array.flatten()
            
            if len(all_bits) > len(flat):
                return EmbedResult(status=WatermarkStatus.FAILED, message="图片容量不足", file_path=file_path)
            
            for i, bit in enumerate(all_bits):
                if bit == 1:
                    flat[i] = flat[i] | 1
                else:
                    flat[i] = flat[i] & 0xFE
            
            embedded = flat.reshape(img_array.shape)
            result_img = Image.fromarray(embedded.astype(np.uint8), mode='RGB')
            # Save as lossless WebP
            result_img.save(output_path, format='WEBP', lossless=True)
            
            return self._create_success_result(output_path)
            
        except Exception as e:
            logger.error(f"WebP embed failed: {e}")
            return EmbedResult(status=WatermarkStatus.FAILED, message=f"嵌入失败: {str(e)}", file_path=file_path)
    
    def extract(self, file_path: str, **kwargs) -> ExtractResult:
        """
        从 WebP 提取水印

        读取像素LSB，解析长度前缀后解码水印。
        """
        logger.info(f"WebP extract: {file_path}")
        
        if Image is None:
            return ExtractResult(status=WatermarkStatus.FAILED, message="需要Pillow库", file_path=file_path)
        
        error_result = self._validate_file(file_path)
        if error_result:
            return ExtractResult(status=error_result.status, message=error_result.message, file_path=file_path)
        
        try:
            image = Image.open(file_path).convert('RGB')
            img_array = np.array(image)
            flat = img_array.flatten()
            
            length_bits = [flat[i] & 1 for i in range(32)]
            length_bytes = self._bits_to_bytes(length_bits)
            data_length = int.from_bytes(length_bytes, 'big')
            
            if data_length <= 0 or data_length > 10 * 1024 * 1024:
                return ExtractResult(status=WatermarkStatus.EXTRACTION_FAILED, message="无效长度", file_path=file_path)
            
            data_bits = [flat[i] & 1 for i in range(32, 32 + data_length * 8)]
            data_bytes = self._bits_to_bytes(data_bits)
            
            success, content, details = self.codec.decode(data_bytes)
            if success:
                return ExtractResult(
                    status=WatermarkStatus.SUCCESS,
                    message="水印提取成功",
                    file_path=file_path,
                    watermark=WatermarkData(content=content)
                )
            return ExtractResult(status=WatermarkStatus.EXTRACTION_FAILED, message="解码失败", file_path=file_path)
            
        except Exception as e:
            logger.error(f"WebP extract failed: {e}")
            return ExtractResult(status=WatermarkStatus.EXTRACTION_FAILED, message=f"提取失败: {str(e)}", file_path=file_path)
    
    def verify(self, file_path, original_watermark, **kwargs):
        """验证 WebP 水印完整性"""
        extract_result = self.extract(file_path)
        if not extract_result.is_success or not extract_result.watermark:
            return VerifyResult(status=extract_result.status, is_valid=False, is_integrity_ok=False, match_score=0.0)
        is_match = extract_result.watermark.content == original_watermark.content
        return VerifyResult(
            status=WatermarkStatus.SUCCESS if is_match else WatermarkStatus.VERIFICATION_FAILED,
            is_valid=is_match, is_integrity_ok=True, match_score=1.0 if is_match else 0.0
        )


class GIFHandler(BaseHandler):
    """
    GIF图片水印处理器 - GIF Comment Extension

    GIF使用索引颜色，LSB修改调色板索引会导致颜色偏移。
    使用GIF Comment Extension (0x21 0xFE)嵌入水印：
    这是GIF标准定义的注释块，不影响图像显示和色彩。

    嵌入格式:
        [Extension Introducer 0x21][Comment Label 0xFE]
        [Block Size][Comment Data (Base64编码的水印)]...
        [Block Terminator 0x00]

    依赖:
        仅使用Python标准库

    限制:
        - 元数据可被GIF处理工具清除
    """

    SUPPORTED_EXTENSIONS = ('.gif',)
    HANDLER_NAME = "gif"

    # GIF Extension codes
    COMMENT_EXT = 0xFE  # Comment Extension
    TRAILER = 0x3B      # GIF Trailer

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.codec = WatermarkCodec(password=self.config.get('password'))
        logger.debug("GIFHandler initialized")

    def embed(self, file_path: str, watermark: WatermarkData,
              output_path: str, **kwargs) -> EmbedResult:
        """
        嵌入水印到 GIF

        在 GIF Trailer (0x3B) 之前插入 Comment Extension。
        """
        logger.info(f"GIF embed: {file_path} -> {output_path}")
        
        error_result = self._validate_file(file_path)
        if error_result:
            return error_result
        
        try:
            encoded_data = self.codec.encode(watermark.content)
            encoded_b64 = self.codec.to_base64(encoded_data)
            comment_bytes = encoded_b64.encode('ascii')
            
            with open(file_path, 'rb') as f:
                data = f.read()
            
            # Remove existing comment extensions
            data = self._remove_comments(data)
            
            # Find trailer (0x3B)
            trailer_pos = data.rfind(bytes([self.TRAILER]))
            if trailer_pos == -1:
                trailer_pos = len(data)
            
            # Build comment extension block
            comment_block = bytearray()
            comment_block.append(0x21)  # Extension Introducer
            comment_block.append(self.COMMENT_EXT)  # Comment Label
            
            # Split into sub-blocks (max 255 bytes each)
            i = 0
            while i < len(comment_bytes):
                chunk = comment_bytes[i:i+255]
                comment_block.append(len(chunk))  # Block size
                comment_block.extend(chunk)
                i += 255
            
            comment_block.append(0x00)  # Block terminator
            
            # Insert before trailer
            result = data[:trailer_pos] + bytes(comment_block) + data[trailer_pos:]
            
            with open(output_path, 'wb') as f:
                f.write(result)
            
            return self._create_success_result(output_path)
            
        except Exception as e:
            logger.error(f"GIF embed failed: {e}")
            return EmbedResult(status=WatermarkStatus.FAILED, message=f"嵌入失败: {str(e)}", file_path=file_path)
    
    def _remove_comments(self, data: bytes) -> bytes:
        """
        移除 GIF 中现有的 Comment Extension 块

        遍历 GIF 字节流，识别 0x21 0xFE 序列并跳过其后的子块。
        """
        result = bytearray()
        i = 0
        while i < len(data):
            # Check for comment extension: 0x21 0xFE
            if i + 1 < len(data) and data[i] == 0x21 and data[i+1] == self.COMMENT_EXT:
                # Skip this comment block
                i += 2
                while i < len(data):
                    block_size = data[i]
                    i += 1
                    if block_size == 0:  # Block terminator
                        break
                    i += block_size
            else:
                result.append(data[i])
                i += 1
        return bytes(result)
    
    def extract(self, file_path: str, **kwargs) -> ExtractResult:
        """
        从 GIF 提取水印

        遍历 GIF 数据块，搜索 Comment Extension 并解码。
        """
        logger.info(f"GIF extract: {file_path}")
        
        error_result = self._validate_file(file_path)
        if error_result:
            return ExtractResult(status=error_result.status, message=error_result.message, file_path=file_path)
        
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            
            # Search for comment extensions
            i = 0
            while i < len(data):
                if i + 1 < len(data) and data[i] == 0x21 and data[i+1] == self.COMMENT_EXT:
                    # Read comment data
                    i += 2
                    comment_parts = []
                    while i < len(data):
                        block_size = data[i]
                        i += 1
                        if block_size == 0:
                            break
                        comment_parts.append(data[i:i+block_size])
                        i += block_size
                    
                    comment_data = b''.join(comment_parts)
                    try:
                        b64_str = comment_data.decode('ascii')
                        encoded_data = self.codec.from_base64(b64_str)
                        success, text, details = self.codec.decode(encoded_data)
                        if success:
                            return ExtractResult(
                                status=WatermarkStatus.SUCCESS,
                                message="水印提取成功",
                                file_path=file_path,
                                watermark=WatermarkData(content=text)
                            )
                    except Exception:
                        pass
                else:
                    i += 1
            
            return ExtractResult(
                status=WatermarkStatus.EXTRACTION_FAILED,
                message="未找到水印",
                file_path=file_path
            )
            
        except Exception as e:
            logger.error(f"GIF extract failed: {e}")
            return ExtractResult(status=WatermarkStatus.EXTRACTION_FAILED, message=f"提取失败: {str(e)}", file_path=file_path)
    
    def verify(self, file_path, original_watermark, **kwargs):
        """验证 GIF 水印完整性"""
        extract_result = self.extract(file_path)
        if not extract_result.is_success or not extract_result.watermark:
            return VerifyResult(status=extract_result.status, is_valid=False, is_integrity_ok=False, match_score=0.0)
        is_match = extract_result.watermark.content == original_watermark.content
        return VerifyResult(
            status=WatermarkStatus.SUCCESS if is_match else WatermarkStatus.VERIFICATION_FAILED,
            is_valid=is_match, is_integrity_ok=True, match_score=1.0 if is_match else 0.0
        )


logger.info(f"{__name__} module loaded - TIFF/WebP/GIF handlers ready")
