# 31 种格式、1 套架构：StealthMark 隐式水印工具的技术选型与实现

> 当你需要为一个支持 31 种文件格式的水印工具设计架构时，核心挑战不是「怎么做」，而是「如何选择」——每个选择都意味着妥协，本文记录 StealthMark 的决策历程。

## 1. 痛点与目标

StealthMark 的起因：需要一个支持多格式文件的隐形水印工具。

**核心目标：**
- 支持 31 种常见格式（文档、图片、音频、视频）
- 嵌入 / 提取 / 验证三种操作
- CLI / GUI / API 三种接口
- 可逆（可提取原始水印）

**约束条件：**
- Python 生态优先（易集成）
- 嵌入后文件无感知差异（视觉/听觉不可察觉）
- 有损格式（MP3/HEIC）无法保证提取成功（这是客观限制，不是 bug）

## 2. 架构设计：Handler 模式

### 2.1 核心问题

31 种格式的水印算法完全不同：
- PDF：修改元数据 / 隐藏文本
- DOCX：零宽字符
- PNG：LSB 位平面
- JPEG：DCT 系数
- WAV：扩频调制
- MP4：RGB LSB + 无损编码

### 2.2 解决思路：策略模式

每个格式对应一个 Handler，封装独立的水印算法：

```python
class Handler(ABC):
    @abstractmethod
    def embed(self, input_path: str, watermark: str, output_path: str) -> WatermarkResult:
        pass
    
    @abstractmethod
    def extract(self, input_path: str) -> WatermarkResult:
        pass
    
    @abstractmethod
    def verify(self, input_path: str, watermark: str) -> bool:
        pass
```

Manager 负责根据文件扩展名分发：

```python
def get_handler(path: str) -> Handler:
    ext = Path(path).suffix.lower()
    return handler_registry[ext]()
```

### 2.3 注册机制

```python
# handlers/__init__.py
HANDLERS = {
    '.pdf': PDFHandler,
    '.png': PNGHandler,
    '.jpg': JPEGHandler,
    '.wav': WAVHandler,
    '.mp4': MP4Handler,
    # ... 31 种格式
}
```

**关键决策：**
- 运行时注册而非静态 import（支持插件扩展）
- 扩展名精确匹配（避免 .jpeg/.jpg 歧义）
- 未知格式直接抛出明确异常

## 3. 编解码层：水印内容的标准化

### 3.1 编码 Pipeline

水印内容需要经过三层处理：

```
Watermark String → UTF-8 Bytes → CRC32 (4 bytes) → AES-256 (可选) → Base64 → Embeddable Data
```

**为什么需要这三层？**

| 层级 | 作用 | 必要性 |
|------|------|--------|
| CRC32 | 校验提取内容完整性 | 必须（有损压缩可能导致 bit 错误） |
| AES-256 | 加密 | 可选 |
| Base64 | 转换为可嵌入格式 | 必须（零宽字符等需要文本安全字符） |

### 3.2 水印内容格式

```json
{
  "issuer": "user:13800138000",
  "file_id": "FILE-2025-001",
  "timestamp": 1704067200,
  "type": "ownership",
  "extra": {}
}
```

**关键决策：**
- JSON 而非纯文本（结构化便于解析）
- issuer + file_id 唯一标识文件
- timestamp 记录时间

## 4. 分格式策略

### 4.1 文档类（9 种）

| 格式 | 算法 | 说明 |
|------|------|------|
| PDF | 元数据 / 自定义属性 | 支持加密 PDF |
| DOCX | 零宽字符（\u200b=0, \u200c=1） | 隐藏于文字间 |
| XLSX | 隐藏 sheet / 单元格属性 | |
| PPTX | 隐藏形状 | 需保留原布局 |
| ODT/ODS/ODP | XML 属性修改 | 统一用 odt_watermark |
| EPUB | 元数据 | |
| RTF | 隐藏控制字 | |

**关键决策：**
- 零宽字符方案统一应用于所有 XML 格式（DOCX/XLSX/PPTX/ODT/ODS/ODP）
- 原因：XML 可保留隐藏属性，跨平台兼容

### 4.2 图片类（9 种）

| 格式 | 算法 | 备注 |
|------|------|------|
| PNG | LSB（3 倍冗余） | 每 bit 重复 3 次，多数表决提取 |
| JPEG | DCT 中频系数 | 修改 DCT[3,3] |
| BMP | LSB | 无压缩直接修改位平面 |
| GIF | LSB | 帧动画仅修改第一帧 |
| TIFF | LSB | |
| WEBP | LSB / DCT | 有损模式用 DCT |
| HEIC | LSB（有损敏感） | HEVC 有损，CRC 校验放宽 |
| SVG | XML 属性 | 路径 data 中隐藏 |

**关键决策：**
- LSB 作为默认算法（DCT 对 JPEG 有依赖问题，最终回退到块均值）
- 3 倍冗余抵抗小幅度噪声
- 有损格式（HEIC/JPEG）放宽 CRC 校验（magic bytes 匹配即接受）

### 4.3 音视频类（13 种）

| 类别 | 格式 | 算法 |
|------|------|------|
| 音频 | WAV | 扩频水印（自适应 alpha） |
| 音频 | MP3 | ID3 COMMENT 元数据 |
| 音频 | FLAC | 无损，直接修改样本 |
| 音频 | AAC | ffmpeg 写入 m4a（ALAC） |
| 音频 | OGG | VorbisComment 元数据 |
| 视频 | MP4/WebM | RGB 蓝通道 LSB + libx264rgb 无损 |
| 视频 | AVI | RGB LSB + 无损编码 |
| 视频 | WMV | RGB LSB + 无损编码 |
| 视频 | MOV | RGB LSB + ProRes 无损 |
| 视频 | MKV | RGB LSB + 无损 |
| 视频 | FLV | RGB LSB |
| 视频 | MPEG | RGB LSB |
| 视频 | 3GP | RGB LSB |

**关键决策：**
- 视频用 RGB 而非 YUV（YUV 转换破坏 LSB）
- libx264rgb -crf 0 实现无损编码（不能用 libx264 yuv444p）
- 同步头 8 次重复（前 3 帧分散）提升鲁棒性
- WAV 自适应嵌入强度（基于音频能量调整 alpha）

## 5. 三种接口设计

### 5.1 CLI

```bash
stealthmark embed -i input.pdf -m "hello" -o output.pdf
stealthmark extract -i output.pdf
stealthmark verify -i output.pdf -m "hello"
stealthmark batch -d ./files -m "watermark" -o ./output
```

**关键决策：**
- 子命令模式（而非单命令 + flag）
- -m 接受字符串（CLI 场景简单）
- JSON 文件用 -f 指定
- batch 并行处理 + 进度条（-v 显示）

### 5.2 GUI（PyQt6）

主要界面：
- 单文件嵌入 / 提取 tab
- 批量处理 tab
- 设置（水印内容模板、输出目录）

**关键决策：**
- PyQt6 而非 Tkinter（更现代）
- 本地桌面应用（非 Web）

### 5.3 API（FastAPI）

端点设计：

```
POST /embed          # multipart 文件 + watermark
POST /extract       # multipart 文件
POST /verify        # multipart 文件 + watermark
POST /watermark/generate  # JSON → watermark string
POST /validate      # 验证 watermark JSON 格式
GET  /health        # 健康检查
```

**关键决策：**
- FastAPI 而非 Flask（类型提示、自动文档）
- 限流：slowapi（30 req/min for embed/extract）
- 文件存本地（config.ini 配置存储路径）
- CORS 支持跨域调用

## 6. 踩过的坑与决策依据

### 6.1 视频水印：RGB vs YUV

**问题**：最初用 YUV 空间的 Y 通道 LSB，ffmpeg 转码后 LSB 全变。

**原因**：RGB → YUV → RGB 转换有精度损失，LSB 被污染。

**解决**：纯 RGB 空间修改 Blue 通道 LSB，ffmpeg 用 libx264rgb（RGB 直通）编码。

### 6.2 单帧 vs 多帧

**问题**：水印分散到多帧时，帧序号错位导致提取失败。

**原因**：视频重编码 GOP 重组，帧位置偏移。

**解决**：单帧嵌入（仅第一帧 Blue 通道 LSB），同步头 8 次重复。

### 6.3 有损格式的 CRC 校验

**问题**：MP3/HEIC 有损压缩，CRC 匹配率极低。

**原因**：压缩损失信息位，水印 bit 错误。

**解决**：对有损格式放宽 CRC（magic bytes `SMARK` 匹配即接受），不保证提取成功。

### 6.4 DCT 域水印失败

**问题**：DCT 修改后 `astype(np.uint8)` 截断导致系数精度丢失。

**现象**：原始 bits=[1,0,1,0,1,0,1,0] 与提取完全不匹配。

**解决**：回退到空间域块均值（HIGH_THRESH=180, LOW_THRESH=76）。

## 7. 技术选型总结

| 维度 | 选择 | 依据 |
|------|------|------|
| 核心架构 | Handler 模式 | 算法差异大，需要策略分离 |
| 水印格式 | JSON + CRC + AES + Base64 | 结构化 + 完整性 + 加密 + 可嵌入 |
| 图片算法 | LSB（3 倍冗余） | 简单、效果好、有冗余 |
| 视频算法 | RGB LSB + libx264rgb | YUV 转换破坏 LSB |
| 音频算法 | WAV 扩频 / MP3 ID3 | 元数据最稳定 |
| 接口 | CLI + GUI + API | 覆盖桌面 / 命令行 / 集成场景 |
| 测试 | 124 tests | 覆盖所有 Handler |

## 8. v0.2.0 规划

- [ ] Docker 打包
- [ ] AAC Handler 重写
- [ ] HEIC CRC 策略优化
- [ ] Handler docstring 补全

---

**项目地址**：https://github.com/qqtou/stealthmark
**当前版本**：v0.1.0
**测试覆盖**：124 tests，0 failures