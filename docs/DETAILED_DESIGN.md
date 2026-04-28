# StealthMark 详细设计说明书

---

## 文档信息

| 属性 | 内容 |
|------|------|
| 项目名称 | StealthMark |
| 文档版本 | 1.0 |
| 关联文档 | SRS.md, DESIGN.md |
| 创建日期 | 2026-04-28 |

---

## 1. 系统架构

### 1.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              StealthMark                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐               │
│  │   CLI 接口   │    │  Python API  │    │   GUI 接口   │ (Future)    │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘               │
│         │                  │                   │                       │
│         └──────────────────┼───────────────────┘                       │
│                            ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      StealthMark 核心引擎                        │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │   │
│  │  │  WatermarkMgr │  │ FormatHandler │  │  CryptoMgr    │       │   │
│  │  │   (管理器)     │  │  (格式处理器)  │  │   (加密管理)   │       │   │
│  │  └───────┬───────┘  └───────┬───────┘  └───────────────┘       │   │
│  │          │                  │                                   │   │
│  │  ┌───────┴──────────────────┴───────────────────────────┐     │   │
│  │  │                      Codec 模块                        │     │   │
│  │  │  WatermarkCodec ─┬─► CRC32 ──► Base64 ──► AES256      │     │   │
│  │  └──────────────────┴────────────────────────────────────┘     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                            │                                           │
│         ┌──────────────────┼──────────────────┐                        │
│         ▼                  ▼                  ▼                        │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐               │
│  │  Document   │    │   Image    │    │   Media     │               │
│  │   水印模块   │    │  水印模块   │    │  水印模块    │               │
│  └─────────────┘    └─────────────┘    └─────────────┘               │
│         │                  │                  │                       │
│         ▼                  ▼                  ▼                       │
│  ┌─────────────────────────────┐    ┌─────────────────────────────┐    ┌─────────────────────────────┐               │
│  │ PDF/DOCX/PPTX/XLSX/ODT/      │    │ PNG/BMP/JPEG/TIFF/WebP/      │    │ WAV/MP3/FLAC/AAC/MP4/       │               │
│  │ ODS/ODP/EPUB/RTF             │    │ GIF/HEIC                    │    │ AVI/MOV/WebM/WMV            │               │
│  └─────────────────────────────┘    └─────────────────────────────┘    └─────────────────────────────┘               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 模块职责

| 模块 | 职责 | 依赖 |
|------|------|------|
| StealthMark | 门面类，统一入口 | 所有子模块 |
| StealthMark | 门面类，统一入口，注册23个Handler | 所有子模块 |
| Codec | 水印编解码、加密解密（CRC32+Base64+AES-256） | zlib, cryptography |
| DocumentHandlers | PDF/DOCX/PPTX/XLSX/ODT/ODS/ODP/EPUB/RTF水印处理 | Codec |
| ImageHandlers | PNG/BMP/JPEG/TIFF/WebP/GIF/HEIC水印处理 | Codec |
| MediaHandlers | WAV/MP3/FLAC/AAC/MP4/AVI/MOV/WebM/WMV水印处理 | Codec |

---

## 2. 模块详细设计

### 2.1 核心模块 (core/)

#### 2.1.1 base.py - 基类定义

```python
# core/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class WatermarkStatus(Enum):
    """水印操作状态码"""
    SUCCESS = 0
    FAILED = 1
    FILE_NOT_FOUND = 2
    FILE_CORRUPTED = 3
    UNSUPPORTED_FORMAT = 4
    INVALID_WATERMARK = 5
    EXTRACTION_FAILED = 6
    VERIFICATION_FAILED = 7
    ENCRYPTION_FAILED = 8
    DECRYPTION_FAILED = 9


class WatermarkType(Enum):
    """水印类型"""
    TEXT = "text"
    IMAGE = "image"
    BINARY = "binary"


@dataclass
class WatermarkData:
    """水印数据结构"""
    content: str                          # 水印内容
    watermark_type: WatermarkType = WatermarkType.TEXT
    created_at: Optional[str] = None      # 创建时间 (ISO格式)
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外元数据
    
    def __post_init__(self):
        if self.created_at is None:
            from datetime import datetime
            self.created_at = datetime.now().isoformat()


@dataclass
class OperationResult:
    """操作结果基类"""
    status: WatermarkStatus
    message: str = ""
    file_path: Optional[str] = None
    data: Optional[Any] = None
    
    @property
    def is_success(self) -> bool:
        return self.status == WatermarkStatus.SUCCESS


@dataclass 
class EmbedResult(OperationResult):
    """嵌入结果"""
    output_path: Optional[str] = None
    watermark_id: Optional[str] = None   # 水印唯一标识


@dataclass
class ExtractResult(OperationResult):
    """提取结果"""
    watermark: Optional[WatermarkData] = None


@dataclass
class VerifyResult(OperationResult):
    """验证结果"""
    is_valid: bool = False
    is_integrity_ok: bool = False        # 完整性校验
    match_score: float = 0.0             # 一致性评分 0.0-1.0
    details: Dict[str, Any] = field(default_factory=dict)


class BaseHandler(ABC):
    """
    水印处理器基类
    所有具体格式的处理器都继承此类
    """
    
    # 子类必须定义的类属性
    SUPPORTED_EXTENSIONS: tuple = ()     # 支持的文件扩展名
    HANDLER_NAME: str = "base"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化处理器
        
        Args:
            config: 配置字典，可包含密钥、算法参数等
        """
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.HANDLER_NAME}")
        self._validate_config()
    
    def _validate_config(self) -> None:
        """验证配置合法性，子类可重写"""
        pass
    
    @abstractmethod
    def embed(self, file_path: str, watermark: WatermarkData, 
              output_path: str, **kwargs) -> EmbedResult:
        """
        嵌入水印
        
        Args:
            file_path: 原始文件路径
            watermark: 水印数据
            output_path: 输出文件路径
            **kwargs: 额外参数
            
        Returns:
            EmbedResult: 嵌入结果
        """
        pass
    
    @abstractmethod
    def extract(self, file_path: str, **kwargs) -> ExtractResult:
        """
        提取水印
        
        Args:
            file_path: 含水印文件路径
            **kwargs: 额外参数
            
        Returns:
            ExtractResult: 提取结果
        """
        pass
    
    @abstractmethod
    def verify(self, file_path: str, original_watermark: WatermarkData,
               **kwargs) -> VerifyResult:
        """
        验证水印
        
        Args:
            file_path: 含水印文件路径
            original_watermark: 原始水印数据
            **kwargs: 额外参数
            
        Returns:
            VerifyResult: 验证结果
        """
        pass
    
    def is_supported(self, file_path: str) -> bool:
        """
        检查文件是否被此处理器支持
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否支持
        """
        ext = Path(file_path).suffix.lower()
        return ext in self.SUPPORTED_EXTENSIONS
    
    def _validate_file(self, file_path: str) -> Optional[EmbedResult]:
        """
        验证文件是否存在且可读
        
        Returns:
            如果验证失败返回错误结果，否则返回None
        """
        path = Path(file_path)
        if not path.exists():
            return EmbedResult(
                status=WatermarkStatus.FILE_NOT_FOUND,
                message=f"文件不存在: {file_path}",
                file_path=file_path
            )
        if not path.is_file():
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message=f"路径不是文件: {file_path}",
                file_path=file_path
            )
        if not os.access(file_path, os.R_OK):
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message=f"文件不可读: {file_path}",
                file_path=file_path
            )
        return None
    
    def _create_success_result(self, output_path: str, 
                                watermark_id: str = None) -> EmbedResult:
        """创建成功结果"""
        return EmbedResult(
            status=WatermarkStatus.SUCCESS,
            message="水印嵌入成功",
            file_path=output_path,
            output_path=output_path,
            watermark_id=watermark_id
        )


import os
```

#### 2.1.2 codec.py - 水印编解码模块

```python
# core/codec.py

import base64
import zlib
import hashlib
import json
from typing import Optional, Tuple
from dataclasses import dataclass, asdict
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


# 常量定义
WATERMARK_MAGIC = b"SMARK"           # 水印魔数标识
WATERMARK_VERSION = 1                # 水印格式版本
LENGTH_FIELD_SIZE = 4                # 长度字段字节数


class WatermarkCodec:
    """
    水印编解码器
    负责水印数据的编码、解码、加密、解密
    """
    
    def __init__(self, password: Optional[str] = None, salt: Optional[bytes] = None):
        """
        初始化编解码器
        
        Args:
            password: 加密密码（可选）
            salt: 盐值（可选）
        """
        self.password = password
        self.salt = salt or b"StealthMark2024"  # 默认盐值
        self._key = None
        if password:
            self._derive_key(password)
    
    def _derive_key(self, password: str) -> None:
        """使用PBKDF2派生加密密钥"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # AES-256
            salt=self.salt,
            iterations=100000,
            backend=default_backend()
        )
        self._key = kdf.derive(password.encode('utf-8'))
    
    # ========== 编码流程 ==========
    
    def encode(self, watermark_content: str) -> bytes:
        """
        编码水印内容
        
        编码格式:
        [魔数(5)][版本(1)][长度(4)][内容(n)][CRC32(4)]
        
        Args:
            watermark_content: 水印文本内容
            
        Returns:
            bytes: 编码后的二进制数据
        """
        # Step 1: UTF-8编码
        content_bytes = watermark_content.encode('utf-8')
        
        # Step 2: 计算CRC32校验
        crc = zlib.crc32(content_bytes) & 0xFFFFFFFF
        
        # Step 3: 组装数据
        length = len(content_bytes)
        encoded = bytearray()
        
        # 魔数
        encoded.extend(WATERMARK_MAGIC)
        # 版本
        encoded.append(WATERMARK_VERSION)
        # 长度
        encoded.extend(length.to_bytes(LENGTH_FIELD_SIZE, byteorder='big'))
        # 内容
        encoded.extend(content_bytes)
        # CRC32
        encoded.extend(crc.to_bytes(4, byteorder='big'))
        
        return bytes(encoded)
    
    def encode_with_encryption(self, watermark_content: str) -> bytes:
        """
        加密编码水印
        
        Args:
            watermark_content: 水印文本内容
            
        Returns:
            bytes: 加密后的二进制数据
        """
        if not self._key:
            raise ValueError("加密需要提供密码")
        
        # 先编码
        encoded = self.encode(watermark_content)
        
        # AES加密
        return self._aes_encrypt(encoded)
    
    def _aes_encrypt(self, data: bytes) -> bytes:
        """AES-256-CBC加密"""
        # 生成随机IV
        import os
        iv = os.urandom(16)
        
        # PKCS7填充
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(data) + padder.finalize()
        
        # 加密
        cipher = Cipher(
            algorithms.AES(self._key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        encrypted = encryptor.update(padded_data) + encryptor.finalize()
        
        # 返回 IV + 密文
        return iv + encrypted
    
    # ========== 解码流程 ==========
    
    def decode(self, data: bytes) -> Tuple[bool, str, dict]:
        """
        解码水印数据
        
        Args:
            data: 编码后的二进制数据
            
        Returns:
            Tuple[成功标志, 水印内容, 详细信息]
        """
        try:
            pos = 0
            
            # 验证魔数
            magic = data[pos:pos+5]
            if magic != WATERMARK_MAGIC:
                return False, "", {"error": "无效的水印格式"}
            pos += 5
            
            # 读取版本
            version = data[pos]
            pos += 1
            
            # 读取长度
            length = int.from_bytes(data[pos:pos+LENGTH_FIELD_SIZE], byteorder='big')
            pos += LENGTH_FIELD_SIZE
            
            # 读取内容
            content_bytes = data[pos:pos+length]
            pos += length
            
            # 读取CRC32
            stored_crc = int.from_bytes(data[pos:pos+4], byteorder='big')
            
            # 验证CRC32
            calculated_crc = zlib.crc32(content_bytes) & 0xFFFFFFFF
            if stored_crc != calculated_crc:
                return False, "", {
                    "error": "CRC校验失败",
                    "stored_crc": stored_crc,
                    "calculated_crc": calculated_crc
                }
            
            # 解码为文本
            content = content_bytes.decode('utf-8')
            
            return True, content, {
                "version": version,
                "length": length,
                "crc_ok": True
            }
            
        except Exception as e:
            return False, "", {"error": str(e)}
    
    def decode_with_decryption(self, data: bytes) -> Tuple[bool, str, dict]:
        """
        解密解码水印数据
        
        Args:
            data: 加密后的二进制数据
            
        Returns:
            Tuple[成功标志, 水印内容, 详细信息]
        """
        if not self._key:
            raise ValueError("解密需要提供密码")
        
        try:
            # AES解密
            decrypted = self._aes_decrypt(data)
            # 解码
            return self.decode(decrypted)
        except Exception as e:
            return False, "", {"error": f"解密失败: {str(e)}"}
    
    def _aes_decrypt(self, data: bytes) -> bytes:
        """AES-256-CBC解密"""
        # 提取IV和密文
        iv = data[:16]
        ciphertext = data[16:]
        
        # 解密
        cipher = Cipher(
            algorithms.AES(self._key),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()
        
        # 去除填充
        unpadder = padding.PKCS7(128).unpadder()
        data = unpadder.update(padded_data) + unpadder.finalize()
        
        return data
    
    # ========== 辅助方法 ==========
    
    @staticmethod
    def to_hex(data: bytes) -> str:
        """转换为十六进制字符串（用于日志/调试）"""
        return data.hex()
    
    @staticmethod
    def from_hex(hex_str: str) -> bytes:
        """从十六进制字符串转换"""
        return bytes.fromhex(hex_str)
    
    @staticmethod
    def to_base64(data: bytes) -> str:
        """转换为Base64字符串"""
        return base64.b64encode(data).decode('ascii')
    
    @staticmethod
    def from_base64(b64_str: str) -> bytes:
        """从Base64字符串转换"""
        return base64.b64decode(b64_str)
    
    @staticmethod
    def hash_content(content: str) -> str:
        """计算内容SHA256哈希"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
```

#### 2.1.3 manager.py - 水印管理器

```python
# core/manager.py

from typing import Optional, Dict, List, Type
from pathlib import Path
import logging

from .base import (
    BaseHandler, WatermarkData, WatermarkType,
    EmbedResult, ExtractResult, VerifyResult, WatermarkStatus
)
from .codec import WatermarkCodec


logger = logging.getLogger(__name__)


class StealthMark:
    """
    StealthMark 门面类
    提供统一的水印操作入口
    """
    
    def __init__(self, password: Optional[str] = None):
        """
        初始化 StealthMark
        
        Args:
            password: 水印加密密码（可选）
        """
        self.password = password
        self.codec = WatermarkCodec(password=password)
        self._handlers: Dict[str, BaseHandler] = {}
        self._handler_registry: List[Type[BaseHandler]] = []
        
        # 加载所有内置处理器
        self._register_builtin_handlers()
        
        logger.info(f"StealthMark initialized with {len(self._handler_registry)} handlers")
    
    def _register_builtin_handlers(self) -> None:
        """注册内置处理器（23个Handler，30种格式）"""
        from ..document import (
            PDFHandler, DOCXHandler, PPTXHandler,
            XLSXHandler, ODTHandler, ODSHandler, ODPHandler,
            EPUBHandler, RTFHandler
        )
        from ..image import (
            PNGHandler, BMPHandler, JPEGHandler,
            TIFFHandler, WebPHandler, GIFHandler, HEICHandler
        )
        from ..media import (
            WAVHandler, MP3Handler, VideoHandler,
            FLACHandler, AACHandler, WebMHandler, WMVHandler
        )
        
        handler_classes = [
            # 文档（9个Handler）
            PDFHandler, DOCXHandler, PPTXHandler,
            XLSXHandler, ODTHandler, ODSHandler, ODPHandler,
            EPUBHandler, RTFHandler,
            # 图片（7个Handler）
            PNGHandler, BMPHandler, JPEGHandler,
            TIFFHandler, WebPHandler, GIFHandler, HEICHandler,
            # 音频（4个Handler）
            WAVHandler, MP3Handler, FLACHandler, AACHandler,
            # 视频（3个Handler）
            VideoHandler, WebMHandler, WMVHandler,
        ]
        
        for handler_class in handler_classes:
            self.register_handler(handler_class)
    
    def register_handler(self, handler_class: Type[BaseHandler]) -> None:
        """
        注册水印处理器
        
        Args:
            handler_class: 处理器类（必须是BaseHandler的子类）
        """
        try:
            handler = handler_class()
            for ext in handler.SUPPORTED_EXTENSIONS:
                self._handlers[ext.lower()] = handler
            self._handler_registry.append(handler_class)
            logger.debug(f"Registered handler: {handler.HANDLER_NAME}")
        except Exception as e:
            logger.error(f"Failed to register handler {handler_class}: {e}")
    
    def _get_handler(self, file_path: str) -> Optional[BaseHandler]:
        """
        获取文件对应的处理器
        
        Args:
            file_path: 文件路径
            
        Returns:
            对应的处理器，如果没有则返回None
        """
        ext = Path(file_path).suffix.lower()
        return self._handlers.get(ext)
    
    def embed(self, file_path: str, watermark: str, 
              output_path: Optional[str] = None, **kwargs) -> EmbedResult:
        """
        嵌入水印
        
        Args:
            file_path: 原始文件路径
            watermark: 水印文本内容
            output_path: 输出文件路径（默认覆盖原文件）
            **kwargs: 额外参数
            
        Returns:
            EmbedResult: 嵌入结果
        """
        # 验证文件
        path = Path(file_path)
        if not path.exists():
            return EmbedResult(
                status=WatermarkStatus.FILE_NOT_FOUND,
                message=f"文件不存在: {file_path}",
                file_path=file_path
            )
        
        # 获取处理器
        handler = self._get_handler(file_path)
        if not handler:
            return EmbedResult(
                status=WatermarkStatus.UNSUPPORTED_FORMAT,
                message=f"不支持的文件格式: {Path(file_path).suffix}",
                file_path=file_path
            )
        
        # 确定输出路径
        if output_path is None:
            output_path = file_path
        
        # 创建水印数据
        watermark_data = WatermarkData(content=watermark)
        
        # 调用处理器嵌入
        logger.info(f"Embedding watermark to: {file_path}")
        result = handler.embed(file_path, watermark_data, output_path, **kwargs)
        
        if result.is_success:
            logger.info(f"Watermark embedded successfully: {output_path}")
        
        return result
    
    def extract(self, file_path: str, **kwargs) -> ExtractResult:
        """
        提取水印
        
        Args:
            file_path: 含水印文件路径
            **kwargs: 额外参数
            
        Returns:
            ExtractResult: 提取结果
        """
        # 获取处理器
        handler = self._get_handler(file_path)
        if not handler:
            return ExtractResult(
                status=WatermarkStatus.UNSUPPORTED_FORMAT,
                message=f"不支持的文件格式: {Path(file_path).suffix}",
                file_path=file_path
            )
        
        # 调用处理器提取
        logger.info(f"Extracting watermark from: {file_path}")
        result = handler.extract(file_path, **kwargs)
        
        if result.is_success and result.watermark:
            logger.info(f"Watermark extracted: {result.watermark.content[:50]}...")
        
        return result
    
    def verify(self, file_path: str, original_watermark: str,
               **kwargs) -> VerifyResult:
        """
        验证水印
        
        Args:
            file_path: 含水印文件路径
            original_watermark: 原始水印文本
            **kwargs: 额外参数
            
        Returns:
            VerifyResult: 验证结果
        """
        # 提取水印
        extract_result = self.extract(file_path, **kwargs)
        
        if not extract_result.is_success or not extract_result.watermark:
            return VerifyResult(
                status=extract_result.status,
                message=f"提取失败: {extract_result.message}",
                is_valid=False,
                is_integrity_ok=False,
                match_score=0.0
            )
        
        # 比对
        extracted = extract_result.watermark.content
        original = original_watermark
        
        # 计算匹配分数
        if extracted == original:
            match_score = 1.0
        else:
            # 使用编辑距离计算相似度
            match_score = self._calculate_similarity(extracted, original)
        
        # 判断完整性（CRC校验在提取时已验证）
        is_integrity_ok = extract_result.status == WatermarkStatus.SUCCESS
        
        # 判断有效性
        is_valid = match_score >= 0.8 and is_integrity_ok
        
        return VerifyResult(
            status=WatermarkStatus.SUCCESS if is_valid else WatermarkStatus.VERIFICATION_FAILED,
            message="验证通过" if is_valid else "验证失败",
            is_valid=is_valid,
            is_integrity_ok=is_integrity_ok,
            match_score=match_score,
            details={
                "extracted": extracted,
                "original": original,
                "similarity": f"{match_score * 100:.1f}%"
            }
        )
    
    def _calculate_similarity(self, s1: str, s2: str) -> float:
        """计算两个字符串的相似度（Levenshtein距离）"""
        if s1 == s2:
            return 1.0
        if not s1 or not s2:
            return 0.0
        
        len1, len2 = len(s1), len(s2)
        max_len = max(len1, len2)
        
        # 简化的编辑距离计算
        if len1 > 100 or len2 > 100:
            # 长字符串使用哈希比对
            from .codec import WatermarkCodec
            hash1 = WatermarkCodec.hash_content(s1)
            hash2 = WatermarkCodec.hash_content(s2)
            return 1.0 if hash1 == hash2 else 0.0
        
        # 动态规划计算编辑距离
        dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]
        
        for i in range(len1 + 1):
            dp[i][0] = i
        for j in range(len2 + 1):
            dp[0][j] = j
        
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                if s1[i-1] == s2[j-1]:
                    dp[i][j] = dp[i-1][j-1]
                else:
                    dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
        
        distance = dp[len1][len2]
        return 1.0 - (distance / max_len)
    
    def is_supported(self, file_path: str) -> bool:
        """
        检查文件格式是否支持
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否支持
        """
        ext = Path(file_path).suffix.lower()
        return ext in self._handlers
    
    def supported_formats(self) -> List[str]:
        """
        获取所有支持的文件格式
        
        Returns:
            扩展名列表
        """
        return list(self._handlers.keys())
```

---

## 3. 文档水印模块 (document/)

### 3.0 Handler 概览

| Handler | 文件 | 嵌入方案 | 扩展名 |
|---------|------|---------|--------|
| PDFHandler | pdf_watermark.py | 元数据Author字段 | .pdf |
| DOCXHandler | docx_watermark.py | 零宽字符（U+200B/U+200C） | .docx |
| PPTXHandler | pptx_watermark.py | 隐藏形状（hidden_前缀） | .pptx |
| XLSXHandler | xlsx_watermark.py | customXml/item1.xml属性 | .xlsx |
| ODTHandler | odt_watermark.py | ODF user-defined元数据 | .odt |
| ODSHandler | ods_watermark.py | ODF user-defined元数据 | .ods |
| ODPHandler | odp_watermark.py | ODF user-defined元数据 | .odp |
| EPUBHandler | epub_watermark.py | OPF dc:identifier | .epub |
| RTFHandler | rtf_watermark.py | 可忽略控制组 | .rtf |

### 3.1 pdf_watermark.py

```python
# document/pdf_watermark.py

import os
from typing import Optional, Dict, Any
from pathlib import Path
import logging

try:
    import PyPDF2
    from PyPDF2 import PdfReader, PdfWriter
except ImportError:
    PyPDF2 = None

from ..core.base import (
    BaseHandler, WatermarkData, WatermarkStatus,
    EmbedResult, ExtractResult, VerifyResult
)
from ..core.codec import WatermarkCodec


class PDFHandler(BaseHandler):
    """PDF文档水印处理器"""
    
    SUPPORTED_EXTENSIONS = ('.pdf',)
    HANDLER_NAME = "pdf"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.embed_method = self.config.get('embed_method', 'metadata')  # metadata or lsb
        self.codec = WatermarkCodec(password=self.config.get('password'))
    
    def embed(self, file_path: str, watermark: WatermarkData,
              output_path: str, **kwargs) -> EmbedResult:
        """嵌入水印到PDF"""
        
        # 验证文件
        error_result = self._validate_file(file_path)
        if error_result:
            return error_result
        
        try:
            if self.embed_method == 'metadata':
                return self._embed_metadata(file_path, watermark, output_path)
            else:
                return self._embed_lsb(file_path, watermark, output_path)
                
        except Exception as e:
            self.logger.error(f"PDF embed failed: {e}")
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message=f"嵌入失败: {str(e)}",
                file_path=file_path
            )
    
    def _embed_metadata(self, file_path: str, watermark: WatermarkData,
                        output_path: str) -> EmbedResult:
        """
        使用元数据嵌入水印
        
        将水印编码后分散写入多个元数据字段
        """
        reader = PdfReader(file_path)
        writer = PdfWriter()
        
        # 复制所有页面
        for page in reader.pages:
            writer.add_page(page)
        
        # 复制元数据
        if reader.metadata:
            for key, value in reader.metadata.items():
                writer.add_metadata({key: value})
        
        # 编码水印
        encoded_data = self.codec.encode(watermark.content)
        encoded_b64 = self.codec.to_base64(encoded_data)
        
        # 分散写入多个字段（Base64可能被截断，分散存储）
        chunk_size = 100  # 每段最大长度
        chunks = [encoded_b64[i:i+chunk_size] for i in range(0, len(encoded_b64), chunk_size)]
        
        # 写入 /SMMark 字段（StealthMark标记）
        writer.add_metadata({
            '/SMMark': encoded_b64,
            '/SMMarkChunks': str(len(chunks)),  # 分段数量
        })
        
        # 将分段写入不同的标准字段
        metadata_fields = ['/Author', '/Title', '/Subject', '/Creator', '/Producer']
        for i, chunk in enumerate(chunks[:len(metadata_fields)]):
            field_name = metadata_fields[i]
            # 在字段值前添加标记
            writer.add_metadata({field_name: f"[SM{i+1}]{chunk}"})
        
        # 保存
        with open(output_path, 'wb') as f:
            writer.write(f)
        
        return self._create_success_result(output_path)
    
    def _embed_lsb(self, file_path: str, watermark: WatermarkData,
                   output_path: str) -> EmbedResult:
        """
        使用LSB隐写嵌入水印
        （需要PDF中有嵌入图片）
        """
        # 简化实现：实际上LSB需要处理图片流
        # 这里降级为元数据方案
        self.logger.warning("LSB embed not fully implemented, falling back to metadata")
        return self._embed_metadata(file_path, watermark, output_path)
    
    def extract(self, file_path: str, **kwargs) -> ExtractResult:
        """从PDF提取水印"""
        
        error_result = self._validate_file(file_path)
        if error_result:
            return ExtractResult(
                status=error_result.status,
                message=error_result.message,
                file_path=file_path
            )
        
        try:
            reader = PdfReader(file_path)
            
            if not reader.metadata:
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message="PDF没有元数据",
                    file_path=file_path
                )
            
            metadata = reader.metadata
            
            # 尝试从 /SMMark 字段提取
            smmark = metadata.get('/SMMark', '')
            
            if smmark:
                # 解码
                encoded_data = self.codec.from_base64(smmark)
                success, content, details = self.codec.decode(encoded_data)
                
                if success:
                    return ExtractResult(
                        status=WatermarkStatus.SUCCESS,
                        message="水印提取成功",
                        file_path=file_path,
                        watermark=WatermarkData(content=content)
                    )
            
            return ExtractResult(
                status=WatermarkStatus.EXTRACTION_FAILED,
                message="未找到水印",
                file_path=file_path
            )
            
        except Exception as e:
            self.logger.error(f"PDF extract failed: {e}")
            return ExtractResult(
                status=WatermarkStatus.EXTRACTION_FAILED,
                message=f"提取失败: {str(e)}",
                file_path=file_path
            )
    
    def verify(self, file_path: str, original_watermark: WatermarkData,
               **kwargs) -> VerifyResult:
        """验证PDF水印"""
        
        extract_result = self.extract(file_path)
        
        if not extract_result.is_success or not extract_result.watermark:
            return VerifyResult(
                status=extract_result.status,
                is_valid=False,
                is_integrity_ok=False,
                match_score=0.0,
                message=f"提取失败: {extract_result.message}"
            )
        
        extracted = extract_result.watermark.content
        original = original_watermark.content
        
        is_match = extracted == original
        match_score = 1.0 if is_match else 0.0
        
        return VerifyResult(
            status=WatermarkStatus.SUCCESS if is_match else WatermarkStatus.VERIFICATION_FAILED,
            is_valid=is_match,
            is_integrity_ok=extract_result.is_success if hasattr(extract_result, 'is_success') else True,
            match_score=match_score,
            message="验证通过" if is_match else "水印不匹配"
        )
```

### 3.2 docx_watermark.py

```python
# document/docx_watermark.py

import os
import zipfile
import xml.etree.ElementTree as ET
from typing import Optional, Dict, Any
from pathlib import Path
import logging

try:
    import docx
except ImportError:
    docx = None

from ..core.base import (
    BaseHandler, WatermarkData, WatermarkStatus,
    EmbedResult, ExtractResult, VerifyResult
)
from ..core.codec import WatermarkCodec


# Unicode零宽字符映射
ZWSP = '\u200b'      # 零宽空格 (Zero Width Space) = 0
ZWNJ = '\u200c'      # 零宽非连接符 (Zero Width Non-Joiner) = 1
ZWJ = '\u200d'       # 零宽连接符 (Zero Width Joiner) = 1


class DOCXHandler(BaseHandler):
    """Word文档水印处理器"""
    
    SUPPORTED_EXTENSIONS = ('.docx',)
    HANDLER_NAME = "docx"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.codec = WatermarkCodec(password=self.config.get('password'))
    
    def _text_to_zwc(self, text: str) -> str:
        """
        将文本转换为零宽字符序列
        
        Args:
            text: 原始文本
            
        Returns:
            零宽字符序列
        """
        # UTF-8编码
        bytes_data = text.encode('utf-8')
        
        # 每 bit 转换为零宽字符
        zwc_text = []
        for byte in bytes_data:
            for i in range(7, -1, -1):  # 从高位到低位
                bit = (byte >> i) & 1
                zwc_text.append(ZWSP if bit == 0 else ZWNJ)
        
        return ''.join(zwc_text)
    
    def _zwc_to_text(self, zwc_seq: str) -> Optional[str]:
        """
        将零宽字符序列还原为文本
        
        Args:
            zwc_seq: 零宽字符序列
            
        Returns:
            还原后的文本，失败返回None
        """
        try:
            # 提取零宽字符
            bits = []
            for char in zwc_seq:
                if char in (ZWSP, ZWNJ, ZWJ):
                    bits.append('1' if char != ZWSP else '0')
            
            # 按8位分组
            bytes_data = []
            for i in range(0, len(bits), 8):
                byte_bits = bits[i:i+8]
                if len(byte_bits) < 8:
                    break
                byte = int(''.join(byte_bits), 2)
                bytes_data.append(byte)
            
            # 解码
            return bytes(bytes_data).decode('utf-8')
            
        except Exception as e:
            self.logger.error(f"ZWC decode failed: {e}")
            return None
    
    def embed(self, file_path: str, watermark: WatermarkData,
              output_path: str, **kwargs) -> EmbedResult:
        """嵌入水印到Word文档"""
        
        error_result = self._validate_file(file_path)
        if error_result:
            return error_result
        
        try:
            # 打开文档
            doc = docx.Document(file_path)
            
            # 获取body元素
            body = doc._body._body
            
            # 添加水印段落（在文档末尾）
            # 使用特殊样式使水印段落看起来不明显
            p = body.makeelement('w:p', {})
            
            # 创建包含零宽字符的run
            zwc_seq = self._text_to_zwc(watermark.content)
            
            # 添加水印文本（零宽字符 + 普通分隔符 + 零宽字符）
            # 在文档末尾添加一个隐藏的段落
            run = doc.add_run(zwc_seq)
            run._element.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rsidR', '')
            
            # 设置字体为极小字号（近似隐藏）
            rPr = run._element.makeelement('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rPr', {})
            sz = rPr.makeelement('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sz', {})
            sz.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', '1')  # 1半点 = 0.5pt
            rPr.append(sz)
            
            # 也可以添加一个带有零宽字符的文本框（更隐蔽）
            # 这里简化处理，直接用段落
            
            # 保存
            doc.save(output_path)
            
            return self._create_success_result(output_path)
            
        except Exception as e:
            self.logger.error(f"DOCX embed failed: {e}")
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message=f"嵌入失败: {str(e)}",
                file_path=file_path
            )
    
    def extract(self, file_path: str, **kwargs) -> ExtractResult:
        """从Word文档提取水印"""
        
        error_result = self._validate_file(file_path)
        if error_result:
            return ExtractResult(
                status=error_result.status,
                message=error_result.message,
                file_path=file_path
            )
        
        try:
            # docx本质是zip，直接解析XML
            with zipfile.ZipFile(file_path, 'r') as zf:
                # 读取document.xml
                with zf.open('word/document.xml') as f:
                    content = f.read().decode('utf-8')
            
            # 提取所有文本（包括零宽字符）
            # 简单解析：查找所有w:t元素
            root = ET.fromstring(content)
            
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            
            # 收集所有文本
            all_text = []
            for t_elem in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
                if t_elem.text:
                    all_text.append(t_elem.text)
            
            full_text = ''.join(all_text)
            
            # 提取零宽字符
            zwc_chars = []
            for char in full_text:
                if char in (ZWSP, ZWNJ, ZWJ):
                    zwc_chars.append(char)
            
            zwc_seq = ''.join(zwc_chars)
            
            if not zwc_seq:
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message="未找到水印",
                    file_path=file_path
                )
            
            # 解码
            text = self._zwc_to_text(zwc_seq)
            
            if text:
                return ExtractResult(
                    status=WatermarkStatus.SUCCESS,
                    message="水印提取成功",
                    file_path=file_path,
                    watermark=WatermarkData(content=text)
                )
            else:
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message="水印解码失败",
                    file_path=file_path
                )
                
        except Exception as e:
            self.logger.error(f"DOCX extract failed: {e}")
            return ExtractResult(
                status=WatermarkStatus.EXTRACTION_FAILED,
                message=f"提取失败: {str(e)}",
                file_path=file_path
            )
    
    def verify(self, file_path: str, original_watermark: WatermarkData,
               **kwargs) -> VerifyResult:
        """验证Word文档水印"""
        
        extract_result = self.extract(file_path)
        
        if not extract_result.is_success or not extract_result.watermark:
            return VerifyResult(
                status=extract_result.status,
                is_valid=False,
                is_integrity_ok=False,
                match_score=0.0,
                message=f"提取失败: {extract_result.message}"
            )
        
        extracted = extract_result.watermark.content
        original = original_watermark.content
        
        is_match = extracted == original
        match_score = 1.0 if is_match else 0.0
        
        return VerifyResult(
            status=WatermarkStatus.SUCCESS if is_match else WatermarkStatus.VERIFICATION_FAILED,
            is_valid=is_match,
            is_integrity_ok=True,
            match_score=match_score,
            message="验证通过" if is_match else "水印不匹配"
        )
```

---

## 4. 图片水印模块 (image/)

### 4.0 Handler 概览

| Handler | 文件 | 嵌入方案 | 扩展名 |
|---------|------|---------|--------|
| PNGHandler | image_watermark.py | LSB隐写（RGB三通道） | .png |
| BMPHandler | image_watermark.py | LSB隐写（RGB三通道） | .bmp |
| JPEGHandler | image_watermark.py | DCT域水印（量化系数） | .jpg, .jpeg |
| TIFFHandler | tiff_webp_gif_watermark.py | LSB隐写 | .tiff, .tif |
| WebPHandler | tiff_webp_gif_watermark.py | LSB隐写（无损） | .webp |
| GIFHandler | tiff_webp_gif_watermark.py | Comment Extension块 | .gif |
| HEICHandler | heic_handler.py | EXIF UserComment | .heic |

### 4.1 image_watermark.py (通用LSB)

```python
# image/image_watermark.py

import os
from typing import Optional, Dict, Any
from pathlib import Path
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


class ImageLSBHandler(BaseHandler):
    """
    图片LSB隐写处理器基类
    PNG、BMP等无损格式使用此处理器
    """
    
    HANDLER_NAME = "image_lsb"
    
    # LSB参数
    BITS_PER_CHANNEL = 1  # 每通道使用的位数
    HEADER_SIZE = 32       # 文件头大小（bits）
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.codec = WatermarkCodec(password=self.config.get('password'))
    
    def _embed_bits(self, image: 'Image.Image', bits: list) -> 'Image.Image':
        """
        将比特序列嵌入到图像LSB
        
        Args:
            image: PIL Image对象
            bits: 比特列表 [0, 1, 0, 1, ...]
            
        Returns:
            修改后的Image对象
        """
        # 转换为numpy数组
        img_array = np.array(image)
        
        # 记录原始形状
        original_shape = img_array.shape
        
        # 展平
        flat = img_array.flatten()
        
        # 嵌入
        bit_idx = 0
        for i in range(len(flat)):
            if bit_idx >= len(bits):
                break
            
            # 修改最低位
            if bits[bit_idx] == 1:
                flat[i] = flat[i] | 1  # 置1
            else:
                flat[i] = flat[i] & 0xFE  # 置0
            
            bit_idx += 1
        
        # 恢复形状
        embedded = flat.reshape(original_shape)
        
        return Image.fromarray(embedded.astype(np.uint8))
    
    def _extract_bits(self, image: 'Image.Image', num_bits: int) -> list:
        """
        从图像LSB提取比特序列
        
        Args:
            image: PIL Image对象
            num_bits: 要提取的比特数
            
        Returns:
            比特列表
        """
        img_array = np.array(image)
        flat = img_array.flatten()
        
        bits = []
        for i in range(min(num_bits, len(flat))):
            bits.append(flat[i] & 1)
        
        return bits
    
    def _calculate_capacity(self, image: 'Image.Image') -> int:
        """计算图像可嵌入的最大比特数"""
        img_array = np.array(image)
        return img_array.size  # 总像素数 × 通道数
    
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
    """PNG图片水印处理器"""
    
    SUPPORTED_EXTENSIONS = ('.png',)
    HANDLER_NAME = "png"
    
    def embed(self, file_path: str, watermark: WatermarkData,
              output_path: str, **kwargs) -> EmbedResult:
        
        error_result = self._validate_file(file_path)
        if error_result:
            return error_result
        
        try:
            # 打开图片
            image = Image.open(file_path)
            
            # 编码水印
            encoded_data = self.codec.encode(watermark.content)
            
            # 添加长度前缀（4字节 = 32bits）
            length_bits = self._bytes_to_bits(len(encoded_data).to_bytes(4, 'big'))
            data_bits = self._bytes_to_bits(encoded_data)
            
            all_bits = length_bits + data_bits
            
            # 检查容量
            capacity = self._calculate_capacity(image)
            if len(all_bits) > capacity:
                return EmbedResult(
                    status=WatermarkStatus.FAILED,
                    message=f"图片容量不足，需要{len(all_bits)}bits，只能提供{capacity}bits",
                    file_path=file_path
                )
            
            # 嵌入
            embedded_image = self._embed_bits(image, all_bits)
            
            # 保存（无损格式）
            embedded_image.save(output_path, format='PNG')
            
            return self._create_success_result(output_path)
            
        except Exception as e:
            self.logger.error(f"PNG embed failed: {e}")
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message=f"嵌入失败: {str(e)}",
                file_path=file_path
            )
    
    def extract(self, file_path: str, **kwargs) -> ExtractResult:
        
        error_result = self._validate_file(file_path)
        if error_result:
            return ExtractResult(
                status=error_result.status,
                message=error_result.message,
                file_path=file_path
            )
        
        try:
            image = Image.open(file_path)
            
            # 提取长度（32bits = 4字节）
            length_bits = self._extract_bits(image, 32)
            length_bytes = self._bytes_to_bytes(length_bits)
            data_length = int.from_bytes(length_bytes, 'big')
            
            # 检查长度有效性
            if data_length <= 0 or data_length > 10 * 1024 * 1024:  # 最大10MB
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message="无效的水印长度",
                    file_path=file_path
                )
            
            # 提取数据
            data_bits = self._extract_bits(image, 32 + data_length * 8)
            data_bytes = self._bytes_to_bytes(data_bits[32:])  # 跳过长度字段
            
            # 解码
            success, content, details = self.codec.decode(data_bytes)
            
            if success:
                return ExtractResult(
                    status=WatermarkStatus.SUCCESS,
                    message="水印提取成功",
                    file_path=file_path,
                    watermark=WatermarkData(content=content)
                )
            else:
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message=f"解码失败: {details.get('error', '未知错误')}",
                    file_path=file_path
                )
                
        except Exception as e:
            self.logger.error(f"PNG extract failed: {e}")
            return ExtractResult(
                status=WatermarkStatus.EXTRACTION_FAILED,
                message=f"提取失败: {str(e)}",
                file_path=file_path
            )
    
    def verify(self, file_path: str, original_watermark: WatermarkData,
               **kwargs) -> VerifyResult:
        
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
        
        return VerifyResult(
            status=WatermarkStatus.SUCCESS if is_match else WatermarkStatus.VERIFICATION_FAILED,
            is_valid=is_match,
            is_integrity_ok=True,
            match_score=1.0 if is_match else 0.0
        )


class BMPHandler(PNGHandler):
    """BMP图片水印处理器（复用PNG的LSB实现）"""
    
    SUPPORTED_EXTENSIONS = ('.bmp',)
    HANDLER_NAME = "bmp"
    
    def embed(self, file_path: str, watermark: WatermarkData,
              output_path: str, **kwargs) -> EmbedResult:
        
        result = super().embed(file_path, watermark, output_path, **kwargs)
        
        # BMP保存需要特殊处理
        if result.is_success:
            try:
                image = Image.open(output_path)
                image.save(output_path, format='BMP')
            except:
                pass
        
        return result


class JPEGHandler(BaseHandler):
    """JPEG图片水印处理器 - DCT域"""
    
    SUPPORTED_EXTENSIONS = ('.jpg', '.jpeg')
    HANDLER_NAME = "jpeg"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.codec = WatermarkCodec(password=self.config.get('password'))
        self.quality = self.config.get('quality', 95)
    
    def embed(self, file_path: str, watermark: WatermarkData,
              output_path: str, **kwargs) -> EmbedResult:
        
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
            
            # 简化的DCT水印实现
            # 将水印数据转换为二进制
            data_bits = []
            for byte in encoded_data:
                for i in range(7, -1, -1):
                    data_bits.append((byte >> i) & 1)
            
            # 添加同步头（特定比特序列）
            sync_header = [1, 0, 1, 0, 1, 0, 1, 0]  # 10101010
            data_bits = sync_header + data_bits
            
            # 转换到YUV空间
            img_yuv = cv2.cvtColor(img, cv2.COLOR_BGR2YUV)
            
            # 对Y通道进行8x8分块DCT
            height, width = img_yuv.shape[:2]
            bit_idx = 0
            
            for h in range(0, height - 7, 8):
                for w in range(0, width - 7, 8):
                    if bit_idx >= len(data_bits):
                        break
                    
                    # 提取8x8块
                    block = img_yuv[h:h+8, w:w+8, 0].astype(float)
                    
                    # 简单的DCT近似（使用均值替代）
                    dct_mean = block.mean()
                    
                    # 修改均值来编码比特
                    if data_bits[bit_idx] == 1:
                        if dct_mean < 128:
                            block = block + 1
                    else:
                        if dct_mean >= 128:
                            block = block - 1
                    
                    # 写回
                    img_yuv[h:h+8, w:w+8, 0] = block.clip(0, 255)
                    
                    bit_idx += 1
            
            # 转换回BGR
            img_result = cv2.cvtColor(img_yuv, cv2.COLOR_YUV2BGR)
            
            # 保存
            cv2.imwrite(output_path, img_result, [cv2.IMWRITE_JPEG_QUALITY, self.quality])
            
            return self._create_success_result(output_path)
            
        except Exception as e:
            self.logger.error(f"JPEG embed failed: {e}")
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message=f"嵌入失败: {str(e)}",
                file_path=file_path
            )
    
    def extract(self, file_path: str, **kwargs) -> ExtractResult:
        
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
            
            # 转换到YUV
            img_yuv = cv2.cvtColor(img, cv2.COLOR_BGR2YUV)
            
            # 提取比特
            # 这里简化实现，实际需要更复杂的DCT分析
            bits = []
            height, width = img_yuv.shape[:2]
            
            for h in range(0, height - 7, 8):
                for w in range(0, width - 7, 8):
                    block = img_yuv[h:h+8, w:w+8, 0].astype(float)
                    dct_mean = block.mean()
                    
                    # 提取（简化判断）
                    bit = 1 if dct_mean >= 128 else 0
                    bits.append(bit)
            
            # 查找同步头
            sync = [1, 0, 1, 0, 1, 0, 1, 0]
            sync_idx = -1
            for i in range(len(bits) - 8):
                if bits[i:i+8] == sync:
                    sync_idx = i + 8
                    break
            
            if sync_idx == -1:
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message="未找到同步头",
                    file_path=file_path
                )
            
            # 提取长度（32bits）
            length_bits = bits[sync_idx:sync_idx+32]
            length_bytes = bytearray()
            for i in range(0, 32, 8):
                byte = 0
                for j in range(8):
                    byte |= (length_bits[i+j] << (7-j))
                length_bytes.append(byte)
            
            data_length = int.from_bytes(bytes(length_bytes), 'big')
            
            if data_length <= 0 or data_length > 10 * 1024 * 1024:
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message="无效长度",
                    file_path=file_path
                )
            
            # 提取数据
            data_start = sync_idx + 32
            data_end = data_start + data_length * 8
            data_bits = bits[data_start:data_end]
            
            # 转换为字节
            data_bytes = bytearray()
            for i in range(0, len(data_bits), 8):
                if i + 8 > len(data_bits):
                    break
                byte = 0
                for j in range(8):
                    byte |= (data_bits[i+j] << (7-j))
                data_bytes.append(byte)
            
            # 解码
            success, content, details = self.codec.decode(bytes(data_bytes))
            
            if success:
                return ExtractResult(
                    status=WatermarkStatus.SUCCESS,
                    message="水印提取成功",
                    file_path=file_path,
                    watermark=WatermarkData(content=content)
                )
            else:
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message="解码失败",
                    file_path=file_path
                )
                
        except Exception as e:
            self.logger.error(f"JPEG extract failed: {e}")
            return ExtractResult(
                status=WatermarkStatus.EXTRACTION_FAILED,
                message=f"提取失败: {str(e)}",
                file_path=file_path
            )
    
    def verify(self, file_path: str, original_watermark: WatermarkData,
               **kwargs) -> VerifyResult:
        
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
        
        return VerifyResult(
            status=WatermarkStatus.SUCCESS if is_match else WatermarkStatus.VERIFICATION_FAILED,
            is_valid=is_match,
            is_integrity_ok=True,
            match_score=1.0 if is_match else 0.0
        )
```

---

## 5. 音视频水印模块 (media/)

### 5.0 Handler 概览

| Handler | 文件 | 嵌入方案 | 扩展名 |
|---------|------|---------|--------|
| WAVHandler | audio_watermark.py | 扩频水印（LCG PN序列，α=0.005） | .wav |
| MP3Handler | audio_watermark.py | 扩频水印（继承WAV） | .mp3 |
| FLACHandler | flac_handler.py | 扩频水印（继承WAV） | .flac |
| AACHandler | aac_handler.py | 扩频水印（继承WAV） | .aac, .m4a |
| VideoHandler | video_watermark.py | RGB Blue通道LSB + libx264rgb CRF0 | .mp4, .avi, .mkv, .mov |
| WebMHandler | webm_handler.py | RGB Blue通道LSB + VP9无损 | .webm |
| WMVHandler | wmv_handler.py | RGB Blue通道LSB + FFV1备选 | .wmv |

### 5.1 audio_watermark.py

```python
# media/audio_watermark.py

import os
import numpy as np
from typing import Optional, Dict, Any
from pathlib import Path
import logging

try:
    import librosa
    import scipy.signal
except ImportError:
    librosa = None
    scipy = None

from ..core.base import (
    BaseHandler, WatermarkData, WatermarkStatus,
    EmbedResult, ExtractResult, VerifyResult
)
from ..core.codec import WatermarkCodec


class AudioSpreadSpectrumHandler(BaseHandler):
    """
    音频扩频水印处理器
    使用直接序列扩频（DSSS）将水印嵌入音频信号
    """
    
    HANDLER_NAME = "audio_ss"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.codec = WatermarkCodec(password=self.config.get('password'))
        
        # 扩频参数
        self.pn_sequence = None  # 伪随机序列
        self.spread_factor = config.get('spread_factor', 31)  # 扩频因子
        self.alpha = config.get('alpha', 0.005)  # 嵌入强度
        
        # 生成PN序列
        self._generate_pn_sequence(1024)
    
    def _generate_pn_sequence(self, length: int) -> np.ndarray:
        """生成伪随机噪声序列"""
        # 使用线性同余生成器
        seed = self.config.get('pn_seed', 12345)
        sequence = []
        a, c, m = 1103515245, 12345, 2**31
        
        x = seed
        for _ in range(length):
            x = (a * x + c) % m
            sequence.append(1 if (x % 2) else -1)
        
        self.pn_sequence = np.array(sequence)
        return self.pn_sequence
    
    def _generate_pn(self, length: int) -> np.ndarray:
        """生成指定长度的PN序列（循环使用基础序列）"""
        if self.pn_sequence is None:
            self._generate_pn_sequence(1024)
        
        repeats = (length // len(self.pn_sequence)) + 1
        return np.tile(self.pn_sequence, repeats)[:length]
    
    def _embed_bit(self, signal: np.ndarray, bit: int, pn: np.ndarray) -> np.ndarray:
        """嵌入单个比特"""
        if bit == 1:
            bit_signal = 1.0
        else:
            bit_signal = -1.0
        
        # 扩频
        spread_signal = bit_signal * pn[:len(signal)]
        
        # 叠加到原始信号
        embedded = signal + self.alpha * spread_signal
        
        return embedded
    
    def _extract_bit(self, signal: np.ndarray, pn: np.ndarray) -> int:
        """提取单个比特（相关检测）"""
        # 计算相关性
        correlation = np.correlate(signal, pn[:len(signal)], mode='valid')
        
        if len(correlation) == 0:
            return 0
        
        mean_corr = np.mean(correlation)
        
        # 判断
        return 1 if mean_corr > 0 else 0


class WAVHandler(AudioSpreadSpectrumHandler):
    """WAV音频水印处理器"""
    
    SUPPORTED_EXTENSIONS = ('.wav',)
    HANDLER_NAME = "wav"
    
    def embed(self, file_path: str, watermark: WatermarkData,
              output_path: str, **kwargs) -> EmbedResult:
        
        error_result = self._validate_file(file_path)
        if error_result:
            return error_result
        
        if librosa is None:
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message="需要安装librosa库",
                file_path=file_path
            )
        
        try:
            # 读取音频
            signal, sr = librosa.load(file_path, sr=None, mono=False)
            
            # 转单声道
            if len(signal.shape) > 1:
                signal = np.mean(signal, axis=0)
            
            # 编码水印
            encoded_data = self.codec.encode(watermark.content)
            
            # 转换为比特
            bits = []
            for byte in encoded_data:
                for i in range(7, -1, -1):
                    bits.append((byte >> i) & 1)
            
            # 嵌入
            # 每比特分配的样本数
            bits_per_sample = max(1, len(signal) // (len(bits) + 100))  # 留一些余量
            
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
            
            return self._create_success_result(output_path)
            
        except Exception as e:
            self.logger.error(f"WAV embed failed: {e}")
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message=f"嵌入失败: {str(e)}",
                file_path=file_path
            )
    
    def extract(self, file_path: str, **kwargs) -> ExtractResult:
        
        error_result = self._validate_file(file_path)
        if error_result:
            return ExtractResult(
                status=error_result.status,
                message=error_result.message,
                file_path=file_path
            )
        
        if librosa is None:
            return ExtractResult(
                status=WatermarkStatus.FAILED,
                message="需要安装librosa库",
                file_path=file_path
            )
        
        try:
            signal, sr = librosa.load(file_path, sr=None, mono=False)
            
            if len(signal.shape) > 1:
                signal = np.mean(signal, axis=0)
            
            # 估计比特数（基于信号长度，假设每比特bits_per_sample）
            bits_per_sample = kwargs.get('bits_per_sample', 
                                         self.config.get('bits_per_sample', 1000))
            
            # 提取最大约10MB数据的水印
            max_bits = min(10 * 1024 * 1024 * 8, len(signal) // bits_per_sample)
            
            # 先提取长度字段（4字节 = 32bits）
            length_bits = []
            for i in range(32):
                start = i * bits_per_sample
                end = start + bits_per_sample
                
                if start >= len(signal):
                    break
                
                pn = self._generate_pn(bits_per_sample)
                bit = self._extract_bit(signal[start:end], pn)
                length_bits.append(bit)
            
            # 转换长度
            length_bytes = bytearray()
            for i in range(0, 32, 8):
                byte = 0
                for j in range(8):
                    byte |= (length_bits[i+j] << (7-j))
                length_bytes.append(byte)
            
            data_length = int.from_bytes(bytes(length_bytes), 'big')
            
            if data_length <= 0 or data_length > 10 * 1024 * 1024:
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message="无效的水印长度",
                    file_path=file_path
                )
            
            # 提取数据
            data_bits = []
            total_bits = 32 + data_length * 8
            
            for i in range(32, total_bits):
                start = i * bits_per_sample
                end = start + bits_per_sample
                
                if start >= len(signal):
                    break
                
                pn = self._generate_pn(bits_per_sample)
                bit = self._extract_bit(signal[start:end], pn)
                data_bits.append(bit)
            
            # 转换为字节
            data_bytes = bytearray()
            for i in range(0, len(data_bits), 8):
                if i + 8 > len(data_bits):
                    break
                byte = 0
                for j in range(8):
                    byte |= (data_bits[i+j] << (7-j))
                data_bytes.append(byte)
            
            # 解码
            success, content, details = self.codec.decode(bytes(data_bytes))
            
            if success:
                return ExtractResult(
                    status=WatermarkStatus.SUCCESS,
                    message="水印提取成功",
                    file_path=file_path,
                    watermark=WatermarkData(content=content)
                )
            else:
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message=f"解码失败: {details.get('error', '未知')}",
                    file_path=file_path
                )
                
        except Exception as e:
            self.logger.error(f"WAV extract failed: {e}")
            return ExtractResult(
                status=WatermarkStatus.EXTRACTION_FAILED,
                message=f"提取失败: {str(e)}",
                file_path=file_path
            )
    
    def verify(self, file_path: str, original_watermark: WatermarkData,
               **kwargs) -> VerifyResult:
        
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
        
        return VerifyResult(
            status=WatermarkStatus.SUCCESS if is_match else WatermarkStatus.VERIFICATION_FAILED,
            is_valid=is_match,
            is_integrity_ok=True,
            match_score=1.0 if is_match else 0.0
        )


class MP3Handler(WAVHandler):
    """MP3音频水印处理器（复用WAV实现，处理前先转WAV）"""
    
    SUPPORTED_EXTENSIONS = ('.mp3',)
    HANDLER_NAME = "mp3"
```

### 5.2 video_watermark.py

```python
# media/video_watermark.py

import os
import numpy as np
import logging
from typing import Optional, Dict, Any
from pathlib import Path

try:
    import cv2
except ImportError:
    cv2 = None

from ..core.base import (
    BaseHandler, WatermarkData, WatermarkStatus,
    EmbedResult, ExtractResult, VerifyResult
)
from ..core.codec import WatermarkCodec


class VideoHandler(BaseHandler):
    """
    视频水印处理器
    使用DCT域方法在I帧中嵌入水印
    """
    
    SUPPORTED_EXTENSIONS = ('.mp4', '.avi', '.mkv', '.mov')
    HANDLER_NAME = "video"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.codec = WatermarkCodec(password=self.config.get('password'))
        self.frame_interval = self.config.get('frame_interval', 30)  # 每隔多少帧处理一次
        self.alpha = self.config.get('alpha', 0.1)  # 嵌入强度
    
    def _dct_embed_bit(self, block: np.ndarray, bit: int) -> np.ndarray:
        """
        在8x8块中嵌入比特（DCT域）
        
        Args:
            block: 8x8像素块
            bit: 要嵌入的比特 (0 或 1)
            
        Returns:
            修改后的块
        """
        # DCT变换
        dct_block = cv2.dct(block.astype(float))
        
        # 在中频系数嵌入（选择 (2,3) 或 (3,2) 位置）
        # 这些位置对压缩相对鲁棒
        if bit == 1:
            if dct_block[2, 3] < 0:
                dct_block[2, 3] = abs(dct_block[2, 3])
            dct_block[2, 3] = max(dct_block[2, 3], self.alpha)
        else:
            if dct_block[2, 3] > 0:
                dct_block[2, 3] = -abs(dct_block[2, 3])
            dct_block[2, 3] = min(dct_block[2, 3], -self.alpha)
        
        # 逆DCT
        embedded = cv2.idct(dct_block)
        
        return embedded
    
    def _dct_extract_bit(self, block: np.ndarray) -> int:
        """从8x8块提取比特"""
        dct_block = cv2.dct(block.astype(float))
        
        # 从中频系数提取
        coef = dct_block[2, 3]
        
        return 1 if coef > 0 else 0
    
    def embed(self, file_path: str, watermark: WatermarkData,
              output_path: str, **kwargs) -> EmbedResult:
        
        error_result = self._validate_file(file_path)
        if error_result:
            return error_result
        
        if cv2 is None:
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message="需要安装opencv-python",
                file_path=file_path
            )
        
        try:
            # 打开视频
            cap = cv2.VideoCapture(file_path)
            
            # 获取视频信息
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # 创建输出视频
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            # 编码水印
            encoded_data = self.codec.encode(watermark.content)
            
            # 转换为比特
            bits = []
            for byte in encoded_data:
                for i in range(7, -1, -1):
                    bits.append((byte >> i) & 1)
            
            # 添加同步头
            sync = [1, 0, 1, 0, 1, 0, 1, 0]
            bits = sync + bits
            
            bit_idx = 0
            frame_idx = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 只处理关键帧或间隔帧
                if frame_idx % self.frame_interval == 0 and bit_idx < len(bits):
                    # 转灰度
                    if len(frame.shape) == 3:
                        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    else:
                        gray = frame
                    
                    # 8x8分块处理
                    h, w = gray.shape
                    for y in range(0, h - 7, 8):
                        for x in range(0, w - 7, 8):
                            if bit_idx >= len(bits):
                                break
                            
                            block = gray[y:y+8, x:x+8]
                            embedded_block = self._dct_embed_bit(block, bits[bit_idx])
                            gray[y:y+8, x:x+8] = embedded_block
                            
                            bit_idx += 1
                    
                    # 转回BGR
                    frame = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
                
                out.write(frame)
                frame_idx += 1
            
            cap.release()
            out.release()
            
            return self._create_success_result(output_path)
            
        except Exception as e:
            self.logger.error(f"Video embed failed: {e}")
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message=f"嵌入失败: {str(e)}",
                file_path=file_path
            )
    
    def extract(self, file_path: str, **kwargs) -> ExtractResult:
        
        error_result = self._validate_file(file_path)
        if error_result:
            return ExtractResult(
                status=error_result.status,
                message=error_result.message,
                file_path=file_path
            )
        
        if cv2 is None:
            return ExtractResult(
                status=WatermarkStatus.FAILED,
                message="需要安装opencv-python",
                file_path=file_path
            )
        
        try:
            cap = cv2.VideoCapture(file_path)
            
            bits = []
            frame_idx = 0
            sync_found = False
            sync = [1, 0, 1, 0, 1, 0, 1, 0]
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                if frame_idx % self.frame_interval == 0:
                    if len(frame.shape) == 3:
                        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    else:
                        gray = frame
                    
                    h, w = gray.shape
                    for y in range(0, h - 7, 8):
                        for x in range(0, w - 7, 8):
                            block = gray[y:y+8, x:x+8]
                            bit = self._dct_extract_bit(block)
                            bits.append(bit)
                
                frame_idx += 1
            
            cap.release()
            
            # 查找同步头
            sync_idx = -1
            for i in range(len(bits) - 8):
                if bits[i:i+8] == sync:
                    sync_idx = i + 8
                    sync_found = True
                    break
            
            if not sync_found:
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message="未找到同步头",
                    file_path=file_path
                )
            
            # 提取长度（32bits）
            length_bits = bits[sync_idx:sync_idx+32]
            length_bytes = bytearray()
            for i in range(0, 32, 8):
                byte = 0
                for j in range(8):
                    byte |= (length_bits[i+j] << (7-j))
                length_bytes.append(byte)
            
            data_length = int.from_bytes(bytes(length_bytes), 'big')
            
            if data_length <= 0 or data_length > 10 * 1024 * 1024:
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message="无效长度",
                    file_path=file_path
                )
            
            # 提取数据
            data_start = sync_idx + 32
            data_end = data_start + data_length * 8
            data_bits = bits[data_start:data_end]
            
            # 转换为字节
            data_bytes = bytearray()
            for i in range(0, len(data_bits), 8):
                if i + 8 > len(data_bits):
                    break
                byte = 0
                for j in range(8):
                    byte |= (data_bits[i+j] << (7-j))
                data_bytes.append(byte)
            
            # 解码
            success, content, details = self.codec.decode(bytes(data_bytes))
            
            if success:
                return ExtractResult(
                    status=WatermarkStatus.SUCCESS,
                    message="水印提取成功",
                    file_path=file_path,
                    watermark=WatermarkData(content=content)
                )
            else:
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message="解码失败",
                    file_path=file_path
                )
                
        except Exception as e:
            self.logger.error(f"Video extract failed: {e}")
            return ExtractResult(
                status=WatermarkStatus.EXTRACTION_FAILED,
                message=f"提取失败: {str(e)}",
                file_path=file_path
            )
    
    def verify(self, file_path: str, original_watermark: WatermarkData,
               **kwargs) -> VerifyResult:
        
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
        
        return VerifyResult(
            status=WatermarkStatus.SUCCESS if is_match else WatermarkStatus.VERIFICATION_FAILED,
            is_valid=is_match,
            is_integrity_ok=True,
            match_score=1.0 if is_match else 0.0
        )
```

---

## 6. 命令行接口 (cli.py)

```python
# cli.py

import argparse
import sys
import logging
from pathlib import Path

from src.core.manager import StealthMark
from src.core.base import WatermarkStatus


def setup_logging(verbose: bool = False):
    """配置日志"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def cmd_embed(args):
    """嵌入水印命令"""
    wm = StealthMark(password=args.password)
    
    result = wm.embed(
        file_path=args.input,
        watermark=args.watermark,
        output_path=args.output
    )
    
    if result.is_success:
        print(f"✓ 水印嵌入成功: {result.output_path}")
        return 0
    else:
        print(f"✗ 嵌入失败: {result.message}", file=sys.stderr)
        return 1


def cmd_extract(args):
    """提取水印命令"""
    wm = StealthMark(password=args.password)
    
    result = wm.extract(file_path=args.file)
    
    if result.is_success:
        print(f"水印内容: {result.watermark.content}")
        return 0
    else:
        print(f"✗ 提取失败: {result.message}", file=sys.stderr)
        return 1


def cmd_verify(args):
    """验证水印命令"""
    wm = StealthMark(password=args.password)
    
    result = wm.verify(
        file_path=args.file,
        original_watermark=args.watermark
    )
    
    if result.is_valid:
        print(f"✓ 验证通过")
        print(f"  一致性: {result.match_score * 100:.1f}%")
        return 0
    else:
        print(f"✗ 验证失败")
        print(f"  原因: {result.message}")
        return 1


def cmd_info(args):
    """显示支持格式"""
    wm = StealthMark()
    formats = wm.supported_formats()
    
    print("支持的格式:")
    for fmt in formats:
        print(f"  - {fmt}")


def main():
    parser = argparse.ArgumentParser(
        description='StealthMark - 隐式水印工具',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='显示详细日志')
    parser.add_argument('-p', '--password', type=str, default=None,
                        help='水印加密密码')
    
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # embed 命令
    embed_parser = subparsers.add_parser('embed', help='嵌入水印')
    embed_parser.add_argument('input', help='输入文件路径')
    embed_parser.add_argument('watermark', help='水印文本')
    embed_parser.add_argument('-o', '--output', help='输出文件路径（默认覆盖原文件）')
    embed_parser.set_defaults(func=cmd_embed)
    
    # extract 命令
    extract_parser = subparsers.add_parser('extract', help='提取水印')
    extract_parser.add_argument('file', help='含水印文件路径')
    extract_parser.set_defaults(func=cmd_extract)
    
    # verify 命令
    verify_parser = subparsers.add_parser('verify', help='验证水印')
    verify_parser.add_argument('file', help='含水印文件路径')
    verify_parser.add_argument('watermark', help='原始水印文本')
    verify_parser.set_defaults(func=cmd_verify)
    
    # info 命令
    info_parser = subparsers.add_parser('info', help='显示支持格式')
    info_parser.set_defaults(func=cmd_info)
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    if args.command is None:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
```

---

## 7. 模块初始化文件

### 7.1 __init__.py

```python
# src/__init__.py
"""
StealthMark - 隐式水印系统
"""

from .core.manager import StealthMark
from .core.base import (
    WatermarkData, WatermarkStatus,
    EmbedResult, ExtractResult, VerifyResult
)

__version__ = "0.1.0"
__all__ = [
    'StealthMark',
    'WatermarkData',
    'WatermarkStatus',
    'EmbedResult',
    'ExtractResult',
    'VerifyResult',
]
```

### 7.2 子模块 __init__.py

```python
# src/document/__init__.py
from .pdf_watermark import PDFHandler
from .docx_watermark import DOCXHandler
from .pptx_watermark import PPTXHandler

__all__ = ['PDFHandler', 'DOCXHandler', 'PPTXHandler']

# src/image/__init__.py
from .image_watermark import PNGHandler, BMPHandler, JPEGHandler

__all__ = ['PNGHandler', 'BMPHandler', 'JPEGHandler']

# src/media/__init__.py
from .audio_watermark import WAVHandler, MP3Handler
from .video_watermark import VideoHandler

__all__ = ['WAVHandler', 'MP3Handler', 'VideoHandler']
```

---

## 8. 错误处理设计

### 8.1 异常类层次

```python
# core/exceptions.py

class StealthMarkError(Exception):
    """StealthMark基础异常"""
    pass


class FileNotFoundError(StealthMarkError):
    """文件不存在"""
    pass


class UnsupportedFormatError(StealthMarkError):
    """不支持的文件格式"""
    pass


class EmbedError(StealthMarkError):
    """嵌入失败"""
    pass


class ExtractError(StealthMarkError):
    """提取失败"""
    pass


class VerifyError(StealthMarkError):
    """验证失败"""
    pass


class CodecError(StealthMarkError):
    """编解码失败"""
    pass


class EncryptionError(StealthMarkError):
    """加密失败"""
    pass
```

### 8.2 错误码定义

| 错误码 | 枚举值 | 说明 |
|--------|--------|------|
| 0 | SUCCESS | 成功 |
| 1 | FAILED | 通用失败 |
| 2 | FILE_NOT_FOUND | 文件不存在 |
| 3 | FILE_CORRUPTED | 文件损坏 |
| 4 | UNSUPPORTED_FORMAT | 不支持格式 |
| 5 | INVALID_WATERMARK | 无效水印 |
| 6 | EXTRACTION_FAILED | 提取失败 |
| 7 | VERIFICATION_FAILED | 验证失败 |
| 8 | ENCRYPTION_FAILED | 加密失败 |
| 9 | DECRYPTION_FAILED | 解密失败 |

---

## 9. 日志设计

### 9.1 日志级别

| 级别 | 用途 |
|------|------|
| DEBUG | 详细的调试信息，算法中间变量 |
| INFO | 正常操作日志（嵌入/提取进度） |
| WARNING | 警告（降级处理、容量不足） |
| ERROR | 错误（操作失败） |
| CRITICAL | 严重错误（系统异常） |

### 9.2 日志格式

```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
2024-04-28 10:30:00 - stealthmark.core.manager - INFO - Embedding watermark to: test.pdf
```

### 9.3 日志输出

- 控制台（默认）
- 文件（可选，通过配置）
- 滚动日志（避免占用过多空间）

---

## 10. 配置设计

### 10.1 配置项

```python
# config/settings.py

DEFAULT_CONFIG = {
    # 通用设置
    'debug': False,
    'log_file': None,
    
    # 编解码设置
    'password': None,           # 水印加密密码
    
    # PDF设置
    'pdf_embed_method': 'metadata',  # metadata 或 lsb
    
    # 图片设置
    'jpeg_quality': 95,
    'png_compress': 6,
    
    # 音频设置
    'audio_spread_factor': 31,
    'audio_alpha': 0.005,
    
    # 视频设置
    'video_frame_interval': 30,
    'video_alpha': 0.1,
}
```

### 10.2 配置文件

支持从以下位置加载配置：
1. `stealthmark.yaml` 或 `stealthmark.json`（当前目录）
2. `~/.stealthmark/config.yaml`（用户目录）
3. 环境变量 `STEALTHMARK_CONFIG`

---

## 11. 目录结构（最终）

```
stealthmark/
├── src/
│   ├── __init__.py             # 包入口
│   ├── __main__.py             # python -m stealthmark 入口
│   ├── core/
│   │   ├── __init__.py
│   │   ├── base.py             # 基类定义（BaseHandler, WatermarkStatus, 结果数据类）
│   │   ├── codec.py            # 编解码器（AES-256加密）
│   │   ├── exceptions.py       # 异常类
│   │   └── manager.py          # 门面类（StealthMark，23个Handler注册）
│   ├── document/
│   │   ├── __init__.py
│   │   ├── pdf_watermark.py     # PDF（元数据Author字段）
│   │   ├── docx_watermark.py    # DOCX（零宽字符）
│   │   ├── pptx_watermark.py    # PPTX（hidden_形状）
│   │   ├── xlsx_watermark.py    # XLSX（customXml属性）
│   │   ├── odt_watermark.py     # ODT（ODF元数据）
│   │   ├── ods_watermark.py     # ODS（ODF元数据）
│   │   ├── odp_watermark.py     # ODP（ODF元数据）
│   │   ├── epub_watermark.py    # EPUB（OPF dc:identifier）
│   │   └── rtf_watermark.py     # RTF（可忽略控制组）
│   ├── image/
│   │   ├── __init__.py
│   │   ├── image_watermark.py   # PNG/BMP/JPEG（LSB + DCT域）
│   │   ├── tiff_webp_gif_watermark.py  # TIFF/WebP/GIF（LSB）
│   │   └── heic_handler.py      # HEIC（EXIF UserComment）
│   ├── media/
│   │   ├── __init__.py
│   │   ├── audio_watermark.py   # WAV/MP3（扩频水印）
│   │   ├── flac_handler.py      # FLAC（扩频，继承WAV）
│   │   ├── aac_handler.py       # AAC/M4A（扩频，继承WAV）
│   │   ├── video_watermark.py   # MP4/AVI/MKV/MOV（RGB Blue LSB）
│   │   ├── webm_handler.py      # WebM（RGB Blue LSB + VP9）
│   │   └── wmv_handler.py       # WMV（RGB Blue LSB）
│   └── utils/
│       ├── __init__.py
│       └── helpers.py
├── cli.py                      # CLI入口
├── config/                     # 配置文件
├── tests/
│   ├── unit/                   # 单元测试（unittest）
│   ├── scripts/                # 集成测试脚本
│   └── fixtures/               # 测试数据文件（30种格式）
├── docs/
│   ├── SRS.md                  # 需求规格说明书
│   ├── DESIGN.md               # 设计方案
│   ├── DETAILED_DESIGN.md     # 详细设计
│   └── API.md                 # API文档
├── README.md
├── requirements.txt
└── setup.py
```

---

## 12. 依赖关系图

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI / API                            │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                     StealthMark (Manager)                   │
│  - 路由分发                                              │
│  - 结果封装                                              │
└─────────────────────────────┬───────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  FormatHandler │    │    Codec      │    │   Utils       │
│  (路由)        │    │  (编解码)     │    │  (辅助)       │
└───────┬───────┘    └───────────────┘    └───────────────┘
        │
        ├─────────────────────────────────────────┐
        │                                         │
        ▼                                         ▼
┌───────────────┐                        ┌───────────────┐
│   Document    │                        │    Media      │
│   Handlers    │                        │   Handlers    │
├───────────────┤                        ├───────────────┤
│ PDFHandler    │                        │ WAVHandler    │
│ DOCXHandler   │                        │ MP3Handler    │
│ PPTXHandler   │                        │ VideoHandler  │
└───────────────┘                        └───────────────┘
        │                                         │
        ▼                                         ▼
┌───────────────┐                        ┌───────────────┐
│   第三方库    │                        │   第三方库    │
├───────────────┤                        ├───────────────┤
│ PyPDF2        │                        │ librosa       │
│ python-docx   │                        │ opencv        │
│ python-pptx   │                        │ numpy         │
│ Pillow        │                        │ scipy         │
└───────────────┘                        └───────────────┘
```

---

*文档版本: 1.0*
*最后更新: 2026-04-28*
