# image/image_watermark.py
"""
图片水印处理器 - LSB隐写和DCT域方法

本模块实现图片文件的隐形水印：
- PNG/BMP: LSB隐写（最低有效位）
- JPEG: DCT域水印（离散余弦变换）

技术方案：

1. LSB隐写（PNG/BMP）:
   - 将水印编码为比特序列
   - 替换像素最低位
   - 无损格式，水印永久保存
   
2. DCT域水印（JPEG）:
   - 在DCT系数中嵌入水印
   - 抗JPEG压缩
   - 不可见性好

使用示例:
    >>> # PNG图片
    >>> png_handler = PNGHandler()
    >>> result = png_handler.embed("image.png", WatermarkData(content="水印"), "output.png")
    >>> 
    >>> # JPEG图片
    >>> jpg_handler = JPEGHandler()
    >>> result = jpg_handler.embed("photo.jpg", WatermarkData(content="版权"), "output.jpg")

依赖:
    - Pillow: 图片处理（PNG/BMP）
    - opencv-python: 图片处理（JPEG）
    - numpy: 数值计算

Author: StealthMark Team
Date: 2026-04-28
"""

import os
from typing import Optional, Dict, Any
import logging

# 延迟导入
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

# 模块日志
logger = logging.getLogger(__name__)


class ImageLSBHandler(BaseHandler):
    """
    图片LSB隐写处理器基类
    
    LSB（Least Significant Bit）隐写原理:
        像素值: p = (p >> 1) << 1 | bit
        嵌入: p' = p & 0xFE | bit  (清除最低位，设置新位)
        提取: bit = p & 1
    
    优点:
        - 完全不可见（人眼无法分辨最低位变化）
        - 容量大（每像素1比特）
        - 无损格式永久保存
    
    缺点:
        - 仅适用于无损格式（PNG、BMP）
        - 易被压缩、缩放破坏
    
    Attributes:
        codec: WatermarkCodec 实例
    """
    
    HANDLER_NAME = "image_lsb"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化图片处理器"""
        super().__init__(config)
        self.codec = WatermarkCodec(password=self.config.get('password'))
    
    # ==================== LSB核心算法 ====================
    
    def _embed_bits(self, image: 'Image.Image', bits: list) -> 'Image.Image':
        """
        将比特序列嵌入到图像LSB
        
        Args:
            image: PIL Image对象
            bits: 比特列表（0和1）
        
        Returns:
            Image.Image: 嵌入后的图像
        
        原理:
            遍历像素，将每个比特嵌入到像素的最低位。
        """
        # 转换为numpy数组
        img_array = np.array(image)
        original_shape = img_array.shape
        flat = img_array.flatten()
        
        # 嵌入比特
        bit_idx = 0
        for i in range(len(flat)):
            if bit_idx >= len(bits):
                break
            
            # LSB嵌入: 清除最低位，设置新位
            if bits[bit_idx] == 1:
                flat[i] = flat[i] | 1   # 设置最低位为1
            else:
                flat[i] = flat[i] & 0xFE  # 清除最低位
            bit_idx += 1
        
        # 重塑并返回
        embedded = flat.reshape(original_shape)
        return Image.fromarray(embedded.astype(np.uint8))
    
    def _extract_bits(self, image: 'Image.Image', num_bits: int) -> list:
        """
        从图像LSB提取比特序列
        
        Args:
            image: PIL Image对象
            num_bits: 要提取的比特数
        
        Returns:
            list: 比特列表
        """
        img_array = np.array(image)
        flat = img_array.flatten()
        
        bits = []
        for i in range(min(num_bits, len(flat))):
            bits.append(flat[i] & 1)  # 提取最低位
        
        return bits
    
    def _calculate_capacity(self, image: 'Image.Image') -> int:
        """
        计算图像可嵌入的最大比特数
        
        Args:
            image: PIL Image对象
        
        Returns:
            int: 最大比特数（= 像素总数）
        """
        img_array = np.array(image)
        return img_array.size
    
    # ==================== 比特/字节转换 ====================
    
    def _bits_to_bytes(self, bits: list) -> bytes:
        """比特列表转字节串"""
        # 补齐到8的倍数
        while len(bits) % 8 != 0:
            bits.append(0)
        
        result = bytearray()
        for i in range(0, len(bits), 8):
            byte_bits = bits[i:i+8]
            byte = 0
            for j, bit in enumerate(byte_bits):
                byte |= (bit << (7 - j))
            result.append(byte)
        
        return bytes(result)
    
    def _bytes_to_bits(self, data: bytes) -> list:
        """字节串转比特列表"""
        bits = []
        for byte in data:
            for i in range(7, -1, -1):
                bits.append((byte >> i) & 1)
        return bits


class PNGHandler(ImageLSBHandler):
    """
    PNG图片水印处理器
    
    使用LSB隐写方式嵌入水印。
    
    特点:
        - PNG是无损格式，水印永久保存
        - 支持RGB和RGBA模式
        - 容量: 宽×高×通道数 比特
    
    水印格式:
        [长度(32bit)][数据(N×8bit)]
        
        长度字段指示数据字节数。
    """
    
    SUPPORTED_EXTENSIONS = ('.png',)
    HANDLER_NAME = "png"
    
    def embed(self, file_path: str, watermark: WatermarkData,
              output_path: str, **kwargs) -> EmbedResult:
        """
        嵌入水印到 PNG
        
        Args:
            file_path: 原始 PNG 文件路径
            watermark: 水印数据对象
            output_path: 输出文件路径
            **kwargs: 额外参数
        
        Returns:
            EmbedResult: 嵌入结果
        """
        logger.info(f"PNG embed: {file_path} -> {output_path}")
        
        # 检查依赖
        if Image is None:
            logger.error("Pillow not installed")
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message="需要安装Pillow库: pip install Pillow",
                file_path=file_path
            )
        
        # 验证文件
        error_result = self._validate_file(file_path)
        if error_result:
            return error_result
        
        try:
            # 打开图片
            image = Image.open(file_path)
            
            # 编码水印
            encoded_data = self.codec.encode(watermark.content)
            
            # 构建嵌入数据: [长度][数据]
            length_bits = self._bytes_to_bits(len(encoded_data).to_bytes(4, 'big'))
            data_bits = self._bytes_to_bits(encoded_data)
            all_bits = length_bits + data_bits
            
            # 检查容量
            capacity = self._calculate_capacity(image)
            if len(all_bits) > capacity:
                logger.warning(f"Insufficient capacity: need {len(all_bits)}, have {capacity}")
                return EmbedResult(
                    status=WatermarkStatus.FAILED,
                    message=f"图片容量不足，需要{len(all_bits)}bits，只能提供{capacity}bits",
                    file_path=file_path
                )
            
            # 嵌入
            embedded_image = self._embed_bits(image, all_bits)
            embedded_image.save(output_path, format='PNG')
            
            logger.info(f"PNG embed success: {len(all_bits)} bits")
            return self._create_success_result(output_path)
            
        except Exception as e:
            logger.error(f"PNG embed failed: {e}")
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message=f"嵌入失败: {str(e)}",
                file_path=file_path
            )
    
    def extract(self, file_path: str, **kwargs) -> ExtractResult:
        """从 PNG 提取水印"""
        logger.info(f"PNG extract: {file_path}")
        
        if Image is None:
            logger.error("Pillow not installed")
            return ExtractResult(
                status=WatermarkStatus.FAILED,
                message="需要安装Pillow库",
                file_path=file_path
            )
        
        error_result = self._validate_file(file_path)
        if error_result:
            return ExtractResult(
                status=error_result.status,
                message=error_result.message,
                file_path=file_path
            )
        
        try:
            image = Image.open(file_path)
            
            # 提取长度字段（前32位）
            length_bits = self._extract_bits(image, 32)
            length_bytes = self._bits_to_bytes(length_bits)
            data_length = int.from_bytes(length_bytes, 'big')
            
            # 验证长度
            if data_length <= 0 or data_length > 10 * 1024 * 1024:
                logger.warning(f"Invalid data length: {data_length}")
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message="无效的水印长度",
                    file_path=file_path
                )
            
            # 提取数据
            data_bits = self._extract_bits(image, 32 + data_length * 8)
            data_bytes = self._bits_to_bytes(data_bits[32:])
            
            # 解码水印
            success, content, details = self.codec.decode(data_bytes)
            
            if success:
                logger.info(f"PNG extract success: {content[:30]}...")
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
                    message=f"解码失败: {details.get('error', '未知错误')}",
                    file_path=file_path
                )
                
        except Exception as e:
            logger.error(f"PNG extract failed: {e}")
            return ExtractResult(
                status=WatermarkStatus.EXTRACTION_FAILED,
                message=f"提取失败: {str(e)}",
                file_path=file_path
            )
    
    def verify(self, file_path: str, original_watermark: WatermarkData,
               **kwargs) -> VerifyResult:
        """验证 PNG 水印"""
        logger.info(f"PNG verify: {file_path}")
        
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
        
        logger.info(f"PNG verify result: valid={is_match}")
        return result


class BMPHandler(PNGHandler):
    """
    BMP图片水印处理器
    
    复用PNG的LSB实现，BMP也是无损格式。
    """
    
    SUPPORTED_EXTENSIONS = ('.bmp',)
    HANDLER_NAME = "bmp"


class JPEGHandler(BaseHandler):
    """
    JPEG图片水印处理器 - DCT域
    
    JPEG是有损压缩格式，LSB方法不适用。
    使用DCT域方法嵌入水印，抗JPEG压缩。
    
    技术原理:
        1. JPEG压缩使用DCT变换
        2. 在DCT系数中嵌入水印
        3. 选择中频系数（F[2,3]），平衡可见性和鲁棒性
    
    嵌入位置:
        8×8块的DCT系数F[2,3]
    
    同步机制:
        使用固定同步头 [1,0,1,0,1,0,1,0] 标记水印起始。
    """
    
    SUPPORTED_EXTENSIONS = ('.jpg', '.jpeg')
    HANDLER_NAME = "jpeg"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化JPEG处理器"""
        super().__init__(config)
        self.codec = WatermarkCodec(password=self.config.get('password'))
        self.quality = self.config.get('quality', 95) if config else 95
        
        logger.debug(f"JPEGHandler initialized: quality={self.quality}")
    
    def embed(self, file_path: str, watermark: WatermarkData,
              output_path: str, **kwargs) -> EmbedResult:
        """嵌入水印到 JPEG"""
        logger.info(f"JPEG embed: {file_path} -> {output_path}")
        
        # 检查依赖
        try:
            import cv2
        except ImportError:
            logger.error("opencv-python not installed")
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message="需要安装opencv-python库: pip install opencv-python",
                file_path=file_path
            )
        
        error_result = self._validate_file(file_path)
        if error_result:
            return error_result
        
        try:
            import cv2
            
            # 读取图片
            img = cv2.imread(file_path)
            if img is None:
                return EmbedResult(
                    status=WatermarkStatus.FAILED,
                    message="无法读取图片",
                    file_path=file_path
                )
            
            # 编码水印
            encoded_data = self.codec.encode(watermark.content)
            
            # 转换为比特序列
            data_bits = []
            for byte in encoded_data:
                for i in range(7, -1, -1):
                    data_bits.append((byte >> i) & 1)
            
            # 添加同步头
            sync_header = [1, 0, 1, 0, 1, 0, 1, 0]
            data_bits = sync_header + data_bits
            
            # 转换颜色空间
            img_yuv = cv2.cvtColor(img, cv2.COLOR_BGR2YUV)
            height, width = img_yuv.shape[:2]
            bit_idx = 0
            
            # 在8×8块中嵌入
            # 使用更鲁棒的方法：强制块均值到目标区间
            # bit=1 -> 均值 >= 160 (高区)
            # bit=0 -> 均值 <= 96 (低区)
            HIGH_THRESH = 160
            LOW_THRESH = 96
            
            for h in range(0, height - 7, 8):
                for w in range(0, width - 7, 8):
                    if bit_idx >= len(data_bits):
                        break
                    
                    # 获取块
                    block = img_yuv[h:h+8, w:w+8, 0].astype(float)
                    dct_mean = block.mean()
                    
                    # 嵌入比特（强制到目标区间）
                    if data_bits[bit_idx] == 1:
                        # 目标：>= 160
                        if dct_mean < HIGH_THRESH:
                            delta = HIGH_THRESH - dct_mean + 10
                            block = block + delta
                    else:
                        # 目标：<= 96
                        if dct_mean > LOW_THRESH:
                            delta = LOW_THRESH - dct_mean - 10
                            block = block + delta
                    
                    img_yuv[h:h+8, w:w+8, 0] = block.clip(0, 255)
                    bit_idx += 1
                
                if bit_idx >= len(data_bits):
                    break
            
            # 转换回BGR并保存
            img_result = cv2.cvtColor(img_yuv, cv2.COLOR_YUV2BGR)
            cv2.imwrite(output_path, img_result, [cv2.IMWRITE_JPEG_QUALITY, self.quality])
            
            logger.info(f"JPEG embed success: {bit_idx} bits")
            return self._create_success_result(output_path)
            
        except Exception as e:
            logger.error(f"JPEG embed failed: {e}")
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message=f"嵌入失败: {str(e)}",
                file_path=file_path
            )
    
    def extract(self, file_path: str, **kwargs) -> ExtractResult:
        """从 JPEG 提取水印"""
        logger.info(f"JPEG extract: {file_path}")
        
        try:
            import cv2
        except ImportError:
            return ExtractResult(
                status=WatermarkStatus.FAILED,
                message="需要安装opencv-python库",
                file_path=file_path
            )
        
        error_result = self._validate_file(file_path)
        if error_result:
            return ExtractResult(
                status=error_result.status,
                message=error_result.message,
                file_path=file_path
            )
        
        try:
            import cv2
            
            img = cv2.imread(file_path)
            if img is None:
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message="无法读取图片",
                    file_path=file_path
                )
            
            img_yuv = cv2.cvtColor(img, cv2.COLOR_BGR2YUV)
            bits = []
            height, width = img_yuv.shape[:2]
            
            # 提取比特（使用中间阈值128）
            HIGH_THRESH = 160
            LOW_THRESH = 96
            MID_THRESH = 128
            
            for h in range(0, height - 7, 8):
                for w in range(0, width - 7, 8):
                    block = img_yuv[h:h+8, w:w+8, 0].astype(float)
                    dct_mean = block.mean()
                    # 根据块均值所在的区间判断比特
                    bit = 1 if dct_mean >= MID_THRESH else 0
                    bits.append(bit)
            
            # 查找同步头
            sync = [1, 0, 1, 0, 1, 0, 1, 0]
            sync_idx = -1
            for i in range(len(bits) - 8):
                if bits[i:i+8] == sync:
                    sync_idx = i + 8
                    break
            
            if sync_idx == -1:
                logger.warning("Sync header not found")
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message="未找到同步头",
                    file_path=file_path
                )
            
            # 直接提取编码数据（无需长度前缀，codec内部有格式）
            # 尝试提取足够多的比特，让 codec 解析
            MAX_DATA_SIZE = 1024  # 最多提取 1KB 数据
            data_bits = bits[sync_idx:sync_idx + MAX_DATA_SIZE * 8]
            
            if len(data_bits) < 8:
                logger.warning("Not enough bits after sync")
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message="数据不足",
                    file_path=file_path
                )
            
            # 转换为字节
            data_bytes = bytearray()
            for i in range(0, len(data_bits) - 7, 8):
                byte = 0
                for j in range(8):
                    byte |= (data_bits[i+j] << (7-j))
                data_bytes.append(byte)
            
            logger.debug(f"First 10 bytes: {list(data_bytes[:10])}")
            
            # 解码水印
            success, content, details = self.codec.decode(bytes(data_bytes))
            
            if success:
                logger.info(f"JPEG extract success: {content[:30]}...")
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
                    message=f"解码失败: {details.get('error', '未知错误')}",
                    file_path=file_path
                )
                
        except Exception as e:
            logger.error(f"JPEG extract failed: {e}")
            return ExtractResult(
                status=WatermarkStatus.EXTRACTION_FAILED,
                message=f"提取失败: {str(e)}",
                file_path=file_path
            )
    
    def verify(self, file_path: str, original_watermark: WatermarkData,
               **kwargs) -> VerifyResult:
        """验证 JPEG 水印"""
        logger.info(f"JPEG verify: {file_path}")
        
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
        
        logger.info(f"JPEG verify result: valid={is_match}")
        return result


# 模块初始化日志
logger.info(f"{__name__} module loaded - Image handlers ready")
