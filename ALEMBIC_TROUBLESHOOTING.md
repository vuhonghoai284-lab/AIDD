# Alembic 故障排除指南

## 常见错误: ModuleNotFoundError

### 错误表现
```
ModuleNotFoundError: No module named 'app.models.task_queue'
```

### 原因分析
1. **PYTHONPATH未设置**: Alembic无法找到应用模块
2. **工作目录错误**: 未在正确的目录下运行命令
3. **环境隔离问题**: 虚拟环境或容器环境中路径不一致

### 解决方案

#### 方案1: 使用辅助脚本（推荐）
```bash
# 在backend目录下使用辅助脚本
python run_alembic.py current
python run_alembic.py upgrade head
python run_alembic.py revision --autogenerate -m "description"
```

#### 方案2: 手动设置环境变量
```bash
# 确保在backend目录下
cd backend

# 设置PYTHONPATH并运行
PYTHONPATH=. alembic current
PYTHONPATH=. alembic upgrade head
PYTHONPATH=. CONFIG_FILE=config.blue.yaml alembic upgrade head
```

#### 方案3: 生产环境部署
```bash
# 在生产环境中，确保设置正确的工作目录
cd /path/to/project/backend

# 使用Python模块方式运行
python -m alembic current
python -m alembic upgrade head

# 或使用辅助脚本
python run_alembic.py upgrade head
```

### 环境变量配置
```bash
# 必要的环境变量
export PYTHONPATH=/path/to/backend
export CONFIG_FILE=config.blue.yaml  # 可选，指定配置文件

# 数据库连接环境变量（如需要）
export DATABASE_TYPE=mysql
export MYSQL_HOST=localhost
export MYSQL_USERNAME=ai_docs_user
export MYSQL_PASSWORD=ai_docs_password
export MYSQL_DATABASE=ai_docs_db
```

### Docker环境
```dockerfile
# 在Dockerfile中设置工作目录和环境变量
WORKDIR /app/backend
ENV PYTHONPATH=/app/backend

# 运行迁移
RUN python run_alembic.py upgrade head
```

### 验证步骤
1. **检查当前版本**:
   ```bash
   python run_alembic.py current
   ```

2. **查看迁移历史**:
   ```bash
   python run_alembic.py history
   ```

3. **升级到最新版本**:
   ```bash
   python run_alembic.py upgrade head
   ```

4. **生成新迁移**:
   ```bash
   python run_alembic.py revision --autogenerate -m "描述"
   ```

### 调试信息
如果仍有问题，查看详细的错误信息：
```bash
python -c "
import sys, os
from pathlib import Path
print('当前目录:', os.getcwd())
print('Python路径:', sys.path[:3])
print('Backend目录存在:', Path('backend').exists())
print('App模块存在:', Path('app').exists())
"
```

### 注意事项
1. 始终在backend目录下运行Alembic命令
2. 确保虚拟环境已激活且安装了所需依赖
3. 生产环境中使用绝对路径和环境变量
4. 避免在项目根目录直接运行alembic命令