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
from pathlib import Path

# 将项目 src 目录加入 path
_src = str(Path(__file__).resolve().parent.parent / 'src')
if _src not in sys.path:
    sys.path.insert(0, _src)

# 复用根目录 cli.py 的完整实现
_project_root = str(Path(__file__).resolve().parent.parent)
_cli_path = Path(_project_root) / 'cli.py'

if _cli_path.exists():
    import importlib.util
    spec = importlib.util.spec_from_file_location("stealthmark_cli", str(_cli_path))
    cli_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli_mod)
    sys.exit(cli_mod.main())
else:
    # fallback: 简化 CLI
    from src.core.manager import StealthMark
    import argparse

    def main():
        parser = argparse.ArgumentParser(description="StealthMark 隐形水印工具")
        subparsers = parser.add_subparsers(dest="command")

        embed_p = subparsers.add_parser("embed")
        embed_p.add_argument("input")
        embed_p.add_argument("watermark")
        embed_p.add_argument("-o", "--output")

        extract_p = subparsers.add_parser("extract")
        extract_p.add_argument("file")

        verify_p = subparsers.add_parser("verify")
        verify_p.add_argument("file")
        verify_p.add_argument("watermark")

        args = parser.parse_args()
        if not args.command:
            parser.print_help()
            return 1

        wm = StealthMark()
        if args.command == "embed":
            r = wm.embed(args.input, args.watermark, args.output)
            print(f"{'OK' if r.is_success else 'FAIL'}: {r.message}")
            return 0 if r.is_success else 1
        elif args.command == "extract":
            r = wm.extract(args.file)
            print(f"{'OK' if r.is_success else 'FAIL'}: {r.message}")
            if r.watermark:
                print(f"Watermark: {r.watermark.content}")
            return 0 if r.is_success else 1
        elif args.command == "verify":
            r = wm.verify(args.file, args.watermark)
            print(f"{'PASS' if r.is_valid else 'FAIL'}: {r.message}")
            return 0 if r.is_valid else 1

    sys.exit(main())
