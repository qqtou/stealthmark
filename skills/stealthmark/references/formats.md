# 支持格式详解

## 文档格式 (9种)

### PDF (.pdf)
- **Handler**: PdfHandler
- **算法**: 元数据嵌入，将水印写入 PDF 文档元数据字段
- **容量**: ~200 字符
- **限制**: 无特别限制，PDF 1.4+ 支持

### Word (.docx)
- **Handler**: DocxHandler
- **算法**: 零宽字符（\u200b=0, \u200c=1）插入到文本内容中
- **容量**: ~500 字符
- **限制**: 需保留 XML 结构，复杂格式可能影响

### PowerPoint (.pptx)
- **Handler**: PptxHandler
- **算法**: 隐藏形状属性，将水印数据编码为形状 ID
- **容量**: ~300 字符
- **限制**: 隐藏形状数量有限制

### Excel (.xlsx)
- **Handler**: XlsxHandler
- **算法**: XML 属性修改，扩展 XML 标签存储水印
- **容量**: ~200 字符
- **限制**: 需保留工作簿结构

### ODT (.odt), ODS (.ods), ODP (.odp)
- **Handler**: OdtHandler, OdsHandler, OdpHandler
- **算法**: XML 属性修改，与 XLSX 类似
- **容量**: ~200 字符
- **限制**: LibreOffice 格式支持

### EPUB (.epub)
- **Handler**: EpubHandler
- **算法**: XML 属性修改，水印存储在 OPF 元数据中
- **容量**: ~200 字符
- **限制**: 需符合 EPUB 规范

### RTF (.rtf)
- **Handler**: RtfHandler
- **算法**: 控制字注入，水印嵌入到 RTF 控制字序列中
- **容量**: ~100 字符
- **限制**: 纯 RTF 格式，不支持富文本

## 图片格式 (7种)

### PNG (.png)
- **Handler**: ImageHandler (LSB 冗余)
- **算法**: 最低有效位（LSB）3倍冗余嵌入，每 bit 重复 3 次，多数表决提取
- **容量**: ~500 字节（基于图片尺寸）
- **限制**: 有损压缩（如 JPEG 存储后）可能破坏水印

### JPEG (.jpg, .jpeg)
- **Handler**: ImageHandler (DCT)
- **算法**: 离散余弦变换域嵌入，水印写入 DCT 系数
- **容量**: ~500 字节
- **限制**: 重压缩会降低提取成功率

### BMP (.bmp)
- **Handler**: ImageHandler (LSB)
- **算法**: 最低有效位嵌入，无压缩
- **容量**: ~1KB（基于图片尺寸）
- **限制**: 无

### GIF (.gif)
- **Handler**: GifHandler
- **算法**: LSB 嵌入，帧间抖动容忍
- **容量**: ~300 字节
- **限制**: 动画 GIF 逐帧处理

### TIFF (.tif, .tiff)
- **Handler**: TiffHandler
- **算法**: LSB 嵌入，支持多页 TIFF
- **容量**: ~1KB
- **限制**: 取决于标签结构

### WebP (.webp)
- **Handler**: WebpHandler
- **算法**: LSB 嵌入（无损模式）
- **容量**: ~500 字节
- **限制**: 有损 WebP 可能有影响

### HEIC (.heic)
- **Handler**: HeicHandler
- **算法**: EXIF 元数据嵌入
- **限制**: 有损压缩，成功率较低

## 音频格式 (5种)

### WAV (.wav)
- **Handler**: WavHandler
- **算法**: 扩频水印（Spread Spectrum），伪随机序列扩频 + 低能量叠加
- **容量**: ~32 字符/5秒音频
- **特性**: 自适应嵌入强度，低能量段用更高 alpha

### MP3 (.mp3)
- **Handler**: Mp3Handler
- **算法**: ID3 元数据 COMMENT 帧存储
- **限制**: 有损格式，提取成功率依赖 ID3 标签完整性

### FLAC (.flac)
- **Handler**: FlacHandler
- **算法**: Vorbis 元数据 COMMENT 帧
- **限制**: 无损格式，完美支持

### AAC (.aac)
- **Handler**: AacHandler
- **算法**: ID3 元数据 + ffmpeg 转码
- **注意**: 嵌入后输出 .m4a（ALAC 无损编码需 M4A 容器）
- **限制**: 有损 AAC 提取不稳定

### OGG (.ogg)
- **Handler**: OggHandler
- **算法**: Vorbis 元数据 COMMENT 帧（mutagen 库）
- **限制**: Vorbis Comment 规范限制

## 视频格式 (8种)

### MP4 (.mp4)
- **Handler**: VideoHandler
- **算法**: RGB 蓝通道 LSB + libx264rgb 无损编码（CRF 0）
- **容量**: ~30 字节/帧
- **特性**: 同步头 8 次重复，前 3 帧分布提升鲁棒性

### AVI (.avi)
- **Handler**: VideoHandler
- **算法**: 同 MP4
- **限制**: 仅支持特定编码格式

### MKV (.mkv)
- **Handler**: VideoHandler
- **算法**: 同 MP4
- **特性**: imageio-ffmpeg 生成

### MOV (.mov)
- **Handler**: VideoHandler
- **算法**: 同 MP4
- **限制**: QuickTime 格式

### WebM (.webm)
- **Handler**: WebmHandler
- **算法**: RGB 蓝通道 LSB + VP9 编码
- **限制**: VP9 编码可能损失部分水印

### WMV (.wmv)
- **Handler**: WmvHandler
- **算法**: RGB 蓝通道 LSB
- **限制**: WMV 编码格式特殊

### OGG Video (.ogv)
- **Handler**: VideoHandler（扩展）
- **限制**: OGV 视频格式支持待完善

## 格式支持状态总结

| 状态 | 说明 |
|------|------|
| 稳定 | PDF, DOCX, PPTX, PNG, WAV, MP4, FLAC |
| 良好 | XLSX, ODT/ODS/ODP, BMP, GIF, TIFF, WebP, AVI, MKV, MOV |
| 测试中 | HEIC, HEIF, OGV, OGG, AAC |
