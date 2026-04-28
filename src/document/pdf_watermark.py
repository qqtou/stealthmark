# document/pdf_watermark.py
"""
PDF文档水印处理器 - 元数据嵌入方式

本模块实现 PDF 文档的水印处理：
- 嵌入方式：PDF 元数据（/SMMark 字段）
- 优点：不改变文档内容，兼容性好
- 缺点：元数据可被编辑器修改/删除

技术方案：
1. 使用 PyPDF2 读取 PDF 元数据
2. 将水印编码后存入自定义元数据字段 /SMMark
3. 提取时从元数据中读取并解码

使用示例:
    >>> handler = PDFHandler()
    >>> 
    >>> # 嵌入水印
    >>> result = handler.embed(
    ...     "document.pdf",
    ...     WatermarkData(content="版权所有"),
    ...     "output.pdf"
    ... )
    >>> 
    >>> # 提取水印
    >>> result = handler.extract("output.pdf")
    >>> print(result.watermark.content)

依赖:
    - PyPDF2: PDF 文件操作

Author: StealthMark Team
Date: 2026-04-28
"""

import os
from typing import Optional, Dict, Any
import logging

# 延迟导入，允许模块在没有依赖时加载
try:
    from PyPDF2 import PdfReader, PdfWriter
except ImportError:
    PdfReader = None
    PdfWriter = None

from ..core.base import (
    BaseHandler, WatermarkData, WatermarkStatus,
    EmbedResult, ExtractResult, VerifyResult
)
from ..core.codec import WatermarkCodec

# 模块日志
logger = logging.getLogger(__name__)


class PDFHandler(BaseHandler):
    """
    PDF文档水印处理器
    
    使用 PDF 元数据嵌入水印，不改变文档视觉内容。
    
    水印存储位置:
        PDF 元数据字段 /SMMark（Base64 编码）
    
    支持的嵌入方式:
        - metadata: 元数据嵌入（默认，当前实现）
        - lsb: LSB 隐写（未实现，需要解析 PDF 内部结构）
    
    Attributes:
        embed_method: 嵌入方式（'metadata' 或 'lsb'）
        codec: WatermarkCodec 实例，用于编解码
    
    限制:
        - 元数据可能被 PDF 编辑器修改或删除
        - 某些 PDF 阅读器会清理"未知"元数据字段
    """
    
    SUPPORTED_EXTENSIONS = ('.pdf',)
    HANDLER_NAME = "pdf"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化 PDF 处理器
        
        Args:
            config: 配置字典，支持以下选项:
                - embed_method: 嵌入方式（默认 'metadata'）
                - password: 加密密码（可选）
        """
        super().__init__(config)
        self.embed_method = self.config.get('embed_method', 'metadata')
        self.codec = WatermarkCodec(password=self.config.get('password'))
        
        logger.debug(f"PDFHandler initialized: method={self.embed_method}")
    
    def embed(self, file_path: str, watermark: WatermarkData,
              output_path: str, **kwargs) -> EmbedResult:
        """
        嵌入水印到 PDF
        
        嵌入流程:
        1. 读取原始 PDF
        2. 复制所有页面到新 PDF
        3. 复制原有元数据
        4. 添加水印元数据 /SMMark
        5. 保存新 PDF
        
        Args:
            file_path: 原始 PDF 文件路径
            watermark: 水印数据对象
            output_path: 输出 PDF 文件路径
            **kwargs: 额外参数（未使用）
        
        Returns:
            EmbedResult: 嵌入结果
        """
        logger.info(f"PDF embed: {file_path} -> {output_path}")
        
        # 检查依赖
        if PdfReader is None:
            logger.error("PyPDF2 not installed")
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message="需要安装PyPDF2库: pip install PyPDF2",
                file_path=file_path
            )
        
        # 验证文件
        error_result = self._validate_file(file_path)
        if error_result:
            return error_result
        
        try:
            # 读取原始 PDF
            reader = PdfReader(file_path)
            writer = PdfWriter()
            
            # 复制所有页面
            for page in reader.pages:
                writer.add_page(page)
            
            # 复制原有元数据
            if reader.metadata:
                for key, value in reader.metadata.items():
                    writer.add_metadata({key: value})
            
            # 编码水印
            encoded_data = self.codec.encode(watermark.content)
            encoded_b64 = self.codec.to_base64(encoded_data)
            
            # 添加水印元数据
            writer.add_metadata({
                '/SMMark': encoded_b64,  # StealthMark 水印字段
            })
            
            # 保存
            with open(output_path, 'wb') as f:
                writer.write(f)
            
            logger.info(f"PDF embed success: {output_path}")
            return self._create_success_result(output_path)
            
        except Exception as e:
            logger.error(f"PDF embed failed: {e}")
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message=f"嵌入失败: {str(e)}",
                file_path=file_path
            )
    
    def extract(self, file_path: str, **kwargs) -> ExtractResult:
        """
        从 PDF 提取水印
        
        提取流程:
        1. 读取 PDF 元数据
        2. 获取 /SMMark 字段
        3. Base64 解码
        4. 水印解码
        
        Args:
            file_path: PDF 文件路径
            **kwargs: 额外参数（未使用）
        
        Returns:
            ExtractResult: 提取结果
        """
        logger.info(f"PDF extract: {file_path}")
        
        # 检查依赖
        if PdfReader is None:
            logger.error("PyPDF2 not installed")
            return ExtractResult(
                status=WatermarkStatus.FAILED,
                message="需要安装PyPDF2库",
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
            # 读取 PDF
            reader = PdfReader(file_path)
            
            # 检查元数据
            if not reader.metadata:
                logger.warning("PDF has no metadata")
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message="PDF没有元数据",
                    file_path=file_path
                )
            
            # 获取水印字段
            smmark = reader.metadata.get('/SMMark', '')
            
            if smmark:
                # 解码水印
                encoded_data = self.codec.from_base64(smmark)
                success, content, details = self.codec.decode(encoded_data)
                
                if success:
                    logger.info(f"PDF extract success: {content[:30]}...")
                    return ExtractResult(
                        status=WatermarkStatus.SUCCESS,
                        message="水印提取成功",
                        file_path=file_path,
                        watermark=WatermarkData(content=content)
                    )
                else:
                    logger.warning(f"Watermark decode failed: {details}")
            
            # 未找到水印
            logger.warning("No watermark found in PDF")
            return ExtractResult(
                status=WatermarkStatus.EXTRACTION_FAILED,
                message="未找到水印",
                file_path=file_path
            )
            
        except Exception as e:
            logger.error(f"PDF extract failed: {e}")
            return ExtractResult(
                status=WatermarkStatus.EXTRACTION_FAILED,
                message=f"提取失败: {str(e)}",
                file_path=file_path
            )
    
    def verify(self, file_path: str, original_watermark: WatermarkData,
               **kwargs) -> VerifyResult:
        """
        验证 PDF 水印
        
        Args:
            file_path: PDF 文件路径
            original_watermark: 原始水印数据（用于比对）
            **kwargs: 额外参数（未使用）
        
        Returns:
            VerifyResult: 验证结果
        """
        logger.info(f"PDF verify: {file_path}")
        
        # 提取水印
        extract_result = self.extract(file_path)
        
        # 提取失败
        if not extract_result.is_success or not extract_result.watermark:
            return VerifyResult(
                status=extract_result.status,
                is_valid=False,
                is_integrity_ok=False,
                match_score=0.0,
                message=f"提取失败: {extract_result.message}"
            )
        
        # 比对水印
        extracted = extract_result.watermark.content
        original = original_watermark.content
        
        is_match = extracted == original
        match_score = 1.0 if is_match else 0.0
        
        result = VerifyResult(
            status=WatermarkStatus.SUCCESS if is_match else WatermarkStatus.VERIFICATION_FAILED,
            is_valid=is_match,
            is_integrity_ok=True,
            match_score=match_score,
            message="验证通过" if is_match else "水印不匹配"
        )
        
        logger.info(f"PDF verify result: valid={is_match}")
        return result


# 模块初始化日志
logger.info(f"{__name__} module loaded - PDF handler ready")
