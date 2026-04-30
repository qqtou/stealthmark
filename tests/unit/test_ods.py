import unittest
import os
import tempfile
from src.document.ods_watermark import ODSHandler
from src.core.base import WatermarkData

class TestODSHandler(unittest.TestCase):
    def setUp(self):
        self.handler = ODSHandler(config={'password': 'test_secret'})
        self.test_ods_path = r'tests\fixtures\test.ods'
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
    
    def test_embed_success(self):
        """测试ODS水印嵌入成功"""
        output_path = os.path.join(self.temp_dir, 'test_embed.ods')
        watermark = WatermarkData(content='ODSTest-2026')
        
        result = self.handler.embed(
            file_path=self.test_ods_path,
            watermark=watermark,
            output_path=output_path
        )
        
        self.assertTrue(result.is_success, f"ODS embed failed: {result.message}")
        self.assertTrue(os.path.exists(output_path), "Output ODS file not created")
    
    def test_extract_success(self):
        """测试ODS水印提取成功"""
        embed_output = os.path.join(self.temp_dir, 'test_extract.ods')
        watermark = WatermarkData(content='ODSExtract-2026')
        
        # 先嵌入
        embed_result = self.handler.embed(self.test_ods_path, watermark, embed_output)
        self.assertTrue(embed_result.is_success, f"ODS embed failed: {embed_result.message}")
        
        # 再提取
        extract_result = self.handler.extract(embed_output)
        self.assertTrue(extract_result.is_success, f"ODS extract failed: {extract_result.message}")
        self.assertEqual(extract_result.watermark.content, 'ODSExtract-2026', "Extracted content mismatch")
    
    def test_verify_success(self):
        """测试ODS水印验证成功"""
        output_path = os.path.join(self.temp_dir, 'test_verify.ods')
        watermark = WatermarkData(content='ODSVerify-2026')
        
        # 嵌入
        embed_result = self.handler.embed(self.test_ods_path, watermark, output_path)
        self.assertTrue(embed_result.is_success)
        
        # 验证
        verify_result = self.handler.verify(output_path, watermark)
        self.assertTrue(verify_result.is_valid, f"ODS verify failed: {verify_result.message}")
        self.assertEqual(verify_result.status, 'success')

if __name__ == '__main__':
    unittest.main()
