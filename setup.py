# setup.py
"""
StealthMark 安装配置
"""

from setuptools import setup, find_packages
from pathlib import Path

# 读取 README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding='utf-8') if readme_file.exists() else ""

setup(
    name="stealthmark",
    version="0.1.0",
    author="StealthMark Team",
    author_email="contact@stealthmark.dev",
    description="隐式水印工具 - 为文档、图片、音视频添加隐藏水印",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/stealthmark/stealthmark",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Legal Industry",
        "Topic :: Security",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "cryptography>=41.0.0",
        "PyPDF2>=3.0.0",
        "python-docx>=0.8.11",
        "python-pptx>=0.6.21",
        "Pillow>=10.0.0",
        "opencv-python>=4.8.0",
        "librosa>=0.10.0",
        "soundfile>=0.12.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "flake8>=6.0.0",
            "black>=23.0.0",
            "mypy>=1.5.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "stealthmark=cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)