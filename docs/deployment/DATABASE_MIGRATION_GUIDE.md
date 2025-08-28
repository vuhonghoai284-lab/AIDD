# 数据库迁移系统使用指南

## 🎯 概述

我们已经为AI文档测试系统实现了一个完整的数据库版本管理和迁移系统，支持：

- ✅ **SQLite和MySQL双支持**
- ✅ **自动备份和恢复**
- ✅ **迁移脚本生成和执行**
- ✅ **回滚功能**
- ✅ **多环境配置**
- ✅ **命令行工具**

## 🚀 快速开始

### 1. 查看当前状态
```bash
python migrate.py status
```

### 2. 执行现有迁移
```bash
python migrate.py up
```

## 📁 文件结构

```
backend/
├── migrate.py                    # 命令行工具
├── migrations/
│   ├── migration_manager.py      # 核心管理器
│   ├── versions/                 # 迁移文件
│   ├── backups/                  # 自动备份
│   └── README.md                 # 详细文档
├── deploy_with_migration.sh      # 部署脚本
└── test_migration.py             # 测试脚本
```

## 🛠️ 常用命令

### 开发阶段

```bash
# 1. 修改数据模型后，自动生成迁移
python migrate.py auto "添加用户表"

# 2. 手动创建迁移
python migrate.py create "添加索引"

# 3. 执行迁移
python migrate.py up
```

### 生产部署

```bash
# 1. 使用安全部署脚本
./deploy_with_migration.sh production

# 2. 或手动步骤
python migrate.py backup production_backup
python migrate.py up
python migrate.py status
```

### 紧急回滚

```bash
# 1. 恢复备份
python migrate.py restore path/to/backup.db

# 2. 或回滚单个迁移
python migrate.py down <migration_id>
```

## ⚙️ 环境配置

### 开发环境（默认）
```bash
python migrate.py status
```

### 测试环境
```bash
CONFIG_FILE=config.test.yaml python migrate.py status
```

### 生产环境
```bash
CONFIG_FILE=config.production.yaml python migrate.py status
```

## 📝 创建迁移示例

### 自动创建（推荐）
```bash
# 修改app/models/目录下的模型文件后运行：
python migrate.py auto "添加新功能相关表"
```

### 手动创建
```bash
python migrate.py create "添加用户表"
# 然后按提示输入SQL
```

### 迁移文件示例
```python
# migrations/versions/20240101_120000_add_user_table.py

SQL_UP = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_users_username ON users(username);
"""

SQL_DOWN = """
DROP INDEX idx_users_username;
DROP TABLE users;
"""
```

## 🔒 安全最佳实践

### 生产环境部署清单
- [ ] 在维护窗口期进行
- [ ] 提前通知相关人员
- [ ] 创建完整备份
- [ ] 在测试环境验证
- [ ] 准备回滚计划
- [ ] 部署后功能验证

### 备份策略
```bash
# 定期备份（建议加入crontab）
0 2 * * * cd /path/to/project/backend && python migrate.py backup daily_backup_$(date +\%Y\%m\%d)

# 重要操作前手动备份
python migrate.py backup before_major_change
```

## 🚨 故障处理

### 迁移失败
1. 检查错误日志：`migrations/migration.log`
2. 恢复备份：`python migrate.py restore <backup_file>`
3. 修复问题后重新执行

### 数据不一致
1. 比较备份和当前数据
2. 必要时手动修复数据
3. 重新运行迁移

### 权限问题
1. 检查数据库用户权限
2. 确保文件写入权限
3. 验证配置文件路径

## 📊 监控和日志

### 日志文件
- `migrations/migration.log` - 迁移操作日志
- 应用日志中包含数据库连接信息

### 状态检查
```bash
# 检查迁移状态
python migrate.py status

# 查看迁移历史
python migrate.py history
```

## 🧪 测试

### 运行完整测试
```bash
python test_migration.py
```

### 验证特定功能
```bash
# 测试备份恢复
python migrate.py backup test_backup
python migrate.py restore migrations/backups/test_backup.db
```

## 🔧 高级用法

### 批量操作
```bash
# 跳过特定迁移到目标版本
python migrate.py up --target 20240201_120000_target_migration

# 批量备份清理（保留最新10个）
find migrations/backups -name "*.db" | head -n -10 | xargs rm -f
```

### 多数据库支持
```bash
# SQLite -> MySQL 迁移
MYSQL_HOST=localhost MYSQL_PASSWORD=secret python migrate.py up

# 使用不同配置文件
CONFIG_FILE=config.blue.yaml python migrate.py status
```

## 🤝 团队协作

### 开发流程
1. **功能开发**: 修改模型 -> 生成迁移 -> 测试
2. **代码审查**: 包含迁移文件检查
3. **部署**: 使用标准化脚本
4. **监控**: 检查迁移执行结果

### 分支管理
- 每个功能分支包含对应的迁移文件
- 合并前确保迁移顺序正确
- 解决迁移冲突时重新生成ID

## 📞 支持和维护

### 定期维护
- 清理旧备份文件
- 检查日志文件大小
- 验证迁移历史完整性

### 升级系统
- 备份当前迁移系统
- 更新迁移管理器代码
- 测试兼容性

---

💡 **提示**: 始终在测试环境验证迁移后再部署到生产环境！

🔗 **详细文档**: 查看 `backend/migrations/README.md`

📧 **技术支持**: 遇到问题请查看日志文件或运行测试脚本诊断