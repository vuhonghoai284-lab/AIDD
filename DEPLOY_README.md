# AI文档测试系统 - 部署指南

本指南提供了多种部署方式，从GitHub Container Registry获取预构建镜像进行一键部署。

## 🚀 快速开始

### 1. 快速体验部署（推荐新手）

最简单的部署方式，适用于快速体验和演示：

```bash
./quick-deploy.sh
```

特点：
- ✅ 一键启动，无需配置
- ✅ 使用SQLite数据库，无外部依赖
- ✅ 内存缓存，启动快速
- ⚠️ 仅适用于开发和演示环境

### 2. 生产环境部署（推荐生产）

完整的生产级部署，包含PostgreSQL数据库和Redis缓存：

```bash
./deploy-from-github.sh
```

特点：
- ✅ 完整的生产级配置
- ✅ PostgreSQL数据库
- ✅ Redis缓存
- ✅ 可自定义配置
- ✅ 健康检查和监控

## 📋 部署前准备

### 系统要求

- **操作系统**: Linux, macOS, Windows (WSL2)
- **Docker**: 20.10+ 
- **Docker Compose**: 2.0+
- **内存**: 4GB+ 推荐
- **磁盘**: 10GB+ 可用空间
- **网络**: 可访问GitHub Container Registry

### 安装Docker

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 重新登录或运行
newgrp docker

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

## 🛠️ 详细部署说明

### 生产环境部署详细步骤

1. **克隆仓库或下载脚本**
   ```bash
   # 如果从Git仓库
   git clone <repository-url>
   cd ai_docs2
   
   # 或直接下载脚本
   wget https://raw.githubusercontent.com/wantiantian/ai_docs2/main/deploy-from-github.sh
   chmod +x deploy-from-github.sh
   ```

2. **运行部署脚本**
   ```bash
   # 默认配置部署
   ./deploy-from-github.sh
   
   # 自定义端口部署
   ./deploy-from-github.sh --frontend-port 8080 --backend-port 9000
   
   # 指定版本部署
   ./deploy-from-github.sh --version v2.0.0
   ```

3. **配置API密钥**
   
   部署完成后，编辑生成的 `.env` 文件：
   ```bash
   nano .env
   ```
   
   填入以下配置：
   ```env
   # AI服务配置
   OPENAI_API_KEY=sk-your-openai-api-key-here
   BAIDU_API_KEY=your-baidu-api-key-here
   
   # OAuth配置（可选）
   OAUTH_CLIENT_ID=your-oauth-client-id
   OAUTH_CLIENT_SECRET=your-oauth-client-secret
   FRONTEND_DOMAIN=https://your-domain.com
   ```

4. **重启服务使配置生效**
   ```bash
   ./deploy-from-github.sh --restart
   ```

## 📊 部署脚本选项

### deploy-from-github.sh 完整选项

```bash
./deploy-from-github.sh [选项]

选项:
  --version VERSION        指定镜像版本 (默认: latest)
  --registry REGISTRY      指定镜像仓库
  --frontend-port PORT     前端服务端口 (默认: 3000)
  --backend-port PORT      后端服务端口 (默认: 8080)
  --postgres-port PORT     PostgreSQL端口 (默认: 5432)
  --redis-port PORT        Redis端口 (默认: 6379)
  --data-path PATH         数据存储路径 (默认: ./data)
  --log-path PATH          日志存储路径 (默认: ./logs)
  --config-path PATH       配置文件路径 (默认: ./config.yaml)
  --skip-config            跳过配置文件生成，使用现有配置
  --stop                   停止并删除所有服务
  --restart                重启所有服务
  --status                 查看服务状态
  --logs [SERVICE]         查看服务日志
  --update                 更新到最新版本
  -h, --help              显示帮助信息
```

### 常用部署示例

```bash
# 1. 默认部署
./deploy-from-github.sh

# 2. 自定义端口
./deploy-from-github.sh --frontend-port 8080 --backend-port 9000

# 3. 指定版本和自定义数据路径
./deploy-from-github.sh --version v2.0.0 --data-path /opt/aidd/data

# 4. 开发环境部署（跳过配置生成）
./deploy-from-github.sh --skip-config

# 5. 查看服务状态
./deploy-from-github.sh --status

# 6. 查看后端服务日志
./deploy-from-github.sh --logs backend

# 7. 更新服务到最新版本
./deploy-from-github.sh --update

# 8. 停止所有服务
./deploy-from-github.sh --stop
```

## 🔧 服务管理

### 查看服务状态
```bash
./deploy-from-github.sh --status
```

### 查看日志
```bash
# 查看所有服务日志
./deploy-from-github.sh --logs

# 查看特定服务日志
./deploy-from-github.sh --logs backend
./deploy-from-github.sh --logs frontend
```

### 重启服务
```bash
# 重启所有服务
./deploy-from-github.sh --restart

# 或使用Docker Compose
docker-compose restart
```

### 更新服务
```bash
# 更新到最新版本
./deploy-from-github.sh --update
```

### 停止服务
```bash
# 停止并删除服务（保留数据）
./deploy-from-github.sh --stop

# 或使用Docker Compose
docker-compose down
```

## 📂 目录结构

部署完成后的目录结构：

```
ai_docs2/
├── deploy-from-github.sh       # 生产环境部署脚本
├── quick-deploy.sh             # 快速体验部署脚本
├── docker-compose.yml          # 生产环境Docker Compose文件
├── docker-compose.quick.yml    # 快速部署Docker Compose文件
├── .env                        # 环境变量配置
├── config.yaml                 # 应用配置文件
├── data/                       # 数据存储目录
│   ├── postgres/              # PostgreSQL数据
│   ├── redis/                 # Redis数据
│   ├── uploads/               # 用户上传文件
│   └── reports/               # 生成的报告
└── logs/                      # 日志文件
```

## 🌐 访问应用

部署完成后，可通过以下地址访问：

- **前端应用**: http://localhost:3000
- **后端API**: http://localhost:8080
- **API文档**: http://localhost:8080/docs
- **API交互文档**: http://localhost:8080/redoc

## 🔒 安全配置

### 生产环境安全建议

1. **更改默认密码**
   ```bash
   # 编辑 .env 文件，更改数据库密码和JWT密钥
   nano .env
   ```

2. **配置防火墙**
   ```bash
   # 仅开放必要端口
   sudo ufw allow 3000/tcp  # 前端
   sudo ufw allow 8080/tcp  # 后端API
   ```

3. **使用HTTPS**
   
   建议使用Nginx反向代理配置HTTPS：
   ```bash
   # 启用Nginx profile
   docker-compose --profile nginx up -d
   ```

4. **定期备份**
   ```bash
   # 备份数据库
   docker-compose exec postgres pg_dump -U aidd_user aidd_db > backup.sql
   
   # 备份数据目录
   tar -czf data-backup-$(date +%Y%m%d).tar.gz data/
   ```

## 🐛 故障排除

### 常见问题

1. **端口冲突**
   ```bash
   # 检查端口占用
   sudo netstat -tlnp | grep :3000
   
   # 使用不同端口部署
   ./deploy-from-github.sh --frontend-port 8080
   ```

2. **内存不足**
   ```bash
   # 检查系统内存
   free -h
   
   # 调整Docker资源限制
   # 编辑 .env 文件，降低内存限制
   ```

3. **镜像拉取失败**
   ```bash
   # 检查网络连接
   docker pull hello-world
   
   # 手动拉取镜像
   docker pull ghcr.io/wantiantian/ai_docs2/backend:latest
   ```

4. **服务启动失败**
   ```bash
   # 查看详细日志
   ./deploy-from-github.sh --logs
   
   # 检查配置文件
   docker-compose config
   ```

### 日志分析

```bash
# 查看启动日志
docker-compose logs -f backend

# 查看错误日志
docker-compose logs backend | grep ERROR

# 查看最近日志
docker-compose logs --tail=50 backend
```

## 📈 监控和维护

### 健康检查
```bash
# 检查服务健康状态
curl http://localhost:8080/health
curl http://localhost:3000/health
```

### 资源监控
```bash
# 查看容器资源使用
docker stats

# 查看磁盘使用
df -h
du -sh data/ logs/
```

### 定期维护
```bash
# 清理未使用的Docker资源
docker system prune -f

# 清理旧日志
find logs/ -name "*.log" -mtime +30 -delete

# 更新到最新版本
./deploy-from-github.sh --update
```

## 🆘 获取帮助

- 查看脚本帮助: `./deploy-from-github.sh --help`
- 查看服务状态: `./deploy-from-github.sh --status`
- 查看日志: `./deploy-from-github.sh --logs`
- GitHub Issues: [项目Issues页面]
- 文档: [项目文档]

---

## 🎉 快速开始总结

1. **体验部署**（最简单）:
   ```bash
   ./quick-deploy.sh
   ```

2. **生产部署**（推荐）:
   ```bash
   ./deploy-from-github.sh
   # 编辑 .env 文件配置API密钥
   ./deploy-from-github.sh --restart
   ```

3. **访问应用**: http://localhost:3000

就这么简单！🚀