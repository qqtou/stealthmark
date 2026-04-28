# core/codec.py
"""
水印编解码器 - StealthMark 核心组件

本模块实现水印数据的编码、解码、加密、解密功能：
- 编码：UTF-8 → 二进制 → CRC32校验 → 格式封装
- 加密：AES-256-CBC（可选）
- 解码：格式解析 → CRC32校验 → UTF-8解码

编码格式（共14+N字节）:
┌─────────────┬────────┬──────────┬──────────┬─────────┐
│ 魔数(5B)    │ 版本(1B)│ 长度(4B) │ 内容(NB) │ CRC(4B) │
│ "SMARK"     │ 0x01   │ N        │ payload  │ crc32   │
└─────────────┴────────┴──────────┴──────────┴─────────┘

Author: StealthMark Team
Date: 2026-04-28
"""

import base64
import zlib
import os
import logging
from typing import Optional, Tuple

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

# 模块日志
logger = logging.getLogger(__name__)


# ==================== 常量定义 ====================

WATERMARK_MAGIC = b"SMARK"      # 魔数：标识水印数据
WATERMARK_VERSION = 1           # 版本号：当前版本
LENGTH_FIELD_SIZE = 4           # 长度字段大小（字节）
CRC_SIZE = 4                    # CRC32校验码大小（字节）
HEADER_SIZE = 5 + 1 + 4         # 头部大小：魔数(5) + 版本(1) + 长度(4) = 10


class WatermarkCodec:
    """
    水印编解码器
    
    负责水印数据的编码、解码、加密、解密。支持两种模式：
    1. 普通模式：仅编码（CRC32校验）
    2. 加密模式：编码 + AES-256-CBC加密
    
    使用示例:
        >>> # 普通模式
        >>> codec = WatermarkCodec()
        >>> encoded = codec.encode("版权所有")
        >>> success, content, info = codec.decode(encoded)
        
        >>> # 加密模式
        >>> codec = WatermarkCodec(password="secret123")
        >>> encoded = codec.encode_with_encryption("机密水印")
        >>> success, content, info = codec.decode_with_decryption(encoded)
    
    Attributes:
        password: 加密密码
        salt: PBKDF2盐值
        _key: 派生出的AES密钥（32字节）
    """
    
    def __init__(self, password: Optional[str] = None, salt: Optional[bytes] = None):
        """
        初始化编解码器
        
        Args:
            password: 加密密码（可选）。提供时启用加密模式。
            salt: PBKDF2盐值（可选）。默认使用内置盐值。
        
        Note:
            加密模式使用PBKDF2-HMAC-SHA256派生密钥，迭代100000次。
        """
        self.password = password
        self.salt = salt or b"StealthMark2024"  # 默认盐值
        self._key = None
        
        if password:
            self._derive_key(password)
            logger.info("WatermarkCodec initialized with encryption enabled")
        else:
            logger.info("WatermarkCodec initialized (no encryption)")
    
    def _derive_key(self, password: str) -> None:
        """
        使用PBKDF2派生加密密钥
        
        密钥派生参数：
        - 算法：HMAC-SHA256
        - 输出长度：32字节（AES-256）
        - 迭代次数：100000
        - 盐值：self.salt
        
        Args:
            password: 用户提供的密码字符串
        
        Raises:
            cryptography异常：密钥派生失败时抛出
        """
        logger.debug(f"Deriving key from password (salt length: {len(self.salt)})")
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # AES-256需要32字节密钥
            salt=self.salt,
            iterations=100000,  # OWASP推荐的最小迭代次数
            backend=default_backend()
        )
        self._key = kdf.derive(password.encode('utf-8'))
        logger.debug("Key derivation completed")
    
    # ==================== 编码方法 ====================
    
    def encode(self, watermark_content: str) -> bytes:
        """
        编码水印内容（无加密）
        
        编码流程：
        1. UTF-8编码文本内容
        2. 计算CRC32校验码
        3. 按格式封装：魔数 + 版本 + 长度 + 内容 + CRC
        
        Args:
            watermark_content: 水印文本内容
        
        Returns:
            bytes: 编码后的二进制数据（HEADER_SIZE + len(content) + CRC_SIZE 字节）
        
        Example:
            >>> codec = WatermarkCodec()
            >>> encoded = codec.encode("测试水印")
            >>> len(encoded)  # 10 + 12 + 4 = 26字节（中文UTF-8编码后12字节）
        """
        logger.debug(f"Encoding watermark: {len(watermark_content)} chars")
        
        # Step 1: UTF-8编码
        content_bytes = watermark_content.encode('utf-8')
        
        # Step 2: 计算CRC32校验码
        crc = zlib.crc32(content_bytes) & 0xFFFFFFFF  # 确保无符号32位
        
        # Step 3: 封装格式
        length = len(content_bytes)
        encoded = bytearray()
        
        # 魔数（5字节）
        encoded.extend(WATERMARK_MAGIC)
        
        # 版本号（1字节）
        encoded.append(WATERMARK_VERSION)
        
        # 内容长度（4字节，大端序）
        encoded.extend(length.to_bytes(LENGTH_FIELD_SIZE, byteorder='big'))
        
        # 内容（N字节）
        encoded.extend(content_bytes)
        
        # CRC32校验码（4字节，大端序）
        encoded.extend(crc.to_bytes(CRC_SIZE, byteorder='big'))
        
        result = bytes(encoded)
        logger.debug(f"Encoded to {len(result)} bytes (content: {length} bytes, CRC: {crc:08X})")
        
        return result
    
    def encode_with_encryption(self, watermark_content: str) -> bytes:
        """
        加密编码水印内容
        
        编码流程：
        1. 调用encode()进行基础编码
        2. 使用AES-256-CBC加密
        
        Args:
            watermark_content: 水印文本内容
        
        Returns:
            bytes: 加密后的二进制数据（IV + 密文）
        
        Raises:
            ValueError: 未设置密码时抛出
        
        Example:
            >>> codec = WatermarkCodec(password="secret")
            >>> encrypted = codec.encode_with_encryption("机密内容")
        """
        if not self._key:
            logger.error("Encryption requested but no password provided")
            raise ValueError("加密需要提供密码")
        
        logger.debug("Encoding with encryption")
        
        # 先进行基础编码
        encoded = self.encode(watermark_content)
        
        # AES加密
        encrypted = self._aes_encrypt(encoded)
        
        logger.debug(f"Encrypted to {len(encrypted)} bytes")
        return encrypted
    
    def _aes_encrypt(self, data: bytes) -> bytes:
        """
        AES-256-CBC加密
        
        加密参数：
        - 算法：AES-256
        - 模式：CBC
        - 填充：PKCS7
        - IV：随机生成16字节
        
        Args:
            data: 待加密数据
        
        Returns:
            bytes: IV(16字节) + 密文
        """
        # 生成随机IV
        iv = os.urandom(16)
        
        # PKCS7填充
        padder = padding.PKCS7(128).padder()  # 128位 = 16字节块大小
        padded_data = padder.update(data) + padder.finalize()
        
        # 创建加密器
        cipher = Cipher(
            algorithms.AES(self._key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        # 加密
        encrypted = encryptor.update(padded_data) + encryptor.finalize()
        
        # 返回 IV + 密文（IV需要保存用于解密）
        return iv + encrypted
    
    # ==================== 解码方法 ====================
    
    def decode(self, data: bytes) -> Tuple[bool, str, dict]:
        """
        解码水印数据（无解密）
        
        解码流程：
        1. 解析头部：验证魔数、读取版本和长度
        2. 提取内容
        3. CRC32校验
        4. UTF-8解码
        
        Args:
            data: 编码后的二进制数据
        
        Returns:
            Tuple[bool, str, dict]: 
                - bool: 解码是否成功
                - str: 解码后的内容（失败时为空字符串）
                - dict: 元数据信息（版本、长度、CRC状态等）
        
        Example:
            >>> success, content, info = codec.decode(encoded)
            >>> if success:
            ...     print(f"解码成功: {content}")
            ... else:
            ...     print(f"解码失败: {info['error']}")
        """
        logger.debug(f"Decoding {len(data)} bytes")
        
        try:
            pos = 0
            
            # Step 1: 验证魔数
            magic = data[pos:pos+5]
            if magic != WATERMARK_MAGIC:
                logger.warning(f"Invalid magic: {magic}")
                return False, "", {"error": "无效的水印格式", "expected": "SMARK"}
            pos += 5
            
            # Step 2: 读取版本号
            version = data[pos]
            pos += 1
            
            # Step 3: 读取内容长度
            length = int.from_bytes(data[pos:pos+LENGTH_FIELD_SIZE], byteorder='big')
            pos += LENGTH_FIELD_SIZE
            
            # Step 4: 提取内容
            content_bytes = data[pos:pos+length]
            pos += length
            
            # Step 5: 读取并验证CRC32
            stored_crc = int.from_bytes(data[pos:pos+4], byteorder='big')
            calculated_crc = zlib.crc32(content_bytes) & 0xFFFFFFFF
            
            if stored_crc != calculated_crc:
                logger.warning(f"CRC mismatch: stored={stored_crc:08X}, calculated={calculated_crc:08X}")
                return False, "", {
                    "error": "CRC校验失败 - 数据可能被篡改",
                    "stored_crc": f"{stored_crc:08X}",
                    "calculated_crc": f"{calculated_crc:08X}"
                }
            
            # Step 6: UTF-8解码
            content = content_bytes.decode('utf-8')
            
            logger.debug(f"Decoded successfully: {len(content)} chars, version={version}")
            
            return True, content, {
                "version": version,
                "length": length,
                "crc_ok": True,
                "crc_value": f"{calculated_crc:08X}"
            }
            
        except IndexError as e:
            logger.error(f"Decode error: data too short - {e}")
            return False, "", {"error": f"数据长度不足: {str(e)}"}
        except UnicodeDecodeError as e:
            logger.error(f"Decode error: invalid UTF-8 - {e}")
            return False, "", {"error": f"UTF-8解码失败: {str(e)}"}
        except Exception as e:
            logger.error(f"Decode error: {e}")
            return False, "", {"error": str(e)}
    
    def decode_with_decryption(self, data: bytes) -> Tuple[bool, str, dict]:
        """
        解密解码水印数据
        
        解码流程：
        1. AES-256-CBC解密
        2. 调用decode()进行解码
        
        Args:
            data: 加密后的二进制数据（IV + 密文）
        
        Returns:
            Tuple[bool, str, dict]: 同decode()
        
        Raises:
            ValueError: 未设置密码时抛出
        """
        if not self._key:
            logger.error("Decryption requested but no password provided")
            raise ValueError("解密需要提供密码")
        
        logger.debug("Decoding with decryption")
        
        try:
            # AES解密
            decrypted = self._aes_decrypt(data)
            
            # 基础解码
            return self.decode(decrypted)
            
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return False, "", {"error": f"解密失败: {str(e)}"}
    
    def _aes_decrypt(self, data: bytes) -> bytes:
        """
        AES-256-CBC解密
        
        Args:
            data: IV(16字节) + 密文
        
        Returns:
            bytes: 解密后的原始数据
        """
        # 提取IV和密文
        iv = data[:16]
        ciphertext = data[16:]
        
        # 创建解密器
        cipher = Cipher(
            algorithms.AES(self._key),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        # 解密
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()
        
        # 移除PKCS7填充
        unpadder = padding.PKCS7(128).unpadder()
        return unpadder.update(padded_data) + unpadder.finalize()
    
    # ==================== 工具方法 ====================
    
    @staticmethod
    def to_hex(data: bytes) -> str:
        """
        转换为十六进制字符串
        
        用于调试和日志输出。
        
        Args:
            data: 二进制数据
        
        Returns:
            str: 十六进制字符串（小写）
        
        Example:
            >>> WatermarkCodec.to_hex(b'hello')
            '68656c6c6f'
        """
        return data.hex()
    
    @staticmethod
    def from_hex(hex_str: str) -> bytes:
        """
        从十六进制字符串转换
        
        Args:
            hex_str: 十六进制字符串
        
        Returns:
            bytes: 二进制数据
        
        Raises:
            ValueError: 无效的十六进制字符串
        """
        return bytes.fromhex(hex_str)
    
    @staticmethod
    def to_base64(data: bytes) -> str:
        """
        转换为Base64字符串
        
        用于在文本协议中传输二进制数据。
        
        Args:
            data: 二进制数据
        
        Returns:
            str: Base64编码字符串
        """
        return base64.b64encode(data).decode('ascii')
    
    @staticmethod
    def from_base64(b64_str: str) -> bytes:
        """
        从Base64字符串转换
        
        Args:
            b64_str: Base64编码字符串
        
        Returns:
            bytes: 二进制数据
        
        Raises:
            ValueError: 无效的Base64字符串
        """
        return base64.b64decode(b64_str)


# 模块初始化日志
logger.info(f"{__name__} module loaded - Watermark codec ready")
