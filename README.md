# AI文档测试系统

一个基于AI的文档质量检测系统，可以自动分析文档中的语法错误、逻辑问题和内容完整性。

## ✨ 功能特性

- 🔍 **智能检测**: 基于AI的文档质量分析，支持语法、逻辑、完整性检测
- 📄 **多格式支持**: 支持PDF、Word、Markdown、TXT等主流文档格式
- 📊 **批量处理**: 支持单文件和批量文件上传处理
- 🔄 **实时进度**: 实时显示任务处理进度和状态
- 💬 **问题反馈**: 支持用户对检测结果进行反馈和评审
- 📋 **报告生成**: 自动生成Excel格式的详细检测报告
- 🔐 **用户认证**: 支持OAuth第三方登录（Gitee）
- 📤 **任务分享**: 支持任务结果分享和协作

## 🏗️ 技术架构

### 后端技术栈
- **框架**: FastAPI + Python 3.11+
- **数据库**: SQLite（开发）/ MySQL（生产）
- **AI集成**: 支持OpenAI API和自定义AI服务
- **认证**: JWT + OAuth 2.0
- **文档处理**: PyPDF2, python-docx, chardet

### 前端技术栈
- **框架**: React 18 + TypeScript
- **UI库**: Ant Design
- **状态管理**: Zustand
- **数据获取**: TanStack Query
- **构建工具**: Vite

### 部署技术
- **容器化**: Docker + Docker Compose
- **数据库迁移**: 自研迁移系统
- **反向代理**: Nginx（可选）

## 🚀 快速开始

### 方式一：一键启动（推荐）

```bash
# 克隆项目
git clone <repository-url>
cd ai_docs2

# 一键启动（Windows）
start.bat

# 一键启动（Linux/Mac）
./start.sh
```

### 方式二：手动启动

#### 后端启动
```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 数据库迁移
python migrate.py up

# 启动后端服务
python app/main.py
```

#### 前端启动
```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 方式三：Docker部署

```bash
# 使用Docker Compose启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

## 📁 项目结构

```
ai_docs2/
├── backend/                 # 后端服务
│   ├── app/                # 应用代码
│   │   ├── models/         # 数据模型
│   │   ├── services/       # 业务逻辑
│   │   ├── views/          # API视图
│   │   └── core/           # 核心配置
│   ├── migrations/         # 数据库迁移
│   ├── tests/             # 测试代码
│   └── migrate.py         # 迁移工具
├── frontend/              # 前端应用
│   ├── src/               # 源代码
│   │   ├── pages/         # 页面组件
│   │   ├── components/    # 通用组件
│   │   ├── services/      # API服务
│   │   └── hooks/         # 自定义Hook
│   ├── e2e/               # E2E测试
│   └── public/            # 静态资源
├── docs/                  # 项目文档
│   ├── design/            # 设计文档
│   ├── deployment/        # 部署文档
│   ├── development/       # 开发文档
│   ├── architecture/      # 架构文档
│   ├── user-guide/        # 用户指南
│   └── api/               # API文档
├── docker-compose.yml     # Docker编排
└── README.md              # 项目说明
```

## 🔧 配置说明

### 环境变量配置

创建 `backend/.env` 文件：

```bash
# AI服务配置
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1

# 数据库配置（可选，默认使用SQLite）
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USERNAME=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=ai_doc_test

# OAuth配置
JWT_SECRET_KEY=your_jwt_secret_key
GITEE_CLIENT_ID=your_gitee_client_id
GITEE_CLIENT_SECRET=your_gitee_client_secret

# 服务配置
SERVER_HOST=0.0.0.0
SERVER_PORT=8080
FRONTEND_URL=http://localhost:3000
```

### 配置文件

- `backend/config.yaml`: 主配置文件
- `backend/config.test.yaml`: 测试环境配置
- `backend/config.blue.yaml`: 蓝绿部署配置

## 📖 文档中心

详细文档请查看 [docs/README.md](./docs/README.md)，包含：

- **🎨 设计文档**: 系统设计和架构说明
- **🚀 部署文档**: 各种环境的部署指南
- **🛠️ 开发文档**: 开发指南和问题修复
- **🏗️ 架构文档**: 技术架构和设计决策
- **📖 用户指南**: 功能使用和配置指南
- **🔌 API文档**: 接口说明和测试用例

## 🔧 开发工具

### 数据库迁移
```bash
# 查看迁移状态
python migrate.py status

# 创建新迁移
python migrate.py create "描述"

# 执行迁移
python migrate.py up

# 回滚迁移
python migrate.py down <migration_id>

# 创建备份
python migrate.py backup
```

### 测试命令
```bash
# 后端测试
cd backend && python -m pytest

# 前端单元测试
cd frontend && npm run test

# E2E测试
cd frontend && npm run test:e2e
```

## 🤝 贡献指南

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🔗 相关链接

- [在线Demo](https://demo.example.com)（如果有的话）
- [API文档](./docs/api/)
- [部署指南](./docs/deployment/)
- [开发指南](./docs/development/)

---

**注意**: 请确保在生产环境中设置正确的环境变量和配置文件，特别是数据库连接和API密钥。