# 生产环境数据库字段长度问题修复指南

## 问题概述

生产环境出现AI输出数据过大导致的数据库插入失败：

```
(pymysql.err.DataError) (1406, "Data too long for column 'raw_output' at row 1")
```

**原因分析：**
- MySQL的`TEXT`类型最大只能存储65,535字符（64KB）
- AI输出的JSON数据约16万字符，远超TEXT限制
- 需要升级为`LONGTEXT`类型（最大4GB）

## 🚨 紧急修复步骤

### 1. 立即备份数据库

```bash
# 创建完整备份
mysqldump -u root -p ai_doc_test > backup_$(date +%Y%m%d_%H%M%S).sql

# 验证备份完整性
mysql -u root -p -e "SELECT COUNT(*) FROM ai_outputs;" ai_doc_test
```

### 2. 停止应用服务

```bash
# 停止后端服务
pkill -f "python.*main.py"

# 或者如果使用systemd
sudo systemctl stop ai-doc-backend
```

### 3. 执行数据库结构迁移

```sql
-- 连接到MySQL
mysql -u root -p ai_doc_test

-- 查看当前表结构
DESCRIBE ai_outputs;

-- 执行字段类型升级
ALTER TABLE ai_outputs MODIFY COLUMN input_text LONGTEXT NOT NULL;
ALTER TABLE ai_outputs MODIFY COLUMN raw_output LONGTEXT NOT NULL;

-- 验证修改结果
DESCRIBE ai_outputs;

-- 退出MySQL
EXIT;
```

### 4. 部署修复后的代码

```bash
# 拉取最新代码
git pull origin main

# 重启应用服务
python app/main.py

# 或者如果使用systemd
sudo systemctl start ai-doc-backend
sudo systemctl status ai-doc-backend
```

### 5. 验证修复效果

```bash
# 运行迁移验证脚本
cd backend
python migrate_longtext.py --verify

# 测试大数据插入
python migrate_longtext.py --test
```

## 🔧 自动化修复脚本

我们提供了自动化修复脚本，可以安全执行迁移：

```bash
# 进入后端目录
cd backend

# 运行迁移脚本（会提示备份）
python migrate_longtext.py

# 强制执行（跳过备份提示，用于自动化部署）
python migrate_longtext.py --force

# 仅验证不执行迁移
python migrate_longtext.py --verify

# 测试大数据插入能力
python migrate_longtext.py --test
```

## 📊 修复前后对比

| 项目 | 修复前 | 修复后 |
|-----|--------|--------|
| `input_text` | TEXT (65,535字符) | LONGTEXT (4GB) |
| `raw_output` | TEXT (65,535字符) | LONGTEXT (4GB) |
| 支持AI输出大小 | 最大64KB | 最大4GB |
| 跨数据库兼容 | 否 | 是（MySQL使用LONGTEXT，SQLite使用TEXT） |

## 🛠️ 新增功能

### 1. 跨数据库兼容的大文本类型

```python
class LargeText(TypeDecorator):
    """跨数据库的大文本类型，MySQL使用LONGTEXT，SQLite使用TEXT"""
    impl = Text
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'mysql':
            return dialect.type_descriptor(LONGTEXT())
        else:
            return dialect.type_descriptor(Text())
```

### 2. 增强的数据库事务处理

新增 `app/core/database_utils.py` 提供：

- `safe_insert_ai_output()`: 安全插入AI输出，自动处理大数据
- `safe_log_error()`: 安全记录错误日志
- `robust_db_session()`: 增强的数据库会话管理
- `cleanup_large_ai_outputs()`: 清理历史大数据记录

### 3. 自动数据截断保护

```python
# 自动截断过长数据，防止插入失败
if len(raw_output) > max_text_length:
    logger.warning(f"原始输出过长，截断至 {max_text_length} 字符")
    raw_output = raw_output[:max_text_length] + "...[截断]"
```

## ⚠️ 注意事项

### 迁移注意事项

1. **备份优先**：任何操作前都要先备份数据库
2. **停服迁移**：建议在低峰期停服执行迁移
3. **权限检查**：确保MySQL用户有ALTER权限
4. **空间估算**：LONGTEXT会增加存储空间需求

### 性能影响

1. **查询性能**：LONGTEXT字段的查询比TEXT稍慢
2. **索引限制**：LONGTEXT不能作为主键或唯一键
3. **内存使用**：大文本会增加内存占用
4. **备份时间**：备份恢复时间会增加

### 监控建议

```bash
# 监控大数据记录
mysql -u root -p -e "
SELECT 
    COUNT(*) as total_records,
    AVG(CHAR_LENGTH(raw_output)) as avg_size,
    MAX(CHAR_LENGTH(raw_output)) as max_size,
    SUM(CHAR_LENGTH(raw_output)) as total_size
FROM ai_outputs 
WHERE CHAR_LENGTH(raw_output) > 50000;
" ai_doc_test
```

## 🚀 部署后验证

### 1. 检查表结构

```sql
mysql -u root -p -e "DESCRIBE ai_outputs;" ai_doc_test
```

期望输出：
```
+------------------+------------+------+-----+---------+----------------+
| Field            | Type       | Null | Key | Default | Extra          |
+------------------+------------+------+-----+---------+----------------+
| input_text       | longtext   | NO   |     | NULL    |                |
| raw_output       | longtext   | NO   |     | NULL    |                |
+------------------+------------+------+-----+---------+----------------+
```

### 2. 测试AI处理流程

1. 上传一个大文档（>100页PDF）
2. 观察任务处理日志
3. 确认不再出现数据长度错误

### 3. 监控日志

```bash
# 查看应用日志
tail -f logs/app.log | grep -E "(DataError|Data too long)"

# 确认无错误输出
```

## 📞 故障排除

### 问题1：ALTER TABLE执行时间过长

**原因**：表数据量大，ALTER操作需要重建表

**解决**：
```sql
-- 查看进度（另开MySQL连接）
SHOW PROCESSLIST;

-- 如果需要取消操作
KILL QUERY [process_id];
```

### 问题2：磁盘空间不足

**原因**：ALTER TABLE需要额外磁盘空间

**解决**：
```bash
# 检查磁盘空间
df -h

# 清理临时文件
sudo rm -rf /tmp/mysql*
sudo rm -rf /var/tmp/mysql*
```

### 问题3：权限不足

**错误**：`Access denied for user`

**解决**：
```sql
-- 赋予用户ALTER权限
GRANT ALTER ON ai_doc_test.* TO 'username'@'localhost';
FLUSH PRIVILEGES;
```

## 📈 长期优化建议

### 1. 数据分层存储

考虑将大型AI输出存储到文件系统：

```python
# 大于1MB的数据存储到文件
if len(raw_output) > 1024 * 1024:
    file_path = f"data/ai_outputs/{task_id}_{timestamp}.json"
    with open(file_path, 'w') as f:
        f.write(raw_output)
    raw_output = f'{{"file_path": "{file_path}", "size": {len(raw_output)}}}'
```

### 2. 数据压缩

```python
import gzip
import base64

# 压缩大文本
compressed_data = gzip.compress(raw_output.encode())
raw_output = base64.b64encode(compressed_data).decode()
```

### 3. 定期清理

```bash
# 添加定时任务清理历史大数据
0 2 * * * cd /path/to/backend && python -c "
from app.core.database_utils import cleanup_large_ai_outputs
from app.core.database import get_db
db = next(get_db())
cleanup_large_ai_outputs(db, days_old=30, max_size_mb=10)
"
```

---

## ✅ 完成检查清单

- [ ] 数据库已备份
- [ ] 应用服务已停止
- [ ] 表结构已升级为LONGTEXT
- [ ] 新代码已部署
- [ ] 服务已重启
- [ ] 迁移结果已验证
- [ ] 大数据插入测试通过
- [ ] 应用日志无错误
- [ ] 监控告警已配置

## 📞 技术支持

如遇到其他问题，请提供：

1. 完整的错误日志
2. 数据库版本信息：`SELECT VERSION();`
3. 表结构信息：`DESCRIBE ai_outputs;`
4. 磁盘空间信息：`df -h`
5. 内存使用情况：`free -h`