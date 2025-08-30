# 🚀 AI Document Testing System - 本地部署指南

本指南提供完整的本地开发和部署流程，支持一键构建和部署操作。

## 📋 目录

- [快速开始](#快速开始)
- [环境要求](#环境要求)  
- [初始化配置](#初始化配置)
- [一键构建](#一键构建)
- [一键部署](#一键部署)
- [Docker部署](#docker部署)
- [服务管理](#服务管理)
- [故障排除](#故障排除)
- [开发指南](#开发指南)

---

## 🎯 快速开始

### 5分钟快速部署

```bash
# 1. 克隆项目
git clone https://github.com/vuhonghoai284-lab/AIDD.git
cd AIDD

# 2. 初始化环境
cp .env.template .env
# 编辑 .env 文件，填入必要配置

# 3. 一键构建和部署
chmod +x build-local.sh deploy-local.sh
./build-local.sh && ./deploy-local.sh

# 4. 访问应用
# 前端: http://localhost:3000
# 后端: http://localhost:8080
```

---

## 💻 环境要求

### 必需软件

| 软件 | 版本要求 | 说明 |
|------|----------|------|
| **Node.js** | ≥ 18.0.0 | 前端构建和运行 |
| **npm** | ≥ 9.0.0 | 包管理器 |
| **Python** | ≥ 3.8.0 | 后端开发语言 |
| **pip** | 最新版本 | Python包管理器 |

### 可选软件

| 软件 | 用途 | 安装建议 |
|------|------|----------|
| **Docker** | 容器化部署 | 推荐用于生产环境 |
| **Redis** | 缓存和队列 | 本地安装或Docker |
| **Git** | 版本控制 | 必需（用于获取源码） |

### 系统检查

运行环境检查脚本：

```bash
# 检查系统要求
./build-local.sh --help  # 查看构建选项
node --version           # 检查Node.js版本
python3 --version        # 检查Python版本
docker --version         # 检查Docker（可选）
```

---

## ⚙️ 初始化配置

### 1. 环境变量配置

```bash
# 复制环境变量模板
cp .env.template .env

# 编辑环境变量（必需）
vim .env  # 或使用你喜欢的编辑器
```

**关键配置项：**

```bash
# 基础端口配置
FRONTEND_PORT=3000
BACKEND_PORT=8080
REDIS_PORT=6379

# 开发模式
NODE_ENV=development
DEPLOY_MODE=dev
LOG_LEVEL=DEBUG

# AI服务配置（开发可用Mock）
MOCK_AI_ENABLED=true
OPENAI_API_KEY=your_api_key  # 如有真实key

# 数据库（默认SQLite）
DATABASE_URL=sqlite:///./data/app.db
```

### 2. 本地配置文件

系统提供了针对本地开发优化的配置：

- `config.local.yaml` - 本地开发专用配置
- `docker-compose.local.yml` - 本地Docker环境
- `.env.template` - 环境变量模板

### 3. 创建必要目录

```bash
# 系统会自动创建，也可手动创建
mkdir -p data/uploads data/temp data/reports logs pids
```

---

## 🔨 一键构建

### 基础构建

```bash
# 开发环境构建（默认）
./build-local.sh

# 生产环境构建
./build-local.sh --type production

# 清理重新构建
./build-local.sh --clean
```

### 高级构建选项

```bash
# 详细输出构建过程
./build-local.sh --verbose

# 跳过测试的快速构建
./build-local.sh --skip-tests

# 只构建前端
./build-local.sh --skip-backend

# 只构建后端  
./build-local.sh --skip-frontend

# 禁用并行构建
./build-local.sh --no-parallel

# 自定义超时时间
./build-local.sh --timeout 300
```

### 构建过程说明

1. **环境检查** - 验证Node.js、Python等必需工具
2. **清理缓存** - 清理之前的构建文件（可选）
3. **前端构建** - 安装依赖、类型检查、打包
4. **后端构建** - 创建虚拟环境、安装依赖、测试
5. **生成报告** - 输出构建结果和统计信息

**构建成功标志：**
- ✅ `frontend/dist` 目录包含前端构建文件
- ✅ `backend/venv` 目录包含Python虚拟环境
- ✅ 构建报告文件生成

---

## 🚀 一键部署

### 基础部署

```bash
# 开发模式部署（默认）
./deploy-local.sh

# 生产模式部署
./deploy-local.sh --mode prod

# 测试模式部署
./deploy-local.sh --mode test
```

### 部署选项

```bash
# 使用Docker部署
./deploy-local.sh --docker

# 跳过构建直接部署（需先构建）
./deploy-local.sh --no-build

# 跳过健康检查
./deploy-local.sh --skip-health-check

# 自定义端口
./deploy-local.sh --frontend-port 3001 --backend-port 8081

# 指定配置文件
./deploy-local.sh --config config.local.yaml
```

### 部署模式对比

| 模式 | 前端服务 | 热重载 | 日志级别 | 适用场景 |
|------|----------|--------|----------|----------|
| **dev** | Vite开发服务器 | ✅ | DEBUG | 开发调试 |
| **prod** | 静态文件服务 | ❌ | INFO | 生产环境 |
| **test** | 静态文件服务 | ❌ | WARNING | 测试验证 |

### 部署过程说明

1. **前置检查** - 验证端口、依赖服务
2. **配置准备** - 生成环境变量和配置文件
3. **服务启动** - 依次启动Redis、后端、前端
4. **健康检查** - 验证服务正常运行
5. **结果展示** - 显示访问地址和管理命令

---

## 🐳 Docker部署

### 快速Docker部署

```bash
# 使用Docker Compose（推荐）
docker-compose -f docker-compose.local.yml up -d

# 或使用部署脚本
./deploy-local.sh --docker
```

### Docker部署配置

```bash
# 自定义环境变量
export FRONTEND_PORT=3000
export BACKEND_PORT=8080
export REDIS_PORT=6379

# 启动所有服务
docker-compose -f docker-compose.local.yml up -d

# 启动特定服务
docker-compose -f docker-compose.local.yml up -d redis backend

# 查看日志
docker-compose -f docker-compose.local.yml logs -f

# 停止服务
docker-compose -f docker-compose.local.yml down
```

### Docker开发工具

```bash
# 启用开发工具容器
docker-compose -f docker-compose.local.yml --profile devtools up -d

# 启用数据库管理界面
docker-compose -f docker-compose.local.yml --profile admin up -d
# 访问 http://localhost:8081 使用Adminer
```

---

## 🔧 服务管理

### 服务状态管理

```bash
# 查看服务状态
./deploy-local.sh status

# 停止所有服务
./deploy-local.sh stop

# 重启所有服务
./deploy-local.sh restart

# 查看服务日志
./deploy-local.sh logs
```

### 手动服务管理

```bash
# 查看运行的进程
ps aux | grep -E "(python|node|redis)"

# 查看端口占用
lsof -i :3000  # 前端
lsof -i :8080  # 后端
lsof -i :6379  # Redis

# 停止特定服务
kill $(cat pids/frontend.pid)
kill $(cat pids/backend.pid)
```

### 日志管理

```bash
# 实时查看所有日志
tail -f logs/frontend.log logs/backend.log

# 查看后端日志
tail -f logs/backend.log

# 查看前端日志
tail -f logs/frontend.log

# 清理日志文件
rm logs/*.log
```

---

## 🌐 访问和测试

### 应用访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| **前端应用** | http://localhost:3000 | 用户界面 |
| **后端API** | http://localhost:8080 | REST API |
| **API文档** | http://localhost:8080/docs | Swagger文档 |
| **健康检查** | http://localhost:8080/api/system/health | 服务状态 |
| **指标监控** | http://localhost:8080/api/system/metrics | 系统指标 |

### 功能测试

```bash
# 测试后端健康状态
curl http://localhost:8080/api/system/health

# 测试API响应
curl http://localhost:8080/api/system/info

# 上传测试文件
curl -X POST -F "file=@test.md" http://localhost:8080/api/tasks/upload
```

### 开发测试

```bash
# 前端开发模式测试
npm run test --prefix frontend

# 后端单元测试
cd backend && python -m pytest tests/

# 端到端测试
npm run test:e2e --prefix frontend
```

---

## 🛠️ 故障排除

### 常见问题解决

#### 1. 端口被占用

**症状**：部署失败，提示端口已被占用

**解决**：
```bash
# 查找占用进程
lsof -i :3000
lsof -i :8080

# 终止占用进程
kill -9 <PID>

# 或使用其他端口
./deploy-local.sh --frontend-port 3001 --backend-port 8081
```

#### 2. 依赖安装失败

**症状**：构建过程中npm或pip安装失败

**解决**：
```bash
# 清理缓存重新构建
./build-local.sh --clean

# 手动安装前端依赖
cd frontend && npm install

# 手动安装后端依赖
cd backend && pip install -r requirements.txt
```

#### 3. 服务启动失败

**症状**：部署后服务无法访问

**解决**：
```bash
# 查看详细日志
./deploy-local.sh logs

# 检查服务状态
./deploy-local.sh status

# 重启服务
./deploy-local.sh restart
```

#### 4. 配置文件错误

**症状**：服务启动时报配置错误

**解决**：
```bash
# 验证YAML语法
python -c "import yaml; yaml.safe_load(open('backend/config.local.yaml'))"

# 重置配置文件
cp .env.template .env
cp backend/config.yaml backend/config.local.yaml
```

### 调试模式

```bash
# 启用详细日志
export LOG_LEVEL=DEBUG
./deploy-local.sh

# 前端开发者工具
# 在浏览器中按F12打开开发者工具

# 后端调试
cd backend
export PYTHONPATH=.
export CONFIG_FILE=config.local.yaml
python -m pdb app/main.py
```

### 性能问题

```bash
# 检查系统资源
top
htop  # 如果安装了

# 检查磁盘空间
df -h

# 检查内存使用
free -h

# 清理临时文件
rm -rf data/temp/* logs/*.log
```

---

## 👨‍💻 开发指南

### 开发环境设置

```bash
# 1. 设置开发模式
export NODE_ENV=development
export LOG_LEVEL=DEBUG

# 2. 启动开发服务
./deploy-local.sh --mode dev

# 3. 开启热重载
# 前端自动重载
# 后端需要重启：./deploy-local.sh restart
```

### 代码修改流程

```bash
# 1. 修改前端代码
# 文件保存后自动重载

# 2. 修改后端代码
./deploy-local.sh stop
./deploy-local.sh

# 3. 修改配置文件
./deploy-local.sh restart
```

### 测试流程

```bash
# 1. 运行前端测试
cd frontend
npm run test
npm run test:coverage

# 2. 运行后端测试
cd backend
python -m pytest tests/ -v

# 3. 运行端到端测试
cd frontend
npm run test:e2e
```

### 数据库管理

```bash
# 查看SQLite数据
sqlite3 data/app.db ".tables"
sqlite3 data/app.db "SELECT * FROM users;"

# 备份数据库
cp data/app.db data/app.db.backup

# 重置数据库
rm data/app.db
./deploy-local.sh restart
```

---

## 📈 性能优化

### 构建优化

```bash
# 并行构建（默认启用）
./build-local.sh --parallel

# 跳过不必要的检查
./build-local.sh --skip-tests

# 生产环境优化
./build-local.sh --type production
```

### 运行时优化

```bash
# 调整工作进程数
export WORKERS=2
./deploy-local.sh --mode prod

# 启用Redis缓存
export REDIS_URL=redis://localhost:6379/0

# 优化内存使用
export NODE_OPTIONS="--max-old-space-size=2048"
```

---

## 🔒 安全注意事项

### 开发环境安全

- ✅ 使用强密码设置JWT密钥
- ✅ 不要在代码中硬编码敏感信息
- ✅ 定期更新依赖包
- ✅ 启用CORS保护

### 生产环境准备

```bash
# 1. 更改默认密钥
export JWT_SECRET_KEY="your-strong-secret-key"

# 2. 禁用调试模式
export DEBUG=false
export LOG_LEVEL=INFO

# 3. 设置允许的主机
export ALLOWED_HOSTS="your-domain.com"

# 4. 启用HTTPS（生产环境）
export ENABLE_HTTPS=true
```

---

## 🆘 获取帮助

### 命令帮助

```bash
# 构建脚本帮助
./build-local.sh --help

# 部署脚本帮助  
./deploy-local.sh --help
```

### 日志查看

```bash
# 查看所有日志
./deploy-local.sh logs

# 查看构建报告
ls -la build-report-*.txt
```

### 社区支持

- 📚 项目文档：查看 `docs/` 目录
- 🐛 问题报告：GitHub Issues
- 💬 讨论交流：GitHub Discussions

---

## 📚 相关文档

- [项目架构说明](CLAUDE.md)
- [GitHub Actions配置](.github/workflows/README.md)
- [Docker部署指南](DOCKER_DEPLOYMENT.md)
- [生产环境部署](PRODUCTION_DEPLOYMENT.md)

---

**🎉 恭喜！你已经完成了本地部署设置。**

如果遇到任何问题，请查看故障排除章节或查看日志文件获取详细错误信息。