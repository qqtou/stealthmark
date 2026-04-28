# stealthmark/__main__.py
"""
StealthMark 命令行入口

Usage:
    python -m stealthmark embed <input> <watermark> <output>
    python -m stealthmark extract <file>
    python -m stealthmark verify <file> <watermark>
"""

import sys
import argparse
from pathlib import Path

from src.core.manager import StealthMark


def cmd_embed(args):
    """嵌入水印"""
    wm = StealthMark()
    result = wm.embed(
        args.input,
        args.watermark,  # 直接传字符串
        args.output
    )
    print(f"嵌入{result.status.value}: {result.message}")
    return 0 if result.is_success else 1


def cmd_extract(args):
    """提取水印"""
    wm = StealthMark()
    result = wm.extract(args.file)
    print(f"提取{result.status.value}: {result.message}")
    if result.watermark:
        print(f"水印内容: {result.watermark.content}")
    return 0 if result.is_success else 1


def cmd_verify(args):
    """验证水印"""
    wm = StealthMark()
    result = wm.verify(args.file, args.watermark)  # 直接传字符串
    print(f"验证{result.status.value}: {result.message}")
    if result.is_valid:
        print("✓ 水印匹配")
    else:
        print("✗ 水印不匹配")
    return 0 if result.is_valid else 1


def main():
    parser = argparse.ArgumentParser(description="StealthMark 隐形水印工具")
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # embed
    embed_parser = subparsers.add_parser("embed", help="嵌入水印")
    embed_parser.add_argument("input", help="输入文件")
    embed_parser.add_argument("watermark", help="水印内容")
    embed_parser.add_argument("output", help="输出文件")
    
    # extract
    extract_parser = subparsers.add_parser("extract", help="提取水印")
    extract_parser.add_argument("file", help="文件名")
    
    # verify
    verify_parser = subparsers.add_parser("verify", help="验证水印")
    verify_parser.add_argument("file", help="文件名")
    verify_parser.add_argument("watermark", help="原始水印内容")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    commands = {
        "embed": cmd_embed,
        "extract": cmd_extract,
        "verify": cmd_verify
    }
    
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())