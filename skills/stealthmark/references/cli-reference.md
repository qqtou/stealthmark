# CLI 参数速查

## StealthMark CLI

安装后可通过以下方式调用：

```bash
# 模块方式（推荐）
python -m stealthmark embed input.pdf "WATERMARK"
python -m stealthmark extract input_wm.pdf
python -m stealthmark verify input_wm.pdf -w "WATERMARK"

# 直接调用
stealthmark embed input.pdf "WATERMARK"
```

## 子命令详解

### embed - 嵌入水印

```bash
stealthmark embed <input> <watermark> [options]
```

**参数：**
| 参数 | 说明 |
|------|------|
| `<input>` | 输入文件路径 |
| `<watermark>` | 水印文本 |

**选项：**
| 选项 | 说明 |
|------|------|
| `-o, --output <path>` | 输出文件路径 |
| `-f, --force` | 强制覆盖已存在文件 |
| `-v, --verbose` | DEBUG 详细日志 |
| `-q, --quiet` | 仅显示错误 |
| `--encrypt` | 启用 AES-256 加密 |
| `--key <key>` | 加密密钥 |
| `--show-errors` | 显示失败详情 |

**示例：**
```bash
# 基本嵌入
stealthmark embed report.pdf "CONFIDENTIAL"

# 指定输出路径
stealthmark embed report.pdf "CONFIDENTIAL" -o report_wm.pdf

# 加密嵌入
stealthmark embed report.pdf "CONFIDENTIAL" --encrypt --key mysecretkey

# 静默模式
stealthmark embed report.pdf "CONFIDENTIAL" -q
```

### extract - 提取水印

```bash
stealthmark extract <input> [options]
```

**选项：**
| 选项 | 说明 |
|------|------|
| `-o, --output <path>` | 输出文件路径（用于 extract + verify 流程） |
| `-v, --verbose` | 详细日志 |

**示例：**
```bash
stealthmark extract report_wm.pdf
stealthmark extract report_wm.pdf -v
```

### verify - 验证水印

```bash
stealthmark verify <input> [options]
```

**选项：**
| 选项 | 说明 |
|------|------|
| `-w, --watermark <text>` | 期望的水印文本（对比内容） |
| `-v, --verbose` | 详细日志 |

**示例：**
```bash
# 只检测是否有水印
stealthmark verify report_wm.pdf

# 对比水印内容
stealthmark verify report_wm.pdf -w "CONFIDENTIAL"
```

### info - 查看支持格式

```bash
stealthmark info
```

输出按类别分组的 31 种支持格式列表。

### batch - 批量处理

```bash
stealthmark batch <command> <input_dir> [options]
```

**命令：**
| 命令 | 说明 |
|------|------|
| `embed` | 批量嵌入 |
| `extract` | 批量提取 |
| `verify` | 批量验证 |

**选项：**
| 选项 | 说明 |
|------|------|
| `-w, --watermark <text>` | 水印文本（embed/verify 用） |
| `-o, --output-dir <dir>` | 输出目录 |
| `-n, --name-pattern <pat>` | 命名模式：`{name}` `{ext}` `{date}` `{time}` |
| `--include <ext>` | 只处理指定扩展名（可多次） |
| `--exclude <ext>` | 排除指定扩展名（可多次） |
| `--no-recursive` | 不扫描子目录 |
| `--dry-run` | 模拟运行 |
| `--workers <n>` | 并行线程数（默认 4） |
| `--show-errors` | 显示失败详情 |

**命名模式示例：**
```bash
# 默认：report.pdf → report_wm.pdf
stealthmark batch embed ./files -o ./output

# 自定义命名：report.pdf → report_2026-05-01.pdf
stealthmark batch embed ./files -n "{name}_{date}{ext}"
```

### GUI - 图形界面

```bash
python -m stealthmark.gui
# 或
stealthmark gui
```

启动 PyQt6 图形界面。

### Web API - HTTP 服务

```bash
uvicorn stealthmark.api:app --reload --port 8000
```

启动 FastAPI 服务，文档地址：http://localhost:8000/docs

**API 端点：**
| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 + handler 数量 |
| `/info` | GET | 支持格式列表 |
| `/embed` | POST | 嵌入水印 |
| `/extract` | POST | 提取水印 |
| `/verify` | POST | 验证水印 |
| `/batch` | POST | 批量处理 |
| `/test` | GET | 测试前端页面 |
