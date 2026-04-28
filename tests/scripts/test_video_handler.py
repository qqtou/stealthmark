import os, sys
basedir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, basedir)
os.chdir(basedir)

from src.media.video_watermark import VideoHandler
from src.core.base import WatermarkData

h = VideoHandler()

print("=== Embed ===")
r = h.embed(
    os.path.join(basedir, 'tests', 'fixtures', 'test.mp4'),
    WatermarkData(content='Test'),
    os.path.join(basedir, 'tests', 'fixtures', 'test_video_out.mp4')
)
print(f'Status: {r.status}, Message: {r.message}')

print("\n=== Extract ===")
r2 = h.extract(os.path.join(basedir, 'tests', 'fixtures', 'test_video_out.mp4'))
print(f'Status: {r2.status}, Message: {r2.message}')
if r2.watermark:
    print(f'Content: {r2.watermark.content}')
