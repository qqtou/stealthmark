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
    import cv2
except ImportError:
    Image = None
    np = None
    cv2 = None

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
        将比特序列嵌入到图像LSB（每个比特嵌3个像素，冗余）
        
        Args:
            image: PIL Image对象
            bits: 比特列表（0和1）
        
        Returns:
            Image.Image: 嵌入后的图像
        """
        # 转换为numpy数组
        img_array = np.array(image)
        original_shape = img_array.shape
        flat = img_array.flatten()
        
        # 每个比特嵌3个像素（冗余）
        bit_idx = 0
        pixel_idx = 0
        while bit_idx < len(bits) and pixel_idx < len(flat):
            bit = bits[bit_idx]
            # 重复3次
            for _ in range(3):
                if pixel_idx >= len(flat):
                    break
                if bit == 1:
                    flat[pixel_idx] = flat[pixel_idx] | 1
                else:
                    flat[pixel_idx] = flat[pixel_idx] & 0xFE
                pixel_idx += 1
            bit_idx += 1
        
        # 重塑并返回
        embedded = flat.reshape(original_shape)
        return Image.fromarray(embedded.astype(np.uint8))
    
    def _extract_bits(self, image: 'Image.Image', num_bits: int) -> list:
        """
        从图像LSB提取比特序列（每3像素投票1比特）
        
        Args:
            image: PIL Image对象
            num_bits: 要提取的比特数
        
        Returns:
            list: 比特列表
        """
        img_array = np.array(image)
        flat = img_array.flatten()
        
        bits = []
        pixel_idx = 0
        while len(bits) < num_bits and pixel_idx < len(flat):
            # 每3个像素投票
            votes = []
            for _ in range(3):
                if pixel_idx >= len(flat):
                    break
                votes.append(flat[pixel_idx] & 1)
                pixel_idx += 1
            if votes:
                # 多数投票
                bit = 1 if sum(votes) > len(votes)//2 else 0
                bits.append(bit)
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


class HEICHandler(JPEGHandler):
    """
    HEIC图片水印处理器
    
    HEIC格式使用与JPEG相同的DCT域水印方法，但使用Pillow读取HEIC文件。
    
    处理流程:
    - 使用Pillow + pillow-heif读取HEIC为RGB
    - 转换为OpenCV格式(BGR)进行DCT变换
    - 在DCT系数中嵌入水印
    - 逆DCT变换并保存回HEIC
    
    注意: 需要安装 pillow-heif 库支持HEIC读写
    """
    
    SUPPORTED_EXTENSIONS = ('.heic', '.heif')
    HANDLER_NAME = "heic"
    
    # 同步头，用于提取时定位水印
    SYNC_PATTERN = bytes([0xAA] * 4)
    
    def _load_image(self, file_path: str):
        """使用Pillow加载HEIC图片，返回OpenCV格式的numpy数组"""
        from PIL import Image
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
        except ImportError:
            raise ImportError("需要安装pillow-heif库: pip install pillow-heif")
        
        # 使用Pillow打开HEIC
        pil_img = Image.open(file_path)
        # 转换为RGB
        if pil_img.mode != 'RGB':
            pil_img = pil_img.convert('RGB')
        # 转换为numpy数组 (RGB)
        img_array = np.array(pil_img)
        # 转换为BGR (OpenCV格式)
        return cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    
    def _save_image(self, img_array: np.ndarray, output_path: str, quality: int = 95):
        """使用Pillow保存为HEIC格式"""
        from PIL import Image
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
        except ImportError:
            raise ImportError("需要安装pillow-heif库: pip install pillow-heif")
        
        # 转换BGR到RGB
        rgb_array = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
        # 创建Pillow图像
        pil_img = Image.fromarray(rgb_array)
        # 保存为HEIC
        pil_img.save(output_path, 'HEIF', quality=quality)
    
    def embed(self, file_path: str, watermark: WatermarkData, 
              output_path: str, **kwargs) -> EmbedResult:
        """向HEIC图片嵌入水印"""
        logger.info(f"HEIC embed: {file_path}")
        
        try:
            # 加载图片
            img = self._load_image(file_path)
            
            # 准备水印数据
            if hasattr(watermark, 'content'):
                text = watermark.content
            else:
                text = str(watermark)
            
            encoded = self.codec.encode(text)
            payload = self.SYNC_PATTERN + encoded
            bits = [int(b) for b in ''.join(format(b, '08b') for b in payload)]
            
            # DCT嵌入 (复用父类逻辑)
            ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
            y_channel = ycrcb[:, :, 0].astype(np.float32)
            
            h, w = y_channel.shape
            block_h, block_w = h // 8, w // 8
            
            if block_h * block_w < len(bits):
                return EmbedResult(
                    status=WatermarkStatus.FAILED,
                    message=f"图片太小，需要至少{len(bits)}个8x8块",
                    file_path=file_path
                )
            
            # 嵌入比特到DCT系数
            bit_idx = 0
            for i in range(block_h):
                for j in range(block_w):
                    if bit_idx >= len(bits):
                        break
                    block = y_channel[i*8:(i+1)*8, j*8:(j+1)*8]
                    dct_block = cv2.dct(block)
                    dct_block[2, 3] = (dct_block[2, 3] // 10) * 10 + bits[bit_idx] * 5
                    y_channel[i*8:(i+1)*8, j*8:(j+1)*8] = cv2.idct(dct_block)
                    bit_idx += 1
                if bit_idx >= len(bits):
                    break
            
            ycrcb[:, :, 0] = y_channel.astype(np.uint8)
            watermarked = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)
            
            # 保存
            self._save_image(watermarked, output_path)
            
            logger.info(f"HEIC embed success: {bit_idx} bits")
            return self._create_success_result(output_path)
            
        except Exception as e:
            logger.error(f"HEIC embed failed: {e}")
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message=f"嵌入失败: {e}",
                file_path=file_path
            )
    
    def extract(self, file_path: str, **kwargs) -> ExtractResult:
        """从HEIC图片提取水印"""
        logger.info(f"HEIC extract: {file_path}")
        
        try:
            # 加载图片
            img = self._load_image(file_path)
            
            # 提取DCT系数
            ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
            y_channel = ycrcb[:, :, 0].astype(np.float32)
            
            h, w = y_channel.shape
            block_h, block_w = h // 8, w // 8
            
            # 提取所有比特
            bits = []
            for i in range(block_h):
                for j in range(block_w):
                    block = y_channel[i*8:(i+1)*8, j*8:(j+1)*8]
                    dct_block = cv2.dct(block)
                    bit = 1 if (dct_block[2, 3] % 10) >= 5 else 0
                    bits.append(bit)
            
            # 转换为字节
            data_bytes = bytearray()
            for i in range(0, len(bits) - 7, 8):
                byte_val = 0
                for j in range(8):
                    byte_val = (byte_val << 1) | bits[i + j]
                data_bytes.append(byte_val)
            
            # 查找同步头
            try:
                sync_idx = data_bytes.index(0xAA)
                while sync_idx < len(data_bytes) - 3 and data_bytes[sync_idx:sync_idx+4] != self.SYNC_PATTERN:
                    sync_idx = data_bytes.index(0xAA, sync_idx + 1)
                payload_start = sync_idx + 4
            except (ValueError, IndexError):
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message="未找到同步头",
                    file_path=file_path
                )
            
            # 解码
            success, content, details = self.codec.decode(bytes(data_bytes[payload_start:]))
            if success:
                return ExtractResult(
                    status=WatermarkStatus.SUCCESS,
                    watermark=WatermarkData(content=content),
                    file_path=file_path
                )
            else:
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message=f"解码失败: {details.get('error', '未知')}",
                    file_path=file_path
                )
                
        except Exception as e:
            logger.error(f"HEIC extract failed: {e}")
            return ExtractResult(
                status=WatermarkStatus.EXTRACTION_FAILED,
                message=str(e),
                file_path=file_path
            )


# 模块初始化日志
logger.info(f"{__name__} module loaded - Image handlers ready")
