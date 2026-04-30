import unittest
import os
import tempfile
from src.media.audio_watermark import WAVHandler
from src.core.base import WatermarkData

class TestWAVHandler(unittest.TestCase):
    def setUp(self):
        self.handler = WAVHandler(config={'password': 'test_secret', 'spread_factor': 31, 'alpha': 0.005})
        self.test_wav_path = r'tests\fixtures\test.wav'
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
    
    def test_embed_success(self):
        """测试WAV水印嵌入成功"""
        output_path = os.path.join(self.temp_dir, 'test_embed.wav')
        watermark = WatermarkData(content='WAVTest-2026')
        
        result = self.handler.embed(
            file_path=self.test_wav_path,
            watermark=watermark,
            output_path=output_path
        )
        
        self.assertTrue(result.is_success, f"WAV embed failed: {result.message}")
        self.assertTrue(os.path.exists(output_path), "Output WAV file not created")
    
    def test_extract_success(self):
        """测试WAV水印提取成功"""
        embed_output = os.path.join(self.temp_dir, 'test_extract.wav')
        watermark = WatermarkData(content='WAVExtract-2026')
        
        # 先嵌入
        embed_result = self.handler.embed(self.test_wav_path, watermark, embed_output)
        self.assertTrue(embed_result.is_success, f"WAV embed failed: {embed_result.message}")
        
        # 再提取
        extract_result = self.handler.extract(embed_output)
        self.assertTrue(extract_result.is_success, f"WAV extract failed: {extract_result.message}")
        self.assertEqual(extract_result.watermark.content, 'WAVExtract-2026', "Extracted content mismatch")
    
    def test_verify_success(self):
        """测试WAV水印验证成功"""
        output_path = os.path.join(self.temp_dir, 'test_verify.wav')
        watermark = WatermarkData(content='WAVVerify-2026')
        
        # 嵌入
        embed_result = self.handler.embed(self.test_wav_path, watermark, output_path)
        self.assertTrue(embed_result.is_success)
        
        # 验证
        verify_result = self.handler.verify(output_path, watermark)
        self.assertTrue(verify_result.is_valid, f"WAV verify failed: {verify_result.message}")
        self.assertEqual(verify_result.status, 'success')

if __name__ == '__main__':
    unittest.main()
