# Alembic数据库迁移系统

## 概述

本项目已集成Alembic作为标准的数据库迁移工具，替代了之前的自定义SQL迁移系统。

## 主要优势

✅ **自动生成迁移**: 检测模型变更，自动生成DDL语句
✅ **版本控制**: 每个迁移都有唯一版本号和时间戳  
✅ **回滚支持**: 支持向前和向后迁移
✅ **数据库无关**: 支持MySQL、PostgreSQL、SQLite等
✅ **团队协作**: 迁移文件可版本控制，团队共享
✅ **生产安全**: 经过社区验证的成熟工具
✅ **配置灵活**: 支持多环境配置文件

## 安装依赖

```bash
# 在虚拟环境中安装
pip install alembic==1.13.1
```

## 使用方式

### 1. 标准Alembic命令

```bash
# 生成迁移（自动检测模型变更）
alembic revision --autogenerate -m "添加用户表"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1

# 查看当前版本
alembic current

# 查看迁移历史
alembic history
```

### 2. 自定义配置文件支持

```bash
# 环境变量方式
CONFIG_FILE=config.test.yaml alembic upgrade head

# 命令行参数方式  
alembic -x config_file=config.test.yaml upgrade head
```

### 3. Python集成方式

```bash
# 使用集成管理器
python app/core/alembic_manager.py generate --message "添加队列表"
python app/core/alembic_manager.py upgrade
python app/core/alembic_manager.py current
python app/core/alembic_manager.py history

# 指定配置文件
python app/core/alembic_manager.py --config-file config.test.yaml generate --message "测试迁移"
```

## FastAPI集成

### 自动迁移

应用启动时会自动执行数据库迁移：

```python
# app/main.py 中的启动事件
@app.on_event("startup")
async def startup_event():
    # 1. 首先执行数据库迁移
    from app.core.alembic_manager import run_migrations_on_startup
    config_file = os.getenv('CONFIG_FILE')
    await run_migrations_on_startup(config_file)
    
    # 2. 其他初始化操作...
```

### 手动迁移控制

```python
from app.core.alembic_manager import AlembicManager

# 创建管理器
manager = AlembicManager()

# 或指定配置文件
manager = AlembicManager("config.test.yaml")

# 生成迁移
revision = manager.generate_migration("添加新字段", autogenerate=True)

# 执行迁移
manager.upgrade("head")

# 回滚迁移
manager.downgrade("-1")
```

## 迁移最佳实践

### 1. 开发流程

```bash
# 1. 修改模型文件
# 2. 生成迁移
alembic revision --autogenerate -m "描述性的迁移信息"

# 3. 检查生成的迁移文件
# 4. 执行迁移
alembic upgrade head

# 5. 测试功能
# 6. 提交代码（包含迁移文件）
```

### 2. 生产环境部署

```bash
# 部署前执行迁移
CONFIG_FILE=config.prod.yaml alembic upgrade head

# 或使用Docker
docker exec -it app-container alembic upgrade head
```

### 3. 多环境配置

```bash
# 开发环境（SQLite）
CONFIG_FILE=config.yaml alembic upgrade head

# 测试环境（MySQL）  
CONFIG_FILE=config.test.yaml alembic upgrade head

# 生产环境（MySQL）
CONFIG_FILE=config.prod.yaml alembic upgrade head
```

## 迁移文件管理

### 目录结构

```
alembic/
├── versions/           # 迁移文件存储目录
├── env.py             # Alembic环境配置（支持自定义YAML）
└── script.py.mako     # 迁移文件模板

alembic.ini            # Alembic主配置文件
```

### 迁移文件命名

Alembic自动生成的文件名格式：
```
versions/001_20250829_1234_initial_migration.py
versions/002_20250829_1245_add_queue_tables.py
```

## 故障排除

### 常见问题

1. **迁移冲突**
```bash
# 查看冲突
alembic branches

# 合并分支
alembic merge -m "合并迁移分支" heads
```

2. **回滚问题**
```bash
# 查看历史
alembic history

# 回滚到特定版本
alembic downgrade <revision_id>
```

3. **配置问题**
```bash
# 验证配置
python test_alembic_integration.py
```

## 全新数据库部署

### 新项目部署
对于全新的数据库（无任何表），使用以下步骤：

```bash
# 1. 确保虚拟环境激活
source venv/bin/activate

# 2. 执行迁移创建所有表
alembic upgrade head

# 3. 验证表创建
python -c "from app.core.database import engine; from sqlalchemy import inspect; print('表:', inspect(engine).get_table_names())"
```

### 多环境全新部署
```bash
# 开发环境（SQLite）
CONFIG_FILE=config.yaml alembic upgrade head

# 测试环境
CONFIG_FILE=config.test.yaml alembic upgrade head  

# 生产环境（MySQL）
CONFIG_FILE=config.prod.yaml alembic upgrade head
```

### 验证部署结果
完成迁移后应该看到以下表：
- `users` (用户表)
- `ai_models` (AI模型表)  
- `file_infos` (文件信息表)
- `tasks` (任务表)
- `task_queue` (任务队列表)
- `queue_config` (队列配置表)
- `task_shares` (任务分享表)
- `issues` (问题反馈表)
- `ai_outputs` (AI输出表)
- `task_logs` (任务日志表)
- `alembic_version` (Alembic版本表)

## 从旧迁移系统迁移

1. **备份现有数据**: 确保数据安全
2. **生成初始迁移**: 基于现有表结构（已完成）
3. **标记为已应用**: 设置基线版本 `alembic stamp head`
4. **移除旧迁移代码**: 清理自定义迁移逻辑

## 注意事项

⚠️ **重要**: 
- 迁移文件应该纳入版本控制
- 生产环境迁移前务必备份数据
- 复杂迁移建议手动检查生成的SQL
- 多环境部署时确保迁移顺序一致