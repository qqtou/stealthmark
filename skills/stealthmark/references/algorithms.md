# 水印算法原理

## 核心水印流程

所有格式的水印处理遵循统一流程：

```
水印文本 → Codec (UTF-8 → 二进制 → CRC32 → Base64) → 格式特定 Handler → 嵌入/提取
```

## 编解码器 (Codec)

### 编码流程
```
"CONFIDENTIAL" → UTF-8 bytes → CRC32 校验 (4 bytes) → Base64 → payload bytes
```

### 解码流程
```
payload bytes → Base64 解码 → 分离数据/CRC → CRC32 校验 → UTF-8 解码 → 水印文本
```

### 可选加密
- 启用时：编码前用 AES-256-CBC 加密 (`--encrypt` + `--key`)
- 密钥派生：PBKDF2 (100k iterations)

## 文档类算法

### 零宽字符 (DOCX)
利用 Unicode 零宽字符表示二进制：
- `\u200b` (ZWSP) = bit 0
- `\u200c` (ZWNJ) = bit 1

水印通过 Word 的 "隐藏文字" 功能隐入，肉眼不可见但 Word XML 解析可见。

### 元数据嵌入 (PDF, MP3, FLAC)
将水印 payload 写入文件元数据字段：
- PDF: `/Info` 字典的自定义字段
- MP3: `ID3v2.4/TALB` 或 `COMM` 帧
- FLAC: Vorbis Comment

### XML 属性修改 (PPTX, XLSX, ODT 等)
这些格式本质是 ZIP 压缩的 XML 文件：
1. 解压 ZIP
2. 在 XML 属性中插入水印数据
3. 重新压缩

## 图片类算法

### LSB (最低有效位)
最经典的图片水印算法：

```
原始像素: 10110101
修改后:  10110100  (LSB 从 1 变为 0)
```

StealthMark 采用 **LSB 3倍冗余**：
- 每个数据 bit 重复 3 次（嵌入 3 个像素 LSB）
- 提取时多数表决（3 中 2 以上为 1 则取 1）

### DCT (JPEG)
在离散余弦变换系数中嵌入：
1. 将图片转换为 YCbCr 色彩空间
2. 对 Cb/Cr 通道做 DCT
3. 在中频系数中嵌入水印
4. 逆 DCT 生成水印图片

优势：不易被 JPEG 重压缩破坏

## 音频类算法

### 扩频水印 (WAV)
基于扩频通信原理：

1. **PN 序列生成**：用伪随机噪声序列扩展水印信号
2. **频谱扩展**：将窄带水印扩展到整个音频频带
3. **能量叠加**：以极低能量（alpha ≈ 0.005-0.05）叠加到音频
4. **自适应强度**：低能量音频段用更高 alpha

### 自适应嵌入
```python
# 音频能量低时，提高嵌入强度
rms = np.sqrt(np.mean(audio**2))
alpha = base_alpha * (1.0 / rms) if rms > threshold else base_alpha * 2.0
```

## 视频类算法

### RGB 蓝通道 LSB
视频水印在像素级别嵌入：

1. 解码视频为帧序列
2. 在 **Blue 通道** 的最低位嵌入水印
3. **同步头**：8 字节同步标记重复 8 次，提升定位鲁棒性
4. **多帧分布**：水印分布在连续 3 帧，避免单帧损坏导致完全失败

### 无损编码
```bash
ffmpeg -i input.mp4 -c:v libx264rgb -crf 0 output.mp4
```
使用 `libx264rgb` 而非 `libx264`，避免 YUV 转换损失 LSB 修改。

## 有损格式说明

以下格式有损压缩，水印提取失败为预期行为：
- JPEG：重压缩会改变 DCT 系数
- MP3：AAC：音频有损压缩改变采样
- HEIC：HEIF：图片有损压缩

CRC 验证在有损格式上放宽：magic bytes `SMARK` 匹配即接受结果。
