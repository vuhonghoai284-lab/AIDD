# Alembic版本不存在错误解决指南

## 问题描述

当使用Alembic初始化表时，可能遇到"版本不存在"错误，通常表现为：
- `RevisionError: Can't locate revision identified by 'xxxxx'`
- `Target database is not up to date`
- 版本号不匹配或版本文件缺失

## 根本原因分析

### 1. 版本文件与数据库不同步
- 数据库中记录的版本在文件系统中不存在
- 版本文件被删除或移动，但数据库记录未更新
- 多环境间版本文件不一致

### 2. 迁移历史被破坏
- Git操作导致版本文件丢失
- 手动删除版本文件但未更新数据库
- 多分支开发导致版本冲突

### 3. 环境配置问题
- 不同配置文件指向不同数据库
- PYTHONPATH或工作目录不正确
- 数据库连接参数错误

## 诊断步骤

### 1. 运行诊断工具
```bash
PYTHONPATH=. CONFIG_FILE=config.blue.yaml python alembic_diagnosis.py
```

### 2. 检查当前状态
```bash
# 检查当前数据库版本
python run_alembic.py current

# 检查版本历史
python run_alembic.py history

# 检查版本文件
ls -la alembic/versions/
```

### 3. 验证数据库连接
```bash
PYTHONPATH=. CONFIG_FILE=config.blue.yaml python -c "
from app.core.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text('SELECT version_num FROM alembic_version'))
    print('数据库版本:', result.fetchall())
"
```

## 解决方案

### 方案1: 自动修复版本不匹配（推荐）
```bash
# 使用诊断工具自动修复
PYTHONPATH=. CONFIG_FILE=config.blue.yaml python alembic_diagnosis.py
# 选择 'y' 进行自动修复
```

### 方案2: 手动同步版本
```bash
# 1. 查看当前版本文件
ls alembic/versions/

# 2. 获取最新版本号（文件名开头的hash）
# 例如：0719bfc9e700_初始数据库架构_创建所有表.py

# 3. 更新数据库版本记录
PYTHONPATH=. python -c "
from app.core.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    conn.execute(text('DELETE FROM alembic_version'))
    conn.execute(text('INSERT INTO alembic_version (version_num) VALUES (\"0719bfc9e700\")'))
    conn.commit()
    print('版本同步完成')
"
```

### 方案3: 重建迁移历史（彻底解决）
```bash
# ⚠️ 警告：此方案会重置所有迁移历史

# 1. 备份数据库数据（如果有重要数据）
mysqldump -u ai_docs_user -p ai_docs_db > backup.sql

# 2. 清理版本表
PYTHONPATH=. python -c "
from app.core.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    conn.execute(text('DROP TABLE IF EXISTS alembic_version'))
    conn.commit()
"

# 3. 删除现有版本文件
rm alembic/versions/*.py

# 4. 创建新的初始迁移
python run_alembic.py revision --autogenerate -m "Initial migration"

# 5. 应用迁移
python run_alembic.py upgrade head
```

### 方案4: 版本文件恢复
如果知道缺失的版本内容，可以手动创建版本文件：
```bash
# 在 alembic/versions/ 目录下创建缺失的版本文件
# 文件名格式：{revision_id}_{description}.py
```

## 预防措施

### 1. 版本控制最佳实践
```bash
# 总是提交版本文件到Git
git add alembic/versions/
git commit -m "Add migration: description"

# 在团队开发中，合并前先检查版本冲突
git pull --rebase origin main
```

### 2. 环境隔离
```yaml
# 为不同环境使用不同的配置文件
# development: config.yaml
# staging: config.blue.yaml  
# production: config.prod.yaml
```

### 3. 定期备份
```bash
# 定期备份数据库和版本文件
mysqldump -u user -p database > backup_$(date +%Y%m%d).sql
tar -czf migrations_backup_$(date +%Y%m%d).tar.gz alembic/versions/
```

## 常见错误及解决

### 错误1: `RevisionError: Can't locate revision`
**原因**: 数据库中的版本在文件系统中不存在  
**解决**: 使用方案1或方案2同步版本

### 错误2: `Target database is not up to date`
**原因**: 数据库版本落后于代码版本  
**解决**: 
```bash
python run_alembic.py upgrade head
```

### 错误3: `Multiple heads detected`
**原因**: 存在多个分支头版本  
**解决**:
```bash
python run_alembic.py merge -m "merge heads" head1 head2
python run_alembic.py upgrade head
```

### 错误4: `Can't locate table alembic_version`
**原因**: Alembic未初始化  
**解决**:
```bash
python run_alembic.py stamp head
```

## 工具脚本

项目提供了以下辅助工具：

1. **alembic_diagnosis.py** - 自动诊断和修复
2. **run_alembic.py** - 环境无关的Alembic运行器
3. **ALEMBIC_TROUBLESHOOTING.md** - 基础故障排除指南

## 生产环境注意事项

1. **迁移前备份**: 在生产环境执行迁移前，务必完整备份数据库
2. **分阶段部署**: 先在测试环境验证迁移，再部署到生产环境
3. **回滚计划**: 准备好回滚方案和数据恢复计划
4. **监控检查**: 迁移后验证数据完整性和应用功能

## 联系支持

如果问题仍然存在，请提供：
1. 完整的错误日志
2. `python alembic_diagnosis.py` 的输出
3. `alembic history` 的结果
4. 数据库版本信息

这些信息将帮助快速定位和解决问题。