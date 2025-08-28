# 数据库迁移系统

这是一个专为AI文档测试系统设计的数据库版本管理和迁移工具，支持SQLite和MySQL，提供完整的备份、恢复和回滚功能。

## 🚀 快速开始

### 1. 查看迁移状态
```bash
python migrate.py status
```

### 2. 创建新迁移
```bash
# 手动创建迁移
python migrate.py create "添加新表"

# 自动检测并生成迁移
python migrate.py auto "自动检测变更"
```

### 3. 执行迁移
```bash
# 执行所有待迁移
python migrate.py up

# 执行时不创建备份
python migrate.py up --no-backup
```

### 4. 回滚迁移
```bash
python migrate.py down <migration_id>
```

### 5. 数据库备份和恢复
```bash
# 创建备份
python migrate.py backup

# 恢复备份
python migrate.py restore path/to/backup.db
```

## 📁 目录结构

```
migrations/
├── README.md                 # 说明文档
├── migration_manager.py      # 核心迁移管理器
├── migration_history.json    # 迁移历史记录
├── migration.log             # 迁移日志
├── versions/                 # 迁移文件目录
│   ├── __init__.py
│   └── 20240101_000000_example.py
├── backups/                  # 备份文件目录
│   └── backup_20240101.db
└── schema_snapshots/         # 结构快照目录
```

## 🛠️ 功能特性

### ✨ 核心功能
- **版本管理**: 追踪数据库结构变更历史
- **自动检测**: 对比模型和数据库，自动生成迁移
- **安全执行**: 迁移前自动备份，支持回滚
- **多数据库**: 同时支持SQLite和MySQL
- **校验和**: 确保迁移文件完整性

### 🔧 高级功能
- **批量迁移**: 一次执行多个待迁移
- **增量备份**: 只在必要时创建备份
- **并发控制**: 防止并发执行冲突
- **日志记录**: 详细的操作日志
- **环境隔离**: 支持多环境配置

## 📝 迁移文件格式

迁移文件采用Python格式，包含以下内容：

```python
"""
迁移描述

Migration ID: 20240101_120000_add_user_table
Created: 2024-01-01T12:00:00
Checksum: abc123...
"""

from datetime import datetime
from sqlalchemy import text

# 迁移信息
MIGRATION_ID = "20240101_120000_add_user_table"
DESCRIPTION = "添加用户表"
CREATED_AT = datetime.fromisoformat("2024-01-01T12:00:00")
CHECKSUM = "abc123..."

# 升级SQL
SQL_UP = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""

# 降级SQL（回滚）
SQL_DOWN = """
DROP TABLE users
"""

def upgrade(session):
    """执行升级操作"""
    for sql_statement in SQL_UP.strip().split(';'):
        sql_statement = sql_statement.strip()
        if sql_statement:
            session.execute(text(sql_statement))
    session.commit()

def downgrade(session):
    """执行降级操作"""
    for sql_statement in SQL_DOWN.strip().split(';'):
        sql_statement = sql_statement.strip()
        if sql_statement:
            session.execute(text(sql_statement))
    session.commit()
```

## 🚨 安全注意事项

### 生产环境使用
1. **备份策略**: 生产环境必须在迁移前创建备份
2. **测试验证**: 先在测试环境验证迁移
3. **维护窗口**: 在低峰时段执行大型迁移
4. **监控检查**: 迁移后检查应用程序功能

### 回滚准备
1. **编写回滚SQL**: 每个迁移都应包含回滚操作
2. **数据备份**: 重要数据变更前额外备份
3. **测试回滚**: 验证回滚操作的正确性

## 🔄 工作流程

### 开发环境工作流程
```bash
# 1. 修改数据模型
# 2. 生成迁移
python migrate.py auto "添加新功能相关表"

# 3. 检查生成的迁移文件
# 4. 执行迁移
python migrate.py up

# 5. 测试功能
# 6. 提交代码（包含迁移文件）
```

### 生产环境部署流程
```bash
# 1. 检查迁移状态
python migrate.py status

# 2. 创建备份
python migrate.py backup production_backup

# 3. 执行迁移
python migrate.py up

# 4. 验证应用功能
# 5. 如有问题，使用备份恢复
# python migrate.py restore production_backup.db
```

## ⚙️ 配置说明

迁移系统使用应用的配置文件（config.yaml），支持以下配置：

```yaml
database:
  type: "sqlite"  # 或 "mysql"
  
  # SQLite配置
  sqlite:
    path: "./data/app.db"
  
  # MySQL配置
  mysql:
    host: "localhost"
    port: 3306
    username: "root"
    password: "password"
    database: "ai_doc_test"
    charset: "utf8mb4"
```

### 环境变量支持
```bash
# 指定配置文件
CONFIG_FILE=config.test.yaml python migrate.py status

# MySQL配置
MYSQL_HOST=localhost MYSQL_PASSWORD=secret python migrate.py up
```

## 🐛 故障排除

### 常见问题

1. **连接失败**
   ```
   错误: 数据库连接失败
   解决: 检查配置文件中的数据库连接信息
   ```

2. **迁移文件冲突**
   ```
   错误: 迁移ID重复
   解决: 删除重复的迁移文件或重新生成
   ```

3. **权限不足**
   ```
   错误: 无法创建表
   解决: 检查数据库用户权限
   ```

4. **备份失败**
   ```
   错误: mysqldump命令未找到
   解决: 安装MySQL客户端工具
   ```

### 恢复策略

1. **自动备份恢复**
   ```bash
   # 查看可用备份
   ls migrations/backups/
   
   # 恢复指定备份
   python migrate.py restore migrations/backups/backup_20240101.db
   ```

2. **手动数据恢复**
   ```bash
   # SQLite
   cp backup.db current.db
   
   # MySQL
   mysql -u root -p database_name < backup.sql
   ```

## 📚 API参考

### MigrationManager类

```python
from migrations.migration_manager import MigrationManager

# 创建管理器
manager = MigrationManager(config_file="config.yaml")

# 创建迁移
migration_id = manager.create_migration("描述", sql_up, sql_down)

# 自动生成迁移
migration_id = manager.auto_generate_migration("描述")

# 执行迁移
manager.execute_migration(migration_id)

# 回滚迁移
manager.rollback_migration(migration_id)

# 创建备份
backup_path = manager.create_backup("备份名称")

# 恢复备份
manager.restore_backup(backup_path)

# 关闭连接
manager.close()
```

## 🤝 贡献指南

1. **代码规范**: 遵循项目的Python代码规范
2. **测试覆盖**: 新功能需要包含测试用例
3. **文档更新**: 更新相关文档说明
4. **向后兼容**: 确保不破坏现有迁移文件

## 📞 支持

如果在使用过程中遇到问题：

1. 查看迁移日志：`migrations/migration.log`
2. 运行测试脚本：`python test_migration.py`
3. 检查配置文件格式
4. 参考示例迁移文件

---

*最后更新: 2024年1月*