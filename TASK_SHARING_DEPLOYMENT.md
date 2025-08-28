# 任务分享功能生产环境部署指南

## 概述
任务分享功能允许用户将任务分享给其他用户，支持三种权限级别：完全权限、反馈权限、只读权限。

## 🔄 数据库迁移 (必需)

### 迁移内容
此功能需要对数据库进行以下变更：

1. **新增 `task_shares` 表**
   - 存储任务分享关系和权限信息
   - 包含分享者、被分享用户、权限级别等字段

2. **扩展 `issues` 表**
   - 添加反馈操作人相关字段
   - `feedback_user_id` - 反馈操作用户ID
   - `feedback_user_name` - 反馈操作用户名称
   - `feedback_updated_at` - 最后反馈时间

### 执行迁移

⚠️ **重要提醒：执行前请备份数据库**

#### SQLite环境（开发/测试）
```bash
# 1. 进入后端目录
cd backend

# 2. 执行SQLite迁移脚本
python migration_task_sharing.py

# 3. 验证迁移结果
# 脚本会自动验证表结构和索引创建情况
```

#### MySQL环境（生产环境）
```bash
# 1. 配置MySQL连接环境变量
export MYSQL_HOST=your_mysql_host
export MYSQL_PORT=3306
export MYSQL_USERNAME=your_username
export MYSQL_PASSWORD=your_password
export MYSQL_DATABASE=your_database

# 2. 安装MySQL Python驱动
pip install pymysql

# 3. 进入后端目录
cd backend

# 4. 执行MySQL迁移脚本
python migration_task_sharing_mysql.py

# 5. 验证迁移结果
# 脚本会自动验证表结构、索引和外键约束
```

### 迁移脚本功能
- ✅ 自动备份数据库（MySQL支持mysqldump，SQLite支持内置备份）
- ✅ 事务保护（失败时自动回滚）
- ✅ 重复执行安全（检查已存在的表和字段）
- ✅ 创建必要的索引和外键约束（MySQL）
- ✅ 迁移结果验证

## 📋 部署前检查清单

### 1. 环境准备
- [ ] 数据库已备份
- [ ] 应用已停止或处于维护模式
- [ ] 确认Python环境和依赖包完整
- [ ] MySQL环境：确认pymysql已安装
- [ ] MySQL环境：确认数据库用户有DDL权限

### 2. 数据库迁移
**SQLite环境：**
- [ ] 执行 `python migration_task_sharing.py`
- [ ] 验证迁移日志无错误
- [ ] 确认 `task_shares` 表已创建
- [ ] 确认 `issues` 表新字段已添加

**MySQL环境：**
- [ ] 配置正确的环境变量
- [ ] 执行 `python migration_task_sharing_mysql.py`
- [ ] 验证迁移日志无错误
- [ ] 确认 `task_shares` 表已创建（包含索引和外键）
- [ ] 确认 `issues` 表新字段已添加

### 3. 应用配置
- [ ] 更新后端代码到最新版本
- [ ] 更新前端代码到最新版本
- [ ] 检查API路由注册正常

### 4. 功能测试
- [ ] 用户可以正常分享任务
- [ ] 权限控制正确工作
- [ ] 被分享用户能正常访问
- [ ] 分享列表显示正常

## 🔍 验证步骤

### 数据库验证

#### SQLite验证
```sql
-- 检查 task_shares 表
SELECT name FROM sqlite_master WHERE type='table' AND name='task_shares';

-- 检查表结构
PRAGMA table_info(task_shares);

-- 检查 issues 表新字段
PRAGMA table_info(issues);

-- 检查索引
SELECT name FROM sqlite_master WHERE type='index' AND name LIKE '%task_shares%';
```

#### MySQL验证
```sql
-- 检查 task_shares 表
SHOW TABLES LIKE 'task_shares';

-- 检查表结构
DESCRIBE task_shares;

-- 检查 issues 表新字段
DESCRIBE issues;

-- 检查索引
SHOW INDEX FROM task_shares;

-- 检查外键约束
SELECT 
    CONSTRAINT_NAME,
    COLUMN_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
WHERE TABLE_NAME = 'task_shares' 
    AND TABLE_SCHEMA = DATABASE()
    AND REFERENCED_TABLE_NAME IS NOT NULL;
```

### API端点验证
```bash
# 检查分享相关API端点是否可访问
curl -H "Authorization: Bearer <token>" http://your-domain/api/task-share/users/search?q=test

# 检查任务分享API
curl -X POST -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
     -d '{"shared_user_ids":[2],"permission_level":"read_only"}' \
     http://your-domain/api/task-share/1/share
```

## 🛠️ 回滚方案

如果需要回滚到迁移前状态：

1. **数据库回滚**
   ```bash
   # 停止应用
   # 使用备份文件恢复数据库
   cp ./data/app.db.backup_YYYYMMDD_HHMMSS ./data/app.db
   ```

2. **代码回滚**
   ```bash
   # 回滚到上一个稳定版本
   git checkout <previous-stable-commit>
   ```

## 📊 性能影响评估

### 新增表大小估算
- `task_shares` 表预计每月增长：任务数 × 平均分享用户数 × 0.3
- 索引开销：约为表大小的 20-30%

### API性能
- 分享操作：轻量级，影响极小
- 权限检查：已优化，使用索引查询
- 列表查询：支持分页，性能良好

## 🔐 安全考虑

### 权限控制
- ✅ 所有API端点都需要认证
- ✅ 只有任务owner可以分享任务
- ✅ 被分享用户只能执行授权范围内的操作

### 数据保护
- ✅ 使用外键约束保证数据一致性
- ✅ 软删除机制（is_active字段）
- ✅ 级联删除保护

## 🐛 常见问题解决

### 迁移失败
1. 检查数据库文件权限
2. 确认磁盘空间充足
3. 查看详细错误日志

### API 404错误
1. 检查路由注册
2. 重启应用服务
3. 验证URL路径

### 权限问题
1. 检查JWT token有效性
2. 验证用户权限配置
3. 查看权限检查日志

## 📞 技术支持

如遇到问题，请提供以下信息：
- 迁移脚本执行日志
- 应用启动日志
- 具体错误信息
- 数据库版本和大小

---

**最后更新：** 2025-08-28  
**版本：** v1.0.0