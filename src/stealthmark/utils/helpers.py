# utils/helpers.py
"""
辅助工具函数 - StealthMark 工具集

本模块提供通用的文件操作工具函数：
- calculate_file_hash: 计算文件哈希值
- ensure_dir: 确保目录存在
- get_file_size: 获取文件大小
- list_files: 列出目录文件
- safe_filename: 生成安全文件名

Author: StealthMark Team
Date: 2026-04-28
"""

import os
import hashlib
from pathlib import Path
from typing import List, Optional
import logging

# 模块日志
logger = logging.getLogger(__name__)


def calculate_file_hash(file_path: str, algorithm: str = 'sha256') -> str:
    """
    计算文件哈希值
    
    使用分块读取方式，支持大文件哈希计算。
    
    Args:
        file_path: 文件路径
        algorithm: 哈希算法，支持 'md5', 'sha1', 'sha256'（默认）
    
    Returns:
        str: 哈希值的十六进制字符串
    
    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 不支持的哈希算法
    
    Example:
        >>> hash_val = calculate_file_hash("document.pdf")
        >>> print(hash_val)  # 64字符的SHA256哈希值
        
        >>> # 使用MD5（更快但安全性较低）
        >>> hash_val = calculate_file_hash("file.txt", algorithm='md5')
    
    Note:
        - SHA256: 64字符，安全性高，推荐使用
        - SHA1: 40字符，已不推荐用于安全场景
        - MD5: 32字符，仅用于非安全场景（如去重）
    """
    logger.debug(f"Calculating {algorithm} hash for: {file_path}")
    
    # 创建哈希对象
    hash_func = hashlib.new(algorithm)
    
    # 分块读取文件（避免大文件内存问题）
    chunk_size = 8192  # 8KB块大小
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(chunk_size), b''):
            hash_func.update(chunk)
    
    result = hash_func.hexdigest()
    logger.debug(f"Hash: {result}")
    
    return result


def ensure_dir(dir_path: str) -> None:
    """
    确保目录存在
    
    如果目录不存在则创建，包括所有父目录。
    
    Args:
        dir_path: 目录路径
    
    Example:
        >>> ensure_dir("/path/to/output/files")
        # 如果目录不存在，会创建 /path, /path/to, /path/to/output, /path/to/output/files
    
    Note:
        使用 pathlib.Path.mkdir 的 parents=True 和 exist_ok=True，
        不会在目录已存在时抛出异常。
    """
    Path(dir_path).mkdir(parents=True, exist_ok=True)
    logger.debug(f"Directory ensured: {dir_path}")


def get_file_size(file_path: str) -> int:
    """
    获取文件大小
    
    Args:
        file_path: 文件路径
    
    Returns:
        int: 文件大小（字节）
    
    Raises:
        FileNotFoundError: 文件不存在
        OSError: 获取文件信息失败
    
    Example:
        >>> size = get_file_size("video.mp4")
        >>> print(f"文件大小: {size / 1024 / 1024:.2f} MB")
    """
    size = os.path.getsize(file_path)
    logger.debug(f"File size: {file_path} = {size} bytes")
    return size


def list_files(directory: str, extensions: Optional[List[str]] = None) -> List[str]:
    """
    列出目录下的文件
    
    递归遍历目录，返回所有文件路径。支持按扩展名过滤。
    
    Args:
        directory: 目录路径
        extensions: 扩展名过滤列表（可选）
            - 例如: ['.pdf', '.docx', '.png']
            - 不区分大小写
            - None 表示返回所有文件
    
    Returns:
        List[str]: 文件路径列表（绝对路径）
    
    Example:
        >>> # 列出所有文件
        >>> files = list_files("/path/to/dir")
        
        >>> # 只列出PDF文件
        >>> pdfs = list_files("/path/to/dir", extensions=['.pdf'])
        
        >>> # 列出多种格式
        >>> docs = list_files("/path/to/dir", extensions=['.pdf', '.docx', '.pptx'])
    
    Note:
        使用 os.walk 递归遍历，包含所有子目录。
    """
    logger.debug(f"Listing files in: {directory}, extensions: {extensions}")
    
    files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            # 扩展名过滤
            if extensions is None or Path(filename).suffix.lower() in extensions:
                files.append(os.path.join(root, filename))
    
    logger.debug(f"Found {len(files)} files")
    return files


def safe_filename(filename: str) -> str:
    """
    生成安全文件名
    
    移除或替换 Windows/Linux 中的非法字符。
    
    Args:
        filename: 原始文件名
    
    Returns:
        str: 安全的文件名（非法字符替换为下划线）
    
    Example:
        >>> safe_filename('file<>name.pdf')
        'file__name.pdf'
        
        >>> safe_filename('normal_file.pdf')
        'normal_file.pdf'
    
    Note:
        Windows 非法字符: < > : " / \\ | ? *
        这些字符在文件名中不允许，会被替换为下划线。
    """
    # Windows 非法字符
    invalid_chars = '<>:"/\\|?*'
    
    result = filename
    for char in invalid_chars:
        result = result.replace(char, '_')
    
    if result != filename:
        logger.debug(f"Filename sanitized: {filename} -> {result}")
    
    return result


def human_readable_size(size_bytes: int) -> str:
    """
    将字节数转换为人类可读格式
    
    Args:
        size_bytes: 字节数
    
    Returns:
        str: 人类可读的大小字符串
    
    Example:
        >>> human_readable_size(1024)
        '1.00 KB'
        >>> human_readable_size(1536000)
        '1.46 MB'
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"


# 模块初始化日志
logger.info(f"{__name__} module loaded - Helper utilities ready")
