# StealthMark 全格式测试通过

**测试时间**: 2026-04-28 17:15

## 测试结果

```
成功: 18
失败: 0
跳过: 10
总计: 28
```

## 通过的格式 (18种)

### 文档 (9种)
- ✅ PDF - 元数据嵌入
- ✅ DOCX - 零宽字符
- ✅ PPTX - 隐藏形状
- ✅ XLSX - 元数据
- ✅ ODT - 元数据
- ✅ ODS - 元数据
- ✅ ODP - 元数据
- ✅ EPUB - 元数据
- ✅ RTF - 元数据

### 图片 (6种)
- ✅ PNG - LSB隐写
- ✅ JPG - DCT域水印
- ✅ BMP - LSB隐写
- ✅ TIFF - LSB隐写
- ✅ WebP - LSB隐写
- ✅ GIF - LSB隐写

### 音频 (1种)
- ✅ WAV - 扩频隐写

### 视频 (2种)
- ✅ MP4 - RGB Blue通道LSB + 无损编码
- ✅ AVI - RGB Blue通道LSB + 无损编码

## 跳过的格式 (10种)

- HEIC - 需要可选依赖
- MP3, FLAC, AAC, M4A - 需要 ffmpeg 生成测试文件
- WebM, WMV, MKV, MOV - 无测试文件
- JPEG - 与 JPG 相同扩展名

## JPG 修复详情

### 问题
1. 测试图像太小（100×100）且为纯色，无法嵌入
2. DCT 嵌入算法太弱，±1 调整被 JPEG 重编码破坏
3. 提取逻辑错误，期望长度前缀但编码数据无前缀

### 解决方案
1. 创建 800×600 有纹理渐变测试图像
2. 改进 DCT 嵌入：强制块均值到高区(≥160)或低区(≤96)
3. 修复提取：移除长度前缀解析，直接让 codec 解码

### 代码变更

**embed 改进**:
```python
# 使用更鲁棒的方法：强制块均值到目标区间
# bit=1 -> 均值 >= 160 (高区)
# bit=0 -> 均值 <= 96 (低区)
HIGH_THRESH = 160
LOW_THRESH = 96

if data_bits[bit_idx] == 1:
    if dct_mean < HIGH_THRESH:
        delta = HIGH_THRESH - dct_mean + 10
        block = block + delta
else:
    if dct_mean > LOW_THRESH:
        delta = LOW_THRESH - dct_mean - 10
        block = block + delta
```

**extract 修复**:
```python
# 直接提取编码数据（无需长度前缀，codec内部有格式）
MAX_DATA_SIZE = 1024  # 最多提取 1KB 数据
data_bits = bits[sync_idx:sync_idx + MAX_DATA_SIZE * 8]
# 转换为字节并让 codec 解析
```

## 测试命令

```powershell
cd D:\work\code\stealthmark
python tests/scripts/test_all_formats.py
```

## 后续建议

1. **性能测试**: 测试大文件（100MB+）的处理性能
2. **鲁棒性测试**: 测试水印在文件编辑后的存活率
3. **覆盖率测试**: 增加单元测试覆盖率
