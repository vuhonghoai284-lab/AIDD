# Docker 部署指南

本文档介绍如何使用Docker部署AI文档测试系统。

## 🚀 快速开始

### 1. 环境准备

确保您的系统已安装：
- Docker (>= 20.0)
- Docker Compose (>= 1.29)

### 2. 克隆项目

```bash
git clone <repository-url>
cd ai_docs2
```

### 3. 配置环境变量

```bash
# 复制环境配置文件
cp .env.example .env

# 编辑配置文件
vim .env
```

**重要配置项：**
```env
# AI模型API密钥 (必填)
OPENAI_API_KEY=your_openai_api_key_here

# 安全密钥 (生产环境必须修改)
SECRET_KEY=your_secret_key_here
JWT_SECRET_KEY=your_jwt_secret_key_here

# OAuth配置 (可选)
GITEE_CLIENT_ID=your_gitee_client_id_here
GITEE_CLIENT_SECRET=your_gitee_client_secret_here
```

### 4. 一键部署

```bash
# 构建并启动所有服务
./deploy.sh up
```

### 5. 访问系统

- 🌐 **前端界面**: http://localhost
- 🔧 **后端API**: http://localhost/api

## 📋 部署脚本使用

### 基本命令

```bash
# 启动服务
./deploy.sh up

# 停止服务
./deploy.sh down

# 重启服务
./deploy.sh restart

# 查看服务状态
./deploy.sh status

# 查看日志
./deploy.sh logs

# 查看特定服务日志
./deploy.sh logs backend
./deploy.sh logs frontend
```

### 高级命令

```bash
# 重新构建镜像
./deploy.sh build

# 更新服务 (拉取代码 + 重新构建 + 重启)
./deploy.sh update

# 备份数据
./deploy.sh backup

# 清理所有数据和镜像
./deploy.sh clean
```

## 🏗️ 架构说明

### 服务组件

| 服务 | 端口 | 描述 |
|------|------|------|
| frontend | 80 | React前端 + Nginx |
| backend | 8000 | FastAPI后端 |
| redis | 6379 | 缓存和队列 |

### 数据持久化

```
./data/              # 数据目录
├── uploads/         # 上传的文档
├── reports/         # 生成的报告
└── app.db          # SQLite数据库
```

### 网络架构

```
Internet → Nginx (Frontend) → Backend → Redis
                  ↓
            Static Files & API Proxy
```

## ⚙️ 配置详解

### 环境变量

| 变量名 | 默认值 | 描述 |
|--------|--------|------|
| `ENVIRONMENT` | production | 运行环境 |
| `EXTERNAL_HOST` | localhost | 外部访问域名 |
| `EXTERNAL_PORT` | 80 | 外部访问端口 |
| `OPENAI_API_KEY` | - | OpenAI API密钥 |
| `SECRET_KEY` | - | 应用密钥 |
| `JWT_SECRET_KEY` | - | JWT签名密钥 |

### Docker Compose 配置

主要配置文件：
- `docker-compose.yml` - 服务编排
- `backend/Dockerfile` - 后端镜像
- `frontend/Dockerfile` - 前端镜像
- `frontend/nginx.conf` - Nginx配置

## 🔧 自定义配置

### 修改端口

编辑 `docker-compose.yml`:

```yaml
frontend:
  ports:
    - "8080:80"  # 将前端端口改为8080
```

### 启用HTTPS

1. 准备SSL证书文件
2. 修改 `frontend/nginx.conf` 添加SSL配置
3. 更新 `docker-compose.yml` 暴露443端口

### 扩展后端实例

```yaml
backend:
  deploy:
    replicas: 3  # 启动3个后端实例
  scale: 3
```

## 📊 监控和维护

### 健康检查

系统内置健康检查：

```bash
# 检查所有服务状态
./deploy.sh status

# 手动检查
curl http://localhost/api/health
```

### 日志管理

```bash
# 查看实时日志
./deploy.sh logs

# 查看最近100行日志
docker-compose logs --tail=100

# 按时间筛选日志
docker-compose logs --since="2024-01-01T00:00:00Z"
```

### 性能监控

```bash
# 查看容器资源使用
docker stats

# 查看磁盘使用
df -h ./data
```

## 🛠️ 故障排除

### 常见问题

**1. 服务启动失败**
```bash
# 查看详细日志
docker-compose logs backend

# 检查配置文件
./deploy.sh status
```

**2. 无法连接数据库**
```bash
# 重启服务
./deploy.sh restart

# 检查数据目录权限
ls -la ./data
```

**3. AI模型调用失败**
```bash
# 检查API密钥配置
cat .env | grep OPENAI_API_KEY

# 测试API连接
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models
```

### 重置系统

完全重置系统（谨慎操作）：

```bash
# 停止所有服务
./deploy.sh down

# 删除数据
rm -rf ./data/*

# 重新启动
./deploy.sh up
```

## 🔄 更新部署

### 代码更新

```bash
# 自动更新（推荐）
./deploy.sh update

# 手动更新
git pull
./deploy.sh build
./deploy.sh restart
```

### 数据备份

```bash
# 创建备份
./deploy.sh backup

# 备份位置
ls -la backup/
```

## 📝 生产环境部署建议

1. **安全性**
   - 修改所有默认密钥
   - 启用HTTPS
   - 配置防火墙

2. **性能**
   - 使用Redis集群
   - 配置负载均衡
   - 优化数据库连接池

3. **监控**
   - 配置日志收集
   - 设置服务监控
   - 配置告警通知

4. **备份**
   - 定期数据备份
   - 配置自动备份任务
   - 验证备份恢复

## 🆘 技术支持

如遇到部署问题，请：

1. 查看部署日志：`./deploy.sh logs`
2. 检查系统状态：`./deploy.sh status`
3. 参考故障排除文档
4. 提交Issue到项目仓库