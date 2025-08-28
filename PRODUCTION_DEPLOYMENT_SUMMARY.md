# 任务分享功能生产环境部署总结

## ✅ 是的，需要数据库迁移

该功能涉及以下数据库变更：

### 1. 新增表：`task_shares`
```sql
CREATE TABLE task_shares (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,           -- 任务ID
    owner_id INTEGER NOT NULL,          -- 分享者ID  
    shared_user_id INTEGER NOT NULL,    -- 被分享用户ID
    permission_level VARCHAR(20) NOT NULL DEFAULT 'read_only', -- 权限级别
    share_comment TEXT,                 -- 分享备注
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE, 
    FOREIGN KEY (shared_user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### 2. 扩展表：`issues` 
添加反馈操作人字段：
- `feedback_user_id` INTEGER - 反馈操作用户ID
- `feedback_user_name` VARCHAR(100) - 反馈操作用户名称  
- `feedback_updated_at` DATETIME - 最后反馈时间

## 🚀 快速部署方案

### SQLite环境（开发/测试）

**方案一：自动化脚本（推荐）**
```bash
# 在项目根目录执行
./deploy_task_sharing.sh
```

**方案二：手动执行**
```bash
# 1. 数据库迁移
cd backend
python migration_task_sharing.py

# 2. 重启服务
# 根据你的部署方式重启后端和前端服务
```

### MySQL环境（生产环境）

**方案一：自动化脚本（推荐）**
```bash
# 1. 配置环境变量
export MYSQL_HOST=your_mysql_host
export MYSQL_PORT=3306
export MYSQL_USERNAME=your_username
export MYSQL_PASSWORD=your_password
export MYSQL_DATABASE=your_database

# 2. 安装MySQL依赖
pip install pymysql

# 3. 执行部署脚本
./deploy_task_sharing_mysql.sh
```

**方案二：手动执行**
```bash
# 1. 配置环境变量（同上）
# 2. 安装MySQL依赖
pip install pymysql

# 3. 数据库迁移
cd backend
python migration_task_sharing_mysql.py

# 4. 重启服务
# 根据你的部署方式重启后端和前端服务
```

## 📋 部署检查清单

### 执行前
- [ ] 数据库已备份
- [ ] 应用处于维护模式（可选）  
- [ ] 确认磁盘空间充足
- [ ] **MySQL环境**：确认pymysql已安装
- [ ] **MySQL环境**：确认数据库用户有DDL权限
- [ ] **MySQL环境**：确认环境变量配置正确

### 执行后  
- [ ] 迁移脚本执行成功，无错误日志
- [ ] 新表 `task_shares` 已创建
- [ ] `issues` 表新字段已添加
- [ ] **MySQL环境**：外键约束正常工作
- [ ] **MySQL环境**：索引已正确创建
- [ ] 应用服务正常启动
- [ ] 分享功能测试通过

## 🔍 验证方法

### 数据库验证

**SQLite环境：**
```sql
-- 检查新表
SELECT name FROM sqlite_master WHERE type='table' AND name='task_shares';

-- 检查新字段
PRAGMA table_info(issues);
```

**MySQL环境：**
```sql
-- 检查新表
SHOW TABLES LIKE 'task_shares';

-- 检查表结构
DESCRIBE task_shares;

-- 检查新字段
DESCRIBE issues;

-- 检查外键约束
SELECT CONSTRAINT_NAME, REFERENCED_TABLE_NAME 
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
WHERE TABLE_NAME = 'task_shares' 
AND REFERENCED_TABLE_NAME IS NOT NULL;
```

### 功能验证
1. 登录系统
2. 在已完成的任务上点击"分享"按钮
3. 选择用户和权限级别进行分享
4. 被分享用户登录后可在"分享给我的任务"中查看

## 📞 回滚方案

如需回滚：
```bash
# 恢复数据库备份
cp ./data/app.db.backup_YYYYMMDD_HHMMSS ./data/app.db

# 回滚代码版本
git checkout <previous-commit>
```

## ⚠️ 注意事项

1. **迁移脚本是幂等的**，可以安全地重复执行
2. **会自动备份数据库**，备份文件保存在 `./data/app.db.backup_*`
3. **使用事务保护**，失败时自动回滚
4. **对现有功能无影响**，只是新增功能

---
**总结：生产环境部署此功能需要执行数据库迁移，建议使用提供的自动化脚本进行安全部署。**