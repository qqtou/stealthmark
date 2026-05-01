# tests/unit/test_manager.py
"""Unit tests for stealthmark.core.manager"""

import unittest
from stealthmark.core.manager import StealthMark
from stealthmark.core.base import WatermarkStatus


class TestStealthMark(unittest.TestCase):
    """StealthMark manager tests"""

    def setUp(self):
        self.wm = StealthMark()

    def test_init_basic(self):
        wm = StealthMark()
        self.assertIsNotNone(wm.codec)

    def test_init_with_password(self):
        wm = StealthMark(password="test123")
        self.assertEqual(wm.password, "test123")

    def test_handler_registration(self):
        self.assertGreater(len(self.wm._handler_registry), 0)

    def test_supported_formats(self):
        formats = self.wm.supported_formats()
        expected = ['.pdf', '.docx', '.pptx', '.png', '.jpg',
                    '.jpeg', '.bmp', '.wav', '.mp3', '.mp4',
                    '.avi', '.mkv', '.mov']
        for fmt in expected:
            self.assertIn(fmt, formats)

    def test_is_supported_pdf(self):
        self.assertTrue(self.wm.is_supported("test.pdf"))
        self.assertTrue(self.wm.is_supported("test.PDF"))

    def test_is_supported_unsupported(self):
        self.assertFalse(self.wm.is_supported("test.xyz"))
        self.assertFalse(self.wm.is_supported("test"))

    def test_embed_file_not_found(self):
        result = self.wm.embed("nonexistent.pdf", "watermark")
        self.assertFalse(result.is_success)
        self.assertEqual(result.status, WatermarkStatus.FILE_NOT_FOUND)

    def test_extract_unsupported_format(self):
        result = self.wm.extract("test.xyz")
        self.assertFalse(result.is_success)
        self.assertEqual(result.status, WatermarkStatus.UNSUPPORTED_FORMAT)

    def test_verify_nonexistent_file(self):
        result = self.wm.verify("nonexistent.pdf", "watermark")
        self.assertFalse(result.is_valid)

    def test_register_handler(self):
        from stealthmark.core.base import BaseHandler, EmbedResult, ExtractResult, VerifyResult, WatermarkData

        class CustomHandler(BaseHandler):
            SUPPORTED_EXTENSIONS = ('.custom',)
            HANDLER_NAME = "custom"

            def embed(self, file_path, watermark, output_path, **kwargs):
                return EmbedResult(status=WatermarkStatus.SUCCESS)

            def extract(self, file_path, **kwargs):
                return ExtractResult(
                    status=WatermarkStatus.SUCCESS,
                    watermark=WatermarkData(content="custom")
                )

            def verify(self, file_path, original_watermark, **kwargs):
                return VerifyResult(
                    status=WatermarkStatus.SUCCESS,
                    is_valid=True,
                    is_integrity_ok=True,
                    match_score=1.0
                )

        initial_count = len(self.wm._handler_registry)
        self.wm.register_handler(CustomHandler)
        self.assertEqual(len(self.wm._handler_registry), initial_count + 1)
        self.assertTrue(self.wm.is_supported("test.custom"))

    def test_multiple_formats(self):
        formats = self.wm.supported_formats()
        self.assertIn('.pdf', formats)
        self.assertIn('.docx', formats)
        self.assertIn('.png', formats)
        self.assertIn('.mp4', formats)


class TestSimulatedWorkflow(unittest.TestCase):
    """Simulated workflow tests (no real files)"""

    def setUp(self):
        self.wm = StealthMark()

    def test_manager_structure(self):
        self.assertTrue(hasattr(self.wm, 'codec'))
        self.assertTrue(hasattr(self.wm, '_handlers'))
        self.assertTrue(hasattr(self.wm, '_handler_registry'))
        self.assertTrue(hasattr(self.wm, 'embed'))
        self.assertTrue(hasattr(self.wm, 'extract'))
        self.assertTrue(hasattr(self.wm, 'verify'))

    def test_handlers_initialized(self):
        self.assertGreater(len(self.wm._handlers), 0)
        for ext, handler in self.wm._handlers.items():
            self.assertIsNotNone(handler)
            self.assertTrue(hasattr(handler, 'embed'))
            self.assertTrue(hasattr(handler, 'extract'))
            self.assertTrue(hasattr(handler, 'verify'))


if __name__ == '__main__':
    unittest.main()
