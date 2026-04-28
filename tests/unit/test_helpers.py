# tests/test_helpers.py
"""
辅助工具函数测试
"""

import pytest
import os
import tempfile
from pathlib import Path

from src.utils.helpers import (
    calculate_file_hash,
    ensure_dir,
    get_file_size,
    list_files,
    safe_filename
)


class TestCalculateFileHash:
    """文件哈希计算测试"""
    
    def test_sha256(self):
        """测试SHA256"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"hello world")
            temp_path = f.name
        
        try:
            hash_value = calculate_file_hash(temp_path, 'sha256')
            assert hash_value == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
        finally:
            os.unlink(temp_path)
    
    def test_md5(self):
        """测试MD5"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"hello world")
            temp_path = f.name
        
        try:
            hash_value = calculate_file_hash(temp_path, 'md5')
            assert hash_value == "5eb63bbbe01eeed093cb22bb8f5acdc3"
        finally:
            os.unlink(temp_path)
    
    def test_empty_file(self):
        """测试空文件"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name
        
        try:
            hash_value = calculate_file_hash(temp_path)
            assert len(hash_value) == 64  # SHA256 length
        finally:
            os.unlink(temp_path)


class TestEnsureDir:
    """目录创建测试"""
    
    def test_create_new_directory(self):
        """测试创建新目录"""
        temp_dir = tempfile.mkdtemp()
        new_dir = os.path.join(temp_dir, "test", "nested", "dir")
        
        ensure_dir(new_dir)
        assert os.path.exists(new_dir)
        assert os.path.isdir(new_dir)
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)
    
    def test_existing_directory(self):
        """测试已存在目录"""
        temp_dir = tempfile.mkdtemp()
        ensure_dir(temp_dir)
        assert os.path.exists(temp_dir)


class TestGetFileSize:
    """文件大小测试"""
    
    def test_file_size(self):
        """测试获取文件大小"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            content = b"1234567890"
            f.write(content)
            temp_path = f.name
        
        try:
            size = get_file_size(temp_path)
            assert size == 10
        finally:
            os.unlink(temp_path)


class TestListFiles:
    """文件列表测试"""
    
    def setup_method(self):
        """创建测试目录"""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """清理测试目录"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_list_all_files(self):
        """测试列出所有文件"""
        # 创建测试文件
        for i in range(3):
            with open(os.path.join(self.temp_dir, f"file{i}.txt"), 'w') as f:
                f.write("test")
        
        files = list_files(self.temp_dir)
        assert len(files) >= 3
    
    def test_filter_by_extension(self):
        """测试按扩展名过滤"""
        # 创建不同类型的文件
        open(os.path.join(self.temp_dir, "doc.pdf"), 'w').close()
        open(os.path.join(self.temp_dir, "doc.docx"), 'w').close()
        open(os.path.join(self.temp_dir, "doc.txt"), 'w').close()
        
        pdf_files = list_files(self.temp_dir, ['.pdf'])
        assert len(pdf_files) == 1
        assert pdf_files[0].endswith('.pdf')
    
    def test_empty_directory(self):
        """测试空目录"""
        files = list_files(self.temp_dir)
        assert len(files) == 0


class TestSafeFilename:
    """安全文件名测试"""
    
    def test_normal_filename(self):
        """测试正常文件名"""
        assert safe_filename("document.pdf") == "document.pdf"
    
    def test_filenames_with_invalid_chars(self):
        """测试含非法字符的文件名"""
        assert safe_filename("file<>name.pdf") == "file__name.pdf"
        assert safe_filename('file:name.pdf') == "file_name.pdf"
        assert safe_filename("file|name.pdf") == "file_name.pdf"
        assert safe_filename('file*name.pdf') == "file_name.pdf"
        assert safe_filename("file?name.pdf") == "file_name.pdf"
    
    def test_multiple_invalid_chars(self):
        """测试多个非法字符"""
        result = safe_filename('file<>:"\\|?*.pdf')
        assert all(c not in result for c in '<>:"|?*')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])