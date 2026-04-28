# tests/test_base.py
"""
基础类单元测试
"""

import pytest
from src.core.base import (
    WatermarkData, WatermarkStatus, WatermarkType,
    EmbedResult, ExtractResult, VerifyResult, BaseHandler
)


class TestWatermarkData:
    """WatermarkData 测试类"""
    
    def test_create_basic(self):
        """测试基本创建"""
        data = WatermarkData(content="测试")
        
        assert data.content == "测试"
        assert data.watermark_type == WatermarkType.TEXT
        assert data.created_at is not None
        assert data.metadata == {}
    
    def test_create_with_metadata(self):
        """测试带元数据创建"""
        data = WatermarkData(
            content="测试",
            watermark_type=WatermarkType.IMAGE,
            metadata={"author": "张三"}
        )
        
        assert data.watermark_type == WatermarkType.IMAGE
        assert data.metadata["author"] == "张三"
    
    def test_auto_created_at(self):
        """测试自动创建时间"""
        import time
        before = WatermarkData(content="test")
        time.sleep(0.01)
        after = WatermarkData(content="test")
        
        # 时间戳应该不同
        assert before.created_at <= after.created_at


class TestWatermarkStatus:
    """WatermarkStatus 测试类"""
    
    def test_all_status_values(self):
        """测试所有状态值"""
        statuses = [
            WatermarkStatus.SUCCESS,
            WatermarkStatus.FAILED,
            WatermarkStatus.FILE_NOT_FOUND,
            WatermarkStatus.FILE_CORRUPTED,
            WatermarkStatus.UNSUPPORTED_FORMAT,
            WatermarkStatus.INVALID_WATERMARK,
            WatermarkStatus.EXTRACTION_FAILED,
            WatermarkStatus.VERIFICATION_FAILED,
            WatermarkStatus.ENCRYPTION_FAILED,
            WatermarkStatus.DECRYPTION_FAILED,
        ]
        
        assert len(statuses) == 10
    
    def test_status_values_unique(self):
        """测试状态值唯一性"""
        values = [s.value for s in WatermarkStatus]
        assert len(values) == len(set(values))


class TestOperationResults:
    """操作结果测试类"""
    
    def test_embed_result_success(self):
        """测试嵌入成功结果"""
        result = EmbedResult(
            status=WatermarkStatus.SUCCESS,
            message="成功",
            file_path="test.pdf",
            output_path="output.pdf"
        )
        
        assert result.is_success is True
        assert result.status == WatermarkStatus.SUCCESS
    
    def test_embed_result_failure(self):
        """测试嵌入失败结果"""
        result = EmbedResult(
            status=WatermarkStatus.FILE_NOT_FOUND,
            message="文件不存在"
        )
        
        assert result.is_success is False
    
    def test_extract_result_success(self):
        """测试提取成功结果"""
        watermark = WatermarkData(content="提取的水印")
        result = ExtractResult(
            status=WatermarkStatus.SUCCESS,
            message="成功",
            file_path="test.pdf",
            watermark=watermark
        )
        
        assert result.is_success is True
        assert result.watermark.content == "提取的水印"
    
    def test_verify_result_valid(self):
        """测试验证通过结果"""
        result = VerifyResult(
            status=WatermarkStatus.SUCCESS,
            is_valid=True,
            is_integrity_ok=True,
            match_score=1.0,
            message="验证通过"
        )
        
        assert result.is_valid is True
        assert result.match_score == 1.0
    
    def test_verify_result_invalid(self):
        """测试验证失败结果"""
        result = VerifyResult(
            status=WatermarkStatus.VERIFICATION_FAILED,
            is_valid=False,
            is_integrity_ok=False,
            match_score=0.0,
            message="水印不匹配"
        )
        
        assert result.is_valid is False
        assert result.match_score == 0.0


class MockHandler(BaseHandler):
    """测试用模拟处理器"""
    
    SUPPORTED_EXTENSIONS = ('.mock', '.test')
    HANDLER_NAME = "mock"
    
    def embed(self, file_path, watermark, output_path, **kwargs):
        return EmbedResult(status=WatermarkStatus.SUCCESS)
    
    def extract(self, file_path, **kwargs):
        return ExtractResult(
            status=WatermarkStatus.SUCCESS,
            watermark=WatermarkData(content="mock")
        )
    
    def verify(self, file_path, original_watermark, **kwargs):
        return VerifyResult(
            status=WatermarkStatus.SUCCESS,
            is_valid=True,
            is_integrity_ok=True,
            match_score=1.0
        )


class TestBaseHandler:
    """BaseHandler 测试类"""
    
    def setup_method(self):
        """每个测试前创建模拟处理器"""
        self.handler = MockHandler()
    
    def test_is_supported(self):
        """测试文件支持检查"""
        assert self.handler.is_supported("test.mock") is True
        assert self.handler.is_supported("test.test") is True
        assert self.handler.is_supported("test.pdf") is False
        assert self.handler.is_supported("test.xyz") is False
    
    def test_handler_name(self):
        """测试处理器名称"""
        assert self.handler.HANDLER_NAME == "mock"
    
    def test_config(self):
        """测试配置"""
        handler = MockHandler(config={"key": "value"})
        assert handler.config["key"] == "value"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])