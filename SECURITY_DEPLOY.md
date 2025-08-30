# 安全部署指南

## 🚨 部署前必须解决的安全问题

### 1. **数据库迁移问题已修复**
- ✅ 移除了Alembic依赖，使用安全的SQLAlchemy表创建机制
- ✅ 实现了增量表创建，保护现有数据
- ✅ 添加了数据库完整性验证

### 2. **管理员密码安全性已优化**
- ✅ 支持通过环境变量配置管理员账号
- ⚠️ **生产环境必须设置强密码**

### 3. **数据库连接池已优化**
- ✅ SQLite连接池从StaticPool改为QueuePool
- ✅ 增加了连接超时和重试机制
- ✅ 支持PostgreSQL生产级配置

## 📋 部署检查清单

### 🔐 **安全配置（必须完成）**

1. **创建.env文件**:
```bash
cp backend/.env.example backend/.env
```

2. **设置强密码**:
```env
# 生成强JWT密钥
JWT_SECRET_KEY=$(openssl rand -hex 32)

# 设置强管理员密码
ADMIN_USERNAME=your_admin_username
ADMIN_PASSWORD=your_very_strong_password_here
```

3. **配置数据库**（推荐PostgreSQL）:
```env
DATABASE_TYPE=postgresql
POSTGRES_HOST=your_db_host
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_secure_db_password
POSTGRES_DB=ai_docs_production
```

4. **设置AI API密钥**:
```env
OPENAI_API_KEY=sk-your-actual-openai-api-key
```

### 🚀 **生产环境配置**

1. **Redis缓存**（推荐）:
```env
CACHE_STRATEGY=redis
REDIS_HOST=your_redis_host
REDIS_PASSWORD=your_redis_password
```

2. **外部访问配置**:
```env
EXTERNAL_HOST=your-domain.com
EXTERNAL_PORT=443
EXTERNAL_PROTOCOL=https
FRONTEND_DOMAIN=https://your-frontend-domain.com
```

3. **CORS安全配置**:
```env
FRONTEND_PRODUCTION_URL=https://your-frontend-domain.com
CORS_DEVELOPMENT_MODE=false
```

## 🛠️ **部署步骤**

### 开发环境快速启动
```bash
# 1. 安装依赖
cd backend
pip install -r requirements.txt

cd ../frontend
npm install

# 2. 使用默认配置启动（SQLite + 内存缓存）
cd ../backend
python app/main.py
```

### 生产环境部署
```bash
# 1. 配置环境变量
cp backend/.env.example backend/.env
# 编辑.env文件，填入生产配置

# 2. 数据库初始化
cd backend
python -c "from app.core.database_utils import create_tables_sync; create_tables_sync()"

# 3. 验证配置
python -c "from app.core.database_utils import get_db_status; import json; print(json.dumps(get_db_status(), indent=2))"

# 4. 启动应用
python app/main.py
```

## 🔍 **验证部署**

### 数据库验证
```bash
# 检查数据库表
cd backend
python app/core/database_utils.py status

# 验证完整性
python app/core/database_utils.py verify
```

### API验证
```bash
# 健康检查
curl http://localhost:8080/health

# 管理员登录测试
curl -X POST http://localhost:8080/api/auth/system/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your_admin&password=your_password"
```

## ⚡ **性能优化建议**

### 数据库优化
1. **使用PostgreSQL**替代SQLite（生产环境）
2. **配置连接池**：
   - pool_size: 25-50
   - max_overflow: 50-100
3. **创建索引**：
   ```sql
   CREATE INDEX idx_tasks_user_id ON tasks(user_id);
   CREATE INDEX idx_tasks_status ON tasks(status);
   CREATE INDEX idx_tasks_created_at ON tasks(created_at);
   ```

### 缓存优化
1. **使用Redis**替代内存缓存
2. **配置TTL**：合理设置缓存过期时间
3. **监控内存**：定期清理大型缓存条目

### 并发优化
1. **连接池监控**：监控数据库连接使用情况
2. **任务队列**：使用数据库队列管理并发任务
3. **限流控制**：启用API速率限制

## 🚨 **安全注意事项**

### 文件安全
- 限制上传文件类型和大小
- 验证文件路径，防止路径遍历攻击
- 定期清理临时文件

### 网络安全
- 使用HTTPS（生产环境必须）
- 配置防火墙，只开放必要端口
- 启用CORS白名单

### 数据保护
- 定期备份数据库
- 加密敏感信息
- 启用审计日志

## 📊 **监控和维护**

### 数据库维护
```bash
# 定期清理大型AI输出记录
python -c "from app.core.database_utils import *; cleanup_large_ai_outputs(db, days_old=30)"

# 数据库状态监控
python -c "from app.core.database_utils import get_db_status; print(get_db_status())"
```

### 系统监控
- CPU和内存使用率
- 数据库连接数
- API响应时间
- 文件存储空间

## 🆘 **故障排除**

### 常见问题
1. **数据库连接失败**：检查数据库服务和连接配置
2. **AI API调用失败**：验证API密钥和网络连接
3. **文件上传失败**：检查磁盘空间和权限
4. **并发任务阻塞**：检查数据库连接池和队列状态

### 日志查看
```bash
# 应用日志
tail -f data/logs/app.log

# 数据库查询日志（如果启用）
# 设置 ENABLE_DB_QUERY_LOGGING=true
```

## 📈 **扩展建议**

### 水平扩展
- 使用负载均衡器
- 数据库读写分离
- Redis集群

### 高可用性
- 多实例部署
- 数据库主从复制
- 自动故障转移

---

**重要提醒**：生产环境部署前，请务必完成所有安全配置检查，特别是管理员密码、JWT密钥和数据库配置。