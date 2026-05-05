# StealthMark 部署指南

本目录提供三种部署方案，从简单到生产级。

---

## 方案一：Docker Compose 一键部署（推荐）

适合快速体验和小型生产环境。

### 前置条件

- Docker 20.10+
- Docker Compose v2+
- 已解析到服务器的域名（申请 SSL 证书用）

### 部署步骤

```bash
cd examples/deploy

# 1. 首次申请 Let's Encrypt 证书
# 先创建目录
mkdir -p certs-challenge certs/live/your-domain.com

# 使用 certbot 申请证书（需要域名已解析到服务器）
docker run --rm \
  -v "$(pwd)/certs-challenge:/var/www/certbot" \
  -v "$(pwd)/certs:/etc/letsencrypt" \
  certbot/certbot certonly \
  --webroot -w /var/www/certbot \
  -d your-domain.com \
  --email your@email.com \
  --agree-tos --no-eff-email

# 2. 修改 nginx.conf 中的 your-domain.com 为实际域名
# 3. 启动服务
docker compose up -d

# 4. 验证
curl http://localhost:8000/health
```

### 更新配置后重载

```bash
docker compose down
# 修改 nginx.conf 或其他配置
docker compose up -d --build
```

---

## 方案二：nginx 反向代理（已有服务器）

适合已有 Web 服务器的场景。

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate     /etc/ssl/certs/stealthmark.crt;
    ssl_certificate_key /etc/ssl/private/stealthmark.key;
    ssl_protocols TLSv1.2 TLSv1.3;

    client_max_body_size 200M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

```bash
# 安装证书（Let's Encrypt）
sudo certbot --nginx -d your-domain.com

# 启动 API
cd /path/to/stealthmark
uvicorn stealthmark.api:app --host 127.0.0.1 --port 8000
```

---

## 方案三：Caddy（最简单，自动 HTTPS）

```bash
# 安装 Caddy
# https://caddyserver.com/docs/install

# 创建 Caddyfile
your-domain.com {
    reverse_proxy localhost:8000
    encode gzip
    request_body /embed* {
        max_size 200MB
    }
}

# 启动
caddy run
```

---

## 文件说明

| 文件 | 说明 |
|------|------|
| `docker-compose.yml` | Docker Compose 部署配置 |
| `nginx.conf` | nginx 反向代理配置（含 TLS） |
| `Caddyfile` | Caddy 一键 HTTPS 配置 |

---

## 目录结构

```
examples/deploy/
├── docker-compose.yml   # Docker Compose 配置
├── nginx.conf           # nginx 配置模板
├── Caddyfile            # Caddy 配置模板
├── certs/               # SSL 证书（需手动申请后放入）
│   └── live/
│       └── your-domain.com/
├── certs-challenge/     # certbot ACME 挑战目录
└── README.md            # 本文件
```

---

## 常见问题

**Q：docker-compose up 报 `image not found`？**
A：使用 `docker compose up -d --build` 从本地源码构建，或先推送到 Docker Hub 再 pull。

**Q：证书申请失败？**
A：确保域名已解析到服务器，且 80 端口未被占用。

**Q：文件上传超时？**
A：nginx 和 uvicorn 的超时都需要调大，参考方案一中的配置。
