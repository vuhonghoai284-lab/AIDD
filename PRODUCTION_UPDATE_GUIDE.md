# 生产环境更新部署指南

本指南详细说明如何将最新的功能更新和错误修复安全地部署到生产环境。

## 🎯 本次更新内容概览

### 主要功能更新
- **并发任务限制功能**: 用户级和系统级并发控制（默认用户10个，系统100个）
- **外键约束修复**: 解决生产环境数据库完整性问题
- **数据库字段升级**: TEXT字段升级为LONGTEXT以支持大数据处理
- **错误处理增强**: 更robust的异常处理和事务管理

### 关键修复
- 修复 ai_outputs 表外键约束失败问题
- 修复 issues 和 task_logs 表的数据一致性问题
- 增强大文档处理能力
- 优化文件下载功能

---

## 📋 部署前准备清单

### 1. 环境检查
- [ ] 确认生产环境状态正常
- [ ] 检查磁盘空间（至少保留2GB用于备份）
- [ ] 确认数据库连接正常
- [ ] 验证必要权限（数据库ALTER权限）

### 2. 依赖检查
```bash
# 检查Python依赖
pip list | grep -E "(pymysql|sqlalchemy)"

# 检查MySQL服务状态
systemctl status mysql
# 或
service mysql status
```

---

## 🔄 部署步骤

### 步骤1: 数据库备份（🚨 关键步骤）

**MySQL备份命令：**
```bash
# 完整备份（推荐）
mysqldump -u root -p --single-transaction --routines --triggers ai_doc_test > backup_$(date +%Y%m%d_%H%M%S).sql

# 仅数据备份（更快）
mysqldump -u root -p --single-transaction --no-create-info ai_doc_test > backup_data_$(date +%Y%m%d_%H%M%S).sql
```

**验证备份：**
```bash
# 检查备份文件大小
ls -lh backup_*.sql

# 检查备份内容
head -n 20 backup_*.sql
```

### 步骤2: 应用代码更新

**拉取最新代码：**
```bash
cd /path/to/your/project
git fetch origin
git checkout main
git pull origin main
```

**验证更新内容：**
```bash
# 查看最新提交
git log --oneline -5

# 确认关键文件存在
ls -la backend/migrate_user_concurrency.py
ls -la backend/fix_foreign_key_constraints.py
```

### 步骤3: 执行数据库迁移

**3.1 并发限制字段迁移**
```bash
cd backend

# 检查当前数据库状态
python migrate_user_concurrency.py --verify

# 执行迁移（如果需要）
python migrate_user_concurrency.py

# 验证迁移结果
python migrate_user_concurrency.py --verify
```

**3.2 外键约束问题修复**
```bash
# 分析当前问题
python fix_foreign_key_constraints.py --stats

# 执行修复（如果有问题）
python fix_foreign_key_constraints.py --force

# 验证修复结果
python fix_foreign_key_constraints.py --verify
```

### 步骤4: 重启服务

**重启后端服务：**
```bash
# 使用systemd（推荐）
sudo systemctl restart ai-doc-backend

# 或使用进程管理器
pm2 restart ai-doc-backend

# 或手动重启
pkill -f "python.*main.py"
cd backend && python app/main.py &
```

**重启前端服务：**
```bash
# 重新构建前端
cd frontend
npm run build

# 重启Web服务器
sudo systemctl restart nginx
# 或
sudo service nginx restart
```

### 步骤5: 功能验证

**5.1 基础服务检查**
```bash
# 检查后端服务状态
curl -f http://localhost:8080/health || echo "后端服务异常"

# 检查数据库连接
python -c "
import sys
sys.path.append('/path/to/backend')
from app.core.database import get_db
from app.core.config import get_settings
print('✅ 数据库连接正常')
"
```

**5.2 新功能验证**
```bash
cd backend

# 测试并发控制功能
python -c "
import sys
sys.path.append('.')
from app.services.concurrency_service import concurrency_service
from app.core.database import get_db
from app.models.user import User
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.core.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

try:
    user = db.query(User).first()
    if user:
        status = concurrency_service.get_concurrency_status(db, user)
        print(f'✅ 并发控制功能正常: 系统{status[\"system\"][\"max_count\"]}，用户{status[\"user\"][\"max_count\"]}')
    else:
        print('⚠️ 没有用户数据进行测试')
finally:
    db.close()
"
```

---

## 🔍 验证检查点

### 数据完整性验证
```sql
-- 检查外键约束
SELECT 
    'ai_outputs' as table_name,
    COUNT(*) as total_records,
    COUNT(t.id) as valid_references
FROM ai_outputs ao
LEFT JOIN tasks t ON ao.task_id = t.id;

SELECT 
    'issues' as table_name,
    COUNT(*) as total_records,
    COUNT(t.id) as valid_references
FROM issues i
LEFT JOIN tasks t ON i.task_id = t.id;

SELECT 
    'task_logs' as table_name,
    COUNT(*) as total_records,
    COUNT(t.id) as valid_references
FROM task_logs tl
LEFT JOIN tasks t ON tl.task_id = t.id;
```

### 并发限制验证
```sql
-- 检查用户并发限制字段
SELECT uid, display_name, max_concurrent_tasks, is_admin 
FROM users 
LIMIT 10;

-- 验证配置值
SELECT 
    COUNT(*) as total_users,
    AVG(max_concurrent_tasks) as avg_limit,
    MIN(max_concurrent_tasks) as min_limit,
    MAX(max_concurrent_tasks) as max_limit
FROM users;
```

---

## 🚨 故障排除

### 常见问题及解决方案

**1. 数据库连接失败**
```bash
# 检查MySQL服务
sudo systemctl status mysql

# 检查数据库配置
python -c "
from app.core.config import get_settings
settings = get_settings()
print(f'数据库URL: {settings.database_url}')
"
```

**2. 迁移脚本失败**
```bash
# 检查数据库权限
mysql -u root -p -e "SHOW GRANTS FOR CURRENT_USER();"

# 手动执行关键SQL
mysql -u root -p ai_doc_test -e "
ALTER TABLE users ADD COLUMN max_concurrent_tasks INT DEFAULT 10;
"
```

**3. 外键约束问题持续**
```bash
# 检查具体的孤儿记录
python -c "
import sys
sys.path.append('/path/to/backend')
from sqlalchemy import create_engine, text
from app.core.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url)

with engine.connect() as conn:
    # 查找具体的孤儿记录
    result = conn.execute(text('''
        SELECT task_id, COUNT(*) as count 
        FROM ai_outputs 
        WHERE task_id NOT IN (SELECT id FROM tasks)
        GROUP BY task_id
        LIMIT 5
    ''')).fetchall()
    
    if result:
        print('发现孤儿记录:')
        for row in result:
            print(f'  task_id: {row[0]}, count: {row[1]}')
    else:
        print('✅ 没有发现孤儿记录')
"
```

### 回滚计划

**如果部署失败，使用以下步骤回滚：**

1. **停止服务**
```bash
sudo systemctl stop ai-doc-backend
sudo systemctl stop nginx
```

2. **恢复数据库**
```bash
# 恢复完整备份
mysql -u root -p ai_doc_test < backup_YYYYMMDD_HHMMSS.sql
```

3. **回滚代码**
```bash
git reset --hard HEAD~2  # 回滚到之前的版本
```

4. **重启服务**
```bash
sudo systemctl start ai-doc-backend
sudo systemctl start nginx
```

---

## 📊 部署后监控

### 关键指标监控

1. **数据库性能**
   - 查询响应时间
   - 连接池状态
   - 错误日志

2. **应用性能**
   - 任务创建成功率
   - 并发任务数量
   - 内存使用情况

3. **业务指标**
   - 用户任务创建速度
   - 错误发生频率
   - 系统整体可用性

### 监控命令
```bash
# 检查应用日志
tail -f /path/to/logs/app.log

# 检查MySQL错误日志
sudo tail -f /var/log/mysql/error.log

# 检查系统资源
htop
iostat -x 1
```

---

## ✅ 部署完成检查清单

部署完成后，请确认以下项目：

- [ ] 所有服务正常启动
- [ ] 数据库连接正常
- [ ] 并发限制功能工作正常
- [ ] 无外键约束错误
- [ ] 文件上传下载功能正常
- [ ] 任务创建和处理正常
- [ ] 前端页面加载正常
- [ ] 用户登录功能正常
- [ ] API接口响应正常

---

## 📞 支持联系

如果在部署过程中遇到问题，请：

1. 检查日志文件获取详细错误信息
2. 使用故障排除部分的指导
3. 如需进一步协助，请提供：
   - 错误日志内容
   - 系统环境信息
   - 执行的具体步骤

---

**⚠️ 重要提醒：**
- 始终在生产环境部署前先在测试环境验证
- 确保备份完成后再开始任何更改
- 建议在业务低峰期执行部署
- 部署过程中保持与团队的沟通