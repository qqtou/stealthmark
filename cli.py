# stealthmark/cli.py
"""
StealthMark 命令行接口
"""

import argparse
import sys
import logging
from pathlib import Path

from src.core.manager import StealthMark
from src.core.base import WatermarkStatus


def setup_logging(verbose: bool = False):
    """配置日志"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def cmd_embed(args):
    """嵌入水印命令"""
    wm = StealthMark(password=args.password)
    
    result = wm.embed(
        file_path=args.input,
        watermark=args.watermark,
        output_path=args.output
    )
    
    if result.is_success:
        print(f"[OK] 水印嵌入成功: {result.output_path}")
        return 0
    else:
        print(f"[FAIL] 嵌入失败: {result.message}", file=sys.stderr)
        return 1


def cmd_extract(args):
    """提取水印命令"""
    wm = StealthMark(password=args.password)
    
    result = wm.extract(file_path=args.file)
    
    if result.is_success:
        print(f"水印内容: {result.watermark.content}")
        return 0
    else:
        print(f"✗ 提取失败: {result.message}", file=sys.stderr)
        return 1


def cmd_verify(args):
    """验证水印命令"""
    wm = StealthMark(password=args.password)
    
    result = wm.verify(
        file_path=args.file,
        original_watermark=args.watermark
    )
    
    if result.is_valid:
        print(f"[OK] 验证通过")
        print(f"  一致性: {result.match_score * 100:.1f}%")
        return 0
    else:
        print(f"[FAIL] 验证失败")
        print(f"  原因: {result.message}")
        return 1


def cmd_info(args):
    """显示支持格式"""
    wm = StealthMark()
    formats = wm.supported_formats()
    
    print("支持的格式:")
    for fmt in formats:
        print(f"  - {fmt}")


def main():
    parser = argparse.ArgumentParser(
        description='StealthMark - 隐式水印工具',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='显示详细日志')
    parser.add_argument('-p', '--password', type=str, default=None,
                        help='水印加密密码')
    
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # embed 命令
    embed_parser = subparsers.add_parser('embed', help='嵌入水印')
    embed_parser.add_argument('input', help='输入文件路径')
    embed_parser.add_argument('watermark', help='水印文本')
    embed_parser.add_argument('-o', '--output', help='输出文件路径')
    embed_parser.set_defaults(func=cmd_embed)
    
    # extract 命令
    extract_parser = subparsers.add_parser('extract', help='提取水印')
    extract_parser.add_argument('file', help='含水印文件路径')
    extract_parser.set_defaults(func=cmd_extract)
    
    # verify 命令
    verify_parser = subparsers.add_parser('verify', help='验证水印')
    verify_parser.add_argument('file', help='含水印文件路径')
    verify_parser.add_argument('watermark', help='原始水印文本')
    verify_parser.set_defaults(func=cmd_verify)
    
    # info 命令
    info_parser = subparsers.add_parser('info', help='显示支持格式')
    info_parser.set_defaults(func=cmd_info)
    
    args = parser.parse_args()
    
    setup_logging(args.verbose if hasattr(args, 'verbose') else False)
    
    if args.command is None:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())