import os, sys
basedir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, basedir)
os.chdir(basedir)
from src.core.manager import StealthMark
from PIL import Image

wm = StealthMark()
MARK = 'SM-2026'
FIXTURES = os.path.join(basedir, 'tests', 'fixtures')

tests = [
    ('XLSX', 'test.xlsx', 'out_xlsx.xlsx'),
    ('ODT',  'test.odt',  'out_odt.odt'),
    ('ODS',  'test.ods',  'out_ods.ods'),
    ('ODP',  'test.odp',  'out_odp.odp'),
    ('RTF',  'test.rtf',  'out_rtf.rtf'),
    ('EPUB', 'test.epub', 'out_epub.epub'),
    ('TIFF', 'test.tiff', 'out_tiff.tiff'),
    ('WebP', 'test.webp', 'out_webp.webp'),
    ('GIF',  'test.gif',  'out_gif.gif'),
]

ok_count = 0
for name, src, out in tests:
    src_path = os.path.join(FIXTURES, src)
    out_path = os.path.join(FIXTURES, out)
    if not os.path.exists(src_path):
        print('[MISSING]', name, src_path)
        continue
    r1 = wm.embed(src_path, MARK, out_path)
    r2 = wm.extract(out_path)
    ok = r2.is_success and r2.watermark is not None and r2.watermark.content == MARK
    mark = r2.watermark.content if r2.watermark else '(none)'
    tag = '[OK]' if ok else '[FAIL]'
    print(tag, name, '- status:', r2.status.name, '- extracted:', repr(mark))
    if ok:
        ok_count += 1

print()
print('Result:', ok_count, '/', len(tests), 'passed')
