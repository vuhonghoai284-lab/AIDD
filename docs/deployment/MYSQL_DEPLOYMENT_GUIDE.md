# 任务分享功能MySQL生产环境部署指南

## 📋 概述

针对MySQL生产环境，已专门创建了适配的数据库迁移脚本和部署工具。

## 🔧 MySQL环境专用文件

### 1. MySQL迁移脚本
- **文件**: `backend/migration_task_sharing_mysql.py`
- **功能**: 专为MySQL设计的数据库迁移脚本
- **特性**: 
  - 支持MySQL特有的数据类型和语法
  - 创建外键约束和索引
  - 使用mysqldump进行备份
  - 完整的事务保护

### 2. MySQL部署脚本
- **文件**: `deploy_task_sharing_mysql.sh`
- **功能**: 一键部署脚本，包含环境检查
- **特性**:
  - 自动检查pymysql依赖
  - 验证数据库连接配置
  - 完整的部署流程

## 🚀 快速部署（推荐）

### 步骤1：配置环境变量
```bash
export MYSQL_HOST=your_mysql_host
export MYSQL_PORT=3306
export MYSQL_USERNAME=your_username  
export MYSQL_PASSWORD=your_password
export MYSQL_DATABASE=your_database
```

### 步骤2：安装依赖
```bash
pip install pymysql
```

### 步骤3：执行部署
```bash
# 在项目根目录执行
./deploy_task_sharing_mysql.sh
```

## 🔍 手动部署

### 1. 环境准备
```bash
# 检查MySQL连接
mysql -h $MYSQL_HOST -P $MYSQL_PORT -u $MYSQL_USERNAME -p$MYSQL_PASSWORD $MYSQL_DATABASE -e "SELECT VERSION();"

# 安装Python依赖
pip install pymysql
```

### 2. 执行数据库迁移
```bash
cd backend
python migration_task_sharing_mysql.py
```

### 3. 验证迁移结果
```sql
-- 连接到MySQL数据库
mysql -h your_host -u your_user -p your_database

-- 检查新表
SHOW TABLES LIKE 'task_shares';

-- 检查表结构
DESCRIBE task_shares;

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

-- 检查索引
SHOW INDEX FROM task_shares;
```

## 📊 MySQL专用表结构

### task_shares 表
```sql
CREATE TABLE task_shares (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id INT NOT NULL,
    owner_id INT NOT NULL,
    shared_user_id INT NOT NULL,
    permission_level VARCHAR(20) NOT NULL DEFAULT 'read_only',
    share_comment TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- 索引
    INDEX idx_task_shares_task_id (task_id),
    INDEX idx_task_shares_owner_id (owner_id),
    INDEX idx_task_shares_shared_user_id (shared_user_id),
    INDEX idx_task_shares_is_active (is_active),
    UNIQUE INDEX idx_task_shares_unique (task_id, shared_user_id),
    
    -- 外键约束
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (shared_user_id) REFERENCES users(id) ON DELETE CASCADE
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='任务分享表';
```

### issues 表新增字段
```sql
ALTER TABLE issues ADD COLUMN feedback_user_id INT COMMENT "反馈操作用户ID";
ALTER TABLE issues ADD COLUMN feedback_user_name VARCHAR(100) COMMENT "反馈操作用户名称";
ALTER TABLE issues ADD COLUMN feedback_updated_at DATETIME COMMENT "最后反馈时间";
CREATE INDEX idx_issues_feedback_user ON issues(feedback_user_id);
```

## ⚠️ MySQL特别注意事项

### 1. 权限要求
- 数据库用户需要以下权限：
  - `CREATE` - 创建表
  - `ALTER` - 修改表结构
  - `INDEX` - 创建索引
  - `REFERENCES` - 创建外键

### 2. 字符集要求
- 推荐使用 `utf8mb4` 字符集
- 排序规则推荐 `utf8mb4_unicode_ci`

### 3. 存储引擎
- 使用 `InnoDB` 存储引擎以支持外键约束
- 确保相关表（tasks, users）也使用InnoDB

### 4. 性能考虑
- 所有外键字段都已创建索引
- 唯一约束防止重复分享
- 软删除使用 `is_active` 字段

## 🔄 回滚方案

### 1. 使用备份文件恢复
```bash
# 迁移脚本会自动创建备份文件
mysql -h $MYSQL_HOST -u $MYSQL_USERNAME -p$MYSQL_PASSWORD $MYSQL_DATABASE < backup_database_YYYYMMDD_HHMMSS.sql
```

### 2. 手动清理（仅在必要时）
```sql
-- 删除新增的字段（谨慎操作）
ALTER TABLE issues DROP COLUMN feedback_user_id;
ALTER TABLE issues DROP COLUMN feedback_user_name;
ALTER TABLE issues DROP COLUMN feedback_updated_at;

-- 删除新表（谨慎操作）
DROP TABLE task_shares;
```

## 🐛 常见问题解决

### 1. 外键约束错误
- 确保被引用的表（tasks, users）存在
- 检查被引用字段的数据类型是否匹配

### 2. 字符集问题
- 确保数据库和表使用utf8mb4字符集
- 检查连接字符集配置

### 3. 权限不足
```sql
-- 检查用户权限
SHOW GRANTS FOR 'your_username'@'your_host';

-- 授予必要权限（需要管理员执行）
GRANT CREATE, ALTER, INDEX, REFERENCES ON your_database.* TO 'your_username'@'your_host';
```

## 📞 技术支持

如遇到MySQL特有的问题，请提供：
1. MySQL版本信息
2. 用户权限信息
3. 错误日志详情
4. 表结构信息

---
**MySQL部署指南** | 版本: v1.0.0 | 更新时间: 2025-08-28