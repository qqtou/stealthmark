"""
StealthMark Verify Script
通过 CLI 调用验证水印
"""

import subprocess
import re
import sys
from pathlib import Path

_PYTHON_EXE = getattr(sys, 'executable', 'python')


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


def verify(file_path: str, original_watermark: str = None, verbose: bool = False) -> dict:
    """
    验证文件中的水印

    Args:
        file_path: 文件路径
        original_watermark: 原始水印文本（用于精确匹配）
        verbose: 详细输出

    Returns:
        dict with keys: success, match, score, message, details
    """
    input_path = Path(file_path).resolve()
    if not input_path.exists():
        return {
            'success': False,
            'match': False,
            'score': 0.0,
            'message': f'File not found: {file_path}',
            'details': None,
        }

    args = ['verify']
    if verbose:
        args.append('-v')
    args.append(str(input_path))
    if original_watermark:
        args.append(original_watermark)

    # 尝试多种工作目录
    for cwd in [None, str(input_path.parent), str(Path.cwd())]:
        result = _run_cli(args, cwd=cwd)
        output_text = (result.stdout or '') + (result.stderr or '')

        if result.returncode == 0 or '[OK]' in output_text or 'Verification passed' in output_text:
            # 提取匹配分数
            score_match = re.search(r'Match:\s*([\d.]+)%', output_text)
            score = float(score_match.group(1)) / 100 if score_match else 1.0

            # 提取详细结果
            details = {}
            if 'Extracted:' in output_text:
                ext_match = re.search(r'Extracted:\s*(.+)', output_text)
                if ext_match:
                    details['extracted'] = ext_match.group(1).strip()

            return {
                'success': True,
                'match': True,
                'score': score,
                'message': 'Verification passed',
                'details': details or None,
            }

        if 'not found' in output_text.lower() or 'No module' in output_text:
            continue
        break

    # 验证失败
    match_match = re.search(r'Reason:\s*(.+)', output_text)
    reason = match_match.group(1).strip() if match_match else output_text.strip()

    # 尝试提取分数
    score_match = re.search(r'Match:\s*([\d.]+)%', output_text)
    score = float(score_match.group(1)) / 100 if score_match else 0.0

    return {
        'success': False,
        'match': False,
        'score': score,
        'message': reason or f'Verification failed (exit {result.returncode})',
        'details': None,
    }


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Verify watermark in file')
    parser.add_argument('file', help='File to verify')
    parser.add_argument('watermark', nargs='?', help='Original watermark text (optional)')
    parser.add_argument('-v', '--verbose', help='Verbose output', action='store_true')

    args = parser.parse_args()

    result = verify(
        file_path=args.file,
        original_watermark=args.watermark,
        verbose=args.verbose
    )

    if result['success']:
        print(f"[OK] {result['message']}")
    else:
        print(f"[FAIL] {result['message']}")
        sys.exit(1)