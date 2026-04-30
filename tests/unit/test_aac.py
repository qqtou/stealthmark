import unittest
import os
import tempfile
from src.media.aac_handler import AACHandler
from src.core.base import WatermarkData

class TestAACHandler(unittest.TestCase):
    def setUp(self):
        self.handler = AACHandler(config={'password': 'test_secret'})
        self.test_aac_path = r'tests\fixtures\test.aac'
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
    
    def test_embed_success(self):
        """测试AAC水印嵌入成功"""
        output_path = os.path.join(self.temp_dir, 'test_embed.aac')
        watermark = WatermarkData(content='AACTest-2026')
        
        result = self.handler.embed(
            file_path=self.test_aac_path,
            watermark=watermark,
            output_path=output_path
        )
        
        self.assertTrue(result.is_success, f"AAC embed failed: {result.message}")
        self.assertTrue(os.path.exists(output_path), "Output AAC file not created")
    
    def test_extract_success(self):
        """测试AAC水印提取成功"""
        embed_output = os.path.join(self.temp_dir, 'test_extract.aac')
        watermark = WatermarkData(content='AACExtract-2026')
        
        # 先嵌入
        embed_result = self.handler.embed(self.test_aac_path, watermark, embed_output)
        self.assertTrue(embed_result.is_success, f"AAC embed failed: {embed_result.message}")
        
        # 再提取
        extract_result = self.handler.extract(embed_output)
        self.assertTrue(extract_result.is_success, f"AAC extract failed: {extract_result.message}")
        self.assertEqual(extract_result.watermark.content, 'AACExtract-2026', "Extracted content mismatch")
    
    def test_verify_success(self):
        """测试AAC水印验证成功"""
        output_path = os.path.join(self.temp_dir, 'test_verify.aac')
        watermark = WatermarkData(content='AACVerify-2026')
        
        # 嵌入
        embed_result = self.handler.embed(self.test_aac_path, watermark, output_path)
        self.assertTrue(embed_result.is_success)
        
        # 验证
        verify_result = self.handler.verify(output_path, watermark)
        self.assertTrue(verify_result.is_valid, f"AAC verify failed: {verify_result.message}")
        self.assertEqual(verify_result.status, 'success')

if __name__ == '__main__':
    unittest.main()
