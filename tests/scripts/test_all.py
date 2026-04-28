import os, sys
basedir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, basedir)
os.chdir(basedir)
from src.core.manager import StealthMark
import os

sm = StealthMark()
test_dir = os.path.join(basedir, 'tests', 'fixtures')
results = {}

for ext, label in [('pdf','PDF'), ('docx','DOCX'), ('pptx','PPTX'), ('png','PNG'), ('wav','WAV'), ('mp4','MP4')]:
    src = os.path.join(test_dir, f'test.{ext}')
    out = os.path.join(test_dir, f'test_{ext}_out.{ext}')
    if not os.path.exists(src):
        results[label] = 'SKIP: no test file'
        continue
    
    try:
        r = sm.embed(src, label, out)
        if not r.is_success:
            results[label] = f'EMBED_FAIL: {r.message}'
            continue
    except Exception as e:
        results[label] = f'EMBED_ERR: {e}'
        continue
    
    try:
        r = sm.extract(out)
        if r.is_success:
            content = r.watermark.content if hasattr(r.watermark, 'content') else str(r.watermark)
            results[label] = f'OK: extracted=[{content}]'
        else:
            results[label] = f'EXTRACT_FAIL: {r.message}'
    except Exception as e:
        results[label] = f'EXTRACT_ERR: {e}'

for k, v in results.items():
    print(f'{k}: {v}')
