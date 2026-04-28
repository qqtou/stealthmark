import os, sys
basedir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, basedir)
os.chdir(basedir)
from src.core.manager import StealthMark
from src.core.base import WatermarkData
import os

sm = StealthMark()
test_dir = os.path.join(basedir, 'tests', 'fixtures')
results = {}

test_text = "StealthMark-Test-2026"

for ext, label in [('pdf','PDF'), ('docx','DOCX'), ('pptx','PPTX'), ('png','PNG'), ('wav','WAV'), ('mp4','MP4')]:
    src = os.path.join(test_dir, f'test.{ext}')
    out = os.path.join(test_dir, f'verify_{ext}_out.{ext}')
    if not os.path.exists(src):
        results[label] = 'SKIP'
        continue
    
    try:
        r = sm.embed(src, test_text, out)
        if not r.is_success:
            results[label] = f'EMBED_FAIL: {r.message}'
            continue
    except Exception as e:
        results[label] = f'EMBED_ERR: {e}'
        continue
    
    try:
        r = sm.extract(out)
        if not r.is_success:
            results[label] = f'EXTRACT_FAIL: {r.message}'
            continue
        content = r.watermark.content
    except Exception as e:
        results[label] = f'EXTRACT_ERR: {e}'
        continue
    
    try:
        r = sm.verify(out, test_text)
        match = r.is_valid
    except Exception as e:
        match = f'ERR: {e}'
    
    results[label] = f'embed=OK extract=[{content}] verify={match}'

for k, v in results.items():
    print(f'{k}: {v}')
