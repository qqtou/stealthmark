import os, sys
basedir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, basedir)
os.chdir(basedir)

import imageio

mp4_path = os.path.join(basedir, 'tests', 'fixtures', 'test.mp4')
reader = imageio.get_reader(mp4_path)
meta = reader.get_meta_data()
print('FPS:', meta.get('fps'))
print('Duration:', meta.get('duration'))

for i, frame in enumerate(reader):
    print(f'Frame {i}:', frame.shape)
    if i >= 2:
        break
reader.close()
print('OK!')
