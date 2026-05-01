import unittest
import os
import tempfile
from stealthmark.image.image_watermark import PNGHandler
from stealthmark.core.base import WatermarkData, WatermarkStatus

class TestImageHandler(unittest.TestCase):
    def setUp(self):
        self.handler = PNGHandler(config={'password': 'test_secret'})
        self.test_image_path = r'tests\fixtures\test.png'
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
    
    def test_embed_success(self):
        """Test PNG watermark embed"""
        output_path = os.path.join(self.temp_dir, 'test_embed.png')
        watermark = WatermarkData(content='ImageTest-2026')
        
        result = self.handler.embed(
            file_path=self.test_image_path,
            watermark=watermark,
            output_path=output_path
        )
        
        self.assertTrue(result.is_success, f"Image embed failed: {result.message}")
        self.assertTrue(os.path.exists(output_path), "Output image file not created")
    
    def test_extract_success(self):
        """Test PNG watermark extract"""
        embed_output = os.path.join(self.temp_dir, 'test_extract.png')
        watermark = WatermarkData(content='ImageExtract-2026')
        
        # embed first
        embed_result = self.handler.embed(self.test_image_path, watermark, embed_output)
        self.assertTrue(embed_result.is_success, f"Image embed failed: {embed_result.message}")
        
        # then extract
        extract_result = self.handler.extract(embed_output)
        self.assertTrue(extract_result.is_success, f"Image extract failed: {extract_result.message}")
        self.assertEqual(extract_result.watermark.content, 'ImageExtract-2026', "Extracted content mismatch")
    
    def test_verify_success(self):
        """Test PNG watermark verify"""
        output_path = os.path.join(self.temp_dir, 'test_verify.png')
        watermark = WatermarkData(content='ImageVerify-2026')
        
        # embed
        embed_result = self.handler.embed(self.test_image_path, watermark, output_path)
        self.assertTrue(embed_result.is_success)
        
        # verify
        verify_result = self.handler.verify(output_path, watermark)
        self.assertTrue(verify_result.is_valid, f"Image verify failed: {verify_result.message}")
        self.assertEqual(verify_result.status, WatermarkStatus.SUCCESS)

if __name__ == '__main__':
    unittest.main()
