# tests/unit/test_codec.py
"""Unit tests for stealthmark.core.codec"""

import unittest
from stealthmark.core.codec import WatermarkCodec


class TestWatermarkCodec(unittest.TestCase):
    """WatermarkCodec tests"""

    def setUp(self):
        self.codec = WatermarkCodec()

    def test_encode_basic(self):
        content = "test watermark content"
        encoded = self.codec.encode(content)
        self.assertIsNotNone(encoded)
        self.assertGreater(len(encoded), 0)
        self.assertEqual(encoded[:5], b"SMARK")

    def test_decode_basic(self):
        content = "test watermark content"
        encoded = self.codec.encode(content)
        success, decoded, details = self.codec.decode(encoded)
        self.assertTrue(success)
        self.assertEqual(decoded, content)

    def test_encode_decode_empty(self):
        content = ""
        encoded = self.codec.encode(content)
        success, decoded, _ = self.codec.decode(encoded)
        self.assertTrue(success)
        self.assertEqual(decoded, "")

    def test_encode_decode_long_text(self):
        content = "A" * 1000
        encoded = self.codec.encode(content)
        success, decoded, _ = self.codec.decode(encoded)
        self.assertTrue(success)
        self.assertEqual(decoded, content)

    def test_encode_decode_special_chars(self):
        content = "test\r\n\t!@#$%^&*()_+-=[]{}|;':\",./<>?"
        encoded = self.codec.encode(content)
        success, decoded, _ = self.codec.decode(encoded)
        self.assertTrue(success)
        self.assertEqual(decoded, content)

    def test_encode_decode_with_password(self):
        codec = WatermarkCodec(password="test123")
        content = "encrypted watermark"
        encoded = codec.encode(content)
        success, decoded, _ = codec.decode(encoded)
        self.assertTrue(success)
        self.assertEqual(decoded, content)

    def test_hex_conversion(self):
        data = b"hello world"
        hex_str = WatermarkCodec.to_hex(data)
        decoded = WatermarkCodec.from_hex(hex_str)
        self.assertEqual(decoded, data)
        self.assertEqual(hex_str, "68656c6c6f20776f726c64")

    def test_base64_conversion(self):
        data = b"hello world"
        b64_str = WatermarkCodec.to_base64(data)
        decoded = WatermarkCodec.from_base64(b64_str)
        self.assertEqual(decoded, data)

    def test_crc_validation(self):
        content = "CRC test"
        encoded = self.codec.encode(content)
        tampered = bytearray(encoded)
        tampered[15] ^= 0xFF
        tampered = bytes(tampered)
        success, _, details = self.codec.decode(tampered)
        self.assertFalse(success)
        self.assertIn('crc', details.get('error', '').lower())

    def test_invalid_magic(self):
        invalid_data = b"INVALID" + b"\x00" * 20
        success, _, _ = self.codec.decode(invalid_data)
        self.assertFalse(success)

    def test_multiple_encode(self):
        content = "consistency test"
        encoded1 = self.codec.encode(content)
        encoded2 = self.codec.encode(content)
        self.assertEqual(encoded1, encoded2)


if __name__ == '__main__':
    unittest.main()
