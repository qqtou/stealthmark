import unittest
import os
import tempfile
from src.media.audio_watermark import MP3Handler
from src.core.base import WatermarkData

class TestMP3Handler(unittest.TestCase):
    def setUp(self):
        self.handler = MP3Handler(config={'password': 'test_secret', 'bit_duration': 0.12})
        self.test_mp3_path = r'tests\fixtures\test_long.mp3'  # 使用长音频测试
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
    
    def test_embed_success(self):
        """测试MP3水印嵌入成功"""
        output_path = os.path.join(self.temp_dir, 'test_embed.mp3')
        watermark = WatermarkData(content='MP3Test-2026')
        
        result = self.handler.embed(
            file_path=self.test_mp3_path,
            watermark=watermark,
            output_path=output_path
        )
        
        self.assertTrue(result.is_success, f"MP3 embed failed: {result.message}")
        self.assertTrue(os.path.exists(output_path), "Output MP3 file not created")
    
    def test_extract_success(self):
        """测试MP3水印提取成功"""
        embed_output = os.path.join(self.temp_dir, 'test_extract.mp3')
        watermark = WatermarkData(content='MP3Extract-2026')
        
        # 先嵌入
        embed_result = self.handler.embed(self.test_mp3_path, watermark, embed_output)
        self.assertTrue(embed_result.is_success, f"MP3 embed failed: {embed_result.message}")
        
        # 再提取
        extract_result = self.handler.extract(embed_output)
        self.assertTrue(extract_result.is_success, f"MP3 extract failed: {extract_result.message}")
        self.assertEqual(extract_result.watermark.content, 'MP3Extract-2026', "Extracted content mismatch")
    
    def test_verify_success(self):
        """测试MP3水印验证成功"""
        output_path = os.path.join(self.temp_dir, 'test_verify.mp3')
        watermark = WatermarkData(content='MP3Verify-2026')
        
        # 嵌入
        embed_result = self.handler.embed(self.test_mp3_path, watermark, output_path)
        self.assertTrue(embed_result.is_success)
        
        # 验证
        verify_result = self.handler.verify(output_path, watermark)
        self.assertTrue(verify_result.is_valid, f"MP3 verify failed: {verify_result.message}")
        self.assertEqual(verify_result.status, 'success')

if __name__ == '__main__':
    unittest.main()
