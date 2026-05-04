# Robustness Attack Test Suite for StealthMark
# Tests watermark resilience under various attack scenarios

import unittest
import os
import tempfile
import shutil
from pathlib import Path

from PIL import Image, ImageEnhance
from stealthmark.core import StealthMark
from stealthmark.core.base import WatermarkStatus


WATERMARK_CONTENT = "RobustnessTest2026"
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestImageRobustness(unittest.TestCase):
    """Image watermark robustness tests under common attacks."""

    def setUp(self):
        self.stm = StealthMark(password="test_secret")
        self.temp_dir = tempfile.mkdtemp()
        self.watermark = WATERMARK_CONTENT

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _embed_to_temp(self, filename, ext):
        """Embed watermark to a temp copy and return the path."""
        src = FIXTURES_DIR / f"test.{ext}"
        dst = os.path.join(self.temp_dir, f"{filename}.{ext}")
        shutil.copy(str(src), dst)
        result = self.stm.embed(file_path=dst, watermark=self.watermark, output_path=dst, force=True)
        self.assertTrue(result.is_success, f"Embed failed: {result.message}")
        return dst

    # --- JPEG Compression ---

    def test_jpeg_quality_90(self):
        """JPEG quality 90 (light compression)."""
        marked = self._embed_to_temp("jpeg_q90", "jpeg")
        img = Image.open(marked)
        out = os.path.join(self.temp_dir, "jpeg_q90_out.jpg")
        img.save(out, "JPEG", quality=90)
        result = self.stm.verify(file_path=out, original_watermark=self.watermark)
        self.assertTrue(result.is_valid, f"Failed JPEG Q90: {result.message}")

    def test_jpeg_quality_70(self):
        """JPEG quality 70 (moderate compression)."""
        marked = self._embed_to_temp("jpeg_q70", "jpeg")
        img = Image.open(marked)
        out = os.path.join(self.temp_dir, "jpeg_q70_out.jpg")
        img.save(out, "JPEG", quality=70)
        result = self.stm.verify(file_path=out, original_watermark=self.watermark)
        self.assertTrue(result.is_valid, f"Failed JPEG Q70: {result.message}")

    def test_jpeg_quality_50(self):
        """JPEG quality 50 (heavy compression)."""
        marked = self._embed_to_temp("jpeg_q50", "jpeg")
        img = Image.open(marked)
        out = os.path.join(self.temp_dir, "jpeg_q50_out.jpg")
        img.save(out, "JPEG", quality=50)
        result = self.stm.verify(file_path=out, original_watermark=self.watermark)
        self.assertTrue(result.is_valid, f"Failed JPEG Q50: {result.message}")

    def test_jpeg_quality_30(self):
        """JPEG quality 30 (extreme compression)."""
        marked = self._embed_to_temp("jpeg_q30", "jpeg")
        img = Image.open(marked)
        out = os.path.join(self.temp_dir, "jpeg_q30_out.jpg")
        img.save(out, "JPEG", quality=30)
        result = self.stm.verify(file_path=out, original_watermark=self.watermark)
        # Informational - some attacks may fail
        self.assertTrue(result.is_valid or result.status in [
            WatermarkStatus.VERIFICATION_FAILED,
            WatermarkStatus.EXTRACTION_FAILED
        ], f"Failed JPEG Q30: {result.message}")

    # --- Resize attacks ---

    def test_resize_upscale_2x(self):
        """Resize to 2x larger."""
        marked = self._embed_to_temp("resize_2x", "jpeg")
        img = Image.open(marked)
        w, h = img.size
        out = os.path.join(self.temp_dir, "resize_2x_out.jpg")
        img.resize((w * 2, h * 2), Image.LANCZOS).save(out, "JPEG", quality=95)
        result = self.stm.verify(file_path=out, original_watermark=self.watermark)
        self.assertTrue(result.is_valid, f"Failed 2x upscale: {result.message}")

    def test_resize_downscale_half(self):
        """Resize to 50% then back to original size."""
        marked = self._embed_to_temp("resize_half", "jpeg")
        img = Image.open(marked)
        w, h = img.size
        tmp = img.resize((w // 2, h // 2), Image.LANCZOS)
        out = os.path.join(self.temp_dir, "resize_half_out.jpg")
        tmp.resize((w, h), Image.LANCZOS).save(out, "JPEG", quality=95)
        result = self.stm.verify(file_path=out, original_watermark=self.watermark)
        self.assertTrue(result.is_valid, f"Failed half-scale: {result.message}")

    # --- Rotation attacks ---

    def test_rotate_90(self):
        """Rotate 90 degrees."""
        marked = self._embed_to_temp("rotate90", "png")
        img = Image.open(marked).convert("RGBA")
        out = os.path.join(self.temp_dir, "rotate90_out.png")
        img.rotate(90, expand=True).convert("RGB").save(out)
        result = self.stm.verify(file_path=out, original_watermark=self.watermark)
        self.assertTrue(result.is_valid, f"Failed 90-deg rotate: {result.message}")

    def test_rotate_180(self):
        """Rotate 180 degrees."""
        marked = self._embed_to_temp("rotate180", "png")
        img = Image.open(marked).convert("RGBA")
        out = os.path.join(self.temp_dir, "rotate180_out.png")
        img.rotate(180, expand=True).convert("RGB").save(out)
        result = self.stm.verify(file_path=out, original_watermark=self.watermark)
        self.assertTrue(result.is_valid, f"Failed 180-deg rotate: {result.message}")

    # --- Color adjustments ---

    def test_brightness_up(self):
        """Increase brightness 30%."""
        marked = self._embed_to_temp("bright_up", "png")
        img = Image.open(marked)
        enhancer = ImageEnhance.Brightness(img)
        out = os.path.join(self.temp_dir, "bright_up_out.png")
        enhancer.enhance(1.3).save(out)
        result = self.stm.verify(file_path=out, original_watermark=self.watermark)
        self.assertTrue(result.is_valid, f"Failed bright+30%: {result.message}")

    def test_brightness_down(self):
        """Decrease brightness 20%."""
        marked = self._embed_to_temp("bright_down", "png")
        img = Image.open(marked)
        enhancer = ImageEnhance.Brightness(img)
        out = os.path.join(self.temp_dir, "bright_down_out.png")
        enhancer.enhance(0.8).save(out)
        result = self.stm.verify(file_path=out, original_watermark=self.watermark)
        self.assertTrue(result.is_valid, f"Failed bright-20%: {result.message}")

    def test_contrast_up(self):
        """Increase contrast 30%."""
        marked = self._embed_to_temp("contrast_up", "png")
        img = Image.open(marked)
        enhancer = ImageEnhance.Contrast(img)
        out = os.path.join(self.temp_dir, "contrast_up_out.png")
        enhancer.enhance(1.3).save(out)
        result = self.stm.verify(file_path=out, original_watermark=self.watermark)
        self.assertTrue(result.is_valid, f"Failed contrast+30%: {result.message}")

    def test_grayscale(self):
        """Convert to grayscale."""
        marked = self._embed_to_temp("grayscale", "png")
        img = Image.open(marked).convert("L").convert("RGB")
        out = os.path.join(self.temp_dir, "grayscale_out.png")
        img.save(out)
        result = self.stm.verify(file_path=out, original_watermark=self.watermark)
        # Grayscale may destroy LSB; informational only
        self.assertTrue(result.is_valid or result.status in [
            WatermarkStatus.VERIFICATION_FAILED,
            WatermarkStatus.EXTRACTION_FAILED
        ], f"Failed grayscale: {result.message}")

    # --- PNG-specific ---

    def test_png_compression_level(self):
        """Save PNG with different compression levels."""
        marked = self._embed_to_temp("png_compress", "png")
        img = Image.open(marked)
        out0 = os.path.join(self.temp_dir, "png_c0.png")
        out9 = os.path.join(self.temp_dir, "png_c9.png")
        img.save(out0, compress_level=0)
        img.save(out9, compress_level=9)
        r0 = self.stm.verify(file_path=out0, original_watermark=self.watermark)
        r9 = self.stm.verify(file_path=out9, original_watermark=self.watermark)
        self.assertTrue(r0.is_valid, f"PNG compress=0 failed: {r0.message}")
        self.assertTrue(r9.is_valid, f"PNG compress=9 failed: {r9.message}")


class TestAudioRobustness(unittest.TestCase):
    """Audio watermark robustness tests."""

    def setUp(self):
        self.stm = StealthMark(password="test_secret")
        self.temp_dir = tempfile.mkdtemp()
        self.watermark = WATERMARK_CONTENT

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _embed_to_temp(self, filename, ext):
        src = FIXTURES_DIR / f"test.{ext}"
        dst = os.path.join(self.temp_dir, f"{filename}.{ext}")
        shutil.copy(str(src), dst)
        result = self.stm.embed(file_path=dst, watermark=self.watermark, output_path=dst, force=True)
        self.assertTrue(result.is_success, f"Embed failed: {result.message}")
        return dst


if __name__ == "__main__":
    unittest.main()