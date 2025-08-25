# AI文档测试系统

一个基于AI的文档质量检测系统，可以自动分析文档中的语法错误、逻辑问题和内容完整性。

## 功能特性

- ✅ 支持多种文档格式（PDF、Word、Markdown）
- ✅ 批量文件上传
- ✅ AI智能检测（语法、逻辑、完整性）
- ✅ 问题反馈和评审
- ✅ Excel报告生成和下载
- ✅ 实时进度显示

## 技术栈

- **后端**: FastAPI + SQLite/MySQL + Python 3.8+
- **前端**: React + TypeScript + Ant Design
- **AI服务**: vLLM（需自行部署）

## 快速开始

### 环境要求

- Python 3.8+
- Node.js 14+
- npm 或 yarn

### 安装和启动

#### Windows用户
```bash
# 克隆或下载项目
cd ai_doc_test

# 运行启动脚本
start.bat
```

#### Linux/Mac用户
```bash
# 克隆或下载项目
cd ai_doc_test

# 添加执行权限
chmod +x start.sh

# 运行启动脚本
./start.sh
```

### 手动启动

#### 1. 启动后端服务
```bash
cd backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
python main.py
```

#### 2. 启动前端服务
```bash
cd frontend

# 设置npm镜像源（可选，加速下载）
npm config set registry https://mirrors.huaweicloud.com/repository/npm/

# 安装依赖
npm install

# 启动服务
npm start
```

## 使用说明

1. 打开浏览器访问 http://localhost:3000
2. 点击"创建任务"上传文档文件
3. 等待AI处理完成
4. 查看检测结果并提供反馈
5. 下载Excel格式的测试报告

## 系统架构

```
ai_doc_test/
├── backend/                # 后端服务
│   ├── main.py            # FastAPI主应用
│   ├── database.py        # 数据库模型
│   ├── file_parser.py     # 文件解析器
│   ├── ai_service.py      # AI服务封装
│   ├── task_processor.py  # 任务处理器
│   ├── report_generator.py # 报告生成器
│   └── config.yaml        # 配置文件
├── frontend/              # 前端应用
│   ├── src/
│   │   ├── pages/        # 页面组件
│   │   ├── api.ts        # API封装
│   │   └── types.ts      # 类型定义
│   └── package.json
├── data/                  # 数据目录
│   ├── uploads/          # 上传文件
│   └── reports/          # 生成的报告
└── test_document.md      # 测试文档

```

## API文档

启动后端服务后，访问 http://localhost:8080/docs 查看完整的API文档。

### 主要接口

- `POST /api/tasks` - 创建任务
- `GET /api/tasks` - 获取任务列表
- `GET /api/tasks/{id}` - 获取任务详情
- `DELETE /api/tasks/{id}` - 删除任务
- `PUT /api/issues/{id}/feedback` - 提交问题反馈
- `GET /api/tasks/{id}/report` - 下载报告

## 配置说明

### 数据库配置

系统支持SQLite和MySQL两种数据库。编辑 `backend/config.yaml` 文件：

#### SQLite配置（默认）
```yaml
# 数据库配置
database:
  type: "sqlite"
  sqlite:
    path: "./data/app.db"
```

#### MySQL配置
```yaml
# 数据库配置
database:
  type: "mysql"
  mysql:
    host: "localhost"
    port: 3306
    username: "root"
    password: "your_password"
    database: "ai_doc_test"
    charset: "utf8mb4"
    # 连接池配置
    pool:
      pool_size: 5
      max_overflow: 10
      pool_timeout: 30
      pool_recycle: 3600
      pool_pre_ping: true
```

#### 通过环境变量配置MySQL
```yaml
database:
  type: "mysql"
  mysql:
    host: "${MYSQL_HOST:localhost}"
    port: "${MYSQL_PORT:3306}"
    username: "${MYSQL_USERNAME:root}"
    password: "${MYSQL_PASSWORD}"
    database: "${MYSQL_DATABASE:ai_doc_test}"
    charset: "utf8mb4"
```

对应的环境变量：
```bash
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USERNAME=root
export MYSQL_PASSWORD=your_password
export MYSQL_DATABASE=ai_doc_test
```

### 其他配置

```yaml
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

# 文件设置  
file_settings:
  max_file_size: 10485760  # 10MB
  allowed_extensions:
    - pdf
    - docx
    - md
    - txt

# 目录配置
directories:
  upload_dir: ./data/uploads
  report_dir: ./data/reports
  log_dir: ./data/logs
  temp_dir: ./data/temp
```

## 注意事项

1. **AI服务**: 当前版本使用模拟的AI返回数据。实际使用时需要部署vLLM服务并配置正确的API地址。
2. **文件大小**: 默认限制为10MB，可在配置文件中修改。
3. **并发处理**: 系统支持同时处理多个任务。
4. **数据存储**: 默认使用SQLite数据库，适合测试和小规模使用。生产环境推荐使用MySQL数据库。

## 常见问题

**Q: 为什么AI检测结果都是一样的？**
A: 当前使用模拟数据，实际部署需要配置真实的AI服务。

**Q: 如何修改文件大小限制？**
A: 编辑 `backend/config.yaml` 中的 `max_file_size` 值。

**Q: 支持哪些文件格式？**
A: 目前支持 PDF、Word (.docx) 和 Markdown (.md) 格式。

## License

MIT