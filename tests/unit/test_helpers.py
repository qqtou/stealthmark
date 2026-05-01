# tests/unit/test_helpers.py
"""Unit tests for stealthmark.utils.helpers"""

import unittest
import os
import tempfile

from stealthmark.utils.helpers import (
    calculate_file_hash,
    ensure_dir,
    get_file_size,
    list_files,
    safe_filename
)


class TestCalculateFileHash(unittest.TestCase):
    """File hash calculation tests"""

    def test_sha256(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"hello world")
            temp_path = f.name
        try:
            hash_value = calculate_file_hash(temp_path, 'sha256')
            self.assertEqual(hash_value, "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9")
        finally:
            os.unlink(temp_path)

    def test_md5(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"hello world")
            temp_path = f.name
        try:
            hash_value = calculate_file_hash(temp_path, 'md5')
            self.assertEqual(hash_value, "5eb63bbbe01eeed093cb22bb8f5acdc3")
        finally:
            os.unlink(temp_path)

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name
        try:
            hash_value = calculate_file_hash(temp_path)
            self.assertEqual(len(hash_value), 64)
        finally:
            os.unlink(temp_path)


class TestEnsureDir(unittest.TestCase):
    """Directory creation tests"""

    def test_create_new_directory(self):
        import shutil
        temp_dir = tempfile.mkdtemp()
        new_dir = os.path.join(temp_dir, "test", "nested", "dir")
        try:
            ensure_dir(new_dir)
            self.assertTrue(os.path.exists(new_dir))
            self.assertTrue(os.path.isdir(new_dir))
        finally:
            shutil.rmtree(temp_dir)

    def test_existing_directory(self):
        temp_dir = tempfile.mkdtemp()
        ensure_dir(temp_dir)
        self.assertTrue(os.path.exists(temp_dir))


class TestGetFileSize(unittest.TestCase):
    """File size tests"""

    def test_file_size(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"1234567890")
            temp_path = f.name
        try:
            size = get_file_size(temp_path)
            self.assertEqual(size, 10)
        finally:
            os.unlink(temp_path)


class TestListFiles(unittest.TestCase):
    """File listing tests"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_list_all_files(self):
        for i in range(3):
            with open(os.path.join(self.temp_dir, f"file{i}.txt"), 'w') as f:
                f.write("test")
        files = list_files(self.temp_dir)
        self.assertGreaterEqual(len(files), 3)

    def test_filter_by_extension(self):
        open(os.path.join(self.temp_dir, "doc.pdf"), 'w').close()
        open(os.path.join(self.temp_dir, "doc.docx"), 'w').close()
        open(os.path.join(self.temp_dir, "doc.txt"), 'w').close()
        pdf_files = list_files(self.temp_dir, ['.pdf'])
        self.assertEqual(len(pdf_files), 1)
        self.assertTrue(pdf_files[0].endswith('.pdf'))

    def test_empty_directory(self):
        files = list_files(self.temp_dir)
        self.assertEqual(len(files), 0)


class TestSafeFilename(unittest.TestCase):
    """Safe filename tests"""

    def test_normal_filename(self):
        self.assertEqual(safe_filename("document.pdf"), "document.pdf")

    def test_filenames_with_invalid_chars(self):
        self.assertEqual(safe_filename("file<>name.pdf"), "file__name.pdf")
        self.assertEqual(safe_filename('file:name.pdf'), "file_name.pdf")
        self.assertEqual(safe_filename("file|name.pdf"), "file_name.pdf")
        self.assertEqual(safe_filename('file*name.pdf'), "file_name.pdf")
        self.assertEqual(safe_filename("file?name.pdf"), "file_name.pdf")

    def test_multiple_invalid_chars(self):
        result = safe_filename('file<>:"\\|?*.pdf')
        for c in '<>:"|?*':
            self.assertNotIn(c, result)


if __name__ == '__main__':
    unittest.main()
