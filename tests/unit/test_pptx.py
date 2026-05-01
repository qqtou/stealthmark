import unittest
import os
import tempfile
from stealthmark.document.pptx_watermark import PPTXHandler
from stealthmark.core.base import WatermarkData, WatermarkStatus

class TestPPTXHandler(unittest.TestCase):
    def setUp(self):
        self.handler = PPTXHandler(config={'password': 'test_secret'})
        self.test_pptx_path = r'tests\fixtures\test.pptx'
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
    
    def test_embed_success(self):
        """测试PPTX水印嵌入成功"""
        output_path = os.path.join(self.temp_dir, 'test_embed.pptx')
        watermark = WatermarkData(content='PPTXTest-2026')
        
        result = self.handler.embed(
            file_path=self.test_pptx_path,
            watermark=watermark,
            output_path=output_path
        )
        
        self.assertTrue(result.is_success, f"PPTX embed failed: {result.message}")
        self.assertTrue(os.path.exists(output_path), "Output PPTX file not created")
    
    def test_extract_success(self):
        """测试PPTX水印提取成功"""
        embed_output = os.path.join(self.temp_dir, 'test_extract.pptx')
        watermark = WatermarkData(content='PPTXExtract-2026')
        
        # 先嵌
        embed_result = self.handler.embed(self.test_pptx_path, watermark, embed_output)
        self.assertTrue(embed_result.is_success, f"PPTX embed failed: {embed_result.message}")
        
        # 再提
        extract_result = self.handler.extract(embed_output)
        self.assertTrue(extract_result.is_success, f"PPTX extract failed: {extract_result.message}")
        self.assertEqual(extract_result.watermark.content, 'PPTXExtract-2026', "Extracted content mismatch")
    
    def test_verify_success(self):
        """测试PPTX水印验证成功"""
        output_path = os.path.join(self.temp_dir, 'test_verify.pptx')
        watermark = WatermarkData(content='PPTXVerify-2026')
        
        # 嵌入
        embed_result = self.handler.embed(self.test_pptx_path, watermark, output_path)
        self.assertTrue(embed_result.is_success)
        
        # 验证
        verify_result = self.handler.verify(output_path, watermark)
        self.assertTrue(verify_result.is_valid, f"PPTX verify failed: {verify_result.message}")
        self.assertEqual(verify_result.status, WatermarkStatus.SUCCESS)

if __name__ == '__main__':
    unittest.main()
