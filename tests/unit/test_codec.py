# tests/test_codec.py
"""
编解码器单元测试
"""

import pytest
from src.core.codec import WatermarkCodec


class TestWatermarkCodec:
    """WatermarkCodec 测试类"""
    
    def setup_method(self):
        """每个测试方法前执行"""
        self.codec = WatermarkCodec()
    
    def test_encode_basic(self):
        """测试基本编码"""
        content = "测试水印内容"
        encoded = self.codec.encode(content)
        
        assert encoded is not None
        assert len(encoded) > 0
        assert encoded[:5] == b"SMARK"  # 魔数
    
    def test_decode_basic(self):
        """测试基本解码"""
        content = "测试水印内容"
        encoded = self.codec.encode(content)
        success, decoded, details = self.codec.decode(encoded)
        
        assert success is True
        assert decoded == content
    
    def test_encode_decode_empty(self):
        """测试空字符串"""
        content = ""
        encoded = self.codec.encode(content)
        success, decoded, _ = self.codec.decode(encoded)
        
        assert success is True
        assert decoded == ""
    
    def test_encode_decode_long_text(self):
        """测试长文本"""
        content = "A" * 1000
        encoded = self.codec.encode(content)
        success, decoded, _ = self.codec.decode(encoded)
        
        assert success is True
        assert decoded == content
    
    def test_encode_decode_special_chars(self):
        """测试特殊字符"""
        content = "中文测试\r\n\t!@#$%^&*()_+-=[]{}|;':\",./<>?"
        encoded = self.codec.encode(content)
        success, decoded, _ = self.codec.decode(encoded)
        
        assert success is True
        assert decoded == content
    
    def test_encode_decode_with_password(self):
        """测试加密模式"""
        codec = WatermarkCodec(password="test123")
        content = "加密水印"
        
        encoded = codec.encode(content)
        success, decoded, _ = codec.decode(encoded)
        assert success is True
        assert decoded == content
    
    def test_hex_conversion(self):
        """测试十六进制转换"""
        data = b"hello world"
        hex_str = WatermarkCodec.to_hex(data)
        decoded = WatermarkCodec.from_hex(hex_str)
        
        assert decoded == data
        assert hex_str == "68656c6c6f20776f726c64"
    
    def test_base64_conversion(self):
        """测试Base64转换"""
        data = b"hello world"
        b64_str = WatermarkCodec.to_base64(data)
        decoded = WatermarkCodec.from_base64(b64_str)
        
        assert decoded == data
    
    def test_crc_validation(self):
        """测试CRC校验"""
        content = "CRC测试"
        encoded = self.codec.encode(content)
        
        # 篡改数据
        tampered = bytearray(encoded)
        tampered[15] ^= 0xFF
        tampered = bytes(tampered)
        
        success, _, details = self.codec.decode(tampered)
        assert success is False
        assert 'crc' in details.get('error', '').lower()
    
    def test_invalid_magic(self):
        """测试无效魔数"""
        invalid_data = b"INVALID" + b"\x00" * 20
        success, _, _ = self.codec.decode(invalid_data)
        
        assert success is False
    
    def test_multiple_encode(self):
        """测试多次编码一致性"""
        content = "一致性测试"
        
        encoded1 = self.codec.encode(content)
        encoded2 = self.codec.encode(content)
        
        # 同内容编码结果应相同
        assert encoded1 == encoded2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])