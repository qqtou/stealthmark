import unittest
import os
import tempfile
from src.document.odp_watermark import ODPHandler
from src.core.base import WatermarkData

class TestODPHandler(unittest.TestCase):
    def setUp(self):
        self.handler = ODPHandler(config={'password': 'test_secret'})
        self.test_odp_path = r'tests\fixtures\test.odp'
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
    
    def test_embed_success(self):
        """测试ODP水印嵌入成功"""
        output_path = os.path.join(self.temp_dir, 'test_embed.odp')
        watermark = WatermarkData(content='ODPTest-2026')
        
        result = self.handler.embed(
            file_path=self.test_odp_path,
            watermark=watermark,
            output_path=output_path
        )
        
        self.assertTrue(result.is_success, f"ODP embed failed: {result.message}")
        self.assertTrue(os.path.exists(output_path), "Output ODP file not created")
    
    def test_extract_success(self):
        """测试ODP水印提取成功"""
        embed_output = os.path.join(self.temp_dir, 'test_extract.odp')
        watermark = WatermarkData(content='ODPExtract-2026')
        
        # 先嵌入
        embed_result = self.handler.embed(self.test_odp_path, watermark, embed_output)
        self.assertTrue(embed_result.is_success, f"ODP embed failed: {embed_result.message}")
        
        # 再提取
        extract_result = self.handler.extract(embed_output)
        self.assertTrue(extract_result.is_success, f"ODP extract failed: {extract_result.message}")
        self.assertEqual(extract_result.watermark.content, 'ODPExtract-2026', "Extracted content mismatch")
    
    def test_verify_success(self):
        """测试ODP水印验证成功"""
        output_path = os.path.join(self.temp_dir, 'test_verify.odp')
        watermark = WatermarkData(content='ODPVerify-2026')
        
        # 嵌入
        embed_result = self.handler.embed(self.test_odp_path, watermark, output_path)
        self.assertTrue(embed_result.is_success)
        
        # 验证
        verify_result = self.handler.verify(output_path, watermark)
        self.assertTrue(verify_result.is_valid, f"ODP verify failed: {verify_result.message}")
        self.assertEqual(verify_result.status, 'success')

if __name__ == '__main__':
    unittest.main()
