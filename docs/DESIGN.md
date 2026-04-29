# StealthMark 隐式水印系统设计方案

## 1. 项目概述

**项目名称**: StealthMark
**项目定位**: 文档、音视频隐式水印工具
**核心功能**: 为各类文档和音视频文件添加不可见的数字水印，支持水印提取与验证

---

## 2. 整体架构

### 2.1 核心流程

```
┌─────────────────────────────────────────────────────────────────┐
│                          水印嵌入流程                            │
│  输入文件 ──▶ 水印编码 ──▶ 嵌入算法 ──▶ 输出文件(含水印)        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                          水印提取流程                            │
│  含水印文件 ──▶ 提取算法 ──▶ 水印解码 ──▶ 水印内容              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                          水印验证流程                            │
│  提取内容 vs 原始水印 ──▶ 完整性校验 ──▶ 一致性比对 ──▶ 结果    │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 模块架构

```
stealthmark/
├── src/
│   ├── __init__.py             # 包入口
│   ├── __main__.py             # python -m 入口
│   ├── core/                   # 核心模块
│   │   ├── base.py             # 基类定义（BaseHandler, WatermarkStatus, 结果数据类）
│   │   ├── codec.py            # 水印编码/解码/加密（AES-256）
│   │   ├── exceptions.py       # 异常类定义
│   │   ├── manager.py          # 门面类（StealthMark主入口）
│   │   └── __init__.py
│   ├── document/               # 文档水印模块
│   │   ├── pdf_watermark.py    # PDF（元数据嵌入）
│   │   ├── docx_watermark.py   # Word（零宽字符隐写）
│   │   ├── pptx_watermark.py   # PowerPoint（隐藏形状）
│   │   ├── xlsx_watermark.py   # Excel（customXml属性）
│   │   ├── odt_watermark.py    # ODF文本（user-defined元数据）
│   │   ├── ods_watermark.py    # ODF表格（user-defined元数据）
│   │   ├── odp_watermark.py    # ODF演示（user-defined元数据）
│   │   ├── epub_watermark.py   # EPUB（OPF dc:identifier）
│   │   ├── rtf_watermark.py    # RTF（可忽略控制组）
│   │   └── __init__.py
│   ├── image/                   # 图片水印模块
│   │   ├── image_watermark.py   # PNG/BMP/JPEG（LSB + DCT域）
│   │   ├── tiff_webp_gif_watermark.py  # TIFF/WebP/GIF
│   │   ├── heic_handler.py     # HEIC（EXIF UserComment）
│   │   └── __init__.py
│   ├── media/                   # 音视频水印模块
│   │   ├── audio_watermark.py  # WAV/MP3（扩频水印）
│   │   ├── flac_handler.py     # FLAC（扩频，继承WAV）
│   │   ├── aac_handler.py      # AAC/M4A（扩频，继承WAV）
│   │   ├── video_watermark.py   # MP4/AVI/MKV/MOV（RGB Blue LSB）
│   │   ├── webm_handler.py     # WebM（RGB Blue LSB + VP9无损）
│   │   ├── wmv_handler.py      # WMV（RGB Blue LSB）
│   │   └── __init__.py
│   └── utils/                   # 工具函数
│       ├── helpers.py
│       └── __init__.py
├── tests/
│   ├── unit/                    # 单元测试（unittest）
│   ├── scripts/                 # 集成测试脚本
│   └── fixtures/                # 测试数据文件
├── config/                     # 配置文件
├── docs/                       # 设计文档
├── cli.py                      # CLI入口
├── README.md
├── requirements.txt
└── setup.py
```

---

## 3. 水印编码方案

### 3.1 编码流程

```
原始水印文本 ──▶ UTF-8编码 ──▶ 二进制流 ──▶ CRC32校验 ──▶ Base64编码
```

### 3.2 编码示例

```
输入水印: "ABC123"
Step 1: UTF-8编码 → [65, 66, 67, 49, 50, 51]
Step 2: 转换为二进制 → 01000001 01000010 01000011 00110001 00110010 00110011
Step 3: 添加CRC32校验码（32位）→ [数据位][校验位]
Step 4: Base64编码 → 输出最终编码字符串
```

### 3.3 可选加密（AES-256）

```
原始水印 → AES-256-CBC加密 → Base64编码 → 嵌入
```

---

## 4. 文档类水印详细方案

### 4.1 PDF 文档

#### 嵌入方案

**方案A - 元数据嵌入**

- **原理**: 将水印编码后写入 PDF 的元数据字段
- **字段**: Author、Title、Subject、Keywords
- **编码**: Base64编码水印后写入多个字段分散存储
- **优点**: 实现简单，文件大小不变
- **缺点**: 重编辑或格式转换可能丢失

**方案B - LSB 隐写（针对PDF内嵌图片）**

- **原理**: 在 PDF 中的图片资源上执行 LSB 隐写
- **步骤**:
  1. 解析 PDF，定位嵌入的图片对象
  2. 提取图片像素数据
  3. 将水印编码嵌入到像素最低位
  4. 替换原图片对象
- **优点**: 隐蔽性强
- **缺点**: PDF 中必须有可嵌入的图片资源

**方案C - 文本微调嵌入**

- **原理**: 通过细微调整文字的间距、位置来编码信息
- **适用**: 纯文本 PDF
- **缺点**: 实现复杂，嵌入容量有限

**推荐方案**: 方案A（默认）+ 方案B（当PDF包含图片时）

#### 提取流程

```
PDF文件 ──▶ 解析元数据字段 ──▶ 提取Base64编码 ──▶ Base64解码 ──▶ 水印原文
PDF文件 ──▶ 定位嵌入图片 ──▶ 提取LSB位 ──▶ 重组解码 ──▶ 水印原文
```

#### 验证流程

```
原始水印 ──▶ 编码 ──▶ 与提取结果比对 ──▶ 一致性判断
提取水印 ──▶ CRC32校验 ──▶ 完整性验证
```

---

### 4.2 Word 文档 (.docx)

#### 嵌入方案

**方案A - 文档属性嵌入**

- **原理**: 写入 docx 内置元数据（core.xml 的 creator、title 等字段）
- **优点**: 实现简单
- **缺点**: 元数据可被轻易查看和修改

**方案B - 零宽字符隐写（推荐）**

- **原理**: 使用不可见的 Unicode 字符编码水印信息
- **零宽字符映射**:
  | 字符 | Unicode | 二进制值 |
  |------|---------|----------|
  | 零宽空格 (ZWSP) | U+200B | 0 |
  | 零宽非连接符 (ZWNJ) | U+200C | 1 |
  | 零宽连接符 (ZWJ) | U+200D | 1 |
  | 字节顺序标记 (BOM) | U+FEFF | 0 |

- **编码示例**:
  ```
  水印: "ABC"
  ASCII:    01000001 01000010 01000011
  映射:    ZWSP-ZWSP-ZWSP-ZWSP-0-1-ZWSP-ZWSP-0-ZWSP-ZWSP-ZWSP-1-1-ZWSP
  嵌入:    在文档任意位置插入这些零宽字符
  ```

- **优点**: 人眼不可见，不影响文档显示，无法通过常规方式查看
- **缺点**: 复制粘贴可能丢失零宽字符

**方案C - 隐藏XML注释**

- **原理**: 在文档末尾添加隐藏的 XML 注释节点
- **示例**: `<!--stealthmark:base64encodedwatermark-->`

**推荐方案**: 方案B（零宽字符）

#### 提取流程

```
docx文件 ──▶ 解压为ZIP ──▶ 解析document.xml ──▶ 遍历所有文本节点
──▶ 提取零宽字符 ──▶ 二进制重组 ──▶ Base64解码 ──▶ 水印原文
```

#### 验证流程

```
原始水印 ──▶ 转换为零宽字符序列 ──▶ 与提取结果精确比对
```

---

### 4.3 PPT 演示文稿 (.pptx)

#### 嵌入方案

**方案A - 幻灯片备注嵌入**

- **原理**: 将水印编码写入每张幻灯片的备注页
- **存储方式**: 分散存储（每张幻灯片备注存储一部分水印）
- **优点**: 实现简单
- **缺点**: 查看备注可看到水印

**方案B - 隐藏形状嵌入（推荐）**

- **原理**: 在幻灯片中插入完全透明、不可见的形状
- **属性设置**:
  - 填充颜色: 白色或与背景相同
  - 位置: 移出可见区域或尺寸设为0
  - 或使用零宽字符作为形状名称/替代文字

**方案C - 动画设置嵌入**

- **原理**: 利用动画触发时间的细微差异编码水印
- **示例**: 触发时间偏移 0.001 秒代表 0，偏移 0.002 秒代表 1
- **优点**: 极难察觉
- **缺点**: 实现复杂

**推荐方案**: 方案B（隐藏形状）+ 零宽字符

#### 提取流程

```
pptx文件 ──▶ 解压为ZIP ──▶ 遍历slides/*.xml
──▶ 遍历notesSlides/*.xml（如果使用备注）
──▶ 提取隐藏形状内容或零宽字符 ──▶ 解码 ──▶ 水印原文
```

#### 验证流程

```
原始水印编码后 ──▶ 与提取结果比对
```

---



---

### 4.4 Excel 文档 (.xlsx)

#### 嵌入方案

**方案 - customXml 属性嵌入（推荐）**

- **原理**: 将水印编码后写入 XLSX 的 customXml/item1.xml 自定义属性
- **优点**: Excel 原生支持，最稳定
- **缺点**: 另存为旧格式 (.xls) 会丢失

#### 提取流程

```
xlsx文件 ──▶ 解压为ZIP ──▶ 读取customXml/item1.xml
──▶ 解析自定义属性 ──▶ Base64解码 ──▶ 水印原文
```

#### 验证流程

```
原始水印 ──▶ 编码 ──▶ 与提取结果比对 ──▶ 一致性判断
提取水印 ──▶ CRC32校验 ──▶ 完整性验证
```

---

### 4.5 ODT 文档 (.odt)

#### 嵌入方案

**方案 - ODF user-defined 元数据（推荐）**

- **原理**: 将水印编码后写入 ODT 文件的 user-defined 元数据属性
- **优点**: ODF 标准兼容，LibreOffice/OpenOffice 支持
- **缺点**: 非 ODF 编辑器可能丢失

#### 提取流程

```
odt文件 ──▶ 解压为ZIP ──▶ 读取meta.xml
──▶ 解析user-defined属性 ──▶ Base64解码 ──▶ 水印原文
```

#### 验证流程

```
同PDF验证流程
```

---

### 4.6 ODS 表格 (.ods)

（同 4.5 ODT，使用相同的 ODF user-defined 元数据方案）

### 4.7 ODP 演示 (.odp)

（同 4.5 ODT，使用相同的 ODF user-defined 元数据方案）

---

### 4.8 EPUB 电子书 (.epub)

#### 嵌入方案

**方案 - OPF dc:identifier（推荐）**

- **原理**: 将水印编码后写入 EPUB 的 content.opf 文件的 dc:identifier 字段
- **优点**: EPUB 标准字段，所有阅读器都支持
- **缺点**: 可被手动编辑

#### 提取流程

```
epub文件 ──▶ 解压为ZIP ──▶ 读取content.opf
──▶ 解析dc:identifier ──▶ Base64解码 ──▶ 水印原文
```

#### 验证流程

```
同PDF验证流程
```

---

### 4.9 RTF 文档 (.rtf)

#### 嵌入方案

**方案 - 可忽略控制组嵌入**

- **原理**: 在 RTF 文档中插入特殊控制字，标记为可忽略
- **格式**: `{\*\stealthmark base64encoded}`
- **优点**: 部分 RTF 编辑器会忽略未知控制组
- **缺点**: 许多编辑器会清理未知控制组

#### 提取流程

```
rtf文件 ──▶ 解析RTF控制字 ──▶ 查找\stealthmark ──▶ Base64解码 ──▶ 水印原文
```

#### 验证流程

```
同PDF验证流程
```

---

### 4.10 图片文件 (.png/.jpg/.bmp/.tiff/.webp/.gif/.heic)

#### 嵌入方案

**方案A - LSB隐写（最低有效位）**

- **原理**: 将水印的每一位嵌入到像素颜色的最低有效位
- **嵌入过程**:
  ```
  原始像素: [R=255, G=128, B=64] = [11111111, 10000000, 01000000]
  水印位:   1 (需要嵌入)
  嵌入后:   [R=254, G=128, B=64] = [11111110, 10000000, 01000000]
                    ↑
              只改变最低位
  ```

- **人眼感知**: 1-bit 的变化导致颜色值变化 ±1，人眼完全无法察觉

- **存储结构**:
  ```
  [文件头信息][LSB数据区][水印长度(32bit)][水印数据][CRC32校验(32bit)]
  ```

- **优点**: 实现简单，隐蔽性好
- **缺点**: PNG无损压缩可能保留，但JPEG压缩会破坏

**方案B - DWT离散小波变换水印**

- **原理**: 
  1. 对图像进行DWT变换
  2. 将水印嵌入到HL和LH子带的小波系数中
  3. 进行逆DWT变换

- **优点**: 抗压缩能力强
- **缺点**: 实现复杂

**方案C - JSTP水印（JPEG压缩域）**

- **原理**: 直接在DCT系数上嵌入水印
- **优点**: 抗JPEG压缩性能好
- **缺点**: 仅适用于JPEG格式

**推荐方案**:
- PNG/BMP/GIF/TIFF/WebP: LSB隐写
- JPEG/JPG: JSTP水印

#### 提取流程

```
LSB方案:
图片文件 ──▶ 读取像素数据 ──▶ 提取LSB位 ──▶ 解析长度字段
──▶ 提取水印数据 ──▶ CRC校验 ──▶ Base64解码 ──▶ 水印原文

DWT方案:
图片 ──▶ DWT变换 ──▶ 提取小波系数中的水印位 ──▶ 解码
```


#### 4.10.2 TIFF（LSB隐写）

- **原理**: 与 PNG 相同，将水印嵌入 RGB 通道的最低有效位
- **优点**: TIFF 通常无损，水印保留完整
- **缺点**: 某些 TIFF 使用压缩，可能破坏 LSB

#### 4.10.3 WebP（LSB隐写，无损模式）

- **原理**: 与 PNG 相同，但需确保 WebP 使用无损压缩
- **注意**: 有损 WebP 会破坏 LSB，必须使用无损模式

#### 4.10.4 GIF（Comment Extension块）

- **原理**: 将水印写入 GIF 的 Comment Extension 块
- **格式**: `0x21 0xFE [length] [comment data]`
- **优点**: GIF 标准支持，不影响图像数据
- **缺点**: 某些 GIF 编辑器会删除注释

#### 4.10.5 HEIC（EXIF UserComment）

- **原理**: 将水印写入 HEIC 文件的 EXIF UserComment 字段
- **依赖**: 需要 pillow-heif 库支持
- **优点**: HEIC 标准元数据字段
- **缺点**: 需要额外依赖，部分工具不支持

#### 验证流程

```
提取水印 ──▶ CRC32校验 ──▶ 验证完整性
提取水印内容 ──▶ 与原始水印比对 ──▶ 一致性判断
```

---

## 5. 音视频类水印详细方案

### 5.1 音频文件 (.mp3/.wav/.flac/.aac/.m4a)

#### 嵌入方案

**方案A - 扩频水印（Spread Spectrum）**

- **原理**: 将水印信号扩展到整个音频频谱，功率很低以至于不可闻

- **数学模型**:
  ```
  Y[n] = X[n] + α × w[n] × PN[n]
  
  其中:
  X = 原始音频信号
  w = 水印比特 (±1)
  PN = 伪随机噪声序列（与时间相关）
  α = 嵌入强度因子（控制水印可感知度）
  Y = 含水印音频
  ```

- **嵌入步骤**:
  1. 生成伪随机噪声序列 (PN Sequence)
  2. 将水印比特与PN序列相乘
  3. 将结果叠加到音频信号上
  4. 控制强度因子确保不可闻

- **优点**: 抗干扰能力强，难以去除
- **缺点**: 实现较复杂

**方案B - 相位编码**

- **原理**:
  1. 将音频分帧
  2. 对每帧进行DFT得到相位谱
  3. 用参考相位编码水印信息
  4. 保留幅度谱，只替换相位

- **优点**: 水印信号集中在低频，抗滤波
- **缺点**: 对相位修改敏感

**方案C - 回声隐藏**

- **原理**: 通过引入延迟很小的回声来编码水印
  - 延迟 +d 代表二进制 0
  - 延迟 +2d 代表二进制 1

- **优点**: 实现简单
- **缺点**: 抗攻击能力弱

**推荐方案**: 扩频水印

#### 提取流程

```
含水印音频 ──▶ 分帧
──▶ 生成与嵌入时相同的PN序列
──▶ 相关性检测: corr = Σ(Y[n] × PN[n])
──▶ 相关值 > 阈值 → 1，否则 → 0
──▶ 重组为水印比特流 ──▶ 解码 ──▶ 水印内容
```

#### 验证流程

```
提取水印 ──▶ CRC32校验 ──▶ 完整性验证
提取内容 ──▶ 与原始水印比对 ──▶ 一致性判断
信噪比分析 ──▶ 评估水印抗攻击能力
```

---

### 5.2 视频文件 (.mp4/.avi/.mkv/.mov/.webm/.wmv)

#### 嵌入方案

**方案A - RGB Blue通道LSB（已实现，推荐）**

- **原理**:
  1. 使用 ffmpeg 解码视频为原始像素帧（RGB空间）
  2. 仅修改**第一帧**的 Blue 通道最低有效位（LSB）
  3. 嵌入格式：4字节同步头（0xAA × 4）+ codec编码数据
  4. 用 ffmpeg libx264rgb（CRF 0）重新编码为高质量视频

- **关键设计**：
  - libx264rgb 在 RGB 空间内进行帧内预测无损压缩
  - 普通 libx264 在 YUV 空间编码会破坏 Blue 通道 LSB
  - 仅使用第一帧避免跨帧同步问题
  - 备选编码器：FFV1（纯无损）

- **优点**: 像素级精确保留，不影响视觉质量
- **缺点**: 必须使用无损编码；有损转码会破坏水印

**方案B - ASF元数据（WMV备选）**

- **原理**: 将水印编码写入 WMV/ASF 文件的元数据属性字段
- **适用**: WMV格式，作为LSB方案的备选

**推荐方案**: RGB Blue通道LSB（libx264rgb）

#### 提取流程

```
视频文件 ──▶ ffmpeg 解码为RGB帧
──▶ 读取第一帧 Blue 通道 LSB
──▶ 搜索同步头 0xAA×4
──▶ 提取比特流并重组为字节
──▶ codec.decode() 解码 ──▶ 水印内容
```

#### 验证流程

```
同音频验证流程
```

---

## 6. 验证机制

### 6.1 完整性验证

- **CRC32校验**: 32位循环冗余校验，检测水印是否被篡改
- **SHA256哈希**: 水印内容的密码学哈希值

### 6.2 一致性验证

```
1. 提取水印内容
2. 与原始水印进行精确比对
3. 返回结果:
   - 完全一致: 验证通过
   - 部分匹配: 水印可能受损
   - 完全不匹配: 验证失败
```

### 6.3 鲁棒性测试

| 测试类型 | 描述 | 评估指标 |
|----------|------|----------|
| 抗压缩测试 | JPEG压缩质量调整、MP3比特率变化、视频转码 | 水印存活率 |
| 抗剪裁测试 | 裁剪图片/视频边缘区域 | 水印存活率 |
| 抗噪声测试 | 添加高斯噪声、椒盐噪声 | 水印存活率 |
| 抗滤波测试 | 均值滤波、中值滤波、锐化 | 水印存活率 |
| 抗旋转测试 | 轻微旋转（±5度） | 水印存活率 |
| 抗缩放测试 | 图片/视频尺寸缩放 | 水印存活率 |

---

## 7. 接口设计

### 7.1 核心类定义

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class WatermarkResult(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    FILE_NOT_FOUND = "file_not_found"
    UNSUPPORTED_FORMAT = "unsupported_format"
    INVALID_WATERMARK = "invalid_watermark"

@dataclass
class EmbedResult:
    status: WatermarkResult
    output_path: Optional[str] = None
    message: Optional[str] = None

@dataclass
class ExtractResult:
    status: WatermarkResult
    watermark: Optional[str] = None
    message: Optional[str] = None

@dataclass
class VerifyResult:
    status: WatermarkResult
    is_valid: bool
    integrity_ok: bool
    match_score: float  # 0.0 - 1.0
    message: Optional[str] = None

class BaseWatermarker(ABC):
    """水印基类"""
    
    @abstractmethod
    def embed(self, file_path: str, watermark: str, output_path: str) -> EmbedResult:
        """嵌入水印"""
        pass
    
    @abstractmethod
    def extract(self, file_path: str) -> ExtractResult:
        """提取水印"""
        pass
    
    @abstractmethod
    def verify(self, file_path: str, original_watermark: str) -> VerifyResult:
        """验证水印"""
        pass
    
    @abstractmethod
    def is_supported(self, file_path: str) -> bool:
        """检查文件格式是否支持"""
        pass
```

### 7.2 使用示例

```python
from stealthmark import StealthMark

# 初始化
wm = StealthMark()

# 嵌入水印
result = wm.embed("document.pdf", "版权信息:张三", "output.pdf")
print(result)

# 提取水印
result = wm.extract("output.pdf")
print(result.watermark)

# 验证水印
result = wm.verify("output.pdf", "版权信息:张三")
print(f"验证结果: {result.is_valid}")
```

---

## 8. 技术选型

| 类型 | 库/工具 | 版本 | 用途 |
|------|---------|------|------|
| PDF处理 | PyPDF2 / pdfplumber | >=3.0.0 | 解析和编辑PDF |
| Office文档 | python-docx | >=0.8.11 | 解析Word文档 |
| PPT处理 | python-pptx | >=0.6.21 | 解析PowerPoint |
| 图片处理 | Pillow | >=9.0.0 | 图片编解码、像素操作 |
| 图像处理 | OpenCV | >=4.7.0 | DCT/LSB实现 |
| 数值计算 | numpy | >=1.24.0 | 矩阵运算 |
| 音频处理 | librosa | >=0.10.0 | 音频信号处理 |
| 音频分析 | scipy | >=1.10.0 | 频域变换 |
| 视频处理 | ffmpeg-python | >=0.2.0 | 视频编解码 |
| 加密 | cryptography | >=41.0.0 | AES加密 |
| 日志 | loguru | >=0.7.0 | 日志记录 |

---

## 9. 文件格式支持矩阵

| 格式 | 嵌入方案 | 提取 | 验证 | 备注 |
|------|----------|------|------|------|
| PDF | 元数据（Author字段，Base64） | ✓ | ✓ | 格式转换可能丢失 |
| DOCX | 零宽字符（U+200B=0, U+200C=1） | ✓ | ✓ | 另存为.doc会丢失零宽字符 |
| PPTX | 隐藏形状（hidden_前缀，透明填充） | ✓ | ✓ | 编辑时注意保护形状 |
| XLSX | customXml/item1.xml自定义属性 | ✓ | ✓ | Excel原生支持，最稳定 |
| ODT | ODF user-defined元数据属性 | ✓ | ✓ | ODF标准兼容 |
| ODS | ODF user-defined元数据属性 | ✓ | ✓ | ODF标准兼容 |
| ODP | ODF user-defined元数据属性 | ✓ | ✓ | ODF标准兼容 |
| EPUB | OPF dc:identifier字段 | ✓ | ✓ | ZIP+HTML结构 |
| RTF | 可忽略控制组嵌入 | ✓ | ✓ | 部分编辑器会清理 |
| PNG | LSB隐写（RGB三通道最低位） | ✓ | ✓ | 无损格式，最稳定 |
| JPEG | DCT域水印 | ✓ | ✓ | 抗JPEG压缩能力有限 |
| BMP | LSB隐写（RGB三通道最低位） | ✓ | ✓ | 无压缩，容量大 |
| TIFF | LSB隐写（RGB三通道最低位） | ✓ | ✓ | 无损格式 |
| WebP | LSB隐写（RGB三通道最低位，无损） | ✓ | ✓ | 需无损压缩 |
| GIF | Comment Extension块 | ✓ | ✓ | 使用ImageMagick创建 |
| HEIC | EXIF UserComment字段 | ✓ | ✓ | 可选pillow-heif依赖 |
| WAV | 扩频水印（LCG PN序列，α=0.005） | ✓ | ✓ | 无损音频，最稳定 |
| MP3 | 扩频水印（继承WAV，固定BPS=100） | ✓ | ✓ | 有损压缩 |
| FLAC | 扩频水印（继承WAV，固定BPS=100） | ✓ | ✓ | 无损压缩 |
| AAC/M4A | 扩频水印（继承WAV，固定BPS=100） | ✓ | ✓ | 有损压缩 |
| MP4 | RGB Blue通道LSB + libx264rgb CRF0 | ✓ | ✓ | 必须无损编码；依赖ffmpeg |
| AVI | RGB Blue通道LSB + FFV1无损 | ✓ | ✓ | 必须无损编码；依赖ffmpeg |
| MKV | RGB Blue通道LSB + FFV1无损 | ✓ | ✓ | 必须无损编码；依赖ffmpeg |
| MOV | RGB Blue通道LSB + libx264rgb CRF0 | ✓ | ✓ | 必须无损编码；依赖ffmpeg |
| WebM | RGB Blue通道LSB + VP9无损 | ✓ | ✓ | 必须无损编码；依赖ffmpeg |
| WMV | RGB Blue通道LSB + ASF元数据备选 | ✓ | ✓ | 必须无损编码；依赖ffmpeg |

---

## 10. 安全考虑

### 10.1 水印加密

- 使用 AES-256-CBC 加密水印内容
- 密钥通过用户提供的密码派生（PBKDF2）
- 加密后进行 Base64 编码再嵌入

### 10.2 密钥管理

- 嵌入时需要提供水印密钥
- 提取时需要相同密钥解密
- 密钥不存储在文件中

### 10.3 隐蔽性保证

- 水印不可见（视觉/听觉）
- 水印不显著改变文件大小
- 水印不引入可检测的统计异常

---

## 11. 未来扩展

以下功能已实现或已规划：

- [x] 更多文件格式（Excel/XLSX、ODF三件套、EPUB、RTF、TIFF、WebP、GIF、HEIC、FLAC、AAC、WebM、WMV）
- [x] 盲水印提取（不需要原始文件）
- [x] AES-256水印加密（PBKDF2-HMAC-SHA256密钥派生）
- [ ] 批量处理功能
- [ ] 图形用户界面
- [ ] Web API 服务
- [ ] 抗深度学习水印检测的攻击

---

## 12. 参考文献

1. Cox, I., et al. "Digital Watermarking and Steganography", Morgan Kaufmann, 2008
2. Bender, W., et al. "Techniques for Data Hiding", IBM Systems Journal, 1996
3. Langelaar, G., et al. "Watermarking Digital Image and Video Data", IEEE Signal Processing Magazine, 2000

---

*文档版本: 1.0*
*最后更新: 2026-04-28*
