import os
import sys

basedir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(basedir)

test_dir = os.path.join(basedir, 'tests', 'fixtures')
os.makedirs(test_dir, exist_ok=True)

print("生成缺失的测试文件...")

# 1. JPEG - 用 Pillow
try:
    from PIL import Image
    img = Image.new('RGB', (800, 600), color='red')
    img.save(os.path.join(test_dir, 'test.jpeg'), 'JPEG')
    print("  [OK] test.jpeg")
except Exception as e:
    print(f"  [FAIL] test.jpeg: {e}")

# 2. TIFF - 用 Pillow
try:
    from PIL import Image
    img = Image.new('RGB', (800, 600), color='green')
    img.save(os.path.join(test_dir, 'test.tif'), 'TIFF')
    print("  [OK] test.tif")
except Exception as e:
    print(f"  [FAIL] test.tif: {e}")

# 3. HEIC - 尝试用 Pillow + libheif，如果失败则复制 PNG 并改扩展名（仅用于测试结构）
try:
    # 先尝试用 pillow-heif
    try:
        from pillow_heif import register_heif_opener
        register_heif_opener()
        from PIL import Image
        img = Image.new('RGB', (800, 600), color='blue')
        img.save(os.path.join(test_dir, 'test.heic'), 'HEIF')
        print("  [OK] test.heic (with pillow-heif)")
    except ImportError:
        # 退而求其次：复制一个现有的 PNG 并改名（handler 会尝试处理）
        import shutil
        src = os.path.join(test_dir, 'test.png')
        if os.path.exists(src):
            # 创建一个最小化的 HEIC 占位（实际上 handler 可能无法处理，但至少文件存在）
            # 更好的方法是创建一个有效的 HEIC 文件
            # 这里我们用 imageio 尝试
            import numpy as np
            try:
                import imageio.v3 as iio
                # 创建一个简单帧
                frame = np.zeros((100, 100, 3), dtype=np.uint8)
                iio.imwrite(os.path.join(test_dir, 'test.heic'), frame, extension=".heic")
                print("  [OK] test.heic (with imageio)")
            except Exception as e2:
                print(f"  [WARN] test.heic: {e2}, 创建空占位文件")
                with open(os.path.join(test_dir, 'test.heic'), 'wb') as f:
                    f.write(b'\x00\x00\x00\x20ftypheic')  # 最小 HEIC 头
        else:
            print("  [SKIP] test.heic: 无源文件参考")
except Exception as e:
    print(f"  [FAIL] test.heic: {e}")

# 4. MP3 - 用 pydub 生成静音
try:
    try:
        from pydub import AudioSegment
        # 生成 1 秒静音
        silent = AudioSegment.silent(duration=1000)
        silent.export(os.path.join(test_dir, 'test.mp3'), format='mp3')
        print("  [OK] test.mp3")
    except ImportError:
        # 退而求其次：复制 WAV 并用 ffmpeg 转换（如果有）
        import shutil
        src = os.path.join(test_dir, 'test.wav')
        if os.path.exists(src):
            shutil.copy(src, os.path.join(test_dir, 'test.mp3'))
            print("  [WARN] test.mp3: 复制自 WAV（非真实 MP3）")
        else:
            print("  [SKIP] test.mp3: pydub 未安装且无 WAV 源")
except Exception as e:
    print(f"  [FAIL] test.mp3: {e}")

# 5. AAC - 类似 MP3
try:
    try:
        from pydub import AudioSegment
        silent = AudioSegment.silent(duration=1000)
        silent.export(os.path.join(test_dir, 'test.aac'), format='adts')
        print("  [OK] test.aac")
    except ImportError:
        import shutil
        src = os.path.join(test_dir, 'test.wav')
        if os.path.exists(src):
            shutil.copy(src, os.path.join(test_dir, 'test.aac'))
            print("  [WARN] test.aac: 复制自 WAV（非真实 AAC）")
        else:
            print("  [SKIP] test.aac: pydub 未安装且无 WAV 源")
except Exception as e:
    print(f"  [FAIL] test.aac: {e}")

# 6. MOV - 用 imageio 生成简单视频
try:
    import numpy as np
    import imageio.v3 as iio
    # 创建 10 帧的简单视频
    frames = []
    for i in range(10):
        frame = np.full((100, 100, 3), i * 25, dtype=np.uint8)
        frames.append(frame)
    iio.imwrite(os.path.join(test_dir, 'test.mov'), frames, fps=5, codec='libx264')
    print("  [OK] test.mov")
except Exception as e:
    print(f"  [FAIL] test.mov: {e}")
    # 尝试用 mp4 复制
    try:
        import shutil
        src = os.path.join(test_dir, 'test.mp4')
        if os.path.exists(src):
            shutil.copy(src, os.path.join(test_dir, 'test.mov'))
            print("  [WARN] test.mov: 复制自 MP4")
    except:
        pass

# 7. WMV - Windows Media Video，尝试用 imageio
try:
    import numpy as np
    import imageio.v3 as iio
    frames = []
    for i in range(10):
        frame = np.full((100, 100, 3), 255 - i * 25, dtype=np.uint8)
        frames.append(frame)
    # WMV 可能需要特定编码器，尝试 wmv2
    iio.imwrite(os.path.join(test_dir, 'test.wmv'), frames, fps=5, codec='wmv2')
    print("  [OK] test.wmv")
except Exception as e:
    print(f"  [FAIL] test.wmv: {e}")
    # 复制 MP4 作为后备
    try:
        import shutil
        src = os.path.join(test_dir, 'test.mp4')
        if os.path.exists(src):
            shutil.copy(src, os.path.join(test_dir, 'test.wmv'))
            print("  [WARN] test.wmv: 复制自 MP4")
    except:
        pass

print("\n完成。重新运行 test_all.py 测试。")
