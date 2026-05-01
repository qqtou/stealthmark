# stealthmark/__main__.py
"""
StealthMark 命令行入口

Usage:
    python -m stealthmark embed <input> <watermark> -o <output>
    python -m stealthmark extract <file>
    python -m stealthmark verify <file> <watermark>
    python -m stealthmark info
    python -m stealthmark batch embed <dir> --watermark <text>
"""

import sys
from .cli import main

if __name__ == '__main__':
    sys.exit(main())
