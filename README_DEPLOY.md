# AIDD (AI Document Detector) - 部署指南

## 🚀 一键快速启动

**最简单的启动方式**（适合快速体验）：

```bash
# 克隆项目
git clone <repository-url>
cd ai_docs2

# 一键启动
./start.sh
```

启动后访问：
- 前端界面: http://localhost:3000
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs

## 📋 系统要求

### 基础要求
- Docker 20.10+
- Docker Compose 2.0+ (或docker-compose 1.29+)
- 8GB+ 可用内存
- 10GB+ 可用磁盘空间

### 生产环境推荐
- Docker 24.0+
- 16GB+ 内存
- 50GB+ SSD磁盘空间
- 反向代理（Nginx/Traefik）
- SSL证书

## 🛠️ 部署方式

### 方式1: 快速启动（开发/测试）

```bash
# 使用快速启动脚本
./start.sh

# 或使用原生Docker Compose
docker compose up -d
```

### 方式2: 完整部署脚本

```bash
# 开发环境
./deploy.sh

# 生产环境
./deploy.sh -e prod up

# 查看更多选项
./deploy.sh --help
```

### 方式3: 手动构建部署

```bash
# 构建镜像
./build.sh build

# 启动服务
docker compose up -d

# 推送镜像到仓库
./build.sh --push build
```

## ⚙️ 配置说明

### 环境文件配置

创建 `.env` 文件进行配置：

```bash
# 基础配置
DATABASE_TYPE=sqlite                    # 数据库类型: sqlite/postgresql
ENVIRONMENT=development                 # 环境: development/production
DEBUG=true                             # 调试模式

# 端口配置
BACKEND_PORT=8000                      # 后端端口
FRONTEND_PORT=3000                     # 前端端口

# 安全配置
JWT_SECRET_KEY=your-secret-key         # JWT密钥
OAUTH_CLIENT_SECRET=your-oauth-secret  # OAuth密钥

# AI服务配置
OPENAI_API_KEY=your-openai-api-key     # OpenAI API Key
```

### 生产环境配置

生产环境使用PostgreSQL：

```bash
# 数据库配置
DATABASE_TYPE=postgresql
POSTGRES_DB=aidd_db
POSTGRES_USER=aidd
POSTGRES_PASSWORD=secure-password

# 安全配置
JWT_SECRET_KEY=$(openssl rand -base64 32)
OAUTH_CLIENT_SECRET=your-production-oauth-secret

# 域名配置
EXTERNAL_HOST=yourdomain.com
EXTERNAL_PORT=443
EXTERNAL_PROTOCOL=https
FRONTEND_DOMAIN=https://yourdomain.com
```

## 🌐 Nginx反向代理配置

生产环境建议使用Nginx作为反向代理：

```nginx
# /etc/nginx/sites-available/aidd
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # 前端静态文件
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 后端API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket支持
    location /ws/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 文件上传限制
    client_max_body_size 50M;
}
```

## 📊 监控和日志

### 查看服务状态

```bash
# 查看所有服务状态
./deploy.sh status

# 查看日志
./deploy.sh logs

# 查看特定服务日志
docker compose logs -f aidd-backend
docker compose logs -f aidd-frontend
```

### 健康检查

系统提供健康检查端点：

```bash
# 后端健康检查
curl http://localhost:8000/health

# 前端健康检查
curl http://localhost:3000/
```

## 💾 数据备份与恢复

### 自动备份

```bash
# 创建数据备份
./deploy.sh backup

# 查看备份文件
ls backups/
```

### 手动备份

```bash
# PostgreSQL备份
docker exec aidd-postgres pg_dump -U aidd aidd_db > backup.sql

# SQLite备份
docker cp aidd-backend:/app/data/app.db ./app.db.backup

# 上传文件备份
docker cp aidd-backend:/app/data/uploads ./uploads_backup
```

## 🔧 故障排除

### 常见问题

**1. 端口冲突**
```bash
# 检查端口占用
lsof -i :8000
lsof -i :3000

# 修改端口配置
vi .env
```

**2. 内存不足**
```bash
# 查看内存使用
docker stats

# 增加Docker内存限制
vi docker-compose.yml
```

**3. 数据库连接失败**
```bash
# 检查数据库状态
docker compose ps postgres

# 查看数据库日志
docker compose logs aidd-postgres
```

**4. 镜像构建失败**
```bash
# 清理Docker缓存
docker system prune -f

# 重新构建
./build.sh --no-cache build
```

### 日志位置

```bash
# 容器日志
docker compose logs [service-name]

# 应用日志（如果挂载了日志目录）
./data/logs/
```

## 🛡️ 安全建议

### 生产环境安全检查清单

- [ ] 修改默认密码和密钥
- [ ] 启用HTTPS/SSL
- [ ] 配置防火墙规则
- [ ] 定期更新镜像
- [ ] 设置日志轮转
- [ ] 配置资源限制
- [ ] 启用访问控制
- [ ] 定期备份数据

### 网络安全

```bash
# 限制Docker网络访问
iptables -A DOCKER-USER -i ext_if ! -s 192.168.1.0/24 -j DROP

# 使用内网IP
EXTERNAL_HOST=10.0.0.100
```

## 📱 多平台支持

### ARM64架构支持

```bash
# 构建多平台镜像
./build.sh --platforms linux/amd64,linux/arm64 build

# 在ARM设备上部署
./deploy.sh up
```

### 云平台部署

#### Docker Swarm
```bash
docker stack deploy -c docker-compose.yml aidd
```

#### Kubernetes
```bash
# 生成Kubernetes配置
kompose convert -f docker-compose.yml
kubectl apply -f .
```

## 🔄 更新和升级

### 更新到最新版本

```bash
# 拉取最新代码
git pull origin main

# 重新构建并启动
./deploy.sh --build restart
```

### 滚动更新

```bash
# 逐个更新服务
docker compose up -d --no-deps aidd-backend
docker compose up -d --no-deps aidd-frontend
```

## 📞 技术支持

如遇到部署问题，请：

1. 检查[故障排除](#故障排除)章节
2. 查看项目Issues页面
3. 提供详细的错误日志和环境信息

---

**快速命令参考**：

```bash
# 快速启动
./start.sh

# 完整部署
./deploy.sh up

# 查看状态
./deploy.sh status

# 查看日志  
./deploy.sh logs

# 停止系统
./deploy.sh down

# 数据备份
./deploy.sh backup
```