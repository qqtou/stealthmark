# tests/unit/test_exceptions.py
"""Unit tests for stealthmark.core.exceptions"""

import unittest
from stealthmark.core.exceptions import (
    StealthMarkError,
    FileNotFoundError,
    UnsupportedFormatError,
    EmbedError,
    ExtractError,
    VerifyError,
    CodecError,
    EncryptionError
)


class TestExceptions(unittest.TestCase):
    """Exception class tests"""

    def test_stealthmark_error(self):
        error = StealthMarkError("base error")
        self.assertEqual(str(error), "base error")

    def test_file_not_found_error(self):
        error = FileNotFoundError("file not found")
        self.assertIsInstance(error, StealthMarkError)
        self.assertEqual(str(error), "file not found")

    def test_unsupported_format_error(self):
        error = UnsupportedFormatError("unsupported format")
        self.assertIsInstance(error, StealthMarkError)

    def test_embed_error(self):
        error = EmbedError("embed failed")
        self.assertIsInstance(error, StealthMarkError)

    def test_extract_error(self):
        error = ExtractError("extract failed")
        self.assertIsInstance(error, StealthMarkError)

    def test_verify_error(self):
        error = VerifyError("verify failed")
        self.assertIsInstance(error, StealthMarkError)

    def test_codec_error(self):
        error = CodecError("codec error")
        self.assertIsInstance(error, StealthMarkError)

    def test_encryption_error(self):
        error = EncryptionError("encryption failed")
        self.assertIsInstance(error, StealthMarkError)

    def test_exception_hierarchy(self):
        errors = [
            FileNotFoundError,
            UnsupportedFormatError,
            EmbedError,
            ExtractError,
            VerifyError,
            CodecError,
            EncryptionError
        ]
        for error_class in errors:
            error = error_class("test")
            self.assertIsInstance(error, Exception)
            self.assertIsInstance(error, StealthMarkError)


if __name__ == '__main__':
    unittest.main()
