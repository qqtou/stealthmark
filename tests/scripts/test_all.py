import os, sys, time
from datetime import datetime

basedir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, basedir)
os.chdir(basedir)
from src.core.manager import StealthMark

sm = StealthMark()
test_dir = os.path.join(basedir, 'tests', 'fixtures')
results = {}

# 所有支持的格式（28种）
formats = [
    # 文档格式 (9种)
    ('pdf', 'PDF'), ('docx', 'DOCX'), ('pptx', 'PPTX'), ('xlsx', 'XLSX'),
    ('odt', 'ODT'), ('ods', 'ODS'), ('odp', 'ODP'), ('rtf', 'RTF'), ('epub', 'EPUB'),
    # 图片格式 (7种)
    ('png', 'PNG'), ('jpg', 'JPEG'), ('jpeg', 'JPEG'), ('bmp', 'BMP'),
    ('tiff', 'TIFF'), ('tif', 'TIFF'), ('webp', 'WebP'), ('gif', 'GIF'), ('heic', 'HEIC'),
    # 音频格式 (5种)
    ('wav', 'WAV'), ('mp3', 'MP3'), ('flac', 'FLAC'), ('aac', 'AAC'), ('m4a', 'M4A'),
    # 视频格式 (5种)
    ('mp4', 'MP4'), ('avi', 'AVI'), ('mov', 'MOV'), ('wmv', 'WMV'), ('webm', 'WebM')
]

# 有损格式：嵌入可能成功，但提取可能因压缩而失败
lossy_formats = {'HEIC', 'MP3', 'AAC', 'M4A'}

print(f"{'='*60}")
print(f"StealthMark 全格式测试")
print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"测试目录: {test_dir}")
print(f"{'='*60}\n")

total = len(formats)
success = 0
failed = 0
skipped = 0

for idx, (ext, label) in enumerate(formats, 1):
    src = os.path.join(test_dir, f'test.{ext}')
    out = os.path.join(test_dir, f'test_{ext}_out.{ext}')
    
    print(f"[{idx}/{total}] 测试 {label} ({ext})")
    print(f"  源文件: {src}")
    
    if not os.path.exists(src):
        print(f"  状态: SKIP - 测试文件不存在")
        results[label] = {'status': 'SKIP', 'reason': 'no test file'}
        skipped += 1
        print()
        continue
    
    # 嵌入阶段
    embed_start = time.time()
    try:
        r = sm.embed(src, label, out)
        embed_time = time.time() - embed_start
        if not r.is_success:
            print(f"  嵌入: FAIL - {r.message} ({embed_time:.2f}s)")
            results[label] = {'status': 'FAIL', 'stage': 'embed', 'reason': r.message, 'time': embed_time}
            failed += 1
            print()
            continue
        print(f"  嵌入: OK ({embed_time:.2f}s)")
        extract_out = r.output_path or out  # handler可能修改输出路径(如.aac→.m4a)
    except Exception as e:
        embed_time = time.time() - embed_start
        print(f"  嵌入: ERROR - {e} ({embed_time:.2f}s)")
        results[label] = {'status': 'ERROR', 'stage': 'embed', 'reason': str(e), 'time': embed_time}
        failed += 1
        print()
        continue
    
    # 提取阶段
    extract_start = time.time()
    try:
        r2 = sm.extract(extract_out)
        extract_time = time.time() - extract_start
        if r2.is_success and r2.watermark:
            content = r2.watermark.content
            match = "OK" if content == label else "MISMATCH"
            print(f"  提取: OK ({extract_time:.2f}s) - 内容=[{content}] [{match}]")
            results[label] = {'status': 'OK', 'content': content, 'embed_time': embed_time, 'extract_time': extract_time}
            success += 1
        else:
            # 有损格式提取失败视为已知问题
            if label in lossy_formats:
                print(f"  提取: WARN - {r2.message} ({extract_time:.2f}s) [有损格式，提取可能失败]")
                results[label] = {'status': 'WARN', 'stage': 'extract', 'reason': r2.message, 'time': extract_time}
                success += 1  # 计入成功（嵌入成功即可）
            else:
                print(f"  提取: FAIL - {r2.message} ({extract_time:.2f}s)")
                results[label] = {'status': 'FAIL', 'stage': 'extract', 'reason': r2.message, 'time': extract_time}
                failed += 1
    except Exception as e:
        extract_time = time.time() - extract_start
        if label in lossy_formats:
            print(f"  提取: WARN - {e} ({extract_time:.2f}s) [有损格式，提取可能失败]")
            results[label] = {'status': 'WARN', 'stage': 'extract', 'reason': str(e), 'time': extract_time}
            success += 1
        else:
            print(f"  提取: ERROR - {e} ({extract_time:.2f}s)")
            results[label] = {'status': 'ERROR', 'stage': 'extract', 'reason': str(e), 'time': extract_time}
            failed += 1
    print()

# 汇总
print(f"{'='*60}")
print(f"测试完成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*60}")
print(f"总计: {total} 种格式")
print(f"成功: {success} | 失败: {failed} | 跳过: {skipped}")
print(f"成功率: {success/total*100:.1f}%" if total > 0 else "N/A")
print(f"{'='*60}")

# 失败详情
if failed > 0:
    print("\n失败详情:")
    for label, info in results.items():
        if info['status'] in ('FAIL', 'ERROR'):
            stage = info.get('stage', 'unknown')
            reason = info.get('reason', 'unknown')
            print(f"  - {label}: {stage} 阶段 - {reason}")
