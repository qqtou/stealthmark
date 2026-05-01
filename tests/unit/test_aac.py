import unittest
import os
import tempfile
from stealthmark.media.aac_handler import AACHandler
from stealthmark.core.base import WatermarkData, WatermarkStatus

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
        """Test AAC watermark embed (outputs .m4a)"""
        output_path = os.path.join(self.temp_dir, 'test_embed.aac')
        watermark = WatermarkData(content='AACTest-2026')
        
        result = self.handler.embed(
            file_path=self.test_aac_path,
            watermark=watermark,
            output_path=output_path
        )
        
        self.assertTrue(result.is_success, f"AAC embed failed: {result.message}")
        # AAC handler outputs .m4a (ALAC needs M4A container)
        actual_output = result.output_path
        self.assertTrue(os.path.exists(actual_output), f"Output file not created: {actual_output}")
    
    def test_extract_success(self):
        """Test AAC watermark extract"""
        embed_output = os.path.join(self.temp_dir, 'test_extract.aac')
        watermark = WatermarkData(content='AACExtract-2026')
        
        # embed first
        embed_result = self.handler.embed(self.test_aac_path, watermark, embed_output)
        self.assertTrue(embed_result.is_success, f"AAC embed failed: {embed_result.message}")
        
        # extract from actual output path (.m4a)
        actual_output = embed_result.output_path
        extract_result = self.handler.extract(actual_output)
        self.assertTrue(extract_result.is_success, f"AAC extract failed: {extract_result.message}")
        self.assertEqual(extract_result.watermark.content, 'AACExtract-2026', "Extracted content mismatch")
    
    def test_verify_success(self):
        """Test AAC watermark verify"""
        output_path = os.path.join(self.temp_dir, 'test_verify.aac')
        watermark = WatermarkData(content='AACVerify-2026')
        
        # embed
        embed_result = self.handler.embed(self.test_aac_path, watermark, output_path)
        self.assertTrue(embed_result.is_success)
        
        # verify from actual output path
        actual_output = embed_result.output_path
        verify_result = self.handler.verify(actual_output, watermark)
        self.assertTrue(verify_result.is_valid, f"AAC verify failed: {verify_result.message}")
        self.assertEqual(verify_result.status, WatermarkStatus.SUCCESS)

if __name__ == '__main__':
    unittest.main()
