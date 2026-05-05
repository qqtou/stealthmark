# Java SDK 示例

通过 HTTP 与 [StealthMark API](http://localhost:8001/docs) 集成。

## 快速开始

### 1. 安装依赖

```bash
cd examples/java
mvn compile
```

### 2. 配置 API 地址

编辑 `StealthMarkDemo.java`，修改：

```java
private static final String BASE_URL = "http://localhost:8001";
```

**生产环境**：改为 `https://your-domain.com`（需要先配置 HTTPS，见下）。

### 3. 运行演示

```bash
mvn exec:java -Dexec.mainClass="com.example.stealthmark.StealthMarkDemo"
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `StealthMarkDemo.java` | 完整示例：generate → embed → extract → verify → batch |
| `pom.xml` | Maven 依赖：OkHttp 4.12 + org.json |

## 依赖说明

- **OkHttp 4.x**：连接池、重试、超时、TLS 配置，开箱即用
- **org.json**：轻量 JSON 解析，不依赖 Jackson

> 如用 Spring 生态，可换用 `WebClient`（spring-boot-starter-webflux）。

## 完整工作流

```
① generateWatermark()   生成结构化水印 JSON
        ↓
② embed()               嵌入文件，拿到 /static/file/... 路径
        ↓
③ downloadFile()        下载到本地（如不在同机）
        ↓
④ extract()             从文件提取水印，解析出 author/work_id
        ↓
⑤ verify()             验证 author + work_id 是否匹配
```

## 集成到你的 Java 系统

复制 `StealthMarkDemo.java` 到你的项目，调整：

1. `BASE_URL` → 你的 API 地址
2. `MIME_TYPES` → 补充你需要的文件类型
3. 水印内容字段按业务需求填（author DID / org / work_id / type）
4. 批量接口用 `batch()` 一次处理多文件

## HTTPS 配置（生产环境）

StealthMark API 本身支持 HTTPS（用 nginx/caddy 反向代理即可），客户端无需改代码，只需：

```java
// 信任自签名证书（测试环境）
private static final TrustManager[] INSECURE_TRUST_MANAGER = new TrustManager[]{
    new X509TrustManager() {
        public X509Certificate[] getAcceptedIssuers() { return new X509Certificate[0]; }
        public void checkClientTrusted(X509Certificate[] chain, String authType) {}
        public void checkServerTrusted(X509Certificate[] chain, String authType) {}
    }
};

OkHttpClient client = new OkHttpClient.Builder()
    .sslSocketFactory(createSSLFactory(), (X509TrustManager) INSECURE_TRUST_MANAGER[0])
    .hostnameVerifier((hostname, session) -> true)  // 测试用，生产不要用
    .build();
```

**生产环境**：正确配置 TLS 证书链，`hostnameVerifier` 返回正常验证结果。
