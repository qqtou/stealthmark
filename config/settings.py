# config/settings.py
"""
StealthMark 默认配置
"""

DEFAULT_CONFIG = {
    # 通用设置
    'debug': False,
    'log_file': None,
    
    # 编解码设置
    'password': None,
    
    # PDF设置
    'pdf_embed_method': 'metadata',
    
    # 图片设置
    'jpeg_quality': 95,
    'png_compress': 6,
    
    # 音频设置
    'audio_spread_factor': 31,
    'audio_alpha': 0.005,
    'audio_bits_per_sample': 1000,
    
    # 视频设置
    'video_frame_interval': 30,
    'video_alpha': 0.1,
}