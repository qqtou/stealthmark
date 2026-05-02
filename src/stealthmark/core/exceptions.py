# core/exceptions.py
"""
StealthMark 异常类定义

本模块定义了 StealthMark 的异常层次结构：
- StealthMarkError: 所有异常的基类
- StealthMarkFileNotFoundError: 文件不存在
- UnsupportedFormatError: 不支持的文件格式
- EmbedError/ExtractError/VerifyError: 操作失败
- CodecError: 编解码失败
- EncryptionError: 加密失败

使用示例:
    >>> from stealthmark.core.exceptions import EmbedError
    >>> try:
    ...     raise EmbedError("嵌入失败：文件损坏")
    ... except StealthMarkError as e:
    ...     print(f"StealthMark错误: {e}")

Author: StealthMark Team
Date: 2026-04-28
"""


class StealthMarkError(Exception):
    """
    StealthMark 基础异常
    
    所有 StealthMark 异常的父类，便于统一捕获。
    
    Example:
        >>> try:
        ...     # StealthMark 操作
        ...     pass
        ... except StealthMarkError as e:
        ...     print(f"操作失败: {e}")
    """
    pass


class StealthMarkFileNotFoundError(StealthMarkError):
    """
    文件不存在异常
    
    当操作的文件路径不存在时抛出。
    
    Attributes:
        file_path: 不存在的文件路径
    
    Example:
        >>> raise StealthMarkFileNotFoundError("文件不存在: /path/to/file.pdf")
    """
    pass


class UnsupportedFormatError(StealthMarkError):
    """
    不支持的文件格式异常
    
    当尝试处理不支持的文件格式时抛出。
    
    Example:
        >>> raise UnsupportedFormatError("不支持的格式: .xyz")
    """
    pass


class EmbedError(StealthMarkError):
    """
    水印嵌入失败异常
    
    当水印嵌入过程中发生错误时抛出。
    
    Example:
        >>> raise EmbedError("嵌入失败：文件已损坏")
    """
    pass


class ExtractError(StealthMarkError):
    """
    水印提取失败异常
    
    当水印提取过程中发生错误时抛出。
    
    Example:
        >>> raise ExtractError("提取失败：未找到水印数据")
    """
    pass


class VerifyError(StealthMarkError):
    """
    水印验证失败异常
    
    当水印验证过程中发生错误时抛出。
    
    Example:
        >>> raise VerifyError("验证失败：水印不匹配")
    """
    pass


class CodecError(StealthMarkError):
    """
    编解码失败异常
    
    当编解码过程中发生错误时抛出。
    
    Example:
        >>> raise CodecError("解码失败：CRC校验错误")
    """
    pass


class EncryptionError(StealthMarkError):
    """
    加密失败异常
    
    当加密/解密过程中发生错误时抛出。
    
    Example:
        >>> raise EncryptionError("解密失败：无效的密钥")
    """
    pass
