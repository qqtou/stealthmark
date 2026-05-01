# tests/unit/test_base.py
"""Unit tests for stealthmark.core.base"""

import unittest
from stealthmark.core.base import (
    WatermarkData, WatermarkStatus, WatermarkType,
    EmbedResult, ExtractResult, VerifyResult, BaseHandler
)


class TestWatermarkData(unittest.TestCase):
    """WatermarkData tests"""

    def test_create_basic(self):
        data = WatermarkData(content="test")
        self.assertEqual(data.content, "test")
        self.assertEqual(data.watermark_type, WatermarkType.TEXT)
        self.assertIsNotNone(data.created_at)
        self.assertEqual(data.metadata, {})

    def test_create_with_metadata(self):
        data = WatermarkData(
            content="test",
            watermark_type=WatermarkType.IMAGE,
            metadata={"author": "alice"}
        )
        self.assertEqual(data.watermark_type, WatermarkType.IMAGE)
        self.assertEqual(data.metadata["author"], "alice")

    def test_auto_created_at(self):
        import time
        before = WatermarkData(content="test")
        time.sleep(0.01)
        after = WatermarkData(content="test")
        self.assertLessEqual(before.created_at, after.created_at)


class TestWatermarkStatus(unittest.TestCase):
    """WatermarkStatus tests"""

    def test_all_status_values(self):
        statuses = [
            WatermarkStatus.SUCCESS,
            WatermarkStatus.FAILED,
            WatermarkStatus.FILE_NOT_FOUND,
            WatermarkStatus.FILE_CORRUPTED,
            WatermarkStatus.UNSUPPORTED_FORMAT,
            WatermarkStatus.INVALID_WATERMARK,
            WatermarkStatus.EXTRACTION_FAILED,
            WatermarkStatus.VERIFICATION_FAILED,
            WatermarkStatus.ENCRYPTION_FAILED,
            WatermarkStatus.DECRYPTION_FAILED,
        ]
        self.assertEqual(len(statuses), 10)

    def test_status_values_unique(self):
        values = [s.value for s in WatermarkStatus]
        self.assertEqual(len(values), len(set(values)))


class TestOperationResults(unittest.TestCase):
    """Operation result tests"""

    def test_embed_result_success(self):
        result = EmbedResult(
            status=WatermarkStatus.SUCCESS,
            message="OK",
            file_path="test.pdf",
            output_path="output.pdf"
        )
        self.assertTrue(result.is_success)
        self.assertEqual(result.status, WatermarkStatus.SUCCESS)

    def test_embed_result_failure(self):
        result = EmbedResult(
            status=WatermarkStatus.FILE_NOT_FOUND,
            message="File not found"
        )
        self.assertFalse(result.is_success)

    def test_extract_result_success(self):
        watermark = WatermarkData(content="extracted")
        result = ExtractResult(
            status=WatermarkStatus.SUCCESS,
            message="OK",
            file_path="test.pdf",
            watermark=watermark
        )
        self.assertTrue(result.is_success)
        self.assertEqual(result.watermark.content, "extracted")

    def test_verify_result_valid(self):
        result = VerifyResult(
            status=WatermarkStatus.SUCCESS,
            is_valid=True,
            is_integrity_ok=True,
            match_score=1.0,
            message="OK"
        )
        self.assertTrue(result.is_valid)
        self.assertEqual(result.match_score, 1.0)

    def test_verify_result_invalid(self):
        result = VerifyResult(
            status=WatermarkStatus.VERIFICATION_FAILED,
            is_valid=False,
            is_integrity_ok=False,
            match_score=0.0,
            message="Mismatch"
        )
        self.assertFalse(result.is_valid)
        self.assertEqual(result.match_score, 0.0)


class MockHandler(BaseHandler):
    """Mock handler for testing"""
    SUPPORTED_EXTENSIONS = ('.mock', '.test')
    HANDLER_NAME = "mock"

    def embed(self, file_path, watermark, output_path, **kwargs):
        return EmbedResult(status=WatermarkStatus.SUCCESS)

    def extract(self, file_path, **kwargs):
        return ExtractResult(
            status=WatermarkStatus.SUCCESS,
            watermark=WatermarkData(content="mock")
        )

    def verify(self, file_path, original_watermark, **kwargs):
        return VerifyResult(
            status=WatermarkStatus.SUCCESS,
            is_valid=True,
            is_integrity_ok=True,
            match_score=1.0
        )


class TestBaseHandler(unittest.TestCase):
    """BaseHandler tests"""

    def setUp(self):
        self.handler = MockHandler()

    def test_is_supported(self):
        self.assertTrue(self.handler.is_supported("test.mock"))
        self.assertTrue(self.handler.is_supported("test.test"))
        self.assertFalse(self.handler.is_supported("test.pdf"))
        self.assertFalse(self.handler.is_supported("test.xyz"))

    def test_handler_name(self):
        self.assertEqual(self.handler.HANDLER_NAME, "mock")

    def test_config(self):
        handler = MockHandler(config={"key": "value"})
        self.assertEqual(handler.config["key"], "value")


if __name__ == '__main__':
    unittest.main()
