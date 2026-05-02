# stealthmark/cli.py
"""
StealthMark 命令行接口
Stage 1: CLI 增强 - 进度条 + 详细日志 + 更好的错误提示
Stage 2: 批量处理 - 并行 + 命名模式 + 扩展名过滤 + dry-run
"""

import argparse
import sys
import os
import logging
import re
import shutil
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from .core.manager import StealthMark
from .core.base import WatermarkStatus

# ==================== 日志与颜色 ====================

try:
    from colorama import init, Fore, Style
    import sys as _sys
    # TTY 下保留颜色，非 TTY 下自动移除 ANSI 转义码但保留文本
    init(autoreset=True, strip=not _sys.stdout.isatty())
    _HAS_COLORAMA = True
except ImportError:
    _HAS_COLORAMA = False

if not _HAS_COLORAMA:
    class _DummyColor:
        RESET = BRIGHT = DIM = RED = GREEN = YELLOW = CYAN = MAGENTA = WHITE = ''
    Fore = Style = _DummyColor()

_C = Fore
_S = Style

_OK   = '[OK]'
_FAIL = '[FAIL]'
_DONE = '[DONE]'
_SKIP = '[SKIP]'
_INFO = '[INFO]'
_WARN = '[WARN]'


def _color(text, color):
    return f'{color}{text}{_S.RESET_ALL}' if _HAS_COLORAMA else text


def _ok(text):    print(_color(f'{_OK} {text}',   _C.GREEN  + _S.BRIGHT))
def _fail(text):  print(_color(f'{_FAIL} {text}', _C.RED    + _S.BRIGHT))
def _info(text):  print(_color(f'{_INFO} {text}',  _C.CYAN   + _S.BRIGHT))
def _warn(text):  print(_color(f'{_WARN} {text}', _C.YELLOW + _S.BRIGHT))
def _dim(text):   print(_color(text,               _C.WHITE  + _S.DIM))

# 保留纯字符串版本供内嵌使用（如 print(f'  {_ok_str(...)}')  ）
def _ok_str(text):    return _color(f'{_OK} {text}',   _C.GREEN  + _S.BRIGHT)
def _fail_str(text):  return _color(f'{_FAIL} {text}', _C.RED    + _S.BRIGHT)
def _warn_str(text):  return _color(f'{_WARN} {text}', _C.YELLOW + _S.BRIGHT)


def setup_logging(verbose: bool = False, quiet: bool = False):
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.WARNING  # 默认只显示 WARNING+，-v 才开 DEBUG

    root = logging.getLogger()
    if root.handlers:
        root.handlers.clear()

    logging.basicConfig(
        level=level,
        format='%(asctime)s %(levelname)-8s %(message)s',
        datefmt='%H:%M:%S',
        force=True
    )

    # 第三方库日志级别单独控制，避免 INFO 泄漏到默认输出
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('matplotlib').setLevel(logging.WARNING)


# ==================== 核心命令 ====================

def cmd_embed(args):
    wm = StealthMark(password=args.password)

    input_path = Path(args.input)

    if not input_path.exists():
        _fail(f'File not found: {args.input}')
        return 1

    if args.verbose:
        _info(f'Handler lookup: {input_path.suffix}')
        _info(f'Watermark: {args.watermark}')

    if args.output and Path(args.output).exists():
        if not args.force:
            if not sys.stdin.isatty():
                _fail(f'Output file exists: {args.output}. Use -f to overwrite.')
                return 1
            if not _confirm_overwrite(args.output):
                _warn('Aborted.')
                return 1
    elif not args.output and input_path.exists():
        # 无 -o 时：原地覆盖，强制跳过确认
        pass

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
    wm = StealthMark()
    formats = wm.supported_formats()

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


# ==================== Stage 2: 批量处理 ====================

def _build_output_path(input_file: Path, output_dir: Path, pattern: str, operation: str) -> Path:
    """根据命名模式计算输出路径。

    pattern 支持的占位符:
      {name}   - 原文件名（不含扩展名）
      {ext}    - 扩展名（含点，如 .pdf）
      {stem}   - 同 {name}
      {date}   - 日期 20260101
      {time}   - 时间 153045
      {dt}     - 日期时间 20260101_153045

    embed 操作默认: {name}_wm{ext}
    extract/verify 操作默认: {name}_out{ext}
    """
    if not pattern:
        default_suffix = '_wm' if operation == 'embed' else '_out'
        pattern = '{name}' + default_suffix + '{ext}'

    now = datetime.now()
    subs = {
        'name': input_file.stem,
        'stem': input_file.stem,
        'ext':  input_file.suffix,
        'date': now.strftime('%Y%m%d'),
        'time': now.strftime('%H%M%S'),
        'dt':   now.strftime('%Y%m%d_%H%M%S'),
    }
    new_name = pattern
    for k, v in subs.items():
        new_name = new_name.replace('{' + k + '}', v)

    # 避免覆盖原文件
    out_path = output_dir / new_name
    return out_path


def _collect_files(input_dir: Path, recursive: bool, include_pat: list, exclude_pat: list,
                   wm):
    """收集匹配的文件"""
    supported = set(wm.supported_formats())
    all_files = []

    pattern = '**/*' if recursive else '*'
    for ext in supported:
        all_files.extend(input_dir.glob(f'{pattern}{ext}'))

    # 去重
    seen = set()
    unique = []
    for f in all_files:
        if f not in seen:
            seen.add(f)
            unique.append(f)

    # 扩展名过滤
    if include_pat:
        include_re = re.compile('|'.join(include_pat), re.IGNORECASE)
        unique = [f for f in unique if include_re.search(f.suffix.lower())]

    if exclude_pat:
        exclude_re = re.compile('|'.join(exclude_pat), re.IGNORECASE)
        unique = [f for f in unique if not exclude_re.search(f.suffix.lower())]

    return sorted(unique)


def _process_one(args_tuple):
    """单文件处理（供线程池调用）"""
    f, operation, watermark, out_path, dry_run = args_tuple

    if dry_run:
        return ('dryrun', str(f), out_path, None)

    try:
        actual_out = str(out_path) if out_path else None
        if operation == 'embed':
            if not watermark:
                return ('skip', str(f), None, 'No watermark')
            result = _BATCH_WM.embed(str(f), watermark, str(out_path))
            ok = result.is_success
            msg = result.message if not ok else None
            # handler 可能改变输出路径（如 .aac → .m4a），用实际路径
            if ok and result.output_path:
                actual_out = result.output_path
        elif operation == 'extract':
            result = _BATCH_WM.extract(str(f))
            ok = result.is_success
            msg = result.message if not ok else None
        elif operation == 'verify':
            if not watermark:
                return ('skip', str(f), None, 'No watermark')
            result = _BATCH_WM.verify(str(f), watermark)
            ok = result.is_valid
            msg = result.message if not ok else None
        else:
            return ('skip', str(f), None, f'Unknown operation: {operation}')

        status = 'success' if ok else 'failed'
        return (status, str(f), actual_out, msg)
    except Exception as e:
        return ('failed', str(f), None, str(e))


# 全局 watermark manager（避免每个文件重复初始化 handler）
_BATCH_WM = None


def cmd_batch(args):
    global _BATCH_WM
    from tqdm import tqdm

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir) if args.output_dir else None

    if not input_dir.exists():
        _fail(f'Input directory not found: {input_dir}')
        return 1

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    # 验证 watermark
    if args.operation in ('embed', 'verify') and not args.watermark:
        _warn(f'Operation "{args.operation}" requires --watermark.')
        return 1

    # 统一 manager 实例（减少 handler 重复初始化）
    _BATCH_WM = StealthMark(password=args.password)

    # 收集文件
    files = _collect_files(
        input_dir,
        recursive=not args.no_recursive,
        include_pat=args.include,
        exclude_pat=args.exclude,
        wm=_BATCH_WM
    )

    if not files:
        _warn(f'No matching files found in: {input_dir}')
        return 1

    # Dry-run: 只显示会处理的文件
    if args.dry_run:
        print(f'[{_C.CYAN}DRY RUN{_S.RESET_ALL}] Would process {len(files)} file(s):\n')
        for f in files:
            out_path = _build_output_path(f, output_dir or input_dir,
                                          args.name_pattern, args.operation)
            rel = f.relative_to(input_dir)
            print(f'  {rel}  -->  {out_path.relative_to(output_dir or input_dir)}')
        print(f'\nDry run: {len(files)} file(s) would be processed.')
        return 0

    print(f'Found {len(files)} file(s). Processing...\n')

    workers = getattr(args, 'workers', 4) or 4
    quiet = getattr(args, 'quiet', False)

    # 计算输出路径
    work_items = []
    for f in files:
        out_path = _build_output_path(f, output_dir or input_dir,
                                      args.name_pattern, args.operation)
        work_items.append((f, args.operation, args.watermark, out_path,
                            args.dry_run))

    results = {'success': 0, 'failed': 0, 'skipped': 0, 'dryrun': 0}
    failed_list = []

    # 检测控制台编码，GBK 环境使用 ASCII 进度条
    use_ascii = sys.stdout.encoding and 'gbk' in sys.stdout.encoding.lower()

    # 并行处理
    if workers > 1 and len(files) > 1:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_process_one, item): item for item in work_items}
            for future in tqdm(as_completed(futures), total=len(futures),
                               desc='Processing', unit='file', ncols=80,
                               ascii=use_ascii):
                outcome = future.result()
                res_type = outcome[0]
                results[res_type] = results.get(res_type, 0) + 1
                if res_type == 'failed':
                    failed_list.append((outcome[1], outcome[3]))
                elif not quiet and res_type == 'success':
                    fname = Path(outcome[1]).name
                    out = outcome[2] if outcome[2] else outcome[1]
                    print(f'  {_ok_str(Path(out).name)}  <--  {fname}')
    else:
        for item in tqdm(work_items, desc='Processing', unit='file', ncols=80,
                         ascii=use_ascii):
            outcome = _process_one(item)
            res_type = outcome[0]
            results[res_type] = results.get(res_type, 0) + 1
            f_path = Path(outcome[1])
            out_path = outcome[2] if outcome[2] else None

            if res_type == 'dryrun':
                pass
            elif res_type == 'success':
                if not quiet:
                    disp_out = Path(out_path).name if out_path else f_path.name
                    print(f'  {_ok_str(disp_out)}  <--  {f_path.name}')
            elif res_type == 'skip':
                if not quiet:
                    print(f'  {_SKIP} {f_path.name}: {outcome[3]}')
            else:
                failed_list.append((outcome[1], outcome[3]))
                if not quiet:
                    print(f'  {_fail_str(f_path.name)}')

    # 汇总（GBK 兼容分隔线）
    sep = '-' * 50
    print(f'\n{sep}')
    print(_ok_str(f'Success:  {results["success"]}'))
    print(_fail_str(f'Failed:   {results["failed"]}'))
    if results.get('skipped'):
        print(_warn_str(f'Skipped:  {results["skipped"]}'))

    if failed_list and (args.verbose or args.show_errors):
        print(f'\n{_C.RED}Failed files:{_S.RESET_ALL}')
        for path, msg in failed_list:
            print(f'  {_FAIL} {Path(path).name}')
            print(f'       {msg}')

    return 0 if results['failed'] == 0 else 1


# ==================== 辅助函数 ====================

def _confirm_overwrite(path):
    name = Path(path).name
    try:
        resp = input(f'File exists: {name}. Overwrite? [y/N] ').strip().lower()
    except EOFError:
        resp = 'n'
    return resp in ('y', 'yes')


def _show_traceback(result):
    print(f'\n{_C.RED}--- Error Details ---{_S.RESET_ALL}')
    print(f'  Status: {result.status}')
    print(f'  Message: {result.message}')


def _show_handler_hint(suffix):
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
  %(prog)s batch verify input_dir/ --watermark "Secret" --include ".pdf" ".docx"
  %(prog)s batch embed input/ -o output/ --workers 8 --dry-run
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
    info_parser = subparsers.add_parser('info', help='Show supported formats')
    info_parser.add_argument('-v', '--verbose', action='store_true',
                              help='Show detailed logs')
    info_parser.add_argument('-q', '--quiet', action='store_true',
                              help='Suppress non-error output')
    info_parser.set_defaults(func=cmd_info)

    # --- batch (Stage 2) ---
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
    # Stage 2 new options
    batch_parser.add_argument('-n', '--name-pattern',
                              default=None,
                              help=('Output naming pattern. Placeholders: {name}, {ext}, '
                                    '{stem}, {date}, {time}, {dt}. '
                                    'Default: {{name}}_wm{{ext}} for embed, '
                                    '{{name}}_out{{ext}} for extract/verify'))
    batch_parser.add_argument('--include', nargs='+', default=None,
                              metavar='EXT',
                              help='Only process files with these extensions (e.g. .pdf .docx)')
    batch_parser.add_argument('--exclude', nargs='+', default=None,
                              metavar='EXT',
                              help='Exclude files with these extensions')
    batch_parser.add_argument('--no-recursive', action='store_true',
                              help='Do not scan subdirectories')
    batch_parser.add_argument('--dry-run', action='store_true',
                              help='Show what would be processed without doing it')
    batch_parser.add_argument('--workers', type=int, default=4,
                              help='Number of parallel workers (default: 4, use 1 for sequential)')
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
