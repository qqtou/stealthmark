import unittest
import os
import tempfile
from stealthmark.media.ogg_handler import OGGHandler
from stealthmark.core.base import WatermarkData, WatermarkStatus

class TestOGGHandler(unittest.TestCase):
    def setUp(self):
        self.handler = OGGHandler(config={'password': 'test_secret'})
        self.test_ogg_path = r'tests\fixtures\test.ogg'
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        # 清理临时文件
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
    
    def test_embed_success(self):
        """测试OGG水印嵌入成功"""
        output_path = os.path.join(self.temp_dir, 'test_embed.ogg')
        watermark = WatermarkData(content='OGGTest-2026')
        
        result = self.handler.embed(
            file_path=self.test_ogg_path,
            watermark=watermark,
            output_path=output_path
        )
        
        self.assertTrue(result.is_success, f"Embed failed: {result.message}")
        self.assertTrue(os.path.exists(output_path), "Output file not created")
    
    def test_extract_success(self):
        """测试OGG水印提取成功"""
        # 先嵌入水
        embed_output = os.path.join(self.temp_dir, 'test_extract.ogg')
        watermark = WatermarkData(content='OGGExtract-2026')
        embed_result = self.handler.embed(self.test_ogg_path, watermark, embed_output)
        self.assertTrue(embed_result.is_success)
        
        # 提取水印
        extract_result = self.handler.extract(embed_output)
        self.assertTrue(extract_result.is_success, f"Extract failed: {extract_result.message}")
        self.assertEqual(extract_result.watermark.content, 'OGGExtract-2026')
    
    def test_verify_success(self):
        """测试OGG水印验证成功"""
        output_path = os.path.join(self.temp_dir, 'test_verify.ogg')
        watermark = WatermarkData(content='OGGVerify-2026')
        
        # 嵌入
        embed_result = self.handler.embed(self.test_ogg_path, watermark, output_path)
        self.assertTrue(embed_result.is_success)
        
        # 验证
        verify_result = self.handler.verify(output_path, watermark)
        self.assertTrue(verify_result.is_valid)
        self.assertEqual(verify_result.status, WatermarkStatus.SUCCESS)

if __name__ == '__main__':
    unittest.main()
