# StealthMark 测试前端设计文档

## 1. 概述

### 1.1 目标

为 StealthMark 创建一个 Web 测试页面，支持：
1. **测试文件生成**：在浏览器端生成各格式测试文件
2. **全流程测试**：embed → extract → verify 完整链路
3. **格式查看**：展示所有支持的格式及分类

### 1.2 技术选型

| 方案 | 优点 | 缺点 |
|------|------|------|
| Streamlit | Python原生，零前端代码 | 需额外依赖，独立服务 |
| **HTML单页** | 零依赖，FastAPI直接serve，跨域无问题 | 需手写HTML/CSS/JS |
| 扩展PyQt6 GUI | 复用现有代码 | 不是"页面"，不便于分享 |

**选定方案**：HTML 单页应用

- 单文件，易分发
- 直接被现有 FastAPI serve
- 调用现有 API 端点（/embed, /extract, /verify, /info）

---

## 2. 架构设计

### 2.1 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Browser (HTML/JS)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ 测试文件生成 │  │ 全流程测试  │  │ 格式浏览器          │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │ fetch API
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Backend (stealthmark/api.py)            │
│  /health  /info  /embed  /extract  /verify  /batch          │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  StealthMark Core (23 Handlers)              │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 文件结构

```
stealthmark/
├── static/
│   └── test.html          # 测试前端页面（单文件）
├── api.py                 # FastAPI（新增静态文件服务）
├── gui.py
└── __init__.py
```

---

## 3. 功能设计

### 3.1 页面布局

```
┌─────────────────────────────────────────────────────────────┐
│  StealthMark 测试工具                              [API状态] │
├─────────────────────────────────────────────────────────────┤
│  [测试文件生成]  [全流程测试]  [支持格式]                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                     内容区域                         │   │
│  │                                                     │   │
│  │  根据选中的 Tab 显示不同内容                         │   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  日志/状态栏                                                │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Tab 1: 测试文件生成

**功能**：在浏览器端生成各格式测试文件

**实现方式**：
- 文档类：使用 JSZip + 底层库生成
  - PDF: 使用 jsPDF 或预置 Base64 模板
  - DOCX/PPTX/XLSX: 使用 docx/pptx/xlsx 库或预置模板
  - ODT/ODP/ODS: 使用 JSZip 修改预置模板
  - EPUB: 使用 JSZip 生成
  - RTF: 直接构造文本
  
- 图片类：使用 Canvas 生成
  - PNG/BMP/JPEG/TIFF/WebP/GIF: Canvas.toDataURL()
  - HEIC: 不支持生成，提示需手动上传
  
- 音频类：使用 Web Audio API 或预置 Base64
  - WAV: 手动构造 RIFF 头 + PCM 数据
  - MP3/FLAC/AAC: 预置 Base64 最小文件
  
- 视频类：预置 Base64 最小文件
  - MP4/AVI/MKV/MOV/WebM/WMV: 预置最小测试文件

**简化方案**（推荐）：

由于浏览器生成复杂格式文件较困难，采用**预置模板 + Base64 编码**方式：

```javascript
const TEST_TEMPLATES = {
  // 文档类（最小有效文件）
  '.pdf': 'data:application/pdf;base64,JVBERi0xLjQKMSAwIG9iago...',
  '.docx': 'data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64,UEsDBBQAAAA...',
  // ... 其他格式
};
```

**UI设计**：
```
┌─────────────────────────────────────────────────────────────┐
│ 选择要生成的测试文件格式：                                   │
│                                                             │
│ 文档: [PDF] [DOCX] [PPTX] [XLSX] [ODT] [ODP] [ODS] [EPUB] [RTF] │
│ 图片: [PNG] [JPG] [BMP] [TIFF] [WebP] [GIF]                │
│ 音频: [WAV] [MP3] [FLAC] [AAC] [M4A]                       │
│ 视频: [MP4] [AVI] [MKV] [MOV] [WebM] [WMV]                 │
│                                                             │
│ 水印内容: [________________________]  (默认: StealthMark-Test-2026) │
│                                                             │
│ [生成全部测试文件]  [生成选中文件]                           │
│                                                             │
│ 生成结果：                                                  │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ test.pdf      ✓ 已生成 (15KB)                           ││
│ │ test.docx     ✓ 已生成 (12KB)                           ││
│ │ test.png      ✓ 已生成 (3KB)                            ││
│ │ ...                                                      ││
│ └─────────────────────────────────────────────────────────┘│
│                                                             │
│ [下载全部]  [清除]                                          │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Tab 2: 全流程测试

**功能**：对生成的测试文件执行完整的水印流程

**流程**：
```
生成测试文件 → embed → extract → verify → 报告结果
```

**UI设计**：
```
┌─────────────────────────────────────────────────────────────┐
│ 测试配置：                                                  │
│ 水印内容: [StealthMark-Test-2026_________________]         │
│ 密码(可选): [________________]                              │
│ 并发数: [4▼]                                                │
│                                                             │
│ [开始全流程测试]  [停止]                                    │
│                                                             │
│ 测试进度：                                                  │
│ ████████████████████░░░░░░░░░░ 67% (20/30)                │
│ 当前: test.mp4                                              │
│                                                             │
│ 测试结果：                                                  │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ 文件      Embed  Extract  Verify  耗时   详情          ││
│ ├─────────────────────────────────────────────────────────┤│
│ │ test.pdf   ✓      ✓       ✓     0.3s   [查看]          ││
│ │ test.docx  ✓      ✓       ✓     0.2s   [查看]          ││
│ │ test.png   ✓      ✓       ✗     0.5s   [查看]          ││
│ │ test.mp3   ✓      ✓       ✓     1.2s   [查看]          ││
│ │ ...                                                      ││
│ └─────────────────────────────────────────────────────────┘│
│                                                             │
│ 汇总：成功 28/30，失败 2，跳过 0                            │
│ [导出报告]  [重试失败项]                                    │
└─────────────────────────────────────────────────────────────┘
```

### 3.4 Tab 3: 支持格式

**功能**：展示所有支持的格式，按分类显示

**UI设计**：
```
┌─────────────────────────────────────────────────────────────┐
│ StealthMark 支持 31 种文件格式（23 个 Handler）             │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ 📄 文档类 (9种)                                          ││
│ │ PDF    DOCX   PPTX   XLSX   ODT    ODP    ODS    EPUB   RTF │
│ │ 元数据 零宽字符 隐藏形状 XML属性 ODF元数据 ...            ││
│ ├─────────────────────────────────────────────────────────┤│
│ │ 🖼️ 图片类 (8种)                                          ││
│ │ PNG    JPG    BMP    TIFF   WebP   GIF    HEIC   HEIF  ││
│ │ LSB    DCT    LSB    LSB    LSB    Comment EXIF   EXIF ││
│ ├─────────────────────────────────────────────────────────┤│
│ │ 🎵 音频类 (6种)                                          ││
│ │ WAV    MP3    FLAC   AAC    M4A    OGG                 ││
│ │ 扩频   扩频   扩频    扩频   扩频   元数据              ││
│ ├─────────────────────────────────────────────────────────┤│
│ │ 🎬 视频类 (6种)                                          ││
│ │ MP4    AVI    MKV    MOV    WebM   WMV                 ││
│ │ RGB-LSB RGB-LSB RGB-LSB RGB-LSB RGB-LSB RGB-LSB        ││
│ └─────────────────────────────────────────────────────────┘│
│                                                             │
│ [API: /info]  [刷新]                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. API 集成

### 4.1 现有 API 端点

| 端点 | 方法 | 用途 |
|------|------|------|
| `/health` | GET | 检查 API 状态 |
| `/info` | GET | 获取支持格式列表 |
| `/embed` | POST | 嵌入水印 |
| `/extract` | POST | 提取水印 |
| `/verify` | POST | 验证水印 |
| `/batch` | POST | 批量处理 |

### 4.2 前端调用示例

```javascript
// 检查 API 状态
async function checkHealth() {
  const res = await fetch('/health');
  const data = await res.json();
  return data.status === 'ok';
}

// 获取支持格式
async function getFormats() {
  const res = await fetch('/info');
  const data = await res.json();
  return data.formats;
}

// 嵌入水印
async function embedWatermark(file, watermark, password = null) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('watermark', watermark);
  if (password) formData.append('password', password);
  
  const res = await fetch('/embed', {
    method: 'POST',
    body: formData
  });
  return await res.json();
}

// 提取水印
async function extractWatermark(file, password = null) {
  const formData = new FormData();
  formData.append('file', file);
  if (password) formData.append('password', password);
  
  const res = await fetch('/extract', {
    method: 'POST',
    body: formData
  });
  return await res.json();
}

// 验证水印
async function verifyWatermark(file, watermark, password = null) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('watermark', watermark);
  if (password) formData.append('password', password);
  
  const res = await fetch('/verify', {
    method: 'POST',
    body: formData
  });
  return await res.json();
}
```

---

## 5. 实现计划

### 5.1 文件清单

| 文件 | 说明 |
|------|------|
| `stealthmark/static/test.html` | 测试前端页面（单文件，含HTML/CSS/JS） |
| `stealthmark/api.py` | 修改：添加静态文件服务和 CORS |
| `README.md` | 更新：添加测试前端使用说明 |

### 5.2 依赖

**后端**：
- 现有依赖：fastapi, uvicorn
- 新增：无（使用 FastAPI 内置 StaticFiles）

**前端**：
- 无外部依赖
- 纯 HTML5 + CSS3 + ES6

### 5.3 实现步骤

1. **修改 api.py**
   - 添加 StaticFiles mount
   - 添加 CORS 中间件（如需要）
   - 添加 `/test` 路由重定向

2. **创建 test.html**
   - HTML 结构（三 Tab 布局）
   - CSS 样式（简洁现代风格）
   - JavaScript 逻辑（文件生成、API 调用、结果展示）

3. **预置测试文件模板**
   - 在 HTML 中嵌入最小测试文件的 Base64 编码
   - 或在首次加载时从 API 获取

4. **更新 README**
   - 添加测试前端使用说明

---

## 6. 测试文件生成策略

### 6.1 可在浏览器生成的格式

| 格式 | 生成方式 | 难度 |
|------|----------|------|
| PNG | Canvas.toDataURL('image/png') | 简单 |
| JPG | Canvas.toDataURL('image/jpeg') | 简单 |
| BMP | Canvas + 手动构造 BMP 头 | 中等 |
| WebP | Canvas.toDataURL('image/webp') | 简单 |
| WAV | 手动构造 RIFF 头 + PCM | 中等 |
| RTF | 纯文本构造 | 简单 |

### 6.2 需预置模板的格式

| 格式 | 原因 |
|------|------|
| PDF | 复杂二进制格式 |
| DOCX/PPTX/XLSX | ZIP + XML 结构 |
| ODT/ODP/ODS | ZIP + XML 结构 |
| EPUB | ZIP + XHTML 结构 |
| GIF | LZW 压缩算法复杂 |
| TIFF | 多种压缩格式 |
| HEIC | 专有格式 |
| MP3/FLAC/AAC | 音频编码复杂 |
| MP4/AVI/MKV/MOV/WebM/WMV | 容器格式复杂 |

### 6.3 模板来源

**方案A：从 tests/fixtures/ 读取**
- 优点：使用已有测试文件
- 缺点：需要 API 端点提供下载

**方案B：Base64 嵌入 HTML**
- 优点：完全自包含
- 缺点：HTML 文件变大

**推荐方案A**：
- 新增 API 端点 `/test-templates` 返回测试文件模板
- 前端按需获取，减少初始加载时间

---

## 7. 后续扩展

### 7.1 可选功能

- 测试历史记录（localStorage）
- 测试报告导出（HTML/PDF）
- 批量测试配置保存
- 自定义测试用例

### 7.2 性能优化

- 并发控制（避免同时请求过多）
- 进度条实时更新
- 结果缓存

---

*文档版本: 1.0*
*创建时间: 2026-04-30*
