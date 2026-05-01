"""
StealthMark Batch Script
通过 CLI 调用批量处理文件
"""

import subprocess
import sys
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Optional

# 单文件处理超时（秒）- 视频文件可能较慢
DEFAULT_TIMEOUT = 300


def _run_cli(args: list, cwd: str = None, timeout: int = DEFAULT_TIMEOUT) -> subprocess.CompletedProcess:
    """执行 stealthmark CLI，返回结果"""
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'stealthmark'] + args,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout,
            cwd=cwd
        )
        return result
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"StealthMark CLI timed out after {timeout}s")
    except FileNotFoundError:
        raise RuntimeError("stealthmark not found. Install with: pip install stealthmark")


def _process_single(args_tuple: Tuple) -> dict:
    """处理单个文件"""
    file_path, operation, watermark, output_path, verbose = args_tuple

    if operation == 'embed':
        cmd = ['embed', str(file_path), watermark]
        if verbose:
            cmd.append('-v')
        if output_path:
            cmd.extend(['-o', str(output_path)])
        # 不加 -f：避免非交互环境阻塞
    elif operation == 'extract':
        cmd = ['extract', str(file_path)]
        if verbose:
            cmd.append('-v')
    elif operation == 'verify':
        cmd = ['verify', str(file_path)]
        if verbose:
            cmd.append('-v')
        if watermark:
            cmd.append(watermark)
    else:
        return {'success': False, 'file': str(file_path), 'message': f'Unknown operation: {operation}'}

    try:
        result = _run_cli(cmd)
        output_text = result.stdout + result.stderr

        if result.returncode == 0 or '[OK]' in output_text:
            return {
                'success': True,
                'file': str(file_path),
                'output_path': str(output_path) if output_path else None,
                'message': 'OK'
            }
        else:
            match = re.search(r'\[FAIL\]\s*(.+)', output_text)
            error_msg = match.group(1).strip() if match else output_text.strip()[:200]
            return {
                'success': False,
                'file': str(file_path),
                'output_path': None,
                'message': error_msg
            }
    except TimeoutError as e:
        return {
            'success': False,
            'file': str(file_path),
            'output_path': None,
            'message': str(e)
        }
    except Exception as e:
        return {
            'success': False,
            'file': str(file_path),
            'output_path': None,
            'message': str(e)
        }


def batch(
    input_dir: str,
    operation: str,
    watermark: str = None,
    output_dir: str = None,
    include: List[str] = None,
    exclude: List[str] = None,
    recursive: bool = True,
    workers: int = 1,
    verbose: bool = False,
    dry_run: bool = False,
) -> dict:
    """
    批量处理文件

    Args:
        input_dir: 输入目录
        operation: 操作类型（embed/extract/verify）
        watermark: 水印文本（embed/verify 需要）
        output_dir: 输出目录（None 则原地覆盖）
        include: 只处理这些扩展名，如 ['.pdf', '.docx']
        exclude: 排除这些扩展名
        recursive: 是否递归子目录
        workers: 并行线程数（默认1，顺序执行更稳定）
        verbose: 详细输出
        dry_run: 模拟运行

    Returns:
        dict with keys: success, total, processed, failed, errors
    """
    input_path = Path(input_dir).resolve()
    if not input_path.exists():
        return {
            'success': False,
            'total': 0,
            'processed': 0,
            'failed': 0,
            'errors': [f'Input directory not found: {input_dir}']
        }

    if output_dir:
        output_path = Path(output_dir).resolve()
        output_path.mkdir(parents=True, exist_ok=True)
    else:
        output_path = input_path

    # 获取支持的扩展名
    result = _run_cli(['info', '-q'], cwd=str(input_path))
    if result.returncode != 0:
        return {
            'success': False,
            'total': 0,
            'processed': 0,
            'failed': 0,
            'errors': ['Failed to get supported formats']
        }

    # 收集文件
    pattern = '**/*' if recursive else '*'
    supported_exts = []
    all_files = []

    # 简单解析支持格式
    for line in result.stdout.split('\n'):
        line = line.strip()
        if line.startswith('.'):
            supported_exts.append(line.lower())

    # 按扩展名过滤
    for ext in supported_exts:
        if include and ext not in include:
            continue
        if exclude and ext in exclude:
            continue
        all_files.extend(input_path.glob(f'{pattern}{ext}'))

    # 去重
    seen = set()
    unique_files = []
    for f in all_files:
        if f not in seen:
            seen.add(f)
            unique_files.append(f)

    if not unique_files:
        return {
            'success': True,
            'total': 0,
            'processed': 0,
            'failed': 0,
            'errors': ['No matching files found']
        }

    # Dry run
    if dry_run:
        print(f'[DRY RUN] Would process {len(unique_files)} file(s):')
        for f in unique_files:
            print(f'  {f.relative_to(input_path)}')
        return {
            'success': True,
            'total': len(unique_files),
            'processed': 0,
            'failed': 0,
            'errors': []
        }

    # 构建任务参数
    work_items = []
    for f in unique_files:
        out_path = None
        if output_dir:
            out_name = f.stem + '_wm' + f.suffix if operation == 'embed' else f.stem + '_out' + f.suffix
            out_path = output_path / out_name
        work_items.append((f, operation, watermark, out_path, verbose))

    # 处理
    results = {'success': 0, 'failed': 0, 'errors': []}
    failed_files = []

    if workers > 1 and len(work_items) > 1:
        # 并行：带超时保护
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_process_single, item): item for item in work_items}
            try:
                for future in as_completed(futures, timeout=len(work_items) * DEFAULT_TIMEOUT):
                    try:
                        outcome = future.result(timeout=DEFAULT_TIMEOUT)
                    except TimeoutError:
                        item = futures[future]
                        outcome = {'success': False, 'file': str(item[0]), 'output_path': None, 'message': 'Timeout'}
                    except Exception as e:
                        item = futures[future]
                        outcome = {'success': False, 'file': str(item[0]), 'output_path': None, 'message': str(e)}

                    if outcome['success']:
                        results['success'] += 1
                        if verbose:
                            print(f"[OK] {Path(outcome['file']).name}")
                    else:
                        results['failed'] += 1
                        failed_files.append((outcome['file'], outcome['message']))
                        if verbose:
                            print(f"[FAIL] {Path(outcome['file']).name}: {outcome['message']}")
            except TimeoutError:
                # 整体超时，收集未完成的任务
                for future in futures:
                    if not future.done():
                        item = futures[future]
                        results['failed'] += 1
                        failed_files.append((str(item[0]), 'Overall timeout'))
    else:
        # 顺序执行：更稳定
        for item in work_items:
            outcome = _process_single(item)
            if outcome['success']:
                results['success'] += 1
                if verbose:
                    print(f"[OK] {Path(outcome['file']).name}")
            else:
                results['failed'] += 1
                failed_files.append((outcome['file'], outcome['message']))
                if verbose:
                    print(f"[FAIL] {Path(outcome['file']).name}: {outcome['message']}")

    return {
        'success': results['failed'] == 0,
        'total': len(unique_files),
        'processed': results['success'],
        'failed': results['failed'],
        'errors': failed_files
    }


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Batch process files with StealthMark')
    parser.add_argument('operation', choices=['embed', 'extract', 'verify'],
                        help='Operation to perform')
    parser.add_argument('input_dir', help='Input directory')
    parser.add_argument('-o', '--output-dir', help='Output directory')
    parser.add_argument('--watermark', help='Watermark text')
    parser.add_argument('--include', nargs='+', help='Only process these extensions')
    parser.add_argument('--exclude', nargs='+', help='Exclude these extensions')
    parser.add_argument('--no-recursive', action='store_true')
    parser.add_argument('--workers', type=int, default=1, help='Parallel workers (default: 1)')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('--dry-run', action='store_true')

    args = parser.parse_args()

    result = batch(
        input_dir=args.input_dir,
        operation=args.operation,
        watermark=args.watermark,
        output_dir=args.output_dir,
        include=args.include,
        exclude=args.exclude,
        recursive=not args.no_recursive,
        workers=args.workers,
        verbose=args.verbose,
        dry_run=args.dry_run
    )

    print(f'\n--- Summary ---')
    print(f'Total: {result["total"]}')
    print(f'Processed: {result["processed"]}')
    print(f'Failed: {result["failed"]}')

    if result['errors'] and result['errors'][0]:
        if isinstance(result['errors'][0], tuple):
            print(f'\nFailed files:')
            for path, msg in result['errors']:
                print(f'  {Path(path).name}: {msg}')
        else:
            print(f'\nErrors: {result["errors"]}')

    sys.exit(0 if result['success'] else 1)
