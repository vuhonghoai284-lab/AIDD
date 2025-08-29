# 生产环境部署指南

## 问题解决方案

### 原始问题
- **数据库会话错误**: `❌ 数据库会话错误 [fastapi_a333249c]: ⚠️ 检测到未完成事务，强制回滚`
- **401认证错误**: `INFO: 10.174.181.153:53965 - "GET /api/tasks/statistics HTTP/1.1" 401 Unauthorized` 导致用户自动退出登录

### 已实施的修复

#### 1. JWT认证增强 ✅
- 增强JWT密钥配置检查和日志
- 优化token验证流程，添加详细错误诊断
- 移除用户缓存服务潜在冲突，直接查询数据库
- 增强用户对象完整性验证

#### 2. 数据库会话管理优化 ✅ 
- MySQL会话级别优化设置（wait_timeout, interactive_timeout等）
- 增强事务状态检查和清理机制
- 添加连接池健康监控
- 改进会话异常处理和恢复逻辑

#### 3. 生产环境诊断工具 ✅
- 创建 `production_config_check.py` 配置检查脚本
- 创建 `mysql_compatibility_fix.py` MySQL兼容性修复脚本
- 完整的环境变量验证和数据库连接测试

## 必要的环境变量

### 生产环境必须设置:
```bash
# JWT配置（必须）
export JWT_SECRET_KEY="your-secure-32-char-secret-key"

# MySQL配置（必须）
export DATABASE_TYPE="mysql"
export MYSQL_HOST="your-mysql-host"
export MYSQL_PORT="3306"  
export MYSQL_USERNAME="your-mysql-user"
export MYSQL_PASSWORD="your-mysql-password"
export MYSQL_DATABASE="your-database-name"

# 服务器配置（可选）
export EXTERNAL_HOST="your-domain.com"
export EXTERNAL_PORT="443"
export EXTERNAL_PROTOCOL="https"
export FRONTEND_DOMAIN="https://your-frontend-domain.com"
```

## 部署前检查清单

### 1. 运行配置检查
```bash
cd backend
python production_config_check.py
```

### 2. 运行MySQL兼容性修复
```bash
cd backend  
python mysql_compatibility_fix.py
```

### 3. 验证数据库表结构
确保以下表已正确创建：
- `task_queue` - 任务队列表
- `queue_config` - 队列配置表
- 所有外键约束正常

### 4. 测试关键接口
```bash
# 测试认证
curl -H "Authorization: Bearer invalid-token" \
     http://your-domain/api/tasks/statistics

# 应该返回401错误，确认认证正常工作
```

## 性能优化建议

### MySQL配置优化
```sql
-- 建议的MySQL配置
SET GLOBAL innodb_buffer_pool_size = 256M;
SET GLOBAL max_connections = 150;
SET GLOBAL wait_timeout = 28800;
SET GLOBAL interactive_timeout = 28800;
```

### 应用级别监控
- 启用数据库连接池监控: `/api/tasks/db-monitor`
- 监控队列状态: `/api/tasks/queue-status`
- 关注会话清理日志中的 `❌ 数据库会话错误` 消息

## 故障排除

### 如果仍有401错误:
1. 检查JWT_SECRET_KEY是否在所有应用实例中一致
2. 检查负载均衡器是否正确转发Authorization头
3. 检查MySQL连接是否稳定
4. 查看应用日志中的详细认证错误信息

### 如果有数据库会话错误:
1. 检查MySQL连接池配置
2. 监控数据库连接数是否超限
3. 检查MySQL服务器配置
4. 确保应用正确处理数据库重连

## 监控指标

### 关键日志监控:
- `❌ 数据库会话错误` - 数据库会话问题
- `❌ Token验证失败` - 认证问题  
- `⚠️ 用户认证耗时过长` - 性能问题
- `✅ MySQL会话优化完成` - 数据库连接正常

### API监控:
- `/api/tasks/statistics` 响应时间和错误率
- 用户会话持续时间
- 数据库连接池使用率