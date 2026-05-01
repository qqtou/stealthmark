# core/base.py
"""
水印处理基类和结果数据类

本模块定义了 StealthMark 的核心数据结构：
- WatermarkStatus: 水印操作状态码枚举
- WatermarkType: 水印类型枚举  
- WatermarkData: 水印数据结构
- EmbedResult/ExtractResult/VerifyResult: 操作结果类
- BaseHandler: 所有文件格式处理器的抽象基类

Author: StealthMark Team
Date: 2026-04-28
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any
from pathlib import Path
import os
import logging

# 配置模块日志
logger = logging.getLogger(__name__)


class WatermarkStatus(Enum):
    """
    水印操作状态码
    
    用于标识水印操作的成功或失败原因，便于调用方进行错误处理。
    
    使用示例:
        if result.status == WatermarkStatus.SUCCESS:
            print("操作成功")
    """
    
    SUCCESS = 0              # 操作成功
    FAILED = 1               # 通用失败
    FILE_NOT_FOUND = 2       # 文件不存在
    FILE_CORRUPTED = 3       # 文件损坏
    UNSUPPORTED_FORMAT = 4   # 不支持的文件格式
    INVALID_WATERMARK = 5    # 无效的水印数据
    EXTRACTION_FAILED = 6    # 水印提取失败
    VERIFICATION_FAILED = 7  # 水印验证失败
    ENCRYPTION_FAILED = 8    # 加密失败
    DECRYPTION_FAILED = 9    # 解密失败


class WatermarkType(Enum):
    """
    水印类型枚举
    
    支持文本、图片、二进制三种水印类型。
    """
    
    TEXT = "text"      # 文本水印（默认）
    IMAGE = "image"    # 图片水印
    BINARY = "binary"  # 二进制水印


@dataclass
class WatermarkData:
    """
    水印数据结构
    
    存储水印内容及相关元数据，用于在处理器间传递。
    
    Attributes:
        content: 水印文本内容
        watermark_type: 水印类型，默认TEXT
        created_at: 创建时间（ISO格式），自动生成
        metadata: 额外元数据字典，用于存储扩展信息
    
    Example:
        >>> wm_data = WatermarkData(
        ...     content="版权所有 © 2024",
        ...     metadata={"author": "张三", "version": "1.0"}
        ... )
    """
    
    content: str
    watermark_type: WatermarkType = WatermarkType.TEXT
    created_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后自动设置创建时间"""
        if self.created_at is None:
            from datetime import datetime
            self.created_at = datetime.now().isoformat()
            logger.debug(f"WatermarkData created at {self.created_at}")


@dataclass
class OperationResult:
    """
    操作结果基类
    
    所有操作结果类的父类，定义通用属性。
    
    Attributes:
        status: 操作状态码
        message: 状态描述消息
        file_path: 操作涉及的文件路径
        data: 附加数据
    """
    
    status: WatermarkStatus
    message: str = ""
    file_path: Optional[str] = None
    data: Optional[Any] = None
    
    @property
    def is_success(self) -> bool:
        """判断操作是否成功"""
        return self.status == WatermarkStatus.SUCCESS


@dataclass
class EmbedResult(OperationResult):
    """
    水印嵌入结果
    
    继承自OperationResult，添加嵌入操作的特定属性。
    
    Attributes:
        output_path: 输出文件路径
        watermark_id: 水印唯一标识（可选）
    """
    
    output_path: Optional[str] = None
    watermark_id: Optional[str] = None


@dataclass
class ExtractResult(OperationResult):
    """
    水印提取结果
    
    继承自OperationResult，添加提取操作的特定属性。
    
    Attributes:
        watermark: 提取到的水印数据（WatermarkData类型）
    """
    
    watermark: Optional[WatermarkData] = None


@dataclass
class VerifyResult(OperationResult):
    """
    水印验证结果
    
    继承自OperationResult，添加验证操作的特定属性。
    
    Attributes:
        is_valid: 验证是否通过
        is_integrity_ok: 完整性校验是否通过
        match_score: 一致性评分（0.0-1.0）
        details: 详细信息字典
    """
    
    is_valid: bool = False
    is_integrity_ok: bool = False
    match_score: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


class BaseHandler(ABC):
    """
    水印处理器抽象基类
    
    所有文件格式的水印处理器必须继承此类并实现抽象方法。
    设计模式：模板方法模式 - 定义算法骨架，具体实现由子类完成。
    
    使用示例:
        >>> class MyHandler(BaseHandler):
        ...     SUPPORTED_EXTENSIONS = ('.my',)
        ...     HANDLER_NAME = "myformat"
        ...     
        ...     def embed(self, file_path, watermark, output_path, **kwargs):
        ...         # 实现嵌入逻辑
        ...         pass
        ...     
        ...     def extract(self, file_path, **kwargs):
        ...         # 实现提取逻辑
        ...         pass
        ...     
        ...     def verify(self, file_path, original_watermark, **kwargs):
        ...         # 实现验证逻辑
        ...         pass
    
    Attributes:
        SUPPORTED_EXTENSIONS: 支持的文件扩展名元组
        HANDLER_NAME: 处理器名称，用于日志和调试
        config: 配置字典，可通过构造函数或配置文件传入
    
    Note:
        子类必须实现embed、extract、verify三个抽象方法。
    """
    
    # 类属性：子类必须定义
    SUPPORTED_EXTENSIONS: tuple = ()
    HANDLER_NAME: str = "base"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化处理器
        
        Args:
            config: 配置字典，可包含密码、算法参数等配置项
        """
        self.config = config or {}
        self.logger = logging.getLogger(f"stealthmark.{self.HANDLER_NAME}")
        logger.debug(f"{self.HANDLER_NAME} handler initialized with config: {self.config}")
    
    @abstractmethod
    def embed(self, file_path: str, watermark: WatermarkData, 
              output_path: str, **kwargs) -> EmbedResult:
        """
        嵌入水印到文件
        
        Args:
            file_path: 原始文件路径
            watermark: 水印数据对象
            output_path: 输出文件路径
            **kwargs: 额外参数（可选）
        
        Returns:
            EmbedResult: 嵌入操作结果
        
        Raises:
            NotImplementedError: 子类必须实现此方法
        """
        pass
    
    @abstractmethod
    def extract(self, file_path: str, **kwargs) -> ExtractResult:
        """
        从文件中提取水印
        
        Args:
            file_path: 含水印文件路径
            **kwargs: 额外参数（可选）
        
        Returns:
            ExtractResult: 提取操作结果
        
        Raises:
            NotImplementedError: 子类必须实现此方法
        """
        pass
    
    @abstractmethod
    def verify(self, file_path: str, original_watermark: WatermarkData,
               **kwargs) -> VerifyResult:
        """
        验证文件中的水印
        
        Args:
            file_path: 含水印文件路径
            original_watermark: 原始水印数据对象（用于比对）
            **kwargs: 额外参数（可选）
        
        Returns:
            VerifyResult: 验证操作结果
        
        Raises:
            NotImplementedError: 子类必须实现此方法
        """
        pass
    
    def is_supported(self, file_path: str) -> bool:
        """
        检查文件是否被此处理器支持
        
        Args:
            file_path: 文件路径
        
        Returns:
            bool: 如果文件扩展名在SUPPORTED_EXTENSIONS中返回True
        """
        ext = Path(file_path).suffix.lower()
        is_sup = ext in self.SUPPORTED_EXTENSIONS
        logger.debug(f"{self.HANDLER_NAME}: is_supported({file_path}) = {is_sup}")
        return is_sup
    
    def _validate_file(self, file_path: str) -> Optional[EmbedResult]:
        """
        验证文件是否存在且可读
        
        内部辅助方法，用于在操作前验证文件有效性。
        
        Args:
            file_path: 要验证的文件路径
        
        Returns:
            Optional[EmbedResult]: 
                - 返回None表示验证通过
                - 返回EmbedResult表示验证失败，包含错误信息
        """
        logger.debug(f"Validating file: {file_path}")
        
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            return EmbedResult(
                status=WatermarkStatus.FILE_NOT_FOUND,
                message=f"文件不存在: {file_path}",
                file_path=file_path
            )
        
        if not os.path.isfile(file_path):
            logger.warning(f"Path is not a file: {file_path}")
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message=f"路径不是文件: {file_path}",
                file_path=file_path
            )
        
        if not os.access(file_path, os.R_OK):
            logger.warning(f"File is not readable: {file_path}")
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message=f"文件不可读: {file_path}",
                file_path=file_path
            )
        
        logger.debug(f"File validation passed: {file_path}")
        return None
    
    def _create_success_result(self, output_path: str, 
                                watermark_id: str = None) -> EmbedResult:
        """
        创建成功的嵌入结果
        
        内部辅助方法，用于生成标准化的成功响应。
        
        Args:
            output_path: 输出文件路径
            watermark_id: 水印唯一标识（可选）
        
        Returns:
            EmbedResult: 成功状态的结果对象
        """
        logger.info(f"{self.HANDLER_NAME}: Watermark embedded successfully -> {output_path}")
        return EmbedResult(
            status=WatermarkStatus.SUCCESS,
            message="水印嵌入成功",
            file_path=output_path,
            output_path=output_path,
            watermark_id=watermark_id
        )


# 模块初始化日志
logger.info(f"{__name__} module loaded - StealthMark base classes")