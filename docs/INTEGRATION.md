# StealthMark API 集成指南

> 本文档面向业务系统开发团队，说明如何通过 HTTP API 集成 StealthMark 水印服务，实现文件溯源与内容归属功能。
> 目标读者：后端开发工程师 | 技术负责人

---

## 1. 概述

StealthMark 提供隐式水印服务，可将结构化信息（用户ID、文件标识、业务主键等）以人眼不可见的方式嵌入 PDF、图片、音视频等文件，并在需要时提取验证。

典型应用场景：
- **文件溯源**：追踪泄露文件的来源（通过嵌入发送者/分发者标识）
- **内容归属**：确认文件与业务记录的对应关系
- **分发追踪**：记录文件每次分发的对象和时间

### 支持格式一览

| 类型 | 扩展名 | 推荐场景 |
|------|--------|---------|
| 文档 | `.pdf` `.docx` `.pptx` `.xlsx` `.odt` `.odp` `.ods` `.epub` `.rtf` | 合同/报告/电子书 |
| 图片 | `.png` `.jpg` `.jpeg` `.bmp` `.webp` `.gif` `.tiff` `.heic` | 设计素材/摄影作品 |
| 音频 | `.wav` `.mp3` `.flac` `.aac` `.m4a` `.ogg` | 音乐/语音 |
| 视频 | `.mp4` `.mov` `.avi` `.mkv` `.webm` `.wmv` | 视频/直播录像 |

> 注意：有损压缩格式（MP3/OGG/HEIC）可能无法稳定提取水印，建议使用无损格式或经二次编码后重新嵌入。

---

## 2. 水印内容格式

### 2.1 格式规范

水印内容为 JSON，字段定义如下：

```json
{
  "v": 1,
  "type": "tracking",
  "issuer": "user:13800138000",
  "timestamp": "2026-05-05T10:34:00Z",
  "payload": "FILE-2025-001",
  "nonce": "a1b2c3d4e5f67890"
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 | 示例 |
|------|------|:----:|------|------|
| `v` | int | ✅ | 格式版本，当前固定为 `1` | `1` |
| `type` | string | ✅ | 水印类型，见下表 | `"tracking"` |
| `issuer` | string | ✅ | 签发者标识（用户ID / 分发者ID / 组织ID） | `"user:13800138000"` |
| `timestamp` | string | ✅ | ISO 8601 时间戳（UTC） | `"2026-05-05T10:34:00Z"` |
| `payload` | string | ❌ | 自定义内容，建议放文件ID或业务主键 | `"FILE-2025-001"` |
| `nonce` | string | ✅ | 随机数，防重放攻击，16~32位 hex | `"f3e2d1c0a1b2c3d4"` |

### 水印类型

| type | 适用场景 |
|------|---------|
| `copyright` | 正式权属声明 |
| `provenance` | 来源溯源/作品流传记录 |
| `brand` | 品牌保护 |
| `tracking` | 泄露追踪/分发记录 |
| `watermark` | 通用水印 |

### 2.2 issuer 格式说明

`issuer` 支持三种标识符格式：

| 格式 | 示例 | 适用场景 |
|------|------|---------| 
| 用户ID | `user:13800138000` | 移动端用户 |
| 组织ID | `org:acme-corp` | 企业用户 |
| URI | `https://app.example.com/users/123` | 常规 Web 服务 |
| UUID | `550e8400-e29b-41d4-a716-446655440000` | 内部系统主键 |

### 2.3 完整 JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["v", "type", "issuer", "timestamp", "nonce"],
  "properties": {
    "v": { "type": "integer", "minimum": 1, "maximum": 99 },
    "type": { "type": "string", "enum": ["copyright", "provenance", "brand", "tracking", "watermark"] },
    "issuer": { "type": "string", "minLength": 1, "maxLength": 256 },
    "timestamp": { "type": "string", "format": "date-time" },
    "payload": { "type": "string", "maxLength": 1024 },
    "nonce": { "type": "string", "pattern": "^[0-9a-fA-F]{16,32}$" }
  }
}
```

---

## 3. HTTP API 参考

### 3.1 基础信息

| 项目 | 值 |
|------|---|
| Base URL | `http://<host>:8000` |
| 文档页面 | `http://<host>:8000/docs`（Swagger UI） |
| 认证方式 | 当前版本无认证，建议通过 Nginx 层做 IP 白名单或 JWT 反向代理 |
| 字符编码 | UTF-8 |
| Content-Type | `multipart/form-data` |

### 3.2 限流策略

| 端点 | 限制 | 说明 |
|------|------|------|
| 全局（默认） | 100 次/分钟/IP | 未单独标注的端点 |
| `/embed` | 30 次/分钟/IP | 嵌入操作较重，独立限流 |
| `/extract` | 30 次/分钟/IP | 提取操作较重，独立限流 |
| `/health` | 200 次/分钟/IP | 健康检查，宽松限制 |

超限返回 HTTP `429 Too Many Requests`。

### 3.3 端点一览

| 端点 | 方法 | 限流 | 说明 |
|------|------|:----:|------|
| `/health` | GET | 200/min | 健康检查 |
| `/info` | GET | 100/min | 支持格式列表 |
| `/watermark/generate` | POST | 100/min | 生成合规水印 JSON |
| `/validate` | POST | 100/min | 验证水印格式 |
| `/embed` | POST | 30/min | 嵌入水印 |
| `/extract` | POST | 30/min | 提取水印 |
| `/verify` | POST | 30/min | 验证水印是否匹配 |
| `/batch` | POST | — | 批量处理 |
| `/output-file/{file_id}` | GET | — | 下载输出文件 |

### 3.4 生成水印

**POST** `/watermark/generate`

生成符合格式规范的水印 JSON，自动填充 `timestamp` 和 `nonce`。

**Request Body（JSON）**

```json
{
  "type": "tracking",
  "issuer": "user:13800138000",
  "payload": "FILE-2025-001"
}
```

**Response**

```json
{
  "watermark": "eyJ2IjoxLCJ0eXBlIjoidHJhY2tpbmci...",
  "data": {
    "v": 1,
    "type": "tracking",
    "issuer": "user:13800138000",
    "timestamp": "2026-05-05T10:34:00Z",
    "payload": "FILE-2025-001",
    "nonce": "a1b2c3d4e5f67890"
  }
}
```

> 服务器自动生成 `timestamp`（UTC）和 `nonce`（16字节 hex 随机数）。`issuer` 和 `payload` 由业务系统提供。

### 3.5 嵌入水印

**POST** `/embed`
> 限流：30 次/分钟/IP

**Request（multipart/form-data）**

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `file` | file | ✅ | 待嵌入的文件（multipart 文件上传） |
| `watermark` | string | ✅ | 水印内容（JSON 字符串） |
| `password` | string | ❌ | AES-256 加密密码（设置后提取时也需提供） |
| `permanent` | bool | ❌ | `true` = 永久保留输出文件；默认 90 天后自动清理 |
| `robust` | bool | ❌ | `true` = 鲁棒模式（抗亮度/对比度调整、JPEG 压缩） |

**Response**

```json
{
  "success": true,
  "watermark": "eyJ2IjoxLCJ0eXBlIjoidHJhY2tpbmci...",
  "file_id": "a3f8b2c1-...",
  "filename": "document_watermarked.pdf",
  "message": "Watermark embedded successfully."
}
```

**下载输出文件**

嵌入成功后，通过 `file_id` 下载：

```
GET /output-file/{file_id}
```

### 3.6 提取水印

**POST** `/extract`
> 限流：30 次/分钟/IP

**Request（multipart/form-data）**

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `file` | file | ✅ | 已嵌入水印的文件 |
| `password` | string | ❌ | 解密密码（嵌入时如果设置了 password） |

**Response**

```json
{
  "success": true,
  "watermark": "eyJ2IjoxLCJ0eXBlIjoidHJhY2tpbmci...",
  "format": "pdf",
  "message": "Watermark extracted.",
  "parsed": {
    "v": 1,
    "type": "tracking",
    "issuer": "user:13800138000",
    "timestamp": "2026-05-05T10:34:00Z",
    "payload": "FILE-2025-001",
    "nonce": "a1b2c3d4e5f67890"
  }
}
```

### 3.7 验证水印

**POST** `/verify`
> 限流：30 次/分钟/IP

**Request（multipart/form-data）**

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `file` | file | ✅ | 已嵌入水印的文件 |
| `watermark` | string | ✅ | 期望的水印内容（用于比对） |

**Response**

```json
{
  "success": true,
  "match": true,
  "extracted": "eyJ2IjoxLC...",
  "expected": "eyJ2IjoxLC...",
  "match_score": 1.0
}
```

### 3.8 错误码

| HTTP 状态码 | 说明 |
|------------|------|
| `200` | 成功 |
| `400` | 请求参数错误（如水印格式不合规、缺少必填字段） |
| `404` | 文件不存在或已过期（输出文件超过 90 天保留期） |
| `413` | 文件过大（建议 < 500MB） |
| `422` | 文件格式不支持 |
| `429` | 超过限流（见 3.2 节） |
| `500` | 服务器内部错误 |

---

## 4. 集成流程

### 4.1 文件登记流程（嵌入）

```
1. 业务系统生成文件ID（如 FILE-2025-001）
2. POST /watermark/generate
   → 获取 watermark JSON（含 timestamp + nonce）
3. POST /embed（上传文件 + watermark JSON）
   → 获取 file_id
4. 将 file_id 关联到文件记录，存储元数据库
5. （可选）GET /output-file/{file_id} 下载带水印文件
```

### 4.2 文件溯源流程（提取）

```
1. 从数据库取出文件的 file_id
2. GET /output-file/{file_id} 获取带水印文件
3. POST /extract（上传文件）
   → 获取 watermark JSON（含 issuer, payload 等）
4. 解析 issuer 和 payload，与文件记录比对
5. 匹配则确认归属，不匹配则告警
```

### 4.3 批量处理

**POST** `/batch`

适用于一次性处理大量文件（如批量登记、历史文件补充嵌入）。

**Request Body（JSON）**

```json
{
  "files": ["file1.pdf", "file2.docx", "file3.png"],
  "watermark": "{\"v\":1,\"type\":\"tracking\",...}",
  "password": null,
  "robust": false
}
```

**Response**

```json
{
  "total": 3,
  "success": 2,
  "failed": 1,
  "results": [
    { "filename": "file1.pdf", "success": true,  "file_id": "..." },
    { "filename": "file2.docx", "success": true,  "file_id": "..." },
    { "filename": "file3.png", "success": false,  "message": "Unsupported format" }
  ]
}
```

---

## 5. Java SDK 使用示例

### 5.1 依赖（Maven pom.xml）

```xml
<dependency>
    <groupId>com.squareup.okhttp3</groupId>
    <artifactId>okhttp</artifactId>
    <version>4.12.0</version>
</dependency>
<dependency>
    <groupId>org.json</groupId>
    <artifactId>json</artifactId>
    <version>20240303</version>
</dependency>
```

> 若不想引入第三方 HTTP 库，可用 Java 11 内置的 `java.net.http.HttpClient`。

### 5.2 完整集成示例

```java
package com.example.watermark;

import okhttp3.*;
import org.json.JSONObject;
import java.io.*;
import java.nio.file.*;
import java.util.*;

public class StealthMarkClient {

    private static final String API_BASE = "http://localhost:8000";
    private final OkHttpClient client = new OkHttpClient.Builder()
            .connectTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
            .readTimeout(60, java.util.concurrent.TimeUnit.SECONDS)
            .writeTimeout(60, java.util.concurrent.TimeUnit.SECONDS)
            .build();

    // ==================== 第一步：生成水印 ====================

    /**
     * 向 StealthMark 申请一个合规水印 JSON。
     *
     * @param issuer  签发者标识，如用户ID、分发者ID
     * @param payload 自定义内容，建议放文件ID或业务主键
     * @param type    水印类型：tracking / provenance / brand / copyright
     * @return 水印 JSON 对象（包含 v, type, issuer, timestamp, nonce, payload）
     */
    public JSONObject generateWatermark(String issuer, String payload, String type) throws IOException {
        JSONObject req = new JSONObject();
        req.put("type", type != null ? type : "tracking");
        req.put("issuer", issuer);
        req.put("payload", payload);

        String response = postJson("/watermark/generate", req.toString());
        return new JSONObject(response).getJSONObject("data");
    }

    // ==================== 第二步：嵌入水印 ====================

    /**
     * 将水印嵌入文件，返回输出文件的 file_id。
     *
     * @param inputFilePath 原始文件路径
     * @param watermark     水印 JSON（generateWatermark 返回值）
     * @param password      加密密码（可 null）
     * @return file_id，用于后续下载或关联文件记录
     */
    public String embed(String inputFilePath, JSONObject watermark, String password) throws IOException {
        Path path = Paths.get(inputFilePath);
        String ext = getExt(inputFilePath);
        String mime = getMime(ext);

        RequestBody fileBody = RequestBody.create(Files.readAllBytes(path),
                MediaType.parse(mime));

        MultipartBody.Builder builder = new MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart("file", path.getFileName().toString(), fileBody)
                .addFormDataPart("watermark", watermark.toString())
                .addFormDataPart("permanent", "true");

        if (password != null && !password.isEmpty()) {
            builder.addFormDataPart("password", password);
        }

        String resp = postMultipart("/embed", builder.build());
        JSONObject json = new JSONObject(resp);

        if (!json.getBoolean("success")) {
            throw new IOException("嵌入失败: " + json.optString("message"));
        }
        return json.getString("file_id");
    }

    // ==================== 第三步：提取水印 ====================

    /**
     * 从已嵌入文件提取水印信息。
     *
     * @param filePath 已嵌入的文件路径
     * @param password 加密时的密码（可 null）
     * @return 水印 JSON（含 issuer, payload 等）
     */
    public JSONObject extract(String filePath, String password) throws IOException {
        Path path = Paths.get(filePath);
        String ext = getExt(filePath);
        String mime = getMime(ext);

        MultipartBody.Builder builder = new MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart("file", path.getFileName().toString(),
                        RequestBody.create(Files.readAllBytes(path),
                                MediaType.parse(mime)));

        if (password != null) {
            builder.addFormDataPart("password", password);
        }

        String resp = postMultipart("/extract", builder.build());
        JSONObject json = new JSONObject(resp);

        if (!json.getBoolean("success")) {
            throw new IOException("提取失败: " + json.optString("message"));
        }
        return json.getJSONObject("parsed");
    }

    // ==================== 第四步：下载输出文件 ====================

    /**
     * 根据 file_id 下载带水印的输出文件。
     *
     * @param fileId   embed 接口返回的 file_id
     * @param savePath 本地保存路径
     */
    public void download(String fileId, String savePath) throws IOException {
        Request request = new Request.Builder()
                .url(API_BASE + "/output-file/" + fileId)
                .get().build();

        try (Response response = client.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                throw new IOException("下载失败: HTTP " + response.code());
            }
            Files.write(Paths.get(savePath),
                    Objects.requireNonNull(response.body()).bytes());
        }
    }

    // ==================== 端到端演示 ====================

    public static void main(String[] args) throws Exception {
        StealthMarkClient api = new StealthMarkClient();

        String issuer = "user:13800138000";
        String fileId = "FILE-2025-001";

        // ① 生成水印
        JSONObject watermark = api.generateWatermark(issuer, fileId, "tracking");
        System.out.println("[水印] " + watermark.toString(2));

        // ② 嵌入文件
        String outputFileId = api.embed("test.pdf", watermark, null);
        System.out.println("[嵌入成功] file_id = " + outputFileId);

        // ③ 下载到本地
        api.download(outputFileId, "test_watermarked.pdf");

        // ④ 提取水印（模拟：从下载的文件中提取）
        JSONObject extracted = api.extract("test_watermarked.pdf", null);
        System.out.println("[提取] issuer=" + extracted.optString("issuer")
                + ", file_id=" + extracted.optString("payload"));

        // ⑤ 归属验证：比对提取结果与文件记录
        boolean matched = issuer.equals(extracted.optString("issuer"))
                && fileId.equals(extracted.optString("payload"));
        System.out.println("[归属验证] " + (matched ? "✅ 匹配" : "❌ 不匹配"));
    }

    // ==================== 工具方法 ====================

    private String postJson(String path, String jsonBody) throws IOException {
        RequestBody body = RequestBody.create(jsonBody,
                MediaType.parse("application/json"));
        Request request = new Request.Builder()
                .url(API_BASE + path).post(body).build();
        try (Response r = client.newCall(request).execute()) {
            return r.body() == null ? "" : r.body().string();
        }
    }

    private String postMultipart(String path, RequestBody body) throws IOException {
        Request request = new Request.Builder()
                .url(API_BASE + path).post(body).build();
        try (Response r = client.newCall(request).execute()) {
            if (!r.isSuccessful()) {
                throw new IOException("HTTP " + r.code() + ": " + r.message());
            }
            return r.body() == null ? "" : r.body().string();
        }
    }

    private static String getExt(String path) {
        int dot = path.lastIndexOf('.');
        return dot > 0 ? path.substring(dot + 1).toLowerCase() : "";
    }

    private static String getMime(String ext) {
        return switch (ext) {
            case "pdf"  -> "application/pdf";
            case "docx" -> "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
            case "png"  -> "image/png";
            case "jpg", "jpeg" -> "image/jpeg";
            case "mp4"  -> "video/mp4";
            case "mp3"  -> "audio/mpeg";
            case "wav"  -> "audio/wav";
            default -> "application/octet-stream";
        };
    }
}
```

### 5.3 与文件数据库的关联设计

```
文件记录表（watermarked_files）
─────────────────────────────────
id              BIGINT PRIMARY KEY
file_id         VARCHAR(64)   -- 业务文件标识（payload）
issuer          VARCHAR(256)  -- 签发者标识（issuer）
distributor_id  VARCHAR(128)  -- 分发者ID（如适用）
file_mark_id    VARCHAR(64)   -- StealthMark 返回的 file_id
original_hash   VARCHAR(64)   -- 原始文件 SHA-256（可选）
watermark_json  TEXT          -- 完整水印 JSON（存档）
created_at      TIMESTAMP     -- 登记时间
```

> `file_mark_id` 即嵌入成功后 API 返回的 UUID，可通过 `GET /output-file/{file_mark_id}` 随时获取带水印文件。
>
> 建议将 `watermark_json` 完整存档，便于出现纠纷时提供水印证据链。

---

## 6. 部署说明

### 6.1 快速启动

```bash
# 安装
pip install "stealthmark[api]" -e .

# 启动（默认 8000 端口）
uvicorn stealthmark.api:app --host 0.0.0.0 --port 8000

# 或指定配置
uvicorn stealthmark.api:app --host 0.0.0.0 --port 8000 --workers 4
```

### 6.2 Docker 部署（推荐）

```yaml
# docker-compose.yml
version: '3.8'
services:
  stealthmark:
    build: .
    ports:
      - "8000:8000"
    environment:
      - STEALTHMARK_FILE_DIR=/app/static/file
      - STEALTHMARK_RETENTION_DAYS=90
      - STEALTHMARK_CLEANUP_INTERVAL=3600
    volumes:
      - stealthmark-data:/app/static/file

volumes:
  stealthmark-data:
```

### 6.3 安全建议

1. **网络隔离**：API 服务不应直接暴露公网，通过 Nginx 反向代理
2. **IP 白名单**：在 Nginx 层配置 IP 白名单或 JWT 认证
3. **文件大小限制**：Nginx 配置 `client_max_body_size 500m`
4. **HTTPS**：生产环境必须启用 TLS，推荐 Let's Encrypt + certbot
5. **限流观察**：监控 `/health` 返回的 `rate_limit_remaining`，及时调整阈值

### 6.4 生产环境 Nginx 配置示例

```nginx
server {
    listen 443 ssl;
    server_name stealthmark.example.com;

    ssl_certificate     /etc/letsencrypt/live/stealthmark.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/stealthmark.example.com/privkey.pem;

    # 安全头
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options DENY always;

    # 文件大小限制
    client_max_body_size 500m;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300s;
    }
}
```

### 6.5 存储容量估算

| 文件类型 | 平均大小 | 90天保留估算（1万文件/天） |
|---------|---------|------------------------|
| PDF/文档 | 2 MB | 1.8 TB |
| 图片 | 5 MB | 4.5 TB |
| 音视频 | 50 MB | 45 TB |

> 建议开启 `permanent=false`（默认），90 天后自动清理非永久文件，超大文件建议单独归档。

---

## 7. FAQ

**Q：文件经过微信/QQ/邮箱传输后，水印还能提取吗？**
A：取决于文件格式。PNG/BMP（LSB）经过图片压缩大概率损坏；PDF 元数据通常保留；JPEG（图片）经过微信转码会损坏。建议分发时使用 PDF 或原始无损格式，并告知下游不要二次转码。

**Q：水印支持批量删除/替换吗？**
A：当前版本不支持抹除水印。如需替换，请重新嵌入覆盖原文件（原水印会被覆盖）。

**Q：一个文件可以嵌入多个水印吗？**
A：当前版本每个文件只支持一个水印。如需记录多个分发对象，建议在 `payload` 中用 JSON 数组描述。

**Q：API 支持异步处理大文件吗？**
A：当前版本为同步处理，建议大文件（>100MB）通过消息队列异步调用，结果通过 webhook 或轮询获取。

**Q：提取水印时如何判断文件未被动过手脚？**
A：水印包含 CRC32 校验，提取时会验证数据完整性；另外可结合文件 SHA-256 哈希与存档记录对比，确保文件未被篡改。

---

## 附录：快速参考卡

```bash
# 1. 生成水印
curl -X POST http://localhost:8000/watermark/generate \
  -H "Content-Type: application/json" \
  -d '{"type":"tracking","issuer":"user:13800138000","payload":"FILE-001"}'

# 2. 嵌入
curl -X POST http://localhost:8000/embed \
  -F "file=@document.pdf" \
  -F "watermark={\"v\":1,\"type\":\"tracking\",\"issuer\":\"user:13800138000\",\"timestamp\":\"2026-05-05T10:34:00Z\",\"payload\":\"FILE-001\",\"nonce\":\"a1b2c3d4e5f67890\"}" \
  -F "permanent=true"

# 3. 提取
curl -X POST http://localhost:8000/extract \
  -F "file=@document_watermarked.pdf"

# 4. 验证
curl -X POST http://localhost:8000/verify \
  -F "file=@document_watermarked.pdf" \
  -F "watermark={\"v\":1,\"type\":\"tracking\",...}"
```
