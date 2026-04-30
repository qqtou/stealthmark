# stealthmark/cli.py
"""
StealthMark 命令行接口
Stage 1: CLI 增强 - 进度条 + 详细日志 + 更好的错误提示
"""

import argparse
import sys
import os
import logging
from pathlib import Path

from src.core.manager import StealthMark
from src.core.base import WatermarkStatus

# ==================== 日志与颜色 ====================

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    _HAS_COLORAMA = True
except ImportError:
    _HAS_COLORAMA = False

if not _HAS_COLORAMA:
    class _DummyColor:
        RESET = BRIGHT = DIM = RED = GREEN = YELLOW = CYAN = MAGENTA = WHITE = ''
    Fore = Style = _DummyColor()

_C = Fore
_S = Style

# 状态符号（避免 GBK 乱码，统一用 ASCII）
_OK  = '[OK]'
_FAIL = '[FAIL]'
_DONE = '[DONE]'
_SKIP = '[SKIP]'
_INFO = '[INFO]'
_WARN = '[WARN]'


def _color(text, color):
    return f'{color}{text}{_S.RESET_ALL}' if _HAS_COLORAMA else text


def _ok(text):   return _color(f'{_OK} {text}',   _C.GREEN  + _S.BRIGHT)
def _fail(text): return _color(f'{_FAIL} {text}', _C.RED    + _S.BRIGHT)
def _info(text): return _color(f'{_INFO} {text}',  _C.CYAN   + _S.BRIGHT)
def _warn(text): return _color(f'{_WARN} {text}', _C.YELLOW + _S.BRIGHT)
def _dim(text):  return _color(text,               _C.WHITE  + _S.DIM)


def setup_logging(verbose: bool = False, quiet: bool = False):
    """配置日志"""
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    
    # 避免重复 handler
    root = logging.getLogger()
    if root.handlers:
        root.handlers.clear()
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s %(levelname)-8s %(message)s',
        datefmt='%H:%M:%S',
        force=True
    )


# ==================== 核心命令 ====================

def cmd_embed(args):
    """嵌入水印命令"""
    wm = StealthMark(password=args.password)
    
    input_path = Path(args.input)
    
    if args.verbose:
        _info(f'Handler lookup: {input_path.suffix}')
        _info(f'Watermark: {args.watermark}')
        if args.output:
            _info(f'Output: {args.output}')
        else:
            _info(f'Output: in-place (no -o specified)')
    
    if args.output and Path(args.output).exists():
        if not args.force and not _confirm_overwrite(args.output):
            _warn('Aborted.')
            return 1
    
    if args.verbose:
        _info(f'Embedding...')
    
    result = wm.embed(
        file_path=args.input,
        watermark=args.watermark,
        output_path=args.output
    )
    
    if result.is_success:
        _ok(f'Watermark embedded: {result.output_path}')
        if args.verbose:
            print(f'  watermark_id: {result.watermark_id or "N/A"}')
            print(f'  status: {result.status}')
        return 0
    else:
        _fail(f'Embed failed: {result.message}')
        if args.verbose:
            _show_traceback(result)
        return 1


def cmd_extract(args):
    """提取水印命令"""
    wm = StealthMark(password=args.password)
    
    path = Path(args.file)
    if not path.exists():
        _fail(f'File not found: {args.file}')
        return 1
    
    if args.verbose:
        _info(f'Extracting from: {args.file}')
    
    result = wm.extract(file_path=args.file)
    
    if result.is_success:
        content = result.watermark.content
        _ok(f'Watermark extracted: {content}')
        if args.verbose:
            print(f'  status: {result.status}')
        return 0
    else:
        _fail(f'Extract failed: {result.message}')
        if args.verbose:
            _show_handler_hint(path.suffix)
            _show_traceback(result)
        return 1


def cmd_verify(args):
    """验证水印命令"""
    wm = StealthMark(password=args.password)
    
    result = wm.verify(
        file_path=args.file,
        original_watermark=args.watermark
    )
    
    if result.is_valid:
        _ok(f'Verification passed')
        print(f'  Match: {result.match_score * 100:.1f}%')
        if args.verbose and result.details:
            for k, v in result.details.items():
                print(f'  {k}: {v}')
        return 0
    else:
        _fail(f'Verification failed')
        print(f'  Reason: {result.message}')
        if args.verbose and result.details:
            print(f'  Extracted: {result.details.get("extracted", "N/A")}')
            print(f'  Expected:  {result.details.get("original", "N/A")}')
        return 1


def cmd_info(args):
    """显示支持格式"""
    wm = StealthMark()
    formats = wm.supported_formats()
    
    # 按类别分组
    docs   = [f for f in formats if f in ('.pdf','.docx','.pptx','.xlsx','.odt','.ods','.odp','.epub','.rtf')]
    images = [f for f in formats if f in ('.png','.jpg','.jpeg','.bmp','.tiff','.tif','.webp','.gif','.heic')]
    audio  = [f for f in formats if f in ('.wav','.mp3','.flac','.aac','.m4a')]
    video  = [f for f in formats if f not in docs + images + audio]
    
    print(f'StealthMark - {len(formats)} supported formats\n')
    
    def show_group(title, items):
        print(_color(title, _C.CYAN + _S.BRIGHT))
        for ext in sorted(items):
            print(f'  {ext}')
        print()
    
    show_group('Documents:', docs)
    show_group('Images:', images)
    show_group('Audio:', audio)
    if video:
        show_group('Video:', video)


def cmd_batch(args):
    """批量处理命令"""
    from tqdm import tqdm
    
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir) if args.output_dir else None
    
    if not input_dir.exists():
        _fail(f'Input directory not found: {input_dir}')
        return 1
    
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # 收集文件
    wm = StealthMark(password=args.password)
    files = []
    for ext in wm.supported_formats():
        files.extend(input_dir.rglob(f'*{ext}'))
    
    if not files:
        _warn(f'No supported files found in: {input_dir}')
        return 1
    
    print(f'Found {len(files)} file(s). Processing...\n')
    
    results = {'success': 0, 'failed': 0, 'skipped': 0}
    failed_list = []
    
    for f in tqdm(files, desc='Processing', unit='file', ncols=80):
        try:
            if args.operation == 'embed':
                if not args.watermark:
                    _warn('Missing --watermark for embed operation')
                    return 1
                
                if output_dir:
                    out_path = output_dir / f.name
                else:
                    out_path = str(f).replace(str(input_dir), str(output_dir or input_dir))
                
                result = wm.embed(str(f), args.watermark, out_path)
            elif args.operation == 'extract':
                result = wm.extract(str(f))
            elif args.operation == 'verify':
                if not args.watermark:
                    _warn('Missing --watermark for verify operation')
                    return 1
                result = wm.verify(str(f), args.watermark)
            else:
                continue
            
            if result.is_success if hasattr(result, 'is_success') else result.is_valid:
                results['success'] += 1
            else:
                results['failed'] += 1
                failed_list.append((str(f), result.message if hasattr(result, 'message') else 'unknown'))
        except Exception as e:
            results['failed'] += 1
            failed_list.append((str(f), str(e)))
    
    print(f"\n{'─' * 50}")
    _ok(f"Success:  {results['success']}")
    _fail(f"Failed:   {results['failed']}")
    
    if failed_list and (args.verbose or args.show_errors):
        print(f"\n{_C.RED}Failed files:{_S.RESET_ALL}")
        for path, msg in failed_list:
            print(f'  {_FAIL} {Path(path).name}')
            print(f'       {msg}')
    
    return 0 if results['failed'] == 0 else 1


# ==================== 辅助函数 ====================

def _confirm_overwrite(path):
    """确认覆盖"""
    name = Path(path).name
    resp = input(f'File exists: {name}. Overwrite? [y/N] ').strip().lower()
    return resp in ('y', 'yes')


def _show_traceback(result):
    """显示详细错误追踪"""
    # Result objects don't have traceback in current implementation
    print(f'\n{_C.RED}--- Error Details ---{_S.RESET_ALL}')
    print(f'  Status: {result.status}')
    print(f'  Message: {result.message}')


def _show_handler_hint(suffix):
    """显示格式提示"""
    from src.core.base import WatermarkStatus
    hints = {
        '.pdf':  'PDF files embed watermark in metadata. Ensure file is not scanned.',
        '.docx': 'DOCX uses zero-width characters. Do not re-save as plain text.',
        '.mp3':  'MP3 uses echo hiding. May fail if re-encoded.',
        '.heic': 'HEIC uses DCT LSB. Do not re-encode.',
        '.wav':  'WAV uses spread spectrum LSB.',
        '.mp4':  'MP4 uses RGB Blue channel LSB.',
    }
    hint = hints.get(suffix.lower())
    if hint:
        print(f'  {_C.YELLOW}Hint: {hint}{_S.RESET_ALL}')


# ==================== 主入口 ====================

def main():
    parser = argparse.ArgumentParser(
        description='StealthMark - Invisible Watermark Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s embed input.pdf "MyWatermark" -o output.pdf
  %(prog)s extract output.pdf
  %(prog)s verify output.pdf "MyWatermark"
  %(prog)s batch embed input_dir/ --watermark "Secret" -o output_dir/
        '''
    )
    
    parser.add_argument('-p', '--password', type=str, default=None,
                        help='Watermark encryption password')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # --- embed ---
    embed_parser = subparsers.add_parser('embed', help='Embed watermark')
    embed_parser.add_argument('-v', '--verbose', action='store_true',
                              help='Show detailed logs')
    embed_parser.add_argument('-q', '--quiet', action='store_true',
                              help='Suppress non-error output')
    embed_parser.add_argument('input', help='Input file path')
    embed_parser.add_argument('watermark', help='Watermark text')
    embed_parser.add_argument('-o', '--output', help='Output file path')
    embed_parser.add_argument('-f', '--force', action='store_true',
                              help='Force overwrite without confirmation')
    embed_parser.set_defaults(func=cmd_embed)
    
    # --- extract ---
    extract_parser = subparsers.add_parser('extract', help='Extract watermark')
    extract_parser.add_argument('-v', '--verbose', action='store_true',
                                help='Show detailed logs')
    extract_parser.add_argument('-q', '--quiet', action='store_true',
                                help='Suppress non-error output')
    extract_parser.add_argument('file', help='File containing watermark')
    extract_parser.set_defaults(func=cmd_extract)
    
    # --- verify ---
    verify_parser = subparsers.add_parser('verify', help='Verify watermark')
    verify_parser.add_argument('-v', '--verbose', action='store_true',
                               help='Show detailed logs')
    verify_parser.add_argument('-q', '--quiet', action='store_true',
                               help='Suppress non-error output')
    verify_parser.add_argument('file', help='File to verify')
    verify_parser.add_argument('watermark', help='Original watermark text')
    verify_parser.set_defaults(func=cmd_verify)
    
    # --- info ---
    # --- info ---
    info_parser = subparsers.add_parser('info', help='Show supported formats')
    info_parser.add_argument('-v', '--verbose', action='store_true',
                              help='Show detailed logs')
    info_parser.add_argument('-q', '--quiet', action='store_true',
                              help='Suppress non-error output')
    info_parser.set_defaults(func=cmd_info)
    
    # --- batch ---
    batch_parser = subparsers.add_parser('batch', help='Batch process multiple files')
    batch_parser.add_argument('operation', choices=['embed', 'extract', 'verify'],
                              help='Operation to perform')
    batch_parser.add_argument('input_dir', help='Input directory')
    batch_parser.add_argument('-o', '--output-dir', help='Output directory')
    batch_parser.add_argument('--watermark', help='Watermark text (required for embed/verify)')
    batch_parser.add_argument('--show-errors', action='store_true',
                              help='Show failed file details in batch mode')
    batch_parser.add_argument('-v', '--verbose', action='store_true',
                              help='Show detailed logs')
    batch_parser.add_argument('-q', '--quiet', action='store_true',
                              help='Suppress non-error output')
    batch_parser.set_defaults(func=cmd_batch)
    
    args = parser.parse_args()
    
    setup_logging(
        verbose=getattr(args, 'verbose', False),
        quiet=getattr(args, 'quiet', False)
    )
    
    if getattr(args, 'command', None) is None:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
