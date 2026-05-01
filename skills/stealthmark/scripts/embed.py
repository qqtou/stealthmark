"""
StealthMark Embed Script
通过 CLI 调用嵌入水印，支持所有已安装 stealthmark 的环境
"""

import subprocess
import sys
import re
from pathlib import Path

# 获取当前 Python 可执行文件路径（跨平台兼容）
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


def embed(
    input_file: str,
    watermark: str,
    output_file: str = None,
    force: bool = False,
    verbose: bool = False,
) -> dict:
    """
    嵌入水印到文件

    Args:
        input_file: 输入文件路径
        watermark: 水印文本
        output_file: 输出文件路径（None 则自动生成）
        force: 强制覆盖已存在文件
        verbose: 详细输出

    Returns:
        dict with keys: success, output_path, message, format, handler
    """
    input_path = Path(input_file).resolve()
    if not input_path.exists():
        return {
            'success': False,
            'output_path': None,
            'message': f'File not found: {input_file}',
            'format': None,
            'handler': None,
        }

    # 构建 CLI 参数
    args = ['embed']
    if verbose:
        args.append('-v')
    args.append(str(input_path))
    args.append(watermark)

    if output_file:
        args.extend(['-o', str(Path(output_file).resolve())])
    if force:
        args.append('-f')

    # 尝试多种工作目录
    possible_cwds = [None, str(input_path.parent), str(Path.cwd())]
    last_error = None

    for cwd in possible_cwds:
        result = _run_cli(args, cwd=cwd)
        output_text = (result.stdout or '') + (result.stderr or '')

        if result.returncode == 0 or '[OK]' in output_text or 'Watermark embedded successfully' in output_text:
            # 从输出中提取实际输出路径
            match = re.search(r'Watermark embedded successfully -> (.+)', output_text)
            out_path = match.group(1).strip() if match else (output_file or str(input_path))

            return {
                'success': True,
                'output_path': out_path,
                'message': f'Watermark embedded successfully -> {out_path}',
                'format': input_path.suffix.lower(),
                'handler': None,
            }

        # 检查是否是路径问题
        if 'not found' in output_text.lower() or 'No module' in output_text:
            last_error = output_text
            continue

        # 其他错误，停止重试
        break

    # 所有尝试都失败
    match = re.search(r'\[FAIL\]\s*(.+)', output_text)
    error_msg = match.group(1).strip() if match else (last_error or output_text.strip())
    return {
        'success': False,
        'output_path': None,
        'message': error_msg or f'Embed failed (exit {result.returncode})',
        'format': input_path.suffix.lower(),
        'handler': None,
    }


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Embed watermark into file')
    parser.add_argument('input', help='Input file path')
    parser.add_argument('watermark', help='Watermark text')
    parser.add_argument('-o', '--output', help='Output file path', default=None)
    parser.add_argument('-f', '--force', help='Force overwrite', action='store_true')
    parser.add_argument('-v', '--verbose', help='Verbose output', action='store_true')

    args = parser.parse_args()

    result = embed(
        input_file=args.input,
        watermark=args.watermark,
        output_file=args.output,
        force=args.force,
        verbose=args.verbose,
    )

    if result['success']:
        print(f"[OK] {result['message']}")
    else:
        print(f"[FAIL] {result['message']}")
        sys.exit(1)