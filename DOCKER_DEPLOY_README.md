# AI文档测试系统 - Docker部署指南

## 概述

本指南提供了AI文档测试系统的本地Docker构建和部署方法。用户只需要配置一个YAML文件，即可一键构建和部署整个系统。

## 特性

- 🚀 **一键部署**: 单个命令完成构建和部署
- 🗄️ **多数据库支持**: SQLite、MySQL、PostgreSQL
- 🔧 **配置简单**: 只需配置一个YAML文件
- 🐳 **容器化**: 完全基于Docker，环境隔离
- 🔄 **健康检查**: 自动监控服务状态
- 📝 **详细日志**: 完整的部署和运行日志

## 系统要求

- Docker >= 20.10
- Docker Compose >= 2.0
- 至少 4GB 可用内存
- 至少 10GB 可用磁盘空间

## 快速开始

### 1. 准备配置文件

复制并编辑配置文件：

```bash
# 使用默认配置模板
cp deploy-config.yaml my-config.yaml

# 编辑配置文件
nano my-config.yaml
```

### 2. 配置关键信息

编辑 `my-config.yaml` 文件，重点配置以下信息：

#### 必需配置项

```yaml
# 数据库配置 - 选择一种数据库类型
database:
  type: "postgresql"  # 或 "mysql" 或 "sqlite"
  
  # 如果选择PostgreSQL，修改密码
  postgresql:
    password: "your_secure_password_here"  # 请修改
    
# AI服务配置 - 至少配置一个
ai_services:
  openai:
    api_key: "sk-your-openai-key"  # 请填写真实的OpenAI API密钥
    
# OAuth配置 - 用于用户登录
oauth:
  client_id: "your-gitee-client-id"          # Gitee应用ID
  client_secret: "your-gitee-client-secret"  # Gitee应用密钥
  
# 安全配置
security:
  jwt_secret: "your-random-jwt-secret-key"  # 请生成安全的随机字符串
```

#### 可选配置项

```yaml
# 端口配置
ports:
  frontend: 3000  # 前端访问端口
  backend: 8080   # 后端API端口

# 外部访问配置
external:
  protocol: "http"      # 或 "https"
  host: "localhost"     # 或你的域名
  
# 任务处理配置
task_processing:
  max_concurrent_tasks: 10  # 最大并发任务数
  timeout: 1800            # 任务超时时间（秒）
```

### 3. 一键部署

```bash
# 使用默认配置部署
./docker-deploy.sh

# 使用自定义配置部署
./docker-deploy.sh -c my-config.yaml

# 强制重新构建部署
./docker-deploy.sh --force
```

### 4. 访问系统

部署成功后，可以通过以下地址访问：

- **前端界面**: http://localhost:3000
- **后端API**: http://localhost:8080
- **API文档**: http://localhost:8080/docs

## 详细配置说明

### 数据库配置

#### SQLite (默认，最简单)

```yaml
database:
  type: "sqlite"
  sqlite:
    path: "./data/app.db"
```

- **优点**: 无需额外配置，开箱即用
- **适用场景**: 开发环境、小规模使用
- **注意**: 数据存储在容器的持久卷中

#### PostgreSQL (推荐生产环境)

```yaml
database:
  type: "postgresql"
  postgresql:
    host: "postgres"
    port: 5432
    database: "aidd_db"
    username: "aidd"
    password: "your_secure_password"  # 请修改
```

- **优点**: 性能好，功能完整，适合生产环境
- **适用场景**: 生产环境、大规模使用
- **注意**: 需要设置安全的密码

#### MySQL

```yaml
database:
  type: "mysql"
  mysql:
    host: "mysql"
    port: 3306
    database: "aidd_db"
    username: "aidd"
    password: "your_mysql_password"      # 请修改
    root_password: "your_root_password"  # 请修改
```

- **优点**: 广泛使用，兼容性好
- **适用场景**: 已有MySQL基础设施的环境
- **注意**: 需要设置两个密码（用户密码和root密码）

### AI服务配置

系统支持多个AI服务提供商：

```yaml
ai_services:
  openai:
    api_key: "sk-your-openai-key"
    base_url: "https://api.openai.com/v1"
  baidu:
    api_key: "your-baidu-key"
  deepseek:
    api_key: "your-deepseek-key"
```

**注意**: 至少需要配置一个AI服务提供商，否则文档分析功能将无法使用。

### OAuth配置

目前支持Gitee作为OAuth提供商：

1. **注册Gitee应用**:
   - 访问 https://gitee.com/oauth/applications
   - 创建新应用
   - 设置回调URL: `http://your-domain:3000/third-login/callback`

2. **配置OAuth信息**:
   ```yaml
   oauth:
     provider: "gitee"
     client_id: "your-gitee-client-id"
     client_secret: "your-gitee-client-secret"
     scope: "user_info"
   ```

### 网络和端口配置

```yaml
# 服务端口配置
ports:
  frontend: 3000  # 前端服务端口
  backend: 8080   # 后端服务端口

# 外部访问配置
external:
  protocol: "http"        # 协议类型
  host: "localhost"       # 外部访问域名
  backend_port: 8080      # 后端外部端口
  frontend_port: 3000     # 前端外部端口
```

**注意**: 
- 如果使用域名部署，需要修改 `external.host`
- 如果使用HTTPS，需要修改 `external.protocol` 并配置SSL证书

## 管理命令

### 基本操作

```bash
# 部署服务
./docker-deploy.sh

# 查看服务状态
./docker-deploy.sh --status

# 查看日志
./docker-deploy.sh --logs

# 停止服务
./docker-deploy.sh --down
```

### 高级操作

```bash
# 强制重新构建
./docker-deploy.sh --force

# 使用自定义配置
./docker-deploy.sh -c custom-config.yaml

# 查看帮助
./docker-deploy.sh --help
```

### Docker Compose命令

部署后，也可以直接使用Docker Compose命令：

```bash
# 查看服务状态
docker compose -f docker-compose.yml ps

# 查看日志
docker compose -f docker-compose.yml logs -f

# 重启特定服务
docker compose -f docker-compose.yml restart backend

# 进入容器
docker compose -f docker-compose.yml exec backend bash

# 更新服务
docker compose -f docker-compose.yml up -d --force-recreate
```

## 故障排除

### 常见问题

#### 1. 端口已被占用

```bash
# 检查端口占用
lsof -i :3000
lsof -i :8080

# 修改配置文件中的端口号
# 或停止占用端口的服务
```

#### 2. 数据库连接失败

```bash
# 查看数据库服务日志
docker compose logs postgres  # 或 mysql

# 检查密码配置是否正确
# 检查数据库服务是否启动成功
```

#### 3. AI服务配置错误

```bash
# 检查AI API密钥是否正确
# 查看后端日志确认错误信息
docker compose logs backend
```

#### 4. OAuth登录失败

```bash
# 检查OAuth配置是否正确
# 确认回调URL设置正确
# 查看前端日志
docker compose logs frontend
```

### 调试方法

#### 1. 查看详细日志

```bash
# 查看所有服务日志
docker compose logs -f

# 查看特定服务日志
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f postgres
```

#### 2. 进入容器调试

```bash
# 进入后端容器
docker compose exec backend bash

# 进入数据库容器
docker compose exec postgres psql -U aidd -d aidd_db

# 查看文件系统
docker compose exec backend ls -la /app/data/
```

#### 3. 健康检查

```bash
# 检查服务健康状态
docker compose ps

# 手动测试API
curl http://localhost:8080/health
curl http://localhost:8080/api/system/info
```

## 数据管理

### 数据持久化

所有数据都存储在Docker卷中：

- `backend_data`: 后端数据（上传文件、报告等）
- `backend_logs`: 后端日志
- `redis_data`: Redis缓存数据
- `postgres_data`: PostgreSQL数据（如果使用）
- `mysql_data`: MySQL数据（如果使用）

### 备份和恢复

#### 备份数据

```bash
# 备份所有数据卷
docker run --rm -v aidd_backend_data:/data -v $(pwd):/backup ubuntu tar czf /backup/backend-data-backup.tar.gz /data

# 备份数据库
docker compose exec postgres pg_dump -U aidd aidd_db > backup.sql
```

#### 恢复数据

```bash
# 恢复数据卷
docker run --rm -v aidd_backend_data:/data -v $(pwd):/backup ubuntu tar xzf /backup/backend-data-backup.tar.gz -C /

# 恢复数据库
docker compose exec -T postgres psql -U aidd aidd_db < backup.sql
```

### 清理数据

```bash
# 停止服务并删除所有数据
./docker-deploy.sh --down
docker volume prune

# 删除所有相关镜像
docker rmi $(docker images | grep aidd | awk '{print $3}')
```

## 生产环境部署建议

### 安全配置

1. **修改默认密码**: 确保修改所有默认密码
2. **使用HTTPS**: 配置SSL证书，启用HTTPS
3. **防火墙配置**: 只开放必要的端口
4. **定期更新**: 定期更新Docker镜像和依赖

### 性能优化

1. **资源限制**: 为容器设置合适的CPU和内存限制
2. **数据库优化**: 根据负载调整数据库配置
3. **缓存配置**: 启用Redis缓存，提高性能
4. **负载均衡**: 如需要，可配置负载均衡器

### 监控和日志

1. **日志管理**: 配置日志轮转和集中化日志收集
2. **监控系统**: 设置系统监控和告警
3. **健康检查**: 定期检查服务健康状态
4. **备份策略**: 制定定期备份策略

## 版本更新

### 更新步骤

1. **备份数据** (重要!)
2. **拉取最新代码**
3. **更新配置文件** (如有变更)
4. **重新部署**

```bash
# 备份当前数据
./docker-deploy.sh --down
# 执行备份命令（参见数据管理部分）

# 拉取最新版本
git pull origin main

# 强制重新构建部署
./docker-deploy.sh --force
```

## 支持

如果遇到问题：

1. 查看本文档的故障排除部分
2. 检查项目的 Issue 页面
3. 查看项目的技术文档
4. 联系技术支持团队

## 更新日志

### v2.0.0
- 初始Docker部署版本
- 支持多数据库配置
- 完整的一键部署流程
- 详细的配置文档和故障排除指南