# PostgreSQL 部署指南

本文档说明如何将项目从SQLite/MySQL切换到PostgreSQL数据库。

## 🎯 改动总结

全新部署PostgreSQL **改动量极小**，仅需要修改配置文件，无需改动任何业务代码！

### ✅ 已完成的改动
- [x] 添加PostgreSQL驱动依赖
- [x] 更新数据库连接配置
- [x] 更新Docker Compose配置
- [x] 创建PostgreSQL配置文件模板

### ❌ 无需改动的文件
- 所有数据模型文件（`app/models/*.py`）
- 所有业务逻辑代码
- 所有API接口代码  
- 前端代码

## 🚀 快速部署

### 1. 配置环境变量

```bash
# 复制环境变量模板
cp .env.postgresql.example .env

# 编辑 .env 文件，填入实际的数据库密码和API密钥
nano .env
```

### 2. 启动PostgreSQL服务

```bash
# 启动数据库和相关服务
docker-compose up -d postgres redis

# 等待数据库启动完成
docker-compose logs -f postgres
```

### 3. 使用PostgreSQL配置启动后端

```bash
# 使用PostgreSQL配置文件
CONFIG_FILE=config.postgresql.yaml docker-compose up -d backend

# 或者直接启动所有服务
docker-compose up -d
```

## 📋 配置文件说明

### 环境变量配置 (.env)
```bash
# PostgreSQL配置
POSTGRES_HOST=postgres          # Docker环境使用服务名
POSTGRES_PORT=5432
POSTGRES_USER=ai_docs
POSTGRES_PASSWORD=your_password  # 请修改为安全密码
POSTGRES_DB=ai_docs_db

# 其他配置保持不变...
```

### 应用配置 (config.postgresql.yaml)
```yaml
# 数据库配置
database:
  type: postgresql
  postgresql:
    host: ${POSTGRES_HOST:localhost}
    port: ${POSTGRES_PORT:5432}
    username: ${POSTGRES_USER:ai_docs}
    password: ${POSTGRES_PASSWORD:your_secure_password}
    database: ${POSTGRES_DB:ai_docs_db}
```

## 🔍 验证部署

### 1. 检查服务状态
```bash
# 查看所有服务状态
docker-compose ps

# 检查PostgreSQL连接
docker-compose exec postgres pg_isready -U ai_docs -d ai_docs_db
```

### 2. 检查数据库表创建
```bash
# 进入PostgreSQL容器
docker-compose exec postgres psql -U ai_docs -d ai_docs_db

# 查看表结构
\dt
\d users
\d tasks
\q
```

### 3. 测试API接口
```bash
# 健康检查
curl http://localhost:8000/health

# 检查数据库连接
curl http://localhost:8000/api/system/status
```

## 🛠️ 开发环境设置

### 本地开发（不使用Docker）

1. **安装PostgreSQL**
```bash
# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib

# macOS
brew install postgresql

# Windows - 下载官方安装包
```

2. **创建数据库**
```sql
-- 登录PostgreSQL
sudo -u postgres psql

-- 创建用户和数据库
CREATE USER ai_docs WITH PASSWORD 'your_password';
CREATE DATABASE ai_docs_db OWNER ai_docs;
GRANT ALL PRIVILEGES ON DATABASE ai_docs_db TO ai_docs;
\q
```

3. **安装Python依赖**
```bash
cd backend
pip install -r requirements.txt
```

4. **启动应用**
```bash
CONFIG_FILE=config.postgresql.yaml python app/main.py
```

## 📊 性能优化

### PostgreSQL配置调优

创建 `postgresql.conf` 自定义配置：
```ini
# 内存配置
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB

# 连接配置  
max_connections = 100

# 日志配置
log_statement = 'all'
log_min_duration_statement = 1000
```

挂载到Docker容器：
```yaml
postgres:
  volumes:
    - ./postgresql.conf:/etc/postgresql/postgresql.conf:ro
  command: postgres -c config_file=/etc/postgresql/postgresql.conf
```

### 索引优化

项目已经包含了基础索引配置，PostgreSQL会自动处理：
- 主键索引
- 外键索引  
- 复合索引（任务查询优化）
- 时间戳索引（排序优化）

## 🔧 故障排除

### 常见问题

1. **连接拒绝错误**
```bash
# 检查PostgreSQL是否启动
docker-compose logs postgres

# 检查端口是否开放
docker-compose port postgres 5432
```

2. **权限错误**
```bash
# 检查数据库用户权限
docker-compose exec postgres psql -U ai_docs -d ai_docs_db -c "\du"
```

3. **数据表不存在**
```bash
# SQLAlchemy会自动创建表，检查应用日志
docker-compose logs backend
```

### 数据库管理工具

推荐使用以下工具管理PostgreSQL：
- **pgAdmin** - Web界面管理工具
- **DBeaver** - 跨平台数据库客户端
- **TablePlus** - macOS/Windows客户端
- **psql** - 命令行客户端

## 🔄 回滚到SQLite/MySQL

如需回滚，只需：
1. 停止PostgreSQL服务：`docker-compose stop postgres`
2. 修改环境变量中的数据库配置
3. 重启后端服务：`docker-compose restart backend`

## 📚 进阶功能

部署成功后，可以利用PostgreSQL的高级特性：

### 1. 全文搜索
```python
# 在模型中添加全文搜索索引
class Document(Base):
    content = Column(Text)
    search_vector = Column(TSVectorType('content'))
```

### 2. JSON字段优化
```python
# AI分析结果可以使用JSONB存储
class AIOutput(Base):
    analysis_result = Column(JSON)  # 自动映射为JSONB
```

### 3. 数组字段
```python
# 存储标签数组
class Task(Base):
    tags = Column(ARRAY(String))
```

这些高级特性可以在后续开发中逐步引入，无需现在实施。