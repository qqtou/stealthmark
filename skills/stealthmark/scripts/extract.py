"""
StealthMark Extract Script
通过 CLI 调用提取水印
"""

import subprocess
import re
import sys
from pathlib import Path

_PYTHON_EXE = sys.executable


def _run_cli(args: list, cwd: str = None) -> subprocess.CompletedProcess:
    """执行 stealthmark CLI，返回结果"""
    try:
        result = subprocess.run(
            [_PYTHON_EXE, '-m', 'stealthmark'] + args,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=120,
            cwd=cwd
        )
        return result
    except subprocess.TimeoutExpired:
        raise RuntimeError("StealthMark CLI timed out (>120s)")
    except FileNotFoundError:
        raise RuntimeError(
            "stealthmark not found. Install with:\n"
            "  pip install -e D:/work/code/stealthmark\n"
            "or:\n"
            "  pip install git+https://github.com/qqtou/stealthmark.git"
        )


def _extract_watermark_from_output(output_text: str) -> str:
    # 格式1: "Watermark extracted: content"
    match = re.search(r'Watermark extracted:\s*(.+?)(?:\r?\n|$)', output_text)
    if match:
        return match.group(1).strip()
    # 格式2: "PDF extract success: content..."
    match = re.search(r'PDF extract success:\s*(.+?)(?:\r?\n|$)', output_text)
    if match:
        text = match.group(1).strip()
        return text.rstrip('.') if text else ''
    return ''


def extract(file_path: str, verbose: bool = False) -> dict:
    """从文件中提取水印"""
    input_path = Path(file_path).resolve()
    if not input_path.exists():
        return {
            'success': False,
            'watermark': None,
            'message': f'File not found: {file_path}',
            'format': None,
        }

    args = ['extract']
    if verbose:
        args.append('-v')
    args.append(str(input_path))

    for cwd in [None, str(input_path.parent), str(Path.cwd())]:
        result = _run_cli(args, cwd=cwd)
        output_text = (result.stdout or '') + (result.stderr or '')

        if result.returncode == 0 or '[OK]' in output_text or 'Watermark extracted:' in output_text:
            wm_text = _extract_watermark_from_output(output_text)
            return {
                'success': True,
                'watermark': wm_text,
                'message': f'Watermark extracted: {wm_text}',
                'format': input_path.suffix.lower(),
            }
        if 'not found' in output_text.lower() or 'No module' in output_text:
            continue
        break

    match = re.search(r'\[FAIL\]\s*(.+)', output_text)
    error_msg = match.group(1).strip() if match else output_text.strip()
    return {
        'success': False,
        'watermark': None,
        'message': error_msg or f'Extract failed (exit {result.returncode})',
        'format': input_path.suffix.lower(),
    }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Extract watermark from file')
    parser.add_argument('file', help='File containing watermark')
    parser.add_argument('-v', '--verbose', help='Verbose output', action='store_true')
    args = parser.parse_args()
    result = extract(file_path=args.file, verbose=args.verbose)
    if result['success']:
        print(f"[OK] {result['message']}")
    else:
        print(f"[FAIL] {result['message']}")
        sys.exit(1)