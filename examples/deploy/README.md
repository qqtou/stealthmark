# StealthMark HTTPS 部署方案

## 方案一：nginx 反向代理（推荐生产环境）

```nginx
# examples/deploy/nginx.conf
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # TLS 证书（Let's Encrypt 自动续期推荐 certbot）
    ssl_certificate     /etc/ssl/certs/stealthmark.crt;
    ssl_certificate_key /etc/ssl/private/stealthmark.key;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    # 上传文件大小限制（默认 100MB，StealthMark 最大水印文件）
    client_max_body_size 200M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # 超时配置
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;

        # 文件上传需要较大的 client body
        client_max_body_size 200M;
    }
}
```

### 部署步骤

```bash
# 1. 申请证书（Let's Encrypt）
sudo certbot --nginx -d your-domain.com

# 2. 复制配置文件
sudo cp nginx.conf /etc/nginx/sites-available/stealthmark
sudo ln -s /etc/nginx/sites-available/stealthmark /etc/nginx/sites-enabled/

# 3. 测试并重载
sudo nginx -t
sudo systemctl reload nginx

# 4. 启动 StealthMark API
cd /path/to/stealthmark
uvicorn stealthmark.api:app --host 127.0.0.1 --port 8000
```

---

## 方案二：Caddy（更简单，自动 HTTPS）

```caddy
# examples/deploy/Caddyfile
# 一行配置，自动 Let's Encrypt + TLS 1.3
your-domain.com {
    reverse_proxy localhost:8000
    encode gzip

    # 上传文件限制
    request_body /api/* {
        max_size 200MB
    }
}
```

```bash
# 部署
wget -O caddy "https://github.com/caddyserver/caddy/releases/latest/download/GETTING_STARTED.html"
# 或按官方文档安装
curl -fsSL https://getcaddy.com | bash

# 启动 Caddy
caddy run --config Caddyfile
```

---

## 方案三：Docker Compose 一键部署（推荐）

```yaml
# examples/deploy/docker-compose.yml
services:
  stealthmark-api:
    image: qqtou/stealthmark:latest
    container_name: stealthmark-api
    restart: unless-stopped
    ports:
      - "127.0.0.1:8000:8000"  # 仅本地暴露，由代理对外
    volumes:
      - ./data:/app/data       # 持久化存储
      - ./config.ini:/app/config.ini
    environment:
      - STEALTHMARK_PORT=8000
      - STEALTHMARK_HOST=0.0.0.0
    command: uvicorn stealthmark.api:app --host 0.0.0.0 --port 8000

  nginx:
    image: nginx:alpine
    container_name: stealthmark-nginx
    restart: unless-stopped
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - /etc/ssl/certs/stealthmark.crt:/etc/ssl/certs/stealthmark.crt:ro
      - /etc/ssl/private/stealthmark.key:/etc/ssl/private/stealthmark.key:ro
    depends_on:
      - stealthmark-api

  # 自动续期证书（每周检查）
  certbot:
    image: certbot/certbot
    container_name: stealthmark-certbot
    volumes:
      - ./data/certbot/www:/var/www/certbot
      - ./data/certbot/conf:/etc/letsencrypt
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 86400 & wait $$!; done'"
```

```bash
# 部署
cd examples/deploy
docker compose up -d

# 首次申请证书（需域名已解析）
docker run --rm -v ./data/certbot/www:/var/www/certbot \
  -v ./data/certbot/conf:/etc/letsencrypt \
  certbot/certbot certonly --webroot -w /var/www/certbot \
  -d your-domain.com --email your@email.com --agree-tos --no-eff-email
```

---

## Java 客户端信任证书（自签名测试环境）

如果用自签名证书，Java 客户端需要导入证书：

```java
// 方法1：导入系统证书库
// keytool -importcert -trustcacerts -file your-cert.crt -alias stealthmark -keystore $JAVA_HOME/lib/security/cacerts -storepass changeit

// 方法2：OkHttp 信任自签名（仅测试用）
private static final TrustManager[] INSECURE_TRUST_MANAGER = new TrustManager[]{
    new X509TrustManager() {
        public X509Certificate[] getAcceptedIssuers() { return new X509Certificate[0]; }
        public void checkClientTrusted(X509Certificate[] chain, String authType) {}
        public void checkServerTrusted(X509Certificate[] chain, String authType) {}
    }
};

OkHttpClient client = new OkHttpClient.Builder()
    .sslSocketFactory(createSSLFactory(), (X509TrustManager) INSECURE_TRUST_MANAGER[0])
    .hostnameVerifier((hostname, session) -> true)  // ⚠️ 仅测试
    .build();
```

**生产环境**：用 Let's Encrypt 或商业 CA 签发的证书，Java 客户端无需任何修改。

---

## 快速验证

```bash
# 检查 HTTPS 是否生效
curl -I https://your-domain.com/api/health

# 检查 TLS 版本和加密套件
curl -v https://your-domain.com/api/health 2>&1 | grep -E "SSL|TLS|cipher"
```