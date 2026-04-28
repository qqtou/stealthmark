# StealthMark API 文档

---

## 1. 概述

StealthMark 是一个隐式水印工具，提供 Python API 和命令行接口，支持对文档、图片、音频、视频添加隐藏水印。

### 1.1 安装

```bash
pip install stealthmark
```

### 1.2 快速开始

```python
from stealthmark import StealthMark

# 初始化
wm = StealthMark()

# 嵌入水印
result = wm.embed("document.pdf", "版权信息:张三")
print(result)

# 提取水印
result = wm.extract("document.pdf")
print(result.watermark.content)

# 验证水印
result = wm.verify("document.pdf", "版权信息:张三")
print(f"验证结果: {result.is_valid}")
```

---

## 2. StealthMark 主类

### 2.1 类签名

```python
class StealthMark:
    """
    StealthMark 门面类
    提供统一的水印操作入口
    """
    
    def __init__(self, password: Optional[str] = None) -> None:
        """
        初始化 StealthMark
        
        Args:
            password: 水印加密密码（可选），支持AES-256加密
        """
```

### 2.2 公共方法

#### embed()

```python
def embed(
    self,
    file_path: str,
    watermark: str,
    output_path: Optional[str] = None,
    **kwargs
) -> EmbedResult:
    """
    向文件中嵌入水印
    
    Args:
        file_path: 原始文件路径
        watermark: 水印文本内容
        output_path: 输出文件路径，默认覆盖原文件
        **kwargs: 额外参数，传递给具体处理器
            - pdf_embed_method: str, PDF嵌入方式 ('metadata' 或 'lsb')
            - jpeg_quality: int, JPEG保存质量 (1-100)
            - audio_alpha: float, 音频嵌入强度
            - video_frame_interval: int, 视频关键帧间隔
    
    Returns:
        EmbedResult: 嵌入结果
        
    Raises:
        无异常抛出，所有错误通过返回值体现
    
    Example:
        >>> wm = StealthMark()
        >>> result = wm.embed("test.pdf", "版权所有", "output.pdf")
        >>> if result.is_success:
        ...     print(f"水印已嵌入: {result.output_path}")
    """
```

#### extract()

```python
def extract(
    self,
    file_path: str,
    **kwargs
) -> ExtractResult:
    """
    从文件中提取水印
    
    Args:
        file_path: 含水印文件路径
        **kwargs: 额外参数
    
    Returns:
        ExtractResult: 提取结果
        
    Example:
        >>> result = wm.extract("watermarked.pdf")
        >>> if result.is_success:
        ...     print(f"水印内容: {result.watermark.content}")
    """
```

#### verify()

```python
def verify(
    self,
    file_path: str,
    original_watermark: str,
    **kwargs
) -> VerifyResult:
    """
    验证水印
    
    Args:
        file_path: 含水印文件路径
        original_watermark: 原始水印文本
        **kwargs: 额外参数
    
    Returns:
        VerifyResult: 验证结果
        
    Example:
        >>> result = wm.verify("watermarked.pdf", "版权所有")
        >>> print(f"验证通过: {result.is_valid}")
        >>> print(f"匹配度: {result.match_score * 100}%")
    """
```

#### is_supported()

```python
def is_supported(self, file_path: str) -> bool:
    """
    检查文件格式是否支持
    
    Args:
        file_path: 文件路径
    
    Returns:
        bool: 是否支持
    
    Example:
        >>> wm.is_supported("test.pdf")
        True
        >>> wm.is_supported("test.xyz")
        False
    """
```

#### supported_formats()

```python
def supported_formats(self) -> List[str]:
    """
    获取所有支持的文件格式
    
    Returns:
        List[str]: 扩展名列表，如 ['.pdf', '.docx', '.png', ...]
        
    Example:
        >>> wm.supported_formats()
        ['.pdf', '.docx', '.pptx', '.png', '.jpg', '.bmp', '.wav', '.mp3', '.mp4']
    """
```

---

## 3. 数据类

### 3.1 WatermarkData

```python
@dataclass
class WatermarkData:
    """
    水印数据结构
    
    Attributes:
        content: 水印文本内容
        watermark_type: 水印类型，默认TEXT
        created_at: 创建时间（ISO格式）
        metadata: 额外元数据字典
    """
    
    content: str
    watermark_type: WatermarkType = WatermarkType.TEXT
    created_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### 3.2 WatermarkStatus

```python
class WatermarkStatus(Enum):
    """
    水印操作状态码
    
    Values:
        SUCCESS: 操作成功
        FAILED: 通用失败
        FILE_NOT_FOUND: 文件不存在
        FILE_CORRUPTED: 文件损坏
        UNSUPPORTED_FORMAT: 不支持的文件格式
        INVALID_WATERMARK: 无效的水印数据
        EXTRACTION_FAILED: 水印提取失败
        VERIFICATION_FAILED: 水印验证失败
        ENCRYPTION_FAILED: 加密失败
        DECRYPTION_FAILED: 解密失败
    """
    
    SUCCESS = 0
    FAILED = 1
    FILE_NOT_FOUND = 2
    FILE_CORRUPTED = 3
    UNSUPPORTED_FORMAT = 4
    INVALID_WATERMARK = 5
    EXTRACTION_FAILED = 6
    VERIFICATION_FAILED = 7
    ENCRYPTION_FAILED = 8
    DECRYPTION_FAILED = 9
```

### 3.3 EmbedResult

```python
@dataclass
class EmbedResult:
    """
    水印嵌入结果
    
    Attributes:
        status: 操作状态
        message: 状态消息
        file_path: 目标文件路径
        output_path: 输出文件路径
        watermark_id: 水印唯一标识（如果有）
    """
    
    status: WatermarkStatus
    message: str = ""
    file_path: Optional[str] = None
    output_path: Optional[str] = None
    watermark_id: Optional[str] = None
    
    @property
    def is_success(self) -> bool:
        """是否成功"""
        return self.status == WatermarkStatus.SUCCESS
```

### 3.4 ExtractResult

```python
@dataclass
class ExtractResult:
    """
    水印提取结果
    
    Attributes:
        status: 操作状态
        message: 状态消息
        file_path: 文件路径
        watermark: 提取的水印数据
    """
    
    status: WatermarkStatus
    message: str = ""
    file_path: Optional[str] = None
    watermark: Optional[WatermarkData] = None
    
    @property
    def is_success(self) -> bool:
        """是否成功"""
        return self.status == WatermarkStatus.SUCCESS
```

### 3.5 VerifyResult

```python
@dataclass
class VerifyResult:
    """
    水印验证结果
    
    Attributes:
        status: 操作状态
        is_valid: 验证是否通过
        is_integrity_ok: 完整性校验是否通过
        match_score: 一致性评分 (0.0 - 1.0)
        message: 状态消息
        details: 详细信息字典
    """
    
    status: WatermarkStatus
    is_valid: bool
    is_integrity_ok: bool
    match_score: float
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
```

---

## 4. 命令行接口 (CLI)

### 4.1 全局选项

| 选项 | 说明 |
|------|------|
| `-v, --verbose` | 显示详细日志 |
| `-p, --password` | 水印加密密码 |

### 4.2 子命令

#### embed - 嵌入水印

```bash
stealthmark embed <input_file> <watermark> [-o <output_file>]
```

**参数**:
- `input_file`: 输入文件路径（必需）
- `watermark`: 水印文本（必需）
- `-o, --output`: 输出文件路径（可选，默认覆盖原文件）

**示例**:
```bash
# 嵌入水印到PDF
stealthmark embed document.pdf "版权所有：张三"

# 指定输出文件
stealthmark embed document.pdf "版权所有：张三" -o watermarked.pdf

# 使用加密
stealthmark embed document.pdf "版权所有：张三" -p mypassword
```

#### extract - 提取水印

```bash
stealthmark extract <file>
```

**参数**:
- `file`: 含水印文件路径（必需）

**示例**:
```bash
stealthmark extract watermarked.pdf
# 输出: 水印内容: 版权所有：张三
```

#### verify - 验证水印

```bash
stealthmark verify <file> <watermark>
```

**参数**:
- `file`: 含水印文件路径（必需）
- `watermark`: 原始水印文本（必需）

**示例**:
```bash
stealthmark verify watermarked.pdf "版权所有：张三"
# 输出: ✓ 验证通过
#       一致性: 100.0%
```

#### info - 支持格式

```bash
stealthmark info
```

**示例**:
```bash
stealthmark info
# 输出:
# 支持的格式:
#   - .pdf
#   - .docx
#   - .pptx
#   - .png
#   - .jpg
#   - .bmp
#   - .wav
#   - .mp3
#   - .mp4
```

---

## 5. 处理器接口

每个文件格式对应一个处理器，可单独使用。

### 5.1 BaseHandler 抽象基类

```python
class BaseHandler(ABC):
    """
    水印处理器基类
    所有具体格式的处理器都继承此类
    """
    
    SUPPORTED_EXTENSIONS: tuple = ()
    HANDLER_NAME: str = "base"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化处理器
        
        Args:
            config: 配置字典
        """
    
    @abstractmethod
    def embed(self, file_path: str, watermark: WatermarkData, 
              output_path: str, **kwargs) -> EmbedResult:
        """嵌入水印"""
    
    @abstractmethod
    def extract(self, file_path: str, **kwargs) -> ExtractResult:
        """提取水印"""
    
    @abstractmethod
    def verify(self, file_path: str, original_watermark: WatermarkData,
               **kwargs) -> VerifyResult:
        """验证水印"""
    
    def is_supported(self, file_path: str) -> bool:
        """检查文件是否支持"""
```

### 5.2 可用处理器

| 处理器 | 支持格式 | 嵌入方法 |
|--------|----------|----------|
| `PDFHandler` | .pdf | PDF元数据Author字段（Base64） |
| `DOCXHandler` | .docx | 零宽字符（U+200B=0, U+200C=1） |
| `PPTXHandler` | .pptx | 隐藏形状（hidden_前缀） |
| `XLSXHandler` | .xlsx | customXml/item1.xml属性 |
| `ODTHandler` | .odt | ODF user-defined元数据 |
| `ODSHandler` | .ods | ODF user-defined元数据 |
| `ODPHandler` | .odp | ODF user-defined元数据 |
| `EPUBHandler` | .epub | OPF dc:identifier |
| `RTFHandler` | .rtf | 可忽略控制组 |
| `PNGHandler` | .png | LSB隐写（RGB三通道） |
| `BMPHandler` | .bmp | LSB隐写（RGB三通道） |
| `JPEGHandler` | .jpg, .jpeg | DCT域水印 |
| `TIFFHandler` | .tiff, .tif | LSB隐写 |
| `WebPHandler` | .webp | LSB隐写（无损） |
| `GIFHandler` | .gif | Comment Extension块 |
| `HEICHandler` | .heic | EXIF UserComment |
| `WAVHandler` | .wav | 扩频水印（LCG PN序列） |
| `MP3Handler` | .mp3 | 扩频水印（继承WAV） |
| `FLACHandler` | .flac | 扩频水印（继承WAV） |
| `AACHandler` | .aac, .m4a | 扩频水印（继承WAV） |
| `VideoHandler` | .mp4, .avi, .mkv, .mov | RGB Blue通道LSB + libx264rgb |
| `WebMHandler` | .webm | RGB Blue通道LSB + VP9无损 |
| `WMVHandler` | .wmv | RGB Blue通道LSB |

### 5.3 直接使用处理器

```python
from stealthmark.document import PDFHandler
from stealthmark.core.base import WatermarkData

# 直接使用处理器
handler = PDFHandler()

result = handler.embed(
    file_path="document.pdf",
    watermark=WatermarkData(content="版权所有"),
    output_path="output.pdf"
)
```

---

## 6. 高级用法

### 6.1 水印加密

```python
from stealthmark import StealthMark

# 初始化时提供密码，水印将使用AES-256加密
wm = StealthMark(password="my_secure_password")

# 嵌入时会自动加密
wm.embed("document.pdf", "版权所有")

# 提取时需要相同的密码才能解密
result = wm.extract("document.pdf")
# 需要密码才能解码水印
```

### 6.2 自定义处理器配置

```python
from stealthmark import StealthMark

# 为不同格式指定不同配置
wm = StealthMark()

# 嵌入PDF，使用LSB方法（如果有图片）
wm.embed("document.pdf", "版权所有", 
         pdf_embed_method='lsb')

# 嵌入JPEG，指定质量
wm.embed("image.jpg", "版权所有", 
         jpeg_quality=90)

# 嵌入视频，指定帧间隔
wm.embed("video.mp4", "版权所有", 
         video_frame_interval=15)
```

### 6.3 注册自定义处理器

```python
from stealthmark import StealthMark
from stealthmark.core.base import BaseHandler

class MyCustomHandler(BaseHandler):
    SUPPORTED_EXTENSIONS = ('.myformat',)
    HANDLER_NAME = "myformat"
    
    def embed(self, file_path, watermark, output_path, **kwargs):
        # 自定义嵌入逻辑
        pass
    
    def extract(self, file_path, **kwargs):
        # 自定义提取逻辑
        pass
    
    def verify(self, file_path, original_watermark, **kwargs):
        # 自定义验证逻辑
        pass

# 注册
wm = StealthMark()
wm.register_handler(MyCustomHandler)
```

### 6.4 批量处理

```python
import os
from stealthmark import StealthMark

wm = StealthMark()
watermark = "版权所有"

input_dir = "./files"
output_dir = "./watermarked"

for filename in os.listdir(input_dir):
    input_path = os.path.join(input_dir, filename)
    output_path = os.path.join(output_dir, filename)
    
    if wm.is_supported(input_path):
        result = wm.embed(input_path, watermark, output_path)
        print(f"{filename}: {'✓' if result.is_success else '✗'}")
```

---

## 7. 错误处理

### 7.1 错误码说明

```python
from stealthmark import StealthMark, WatermarkStatus

wm = StealthMark()
result = wm.embed("test.pdf", "版权所有")

if not result.is_success:
    if result.status == WatermarkStatus.FILE_NOT_FOUND:
        print("文件不存在")
    elif result.status == WatermarkStatus.UNSUPPORTED_FORMAT:
        print("不支持的文件格式")
    elif result.status == WatermarkStatus.FAILED:
        print(f"操作失败: {result.message}")
```

### 7.2 异常类

```python
from stealthmark.core.exceptions import (
    StealthMarkError,
    FileNotFoundError,
    UnsupportedFormatError,
    EmbedError,
    ExtractError,
    VerifyError,
    CodecError,
    EncryptionError
)

try:
    wm = StealthMark()
    wm.embed("document.pdf", "版权所有")
except FileNotFoundError:
    print("文件不存在")
except UnsupportedFormatError:
    print("不支持的格式")
except EmbedError as e:
    print(f"嵌入失败: {e}")
```

---

## 8. 配置参考

### 8.1 全局配置

```python
# config/settings.py

DEFAULT_CONFIG = {
    # 通用设置
    'debug': False,
    'log_file': None,
    
    # 编解码设置
    'password': None,           # 水印加密密码
    
    # PDF设置
    'pdf_embed_method': 'metadata',  # metadata 或 lsb
    
    # 图片设置
    'jpeg_quality': 95,
    'png_compress': 6,
    
    # 音频设置
    'audio_spread_factor': 31,
    'audio_alpha': 0.005,
    
    # 视频设置
    'video_frame_interval': 30,
    'video_alpha': 0.1,
}
```

---

## 9. 示例代码

### 9.1 完整工作流

```python
from stealthmark import StealthMark

def main():
    # 初始化
    wm = StealthMark()
    
    # 文件路径
    original = "document.pdf"
    watermarked = "document_watermarked.pdf"
    watermark_text = "版权所有 © 2024 张三"
    
    # 1. 嵌入水印
    print("1. 嵌入水印...")
    embed_result = wm.embed(original, watermark_text, watermarked)
    if not embed_result.is_success:
        print(f"嵌入失败: {embed_result.message}")
        return
    
    print(f"✓ 水印已嵌入: {embed_result.output_path}")
    
    # 2. 提取水印
    print("\n2. 提取水印...")
    extract_result = wm.extract(watermarked)
    if not extract_result.is_success:
        print(f"提取失败: {extract_result.message}")
        return
    
    print(f"✓ 提取到水印: {extract_result.watermark.content}")
    
    # 3. 验证水印
    print("\n3. 验证水印...")
    verify_result = wm.verify(watermarked, watermark_text)
    if verify_result.is_valid:
        print(f"✓ 验证通过！匹配度: {verify_result.match_score * 100:.1f}%")
    else:
        print(f"✗ 验证失败: {verify_result.message}")

if __name__ == "__main__":
    main()
```

---

## 10. 常见问题

### Q: 水印嵌入后文件大小变化明显吗？
A: 变化很小。LSB隐写不会改变文件大小；元数据嵌入增加几百字节；音视频水印基本不影响大小。

### Q: 提取水印需要原始文件吗？
A: 不需要。StealthMark 使用盲水印技术，不需要原始文件即可提取。

### Q: 支持批量处理吗？
A: API层面支持，需要自己实现循环。CLI暂时不支持批量。

### Q: 水印能被移除吗？
A: StealthMark 设计的鲁棒性可以抵抗一般的压缩、裁剪等操作，但如果文件被深度编辑或重新编码，水印可能被破坏。

---

*API版本: 1.0*
*最后更新: 2026-04-28*
