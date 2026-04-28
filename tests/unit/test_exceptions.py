# tests/test_exceptions.py
"""
异常类测试
"""

import pytest
from src.core.exceptions import (
    StealthMarkError,
    FileNotFoundError,
    UnsupportedFormatError,
    EmbedError,
    ExtractError,
    VerifyError,
    CodecError,
    EncryptionError
)


class TestExceptions:
    """异常类测试类"""
    
    def test_stealthmark_error(self):
        """测试基础异常"""
        error = StealthMarkError("基础错误")
        assert str(error) == "基础错误"
    
    def test_file_not_found_error(self):
        """测试文件不存在异常"""
        error = FileNotFoundError("文件不存在")
        assert isinstance(error, StealthMarkError)
        assert str(error) == "文件不存在"
    
    def test_unsupported_format_error(self):
        """测试不支持格式异常"""
        error = UnsupportedFormatError("不支持的格式")
        assert isinstance(error, StealthMarkError)
    
    def test_embed_error(self):
        """测试嵌入异常"""
        error = EmbedError("嵌入失败")
        assert isinstance(error, StealthMarkError)
    
    def test_extract_error(self):
        """测试提取异常"""
        error = ExtractError("提取失败")
        assert isinstance(error, StealthMarkError)
    
    def test_verify_error(self):
        """测试验证异常"""
        error = VerifyError("验证失败")
        assert isinstance(error, StealthMarkError)
    
    def test_codec_error(self):
        """测试编解码异常"""
        error = CodecError("编解码错误")
        assert isinstance(error, StealthMarkError)
    
    def test_encryption_error(self):
        """测试加密异常"""
        error = EncryptionError("加密失败")
        assert isinstance(error, StealthMarkError)
    
    def test_exception_hierarchy(self):
        """测试异常层次"""
        errors = [
            FileNotFoundError,
            UnsupportedFormatError,
            EmbedError,
            ExtractError,
            VerifyError,
            CodecError,
            EncryptionError
        ]
        
        for error_class in errors:
            error = error_class("test")
            assert isinstance(error, Exception)
            assert isinstance(error, StealthMarkError)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])