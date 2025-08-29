# AI文档测试系统 - 后端服务

基于FastAPI的AI文档质量检测系统后端服务，提供文档上传、AI分析、问题检测、满意度评分等功能。

## 📋 目录

- [功能特性](#功能特性)
- [系统要求](#系统要求)
- [快速开始](#快速开始)
- [详细安装](#详细安装)
- [配置说明](#配置说明)
- [运行方式](#运行方式)
- [API文档](#api文档)
- [测试](#测试)
- [部署](#部署)
- [故障排除](#故障排除)

## 🚀 功能特性

- **文档上传与处理**: 支持PDF、Word、Markdown格式
- **AI智能分析**: 集成多种AI模型进行文档质量检测
- **问题检测**: 语法、逻辑、结构、完整性检测
- **满意度评分**: 1-5星问题满意度评分系统
- **实时日志**: WebSocket实时任务处理日志
- **用户认证**: 支持系统管理员和第三方用户登录
- **权限控制**: 基于JWT的API权限管理
- **报告生成**: Excel格式测试报告导出
- **运营数据**: 完整的数据分析和统计功能

## 📦 系统要求

### 基础环境
- Python 3.8+（推荐3.11+）
- 内存：至少4GB（推荐8GB+）
- 磁盘：至少10GB可用空间

### 可选依赖
- Docker（推荐用于部署）
- PostgreSQL/MySQL（生产环境，开发环境使用SQLite）
- Redis（用于缓存和队列管理）

## ⚡ 快速开始

### 1. 克隆项目
```bash
git clone <repository-url>
cd ai_doc_test/backend
```

### 2. 创建虚拟环境
```bash
# Windows
python -m venv venv
venv\\Scripts\\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 启动服务
```bash
# 直接启动（使用默认配置）
python app/main.py

# 或使用PYTHONPATH
PYTHONPATH=. python app/main.py

# 指定配置文件
CONFIG_FILE=config.yaml python app/main.py
```

### 5. 验证安装
```bash
# 访问API文档
curl http://localhost:8080/docs

# 或在浏览器中打开
# http://localhost:8080/docs
```

## 🔧 详细安装

### Python环境准备
```bash
# 确认Python版本
python --version

# 安装pip升级
pip install --upgrade pip

# 创建虚拟环境（推荐）
python -m venv ai_doc_env
source ai_doc_env/bin/activate  # Linux/Mac
# ai_doc_env\\Scripts\\activate  # Windows
```

### 依赖安装
```bash
# 安装核心依赖
pip install -r requirements.txt

# 安装开发依赖（可选）
pip install -r requirements.dev.txt

# 验证关键包安装
python -c "import fastapi, sqlalchemy, pydantic; print('依赖安装成功')"
```

### 数据库初始化
```bash
# 系统会在首次启动时自动创建SQLite数据库
# 数据库文件位置：./data/app.db

# 查看数据库表结构
python -c "
from app.models import *
from app.core.database import engine, Base
Base.metadata.create_all(bind=engine)
print('数据库表创建完成')
"
```

## ⚙️ 配置说明

### 主配置文件 (config.yaml)

```yaml
# 服务器配置
server:
  host: "0.0.0.0"
  port: 8080
  debug: false
  workers: 1

# 数据库配置
database:
  # SQLite (开发环境)
  url: "sqlite:///./data/app.db"
  # PostgreSQL (生产环境)
  # url: "postgresql://user:password@localhost/ai_doc_db"

# CORS配置
cors:
  # 允许的前端域名
  origins:
    - "http://localhost:3000"
    - "http://localhost:5173"
    - "http://127.0.0.1:3000"
    - "http://127.0.0.1:5173"
  # 开发模式（自动允许更多域名）
  development_mode: false

# JWT配置
jwt:
  secret_key: "your-secret-key-here"
  algorithm: "HS256"
  expires_minutes: 30

# AI模型配置
ai_models:
  default_index: 0
  models:
    - label: "GPT-4o Mini (快速)"
      provider: "openai" 
      config:
        api_key: "${OPENAI_API_KEY}"
        base_url: "https://api.openai.com/v1"
        model: "gpt-4o-mini"
        max_tokens: 4000
    - label: "GPT-4o (高精度)"
      provider: "openai"
      config:
        api_key: "${OPENAI_API_KEY}" 
        base_url: "https://api.openai.com/v1"
        model: "gpt-4o"
        max_tokens: 8000

# 第三方登录配置
third_party_auth:
  authorization_url: "https://your-oauth-provider.com/oauth/authorize"
  token_url: "https://your-oauth-provider.com/oauth/token"
  client_id: "${OAUTH_CLIENT_ID}"
  client_secret: "${OAUTH_CLIENT_SECRET}"
  redirect_uri: "http://localhost:3000/auth/callback"
  scope: "read:user user:email"

# 文件上传配置
upload:
  max_file_size: 10485760  # 10MB
  allowed_extensions: [".pdf", ".docx", ".md", ".txt"]
  upload_dir: "./data/uploads"

# 日志配置
logging:
  level: "INFO"
  file: "./data/logs/app.log"
  max_bytes: 10485760
  backup_count: 5
```

### 环境变量配置

创建 `.env` 文件：
```bash
# AI API配置
OPENAI_API_KEY=your-openai-api-key
CLAUDE_API_KEY=your-claude-api-key

# 数据库配置（生产环境）
DATABASE_URL=postgresql://user:password@localhost/ai_doc_db

# 第三方登录
OAUTH_CLIENT_ID=your-oauth-client-id
OAUTH_CLIENT_SECRET=your-oauth-client-secret

# JWT密钥
JWT_SECRET_KEY=your-very-secure-secret-key

# CORS配置
FRONTEND_URL=http://localhost:3000
CORS_DEVELOPMENT_MODE=true

# 部署环境
APP_ENV=development
```

### 测试环境配置 (config.test.yaml)

```yaml
server:
  host: "127.0.0.1"
  port: 8081
  debug: true

database:
  url: "sqlite:///./data/test.db"

cors:
  development_mode: true
  origins:
    - "http://localhost:3000"

ai_models:
  default_index: 0
  models:
    - label: "Test Model"
      provider: "mock"
      config:
        mock_mode: true

upload:
  upload_dir: "./data/test/uploads"

logging:
  level: "DEBUG"
  file: "./data/test/logs/app.log"
```

## 🚀 运行方式

### 开发模式
```bash
# 直接运行
python app/main.py

# 使用uvicorn（推荐）
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# 指定配置文件
CONFIG_FILE=config.yaml python app/main.py

# 开发模式（自动重载）
CONFIG_FILE=config.yaml uvicorn app.main:app --reload
```

### 生产模式
```bash
# 单进程模式
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker

# 指定配置
CONFIG_FILE=config.prod.yaml gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker

# 后台运行
nohup python app/main.py > ./data/logs/app.log 2>&1 &
```

### Docker运行
```bash
# 构建镜像
docker build -t ai-doc-backend .

# 运行容器
docker run -d --name ai-doc-backend \
  -p 8080:8080 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config.yaml:/app/config.yaml \
  ai-doc-backend

# 查看日志
docker logs -f ai-doc-backend
```

## 📚 API文档

### 自动文档
启动服务后访问：
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

### 主要API端点

#### 认证相关
```bash
# 系统管理员登录
POST /api/auth/login
{
  "username": "admin",
  "password": "admin123"
}

# 第三方用户登录
GET /api/auth/thirdparty/login

# 登录回调
POST /api/auth/thirdparty/callback
```

#### 任务管理
```bash
# 创建任务
POST /api/tasks
Content-Type: multipart/form-data
- file: 文档文件
- title: 任务标题
- model_index: AI模型索引

# 获取任务列表
GET /api/tasks

# 获取任务详情
GET /api/tasks/{task_id}

# 删除任务
DELETE /api/tasks/{task_id}
```

#### 问题反馈
```bash
# 提交问题反馈
PUT /api/issues/{issue_id}/feedback
{
  "feedback_type": "accept|reject",
  "comment": "反馈评论"
}

# 提交满意度评分
PUT /api/issues/{issue_id}/satisfaction
{
  "satisfaction_rating": 4.5
}
```

#### AI输出
```bash
# 获取任务AI输出
GET /api/tasks/{task_id}/ai-outputs

# 获取AI输出详情
GET /api/ai-outputs/{output_id}
```

## 🧪 测试

### 运行测试
```bash
# 运行所有测试
python -m pytest

# 运行特定测试文件
python -m pytest tests/test_api.py

# 运行并生成覆盖率报告
python -m pytest --cov=app --cov-report=html

# 运行端到端测试
python -m pytest tests/e2e/ -v

# 运行新数据库启动测试
python -m pytest tests/e2e/test_fresh_database_startup.py -v
```

### 测试脚本
```bash
# 完整测试套件
python tests/run_tests.py

# API测试
python run_api_tests.py

# 性能测试
python -m pytest tests/test_performance.py
```

### 测试配置
```bash
# 使用测试配置文件
CONFIG_FILE=config.test.yaml python -m pytest

# 测试环境变量
export APP_MODE=test
python -m pytest
```

## 🚀 部署

### 本地部署
```bash
# 1. 准备生产配置
cp config.yaml config.prod.yaml
# 编辑config.prod.yaml，配置生产数据库等

# 2. 创建系统服务
sudo tee /etc/systemd/system/ai-doc-backend.service > /dev/null <<EOF
[Unit]
Description=AI Document Testing System Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/ai_doc_test/backend
Environment=CONFIG_FILE=config.prod.yaml
ExecStart=/path/to/venv/bin/python app/main.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 3. 启动服务
sudo systemctl enable ai-doc-backend
sudo systemctl start ai-doc-backend
sudo systemctl status ai-doc-backend
```

### Docker部署
```bash
# 1. 创建Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["python", "app/main.py"]
EOF

# 2. 构建和运行
docker build -t ai-doc-backend .
docker run -d --name ai-doc-backend \
  -p 8080:8080 \
  -v $(pwd)/data:/app/data \
  -e OPENAI_API_KEY=your-key \
  ai-doc-backend
```

### 使用Docker Compose
```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./data:/app/data
      - ./config.prod.yaml:/app/config.yaml
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DATABASE_URL=${DATABASE_URL}
    restart: unless-stopped

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=ai_doc_db
      - POSTGRES_USER=ai_doc_user
      - POSTGRES_PASSWORD=secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

volumes:
  postgres_data:
```

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f backend
```

## 🛠 运行脚本介绍

### start.sh / start.bat
一键启动脚本，自动处理环境准备和服务启动

### run_api_tests.py
API测试脚本，运行所有API端点测试并生成HTML报告

### tests/run_tests.py
完整测试套件，包含单元测试、集成测试和E2E测试

## 🔍 故障排除

### 常见问题

#### 1. 端口被占用
```bash
# 查找占用端口的进程
lsof -i :8080
# 杀死进程
kill -9 <PID>
```

#### 2. 数据库连接错误
```bash
# 重新创建数据库
rm -f data/app.db
python app/main.py  # 会自动创建
```

#### 3. 模块导入错误
```bash
# 确保PYTHONPATH正确
export PYTHONPATH=$(pwd)
python app/main.py
```

#### 4. AI API调用失败
```bash
# 检查API密钥
echo $OPENAI_API_KEY
# 测试API连接
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/models
```

#### 5. CORS错误
在config.yaml中启用开发模式：
```yaml
cors:
  development_mode: true
  origins:
    - "http://localhost:3000"
    - "http://192.168.1.100:3000"  # 添加你的IP
```

## 📞 技术支持

如需技术支持，请：
1. 查看本README文档
2. 检查[API文档](http://localhost:8080/docs)
3. 查看项目Issues
4. 联系开发团队

---

## 🏗 架构说明

### 目录结构
```
backend/
├── app/
│   ├── core/           # 核心配置和依赖
│   ├── models/         # 数据模型（ORM）
│   ├── dto/            # 数据传输对象
│   ├── repositories/   # 数据访问层
│   ├── services/       # 业务逻辑层
│   ├── views/          # 视图层（API路由）
│   └── main.py         # 主应用入口
├── tests/              # 测试目录
├── data/               # 数据目录
├── config.yaml         # 配置文件
└── requirements.txt    # 依赖包
```

### 分层架构优势
1. **解耦性**：各层职责分明，降低耦合度
2. **可维护性**：代码组织清晰，易于理解和修改
3. **可测试性**：每层可独立测试
4. **可扩展性**：方便添加新功能和修改现有功能

**版本**: 2.0.0  
**最后更新**: 2025-08-22