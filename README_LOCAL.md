# AIDD 本机构建部署指南

> 完全不依赖GitHub Actions，在本机完成构建、测试和部署

## 🚀 四种本机部署方案

### 方案1：交互式部署 (推荐新手)

```bash
# 交互式选择数据库和部署方式
./db-deploy.sh
```

**特点**：
- ✅ 交互式选择数据库类型（SQLite/MySQL/PostgreSQL）
- ✅ 交互式选择部署方式（快速/完整）
- ✅ 最适合新手使用
- ✅ 自动配置数据库连接

### 方案2：超简单部署

```bash
# SQLite数据库 (默认)
./quick-deploy.sh

# MySQL数据库
DATABASE_TYPE=mysql ./quick-deploy.sh

# PostgreSQL数据库
DATABASE_TYPE=postgresql ./quick-deploy.sh
```

**特点**：
- ✅ 支持多种数据库类型
- ✅ 一条命令搞定
- ✅ 自动构建Docker镜像
- ✅ 自动创建配置文件

### 方案3：完整本机构建 (推荐进阶用户)

```bash
# SQLite数据库 (默认)
./local-build.sh deploy

# MySQL数据库
DATABASE_TYPE=mysql ./local-build.sh deploy

# PostgreSQL数据库  
DATABASE_TYPE=postgresql ./local-build.sh deploy
```

**特点**：
- ✅ 完整的构建流程控制
- ✅ 支持构建测试和验证
- ✅ 详细的日志和状态显示
- ✅ 支持生产环境配置

### 方案3：传统Docker Compose

```bash
# 使用原有的docker-compose
./start.sh
```

**特点**：
- ✅ 兼容原有配置
- ✅ 简单直接
- ✅ 适合熟悉Docker Compose的用户

## 📋 系统要求

- Docker 20.10+
- Docker Compose 2.0+
- 8GB+ 可用内存
- 5GB+ 可用磁盘空间
- curl (用于健康检查)

## 🛠️ 详细使用说明

### 超简单部署 (quick-deploy.sh)

```bash
# 直接运行
./quick-deploy.sh

# 部署完成后的管理
docker compose -f docker-compose.quick.yml logs -f  # 查看日志
docker compose -f docker-compose.quick.yml down     # 停止服务
docker compose -f docker-compose.quick.yml up -d    # 重启服务
```

### 完整本机构建 (local-build.sh)

```bash
# 查看所有选项
./local-build.sh --help

# 基础操作
./local-build.sh build          # 仅构建镜像
./local-build.sh deploy         # 构建并部署
./local-build.sh start          # 启动已构建的服务
./local-build.sh stop           # 停止服务
./local-build.sh restart        # 重启服务
./local-build.sh status         # 查看状态
./local-build.sh logs           # 查看日志
./local-build.sh clean          # 清理所有资源

# 高级选项
./local-build.sh -t deploy      # 构建、部署并测试
./local-build.sh -p deploy      # 生产环境部署
./local-build.sh -c deploy      # 清理后重新部署
./local-build.sh -b build       # 仅构建，不部署
```

### 自定义配置

```bash
# 指定版本和配置
VERSION=v2.0.0 ./local-build.sh deploy
LOCAL_REGISTRY=mycompany ./local-build.sh deploy
ENVIRONMENT=production ./local-build.sh -p deploy
```

## 🔧 配置文件说明

### 快速部署配置 (.env.quick)

```bash
# 自动生成，包含基础配置
PROJECT_NAME=aidd
BACKEND_PORT=8080
FRONTEND_PORT=3000
DATABASE_TYPE=sqlite
# ... 其他配置
```

### 完整部署配置 (.env.local)

```bash
# 完整构建后生成，包含详细配置
PROJECT_NAME=aidd
VERSION=local-20241230-143022
ENVIRONMENT=development
DATABASE_TYPE=sqlite
# 安全配置
JWT_SECRET_KEY=local-dev-key-abc123...
# Docker镜像配置
BACKEND_IMAGE=local/aidd-backend:local-20241230-143022
FRONTEND_IMAGE=local/aidd-frontend:local-20241230-143022
```

## 🎯 构建产物

### 本机构建生成的文件

```
项目根目录/
├── .env.quick              # 快速部署环境文件
├── .env.local              # 完整部署环境文件  
├── docker-compose.quick.yml # 快速部署配置
├── docker-compose.local.yml # 完整部署配置
├── build-logs/             # 构建日志目录
│   ├── backend-build.log   # 后端构建日志
│   └── frontend-build.log  # 前端构建日志
└── build-config.env        # 构建信息
```

### 生成的Docker镜像

```bash
# 查看构建的镜像
docker images | grep aidd

# 示例输出
local/aidd-backend    latest    abc123def456    2 hours ago    280MB
local/aidd-backend    local-20241230-143022    abc123def456    2 hours ago    280MB  
local/aidd-frontend   latest    def456ghi789    2 hours ago    50MB
local/aidd-frontend   local-20241230-143022    def456ghi789    2 hours ago    50MB
```

## 📊 服务状态检查

### 健康检查

```bash
# 后端健康检查
curl http://localhost:8080/health

# 前端访问检查  
curl http://localhost:3000/

# 查看容器状态
docker ps | grep aidd
```

### 日志查看

```bash
# 快速部署日志
docker compose -f docker-compose.quick.yml logs -f

# 完整部署日志
./local-build.sh logs

# 单独查看后端日志
docker logs aidd-backend-quick -f

# 单独查看前端日志
docker logs aidd-frontend-quick -f
```

## 🐛 故障排除

### 常见问题

**1. 端口冲突**
```bash
# 检查端口占用
lsof -i :8080
lsof -i :3000

# 修改端口配置
vi .env.quick  # 或 .env.local
# 修改 BACKEND_PORT 和 FRONTEND_PORT
```

**2. Docker空间不足**
```bash
# 清理Docker缓存
docker system prune -f

# 清理无用镜像
docker image prune -f

# 查看磁盘使用
docker system df
```

**3. 构建失败**
```bash
# 查看构建日志
cat build-logs/backend-build.log
cat build-logs/frontend-build.log

# 清理后重新构建
./local-build.sh -c deploy
```

**4. 服务启动失败**
```bash
# 查看容器状态
docker ps -a | grep aidd

# 查看失败容器日志
docker logs <container-name>

# 重新启动
./local-build.sh restart
```

### 完全重置

```bash
# 停止所有服务
./local-build.sh stop
docker compose -f docker-compose.quick.yml down

# 清理所有资源
./local-build.sh clean
docker compose -f docker-compose.quick.yml down -v

# 删除所有配置文件
rm -f .env.quick .env.local docker-compose.quick.yml docker-compose.local.yml
rm -rf build-logs build-cache

# 重新开始
./quick-deploy.sh
```

## 🔐 生产环境部署

### 生产环境配置

```bash
# 使用生产环境配置
./local-build.sh -p deploy

# 手动配置生产环境变量
ENVIRONMENT=production \
JWT_SECRET_KEY=$(openssl rand -base64 32) \
OPENAI_API_KEY=your-real-api-key \
./local-build.sh deploy
```

### 生产环境建议

1. **安全配置**
   - 修改默认密钥和密码
   - 使用HTTPS和SSL证书
   - 配置防火墙规则

2. **性能优化**
   - 增加内存和CPU资源
   - 使用SSD存储
   - 配置反向代理

3. **监控和备份**
   - 设置日志轮转
   - 定期备份数据
   - 监控服务状态

## 💡 开发建议

### 开发环境使用

```bash
# 开发时重新构建
./local-build.sh -t deploy

# 只构建不部署（用于测试构建）
./local-build.sh -b build

# 查看实时日志
./local-build.sh logs
```

### 多版本管理

```bash
# 构建不同版本
VERSION=v1.0.0 ./local-build.sh build
VERSION=v2.0.0 ./local-build.sh build

# 查看所有版本
docker images | grep aidd
```

## 📞 技术支持

如果遇到问题：

1. 查看[故障排除](#故障排除)章节
2. 检查构建日志 (`build-logs/` 目录)
3. 确认Docker环境正常运行
4. 提供详细的错误信息和环境描述

---

## ⚡ 快速命令参考

```bash
# 最简单的部署
./quick-deploy.sh

# 完整功能部署  
./local-build.sh deploy

# 查看服务状态
./local-build.sh status

# 查看日志
./local-build.sh logs

# 停止服务
./local-build.sh stop

# 完全清理
./local-build.sh clean
```

选择适合您的部署方案，开始使用AIDD吧！ 🚀