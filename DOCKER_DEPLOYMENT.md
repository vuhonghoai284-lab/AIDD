# Docker 部署指南

本文档说明如何使用Docker部署AI文档测试系统，支持外部配置文件和环境变量。

## 🚀 快速开始

### 1. 使用 Docker Compose（推荐）

```bash
# 开发环境
docker-compose up -d

# 生产环境
docker-compose -f docker-compose.prod.yml up -d
```

### 2. 单独运行容器

```bash
# 后端服务
docker run -d \
  --name ai-docs-backend \
  -p 8000:8000 \
  -v $(pwd)/backend/config.yaml:/app/config/config.yaml:ro \
  -v $(pwd)/.env:/app/.env:ro \
  -v ai-docs-data:/app/data \
  ghcr.io/wantiantian/ai_docs2/backend:latest

# 前端服务
docker run -d \
  --name ai-docs-frontend \
  -p 80:80 \
  -v $(pwd)/frontend/nginx.conf:/etc/nginx/conf.d/default.conf:ro \
  ghcr.io/wantiantian/ai_docs2/frontend:latest
```

## 📋 技术规格

### Docker镜像信息
- **后端基础镜像**: Python 3.12-slim
- **前端基础镜像**: Node 22-alpine + nginx:alpine
- **多架构支持**: linux/amd64, linux/arm64

### 端口配置
- **后端**: 8000
- **前端**: 80, 443 (HTTPS)
- **Redis**: 6379

## ⚙️ 配置文件管理

### 后端配置文件支持

后端支持通过挂载volume的方式提供配置文件：

```yaml
# docker-compose.yml
volumes:
  - ./backend/config.yaml:/app/config/config.yaml:ro
  - ./.env:/app/.env:ro
```

#### 环境变量配置

```bash
# 指定配置文件路径
CONFIG_FILE=/app/config/config.yaml

# 数据库配置
DATABASE_URL=sqlite:///app/data/app.db

# Redis配置
REDIS_URL=redis://redis:6379/0

# AI服务配置
OPENAI_API_KEY=your_openai_api_key
STRUCTURED_AI_API_KEY=your_structured_ai_api_key
```

### 配置文件示例

#### backend/config.yaml
```yaml
# 服务器配置
host: "0.0.0.0"
port: 8000
debug: false

# 数据库配置
database:
  url: "sqlite:///app/data/app.db"
  
# Redis配置
redis:
  url: "redis://redis:6379/0"

# AI模型配置
ai_models:
  default_index: 0
  models:
    - label: "GPT-4o Mini"
      provider: "openai"
      config:
        api_key: "${OPENAI_API_KEY}"
        base_url: "https://api.openai.com/v1"
        model: "gpt-4o-mini"

# 第三方认证配置
third_party_auth:
  gitee:
    client_id: "${GITEE_CLIENT_ID}"
    client_secret: "${GITEE_CLIENT_SECRET}"
    frontend_domain: "http://localhost"
```

#### .env 文件
```bash
# AI服务密钥
OPENAI_API_KEY=sk-your-openai-api-key
STRUCTURED_AI_API_KEY=your-structured-ai-api-key

# 第三方认证
GITEE_CLIENT_ID=your_gitee_client_id
GITEE_CLIENT_SECRET=your_gitee_client_secret

# 数据库（可选）
DATABASE_URL=sqlite:///app/data/app.db

# Redis密码（生产环境）
REDIS_PASSWORD=your_redis_password
```

## 🔧 部署方案

### 开发环境部署

```bash
# 1. 准备配置文件
cp backend/config.example.yaml backend/config.yaml
cp .env.example .env

# 2. 编辑配置文件，填入实际的API密钥

# 3. 启动服务
docker-compose up -d

# 4. 查看日志
docker-compose logs -f
```

### 生产环境部署

```bash
# 1. 拉取最新镜像
docker pull ghcr.io/wantiantian/ai_docs2/backend:latest
docker pull ghcr.io/wantiantian/ai_docs2/frontend:latest

# 2. 准备生产配置
cp backend/config.example.yaml config/config.prod.yaml
cp .env.example .env.prod

# 3. 创建数据目录
sudo mkdir -p /var/lib/ai-docs/{data,redis}
sudo mkdir -p /var/log/ai-docs

# 4. 启动生产环境
docker-compose -f docker-compose.prod.yml up -d

# 5. 设置自动更新（可选）
# Watchtower已包含在生产配置中，会自动更新镜像
```

### Kubernetes部署

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-docs-backend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ai-docs-backend
  template:
    metadata:
      labels:
        app: ai-docs-backend
    spec:
      containers:
      - name: backend
        image: ghcr.io/wantiantian/ai_docs2/backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: CONFIG_FILE
          value: "/app/config/config.yaml"
        volumeMounts:
        - name: config
          mountPath: /app/config
          readOnly: true
        - name: data
          mountPath: /app/data
      volumes:
      - name: config
        configMap:
          name: ai-docs-config
      - name: data
        persistentVolumeClaim:
          claimName: ai-docs-data
```

## 🗂️ 数据持久化

### Volume配置

```yaml
volumes:
  backend_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /var/lib/ai-docs/data
  
  backend_logs:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /var/log/ai-docs
```

### 备份策略

```bash
# 数据备份
docker run --rm \
  -v ai-docs_backend_data:/source:ro \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/ai-docs-data-$(date +%Y%m%d_%H%M%S).tar.gz -C /source .

# 数据恢复
docker run --rm \
  -v ai-docs_backend_data:/target \
  -v $(pwd)/backup:/backup \
  alpine tar xzf /backup/ai-docs-data-20241201_120000.tar.gz -C /target
```

## 🔍 监控和日志

### 健康检查

所有服务都配置了健康检查：

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### 日志查看

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend

# 查看最近100行日志
docker-compose logs --tail=100 backend
```

### 监控指标

使用Watchtower自动监控和更新：

```bash
# 检查更新状态
docker logs ai-docs-watchtower

# 手动触发更新
docker exec ai-docs-watchtower watchtower --run-once
```

## 🔒 安全配置

### 非Root用户

所有容器都配置为使用非root用户运行：

```dockerfile
# 创建非root用户
RUN useradd -m -u 1001 appuser && chown -R appuser:appuser /app
USER appuser
```

### 网络隔离

```yaml
networks:
  ai-docs-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### 密钥管理

```bash
# 使用Docker Secrets（Swarm模式）
echo "your-secret-key" | docker secret create openai_api_key -

# 在compose文件中引用
secrets:
  - openai_api_key
```

## 🚨 故障排除

### 常见问题

1. **配置文件找不到**
   ```bash
   # 检查挂载路径
   docker exec ai-docs-backend ls -la /app/config/
   ```

2. **数据库连接失败**
   ```bash
   # 检查数据目录权限
   docker exec ai-docs-backend ls -la /app/data/
   ```

3. **Redis连接失败**
   ```bash
   # 检查Redis服务状态
   docker-compose exec redis redis-cli ping
   ```

### 调试命令

```bash
# 进入容器调试
docker exec -it ai-docs-backend bash

# 查看容器资源使用
docker stats

# 查看网络连接
docker network inspect ai-docs_ai-docs-network
```

## 📚 相关文档

- [GitHub Actions自动构建](.github/workflows/docker-build.yml)
- [项目配置说明](CLAUDE.md)
- [API文档](backend/docs/api.md)
- [前端开发指南](frontend/README.md)