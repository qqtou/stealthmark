#!/usr/bin/env python3
"""StealthMark 边界测试 - Edge Cases"""

import os
import tempfile
import unittest
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(r"D:\work\code\stealthmark")
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"

# 添加项目路径到 sys.path
import sys
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from stealthmark import StealthMark
from stealthmark.core.base import WatermarkStatus
from stealthmark.core.exceptions import StealthMarkError


class TestBoundaryConditions(unittest.TestCase):
    """边界条件测试"""

    @classmethod
    def setUpClass(cls):
        cls.stm = StealthMark()
        cls.fixtures_dir = FIXTURES_DIR

    def test_empty_watermark(self):
        """1. 空水印"""
        test_file = self.fixtures_dir / "test.png"
        if not test_file.exists():
            self.skipTest("test.png not found")
        
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            out_path = tmp.name
        
        try:
            # 空水印应该能嵌入
            result = self.stm.embed(
                file_path=str(test_file),
                watermark="",
                output_path=out_path
            )
            self.assertEqual(result.status, WatermarkStatus.SUCCESS)
        finally:
            if os.path.exists(out_path):
                os.unlink(out_path)

    def test_very_long_watermark(self):
        """2. 超长水印（超过容量）"""
        test_file = self.fixtures_dir / "test.png"
        if not test_file.exists():
            self.skipTest("test.png not found")
        
        # 生成超长水印（10000 字符）
        long_watermark = "A" * 10000
        
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            out_path = tmp.name
        
        try:
            result = self.stm.embed(
                file_path=str(test_file),
                watermark=long_watermark,
                output_path=out_path
            )
            # 预期：可能失败（超过容量）或成功（取决于格式）
            self.assertIn(result.status, [WatermarkStatus.SUCCESS, WatermarkStatus.FAILED])
        finally:
            if os.path.exists(out_path):
                os.unlink(out_path)

    def test_special_characters_watermark(self):
        """3. 特殊字符 Unicode"""
        test_file = self.fixtures_dir / "test.png"
        if not test_file.exists():
            self.skipTest("test.png not found")
        
        # Unicode 特殊字符
        special_watermarks = [
            "你好世界",
            "🎉 emoji test",
            "日本語",
            "العربية",
            "ΔΟΚΙΜΗ",
            "\u0000\u200b\u200c",  # 零宽字符
        ]
        
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            out_path = tmp.name
        
        try:
            for wm in special_watermarks:
                result = self.stm.embed(
                    file_path=str(test_file),
                    watermark=wm,
                    output_path=out_path
                )
                self.assertEqual(result.status, WatermarkStatus.SUCCESS, f"Failed: {wm}")
        finally:
            if os.path.exists(out_path):
                os.unlink(out_path)

    def test_corrupted_file(self):
        """4. 损坏文件"""
        # 创建一个损坏的 PNG
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            corrupt_path = tmp.name
        
        try:
            # 写入无效数据
            with open(corrupt_path, "wb") as f:
                f.write(b"This is not a valid image file\x00\x01\x02")
            
            result = self.stm.extract(file_path=corrupt_path)
            # 预期失败
            self.assertIn(result.status, [
                WatermarkStatus.FILE_CORRUPTED,
                WatermarkStatus.EXTRACTION_FAILED,
                WatermarkStatus.FAILED
            ])
        finally:
            if os.path.exists(corrupt_path):
                os.unlink(corrupt_path)

    def test_file_not_found(self):
        """5. 文件不存在"""
        result = self.stm.extract(file_path="nonexistent_file_12345.png")
        self.assertEqual(result.status, WatermarkStatus.FILE_NOT_FOUND)

    def test_wrong_password(self):
        """6. 密码错误（解密失败）"""
        test_file = self.fixtures_dir / "test.pdf"
        if not test_file.exists():
            test_file = self.fixtures_dir / "test.docx"
        if not test_file.exists():
            self.skipTest("test.pdf or test.docx not found")
        
        # 先用密码嵌入
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            embedded_path = tmp.name
        
        try:
            result = self.stm.embed(
                file_path=str(test_file),
                watermark="secret",
                password="correct_password",
                output_path=embedded_path
            )
            if result.status != WatermarkStatus.SUCCESS:
                self.skipTest(f"Embed with password not supported: {result.status}")
            
            # 用错误密码提取
            result = self.stm.extract(
                file_path=embedded_path,
                password="wrong_password"
            )
            # 预期解密失败（password错误导致AES解密padding错误，返回EXTRACTION_FAILED）
            self.assertIn(result.status, [
                WatermarkStatus.DECRYPTION_FAILED,
                WatermarkStatus.EXTRACTION_FAILED,
                WatermarkStatus.FAILED
            ])
        finally:
            if os.path.exists(embedded_path):
                os.unlink(embedded_path)

    def test_unsupported_format(self):
        """7. 不支持格式"""
        test_file = self.fixtures_dir / "test.xyz"
        if not test_file.exists():
            self.skipTest("test.xyz not found")
        
        result = self.stm.extract(file_path=str(test_file))
        self.assertEqual(result.status, WatermarkStatus.UNSUPPORTED_FORMAT)


if __name__ == "__main__":
    unittest.main(verbosity=2)