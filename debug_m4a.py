import subprocess, imageio_ffmpeg, os, json

ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
m4a = r'D:\work\code\stealthmark\tests\fixtures\test_m4a_long.m4a'
print(f"File: {m4a}, size={os.path.getsize(m4a)} bytes")

# Probe M4A with ffmpeg
r = subprocess.run([str(ffmpeg), '-v', 'quiet', '-print_format', 'json',
                    '-show_format', '-show_streams', m4a],
                   capture_output=True, text=True)
try:
    info = json.loads(r.stdout)
    for s in info.get('streams', []):
        print(f"Stream: codec={s.get('codec_name')}, sr={s.get('sample_rate')}, "
              f"ch={s.get('channels')}, dur={s.get('duration')}")
    fmt = info.get('format', {})
    print(f"Format: {fmt.get('format_name')}, dur={fmt.get('duration')}")
except Exception as e:
    print("Probe error:", e)
    print("stdout:", r.stdout[:300])
    print("stderr:", r.stderr[:300])

# Check soundfile write formats
import soundfile as sf
subs = list(sf.available_subtypes().keys())
print("\nSoundfile write formats (audio):")
for s in subs:
    print(f"  {s}")

# Check if audioread has any backend
print("\nAudioread backends:")
try:
    import audioread
    print(audioread.having_libsamplerate())
    print("Available:", audioread.audio_open)
except Exception as e:
    print(e)
