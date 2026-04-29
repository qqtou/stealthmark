#!/usr/bin/env python3
"""
StealthMark 全格式测试脚本

测试所有 23 个 Handler 的 embed/extract/verify 功能
测试结束后自动清理生成的临时文件

Usage:
    python tests/scripts/test_all_formats.py
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.manager import StealthMark


# 测试水印内容
TEST_WATERMARK = "StealthMark-Test-2026"

# 所有支持的格式及对应的测试文件
# 格式: (扩展名, 测试文件名, 是否需要跳过)
FORMAT_CONFIG = [
    # 文档格式
    ("pdf", "test.pdf", False),
    ("docx", "test.docx", False),
    ("pptx", "test.pptx", False),
    ("xlsx", "test.xlsx", False),
    ("odt", "test.odt", False),
    ("ods", "test.ods", False),
    ("odp", "test.odp", False),
    ("epub", "test.epub", False),
    ("rtf", "test.rtf", False),
    
    # 图片格式
    ("png", "test.png", False),
    ("jpg", "test.jpg", False),
    ("jpeg", None, True),  # 跳过，与 jpg 相同
    ("bmp", "test.bmp", False),
    ("tiff", "test.tiff", False),
    ("webp", "test.webp", False),
    ("gif", "test.gif", False),
    ("heic", None, True),  # 需要可选依赖，跳过
    
    # 音频格式
    ("wav", "test.wav", False),
    ("mp3", None, True),  # 需要 pydub/lameenc 生成，跳过
    ("flac", "test.flac", False),  # soundfile 生成
    ("aac", None, True),  # 需要额外编码器，跳过
    ("m4a", "test.m4a", False),  # pydub 生成
    
    # 视频格式
    ("mp4", "test.mp4", False),
    ("avi", "test.avi", False),
    ("mkv", None, True),  # 无测试文件，跳过
    ("mov", None, True),  # 无测试文件，跳过
    ("webm", "test.webm", False),  # imageio/pyav 生成
    ("wmv", None, True),  # 需要 Windows 专用工具，跳过
]


def get_fixtures_dir() -> Path:
    """获取测试数据目录"""
    return PROJECT_ROOT / "tests" / "fixtures"


def create_missing_test_files(fixtures_dir: Path):
    """创建缺失的测试文件（使用 Python 库，不依赖命令行工具）"""
    import wave
    import struct
    import math
    
    # 创建基础 WAV 测试文件（如果不存在）
    wav_path = fixtures_dir / "test.wav"
    if not wav_path.exists():
        try:
            with wave.open(str(wav_path), 'w') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(44100)
                # 生成 1 秒 440Hz 正弦波
                frames = []
                for i in range(44100):
                    value = int(32767 * 0.5 * math.sin(2 * math.pi * 440 * i / 44100))
                    frames.append(struct.pack('<h', value))
                wf.writeframes(b''.join(frames))
            print(f"  [INFO] Created test.wav (440Hz sine wave)")
        except Exception as e:
            print(f"  [WARN] Failed to create test.wav: {e}")
    
    # 创建 M4A (AAC) - 使用 imageio-ffmpeg + pydub
    try:
        import soundfile as sf
        import numpy as np

        # 读取 WAV 数据
        if wav_path.exists():
            data, sr = sf.read(str(wav_path))

            # 创建 FLAC
            flac_path = fixtures_dir / "test.flac"
            if not flac_path.exists():
                try:
                    sf.write(str(flac_path), data, sr, format='FLAC')
                    print(f"  [INFO] Created test.flac")
                except Exception as e:
                    print(f"  [WARN] Failed to create test.flac: {e}")

            # 创建 M4A/AAC - 使用 imageio-ffmpeg 提供的 ffmpeg
            m4a_path = fixtures_dir / "test.m4a"
            if not m4a_path.exists():
                try:
                    import imageio_ffmpeg
                    import pydub
                    ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
                    pydub.AudioSegment.converter = ffmpeg_bin

                    audio = pydub.AudioSegment.from_wav(str(wav_path))
                    audio.export(str(m4a_path), format="ipod")
                    print(f"  [INFO] Created test.m4a")
                except Exception as e:
                    print(f"  [WARN] Failed to create test.m4a: {e}")

    except ImportError:
        print(f"  [WARN] soundfile not installed, skip FLAC/M4A generation")

    # 创建 WebM (VP9) - 使用 imageio-ffmpeg + imageio
    webm_path = fixtures_dir / "test.webm"
    if not webm_path.exists():
        mp4_path = fixtures_dir / "test.mp4"
        if mp4_path.exists():
            try:
                import imageio
                import numpy as np
                import imageio_ffmpeg

                # 用 imageio-ffmpeg 的 ffmpeg 读取 MP4 并写入 WebM
                reader = imageio.get_reader(str(mp4_path))
                fps = reader.get_meta_data().get('fps', 30)
                writer = imageio.get_writer(
                    str(webm_path),
                    fps=fps,
                    codec='libvpx-vp9',
                    pixelformat='yuv420p',
                    quality=8
                )
                for frame in reader:
                    writer.append_data(frame)
                writer.close()
                reader.close()
                print(f"  [INFO] Created test.webm")
            except Exception as e:
                print(f"  [WARN] Failed to create test.webm: {e}")
        else:
            print(f"  [WARN] test.mp4 not found, cannot generate test.webm")


def test_format(sm: StealthMark, ext: str, test_file: Path, output_dir: Path) -> dict:
    """测试单个格式"""
    result = {
        "ext": ext,
        "test_file": str(test_file),
        "embed": None,
        "extract": None,
        "verify": None,
        "output_file": None,
        "status": "UNKNOWN"
    }
    
    output_file = output_dir / f"out_{test_file.name}"
    result["output_file"] = str(output_file)
    
    # 1. Embed
    embed_result = sm.embed(str(test_file), TEST_WATERMARK, str(output_file))
    result["embed"] = {
        "status": embed_result.status.value,
        "status_name": embed_result.status.name,
        "message": embed_result.message
    }
    
    if not embed_result.is_success:
        result["status"] = "EMBED_FAILED"
        return result
    
    # 2. Extract
    extract_result = sm.extract(str(output_file))
    result["extract"] = {
        "status": extract_result.status.value,
        "status_name": extract_result.status.name,
        "message": extract_result.message,
        "watermark": extract_result.watermark
    }
    
    if not extract_result.is_success:
        result["status"] = "EXTRACT_FAILED"
        return result
    
    # 3. Verify
    verify_result = sm.verify(str(output_file), TEST_WATERMARK)
    result["verify"] = {
        "status": verify_result.status.value,
        "status_name": verify_result.status.name,
        "message": verify_result.message,
        "is_valid": verify_result.is_valid,
        "match_score": verify_result.match_score
    }
    
    if verify_result.is_valid:
        result["status"] = "SUCCESS"
    else:
        result["status"] = "VERIFY_FAILED"
    
    return result


def main():
    """主测试函数"""
    print("=" * 60)
    print("StealthMark 全格式测试")
    print("=" * 60)
    print(f"测试水印: {TEST_WATERMARK}")
    print(f"项目目录: {PROJECT_ROOT}")
    print()
    
    fixtures_dir = get_fixtures_dir()
    if not fixtures_dir.exists():
        print(f"[ERROR] 测试数据目录不存在: {fixtures_dir}")
        sys.exit(1)
    
    # 尝试创建缺失的测试文件
    print("[INFO] 检查测试文件...")
    create_missing_test_files(fixtures_dir)
    print()
    
    # 创建临时输出目录
    output_dir = Path(tempfile.mkdtemp(prefix="stealthmark_test_"))
    print(f"[INFO] 输出目录: {output_dir}")
    print()
    
    # 初始化 StealthMark
    sm = StealthMark()
    print(f"[INFO] 已注册 Handler: {len(sm._handler_registry)}")
    print(f"[INFO] 支持格式: {len(sm._handlers)} 种扩展名")
    print()
    
    # 测试结果统计
    results = []
    success_count = 0
    skip_count = 0
    fail_count = 0
    
    print("-" * 60)
    print("开始测试...")
    print("-" * 60)
    
    for ext, filename, skip in FORMAT_CONFIG:
        if skip:
            print(f"  [{ext.upper():>5}] SKIP (无测试文件或需要可选依赖)")
            skip_count += 1
            continue
        
        test_file = fixtures_dir / filename if filename else None
        if not test_file or not test_file.exists():
            print(f"  [{ext.upper():>5}] SKIP (测试文件不存在: {filename})")
            skip_count += 1
            continue
        
        # 执行测试
        result = test_format(sm, ext, test_file, output_dir)
        results.append(result)
        
        status_icon = "[OK]" if result["status"] == "SUCCESS" else "[FAIL]"
        if result["status"] == "SUCCESS":
            success_count += 1
            print(f"  [{ext.upper():>5}] {status_icon} embed/extract/verify 全部通过")
        else:
            fail_count += 1
            print(f"  [{ext.upper():>5}] {status_icon} {result['status']}")
            if result["embed"] and result["embed"]["status"] != 0:
                print(f"         Embed: {result['embed']['message']}")
            elif result["extract"] and result["extract"]["status"] != 0:
                print(f"         Extract: {result['extract']['message']}")
            elif result["verify"] and not result["verify"]["is_valid"]:
                print(f"         Verify: match_score={result['verify']['match_score']}")
    
    print("-" * 60)
    print("测试统计:")
    print(f"  成功: {success_count}")
    print(f"  失败: {fail_count}")
    print(f"  跳过: {skip_count}")
    print(f"  总计: {success_count + fail_count + skip_count}")
    print("-" * 60)
    
    # 清理临时文件
    print()
    print("[INFO] 清理临时文件...")
    try:
        shutil.rmtree(output_dir)
        print(f"[INFO] 已删除: {output_dir}")
    except Exception as e:
        print(f"[WARN] 删除失败: {e}")
    
    # 清理 fixtures 目录中的 out_* 和 test_*_out.* 文件
    print("[INFO] 清理测试产物...")
    cleaned = 0
    for pattern in ["out_*", "test_*_out.*", "verify_*"]:
        for f in fixtures_dir.glob(pattern):
            if f.is_file():
                try:
                    f.unlink()
                    cleaned += 1
                except Exception:
                    pass
            elif f.is_dir():
                try:
                    shutil.rmtree(f)
                    cleaned += 1
                except Exception:
                    pass
    print(f"[INFO] 清理了 {cleaned} 个测试产物")
    
    print()
    print("=" * 60)
    if fail_count == 0:
        print("测试通过!")
    else:
        print(f"测试失败: {fail_count} 个格式未通过")
        sys.exit(1)
    print("=" * 60)


if __name__ == "__main__":
    main()
