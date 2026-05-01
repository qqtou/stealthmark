import unittest
import os
import tempfile
from stealthmark.document.docx_watermark import DOCXHandler
from stealthmark.core.base import WatermarkData, WatermarkStatus

class TestDOCXHandler(unittest.TestCase):
    def setUp(self):
        self.handler = DOCXHandler(config={'password': 'test_secret'})
        self.test_docx_path = r'tests\fixtures\test.docx'
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
    
    def test_embed_success(self):
        """测试DOCX水印嵌入成功"""
        output_path = os.path.join(self.temp_dir, 'test_embed.docx')
        watermark = WatermarkData(content='DOCXTest-2026')
        
        result = self.handler.embed(
            file_path=self.test_docx_path,
            watermark=watermark,
            output_path=output_path
        )
        
        self.assertTrue(result.is_success, f"DOCX embed failed: {result.message}")
        self.assertTrue(os.path.exists(output_path), "Output DOCX file not created")
    
    def test_extract_success(self):
        """测试DOCX水印提取成功"""
        embed_output = os.path.join(self.temp_dir, 'test_extract.docx')
        watermark = WatermarkData(content='DOCXExtract-2026')
        
        # 先嵌
        embed_result = self.handler.embed(self.test_docx_path, watermark, embed_output)
        self.assertTrue(embed_result.is_success, f"DOCX embed failed: {embed_result.message}")
        
        # 再提
        extract_result = self.handler.extract(embed_output)
        self.assertTrue(extract_result.is_success, f"DOCX extract failed: {extract_result.message}")
        self.assertEqual(extract_result.watermark.content, 'DOCXExtract-2026', "Extracted content mismatch")
    
    def test_verify_success(self):
        """测试DOCX水印验证成功"""
        output_path = os.path.join(self.temp_dir, 'test_verify.docx')
        watermark = WatermarkData(content='DOCXVerify-2026')
        
        # 嵌入
        embed_result = self.handler.embed(self.test_docx_path, watermark, output_path)
        self.assertTrue(embed_result.is_success)
        
        # 验证
        verify_result = self.handler.verify(output_path, watermark)
        self.assertTrue(verify_result.is_valid, f"DOCX verify failed: {verify_result.message}")
        self.assertEqual(verify_result.status, WatermarkStatus.SUCCESS)

if __name__ == '__main__':
    unittest.main()
