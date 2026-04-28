# tests/test_manager.py
"""
StealthMark 管理器测试
"""

import pytest
from src.core.manager import StealthMark
from src.core.base import WatermarkStatus


class TestStealthMark:
    """StealthMark 管理器测试类"""
    
    def setup_method(self):
        """每个测试前初始化"""
        self.wm = StealthMark()
    
    def test_init_basic(self):
        """测试基本初始化"""
        wm = StealthMark()
        assert wm.codec is not None
    
    def test_init_with_password(self):
        """测试带密码初始化"""
        wm = StealthMark(password="test123")
        assert wm.password == "test123"
    
    def test_handler_registration(self):
        """测试处理器注册"""
        assert len(self.wm._handler_registry) > 0
    
    def test_supported_formats(self):
        """测试支持格式"""
        formats = self.wm.supported_formats()
        
        expected = ['.pdf', '.docx', '.pptx', '.png', '.jpg', 
                   '.jpeg', '.bmp', '.wav', '.mp3', '.mp4', 
                   '.avi', '.mkv', '.mov']
        
        for fmt in expected:
            assert fmt in formats
    
    def test_is_supported_pdf(self):
        """测试PDF支持"""
        assert self.wm.is_supported("test.pdf") is True
        assert self.wm.is_supported("test.PDF") is True
    
    def test_is_supported_unsupported(self):
        """测试不支持的格式"""
        assert self.wm.is_supported("test.xyz") is False
        assert self.wm.is_supported("test") is False
    
    def test_embed_file_not_found(self):
        """测试嵌入不存在的文件"""
        result = self.wm.embed("nonexistent.pdf", "水印")
        
        assert result.is_success is False
        assert result.status == WatermarkStatus.FILE_NOT_FOUND
    
    def test_extract_unsupported_format(self):
        """测试提取不支持格式"""
        result = self.wm.extract("test.xyz")
        
        assert result.is_success is False
        assert result.status == WatermarkStatus.UNSUPPORTED_FORMAT
    
    def test_verify_nonexistent_file(self):
        """测试验证不存在的文件"""
        result = self.wm.verify("nonexistent.pdf", "水印")
        
        assert result.is_valid is False
    
    def test_register_handler(self):
        """测试注册自定义处理器"""
        from src.core.base import BaseHandler, EmbedResult, ExtractResult, VerifyResult, WatermarkData
        
        class CustomHandler(BaseHandler):
            SUPPORTED_EXTENSIONS = ('.custom',)
            HANDLER_NAME = "custom"
            
            def embed(self, file_path, watermark, output_path, **kwargs):
                return EmbedResult(status=WatermarkStatus.SUCCESS)
            
            def extract(self, file_path, **kwargs):
                return ExtractResult(
                    status=WatermarkStatus.SUCCESS,
                    watermark=WatermarkData(content="custom")
                )
            
            def verify(self, file_path, original_watermark, **kwargs):
                return VerifyResult(
                    status=WatermarkStatus.SUCCESS,
                    is_valid=True,
                    is_integrity_ok=True,
                    match_score=1.0
                )
        
        initial_count = len(self.wm._handler_registry)
        self.wm.register_handler(CustomHandler)
        
        assert len(self.wm._handler_registry) == initial_count + 1
        assert self.wm.is_supported("test.custom") is True
    
    def test_multiple_formats(self):
        """测试多种格式"""
        formats = self.wm.supported_formats()
        
        # 文档格式
        assert '.pdf' in formats
        assert '.docx' in formats
        assert '.pptx' in formats
        
        # 图片格式
        assert '.png' in formats
        assert '.jpg' in formats
        
        # 音频格式
        assert '.wav' in formats
        
        # 视频格式
        assert '.mp4' in formats


class TestSimulatedWorkflow:
    """模拟工作流测试（不依赖真实文件）"""
    
    def setup_method(self):
        """每个测试前初始化"""
        self.wm = StealthMark()
    
    def test_manager_structure(self):
        """测试管理器结构"""
        assert hasattr(self.wm, 'codec')
        assert hasattr(self.wm, '_handlers')
        assert hasattr(self.wm, '_handler_registry')
        assert hasattr(self.wm, 'embed')
        assert hasattr(self.wm, 'extract')
        assert hasattr(self.wm, 'verify')
    
    def test_handlers_initialized(self):
        """测试处理器已初始化"""
        assert len(self.wm._handlers) > 0
        
        for ext, handler in self.wm._handlers.items():
            assert handler is not None
            assert hasattr(handler, 'embed')
            assert hasattr(handler, 'extract')
            assert hasattr(handler, 'verify')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])