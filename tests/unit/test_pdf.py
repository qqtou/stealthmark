import unittest
import os
import tempfile
from stealthmark.document.pdf_watermark import PDFHandler
from stealthmark.core.base import WatermarkData, WatermarkStatus

class TestPDFHandler(unittest.TestCase):
    def setUp(self):
        self.handler = PDFHandler(config={'password': 'test_secret'})
        self.test_pdf_path = r'tests\fixtures\test.pdf'
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
    
    def test_embed_success(self):
        """测试PDF水印嵌入成功"""
        output_path = os.path.join(self.temp_dir, 'test_embed.pdf')
        watermark = WatermarkData(content='PDFTest-2026')
        
        result = self.handler.embed(
            file_path=self.test_pdf_path,
            watermark=watermark,
            output_path=output_path
        )
        
        self.assertTrue(result.is_success, f"PDF embed failed: {result.message}")
        self.assertTrue(os.path.exists(output_path), "Output PDF file not created")
    
    def test_extract_success(self):
        """测试PDF水印提取成功"""
        embed_output = os.path.join(self.temp_dir, 'test_extract.pdf')
        watermark = WatermarkData(content='PDFExtract-2026')
        
        # 先嵌
        embed_result = self.handler.embed(self.test_pdf_path, watermark, embed_output)
        self.assertTrue(embed_result.is_success, f"PDF embed failed: {embed_result.message}")
        
        # 再提
        extract_result = self.handler.extract(embed_output)
        self.assertTrue(extract_result.is_success, f"PDF extract failed: {extract_result.message}")
        self.assertEqual(extract_result.watermark.content, 'PDFExtract-2026', "Extracted content mismatch")
    
    def test_verify_success(self):
        """测试PDF水印验证成功"""
        output_path = os.path.join(self.temp_dir, 'test_verify.pdf')
        watermark = WatermarkData(content='PDFVerify-2026')
        
        # 嵌入
        embed_result = self.handler.embed(self.test_pdf_path, watermark, output_path)
        self.assertTrue(embed_result.is_success)
        
        # 验证
        verify_result = self.handler.verify(output_path, watermark)
        self.assertTrue(verify_result.is_valid, f"PDF verify failed: {verify_result.message}")
        self.assertEqual(verify_result.status, WatermarkStatus.SUCCESS)

if __name__ == '__main__':
    unittest.main()
