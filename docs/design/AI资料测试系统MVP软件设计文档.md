# AI资料自主测试系统 - MVP软件设计文档

## 📋 目录
1. [MVP设计理念](#1-mvp设计理念)
2. [技术栈选择](#2-技术栈选择)
3. [系统架构设计](#3-系统架构设计)
4. [模块化设计](#4-模块化设计)
5. [数据库设计](#5-数据库设计)
6. [API接口设计](#6-api接口设计)
7. [本地AI推理方案](#7-本地ai推理方案)
8. [部署方案](#8-部署方案)

---

## 1. MVP设计理念

### 1.1 设计原则
- 🚀 **快速交付**：MVP功能快速实现和部署
- 🎯 **核心功能**：专注文档质量检测核心价值
- 📈 **可扩展**：为后期微服务拆分预留接口
- 🏠 **本地部署**：完全私有化部署，数据不出本地
- 🔧 **易维护**：简化架构，降低维护复杂度

### 1.2 MVP核心功能范围
✅ **包含功能**：
- 用户登录（SSO集成）
- 文档上传（PDF、Word、Markdown）
- AI文档质量检测（静态分析）
- 问题列表展示和用户反馈
- 基础报告生成和下载
- 系统管理和监控

❌ **暂不包含**：
- 动态检测（MCP+Agent）
- 多租户复杂权限
- 高级AI优化算法
- 分布式文件存储
- 复杂监控告警

---

## 2. 技术栈选择

### 2.1 MVP技术栈对比

| 组件类别 | MVP方案 | 选择理由 | 后期扩展 |
|---------|---------|----------|----------|
| **前端框架** | React 18 + TypeScript + Vite | 快速开发，生态成熟 | 保持不变 |
| **状态管理** | Zustand + TanStack Query | 轻量级，学习成本低 | 可升级Redux |
| **UI组件库** | Ant Design | 组件丰富，开箱即用 | 可定制主题 |
| **后端框架** | FastAPI + Python 3.11 | 开发效率高，类型安全 | 保持不变 |
| **架构模式** | 单体服务 + 模块化 | 简化部署，快速迭代 | 拆分微服务 |
| **数据库** | PostgreSQL 15 | JSON支持，功能强大 | 读写分离 |
| **缓存/队列** | Redis 7 | 多功能，简化技术栈 | 保持不变 |
| **文件存储** | 本地文件系统 | 零配置，快速启动 | 对象存储 |
| **AI推理** | vLLM/SGLang + LangChain | 高性能本地推理 | 模型服务化 |
| **容器化** | Docker + Docker Compose | 简化部署 | Kubernetes |

### 2.2 技术栈架构图

```mermaid
graph TB
    subgraph "前端层"
        A[React 18 + TypeScript]
        B[Ant Design + Zustand]
        C[TanStack Query]
        D[Vite构建工具]
    end

    subgraph "后端单体服务"
        E[FastAPI Gateway]
        F[用户模块]
        G[任务模块]
        H[文件模块]
        I[AI分析模块]
        J[报告模块]
        K[系统模块]
    end

    subgraph "数据存储层"
        L[(PostgreSQL)]
        M[(Redis)]
        N[本地文件存储]
    end

    subgraph "外部AI服务"
        O[AI模型网关]
        P[通用AI API]  
        Q[结构化AI API]
    end

    A --> E
    B --> E
    C --> E
    
    E --> F
    E --> G
    E --> H
    E --> I
    E --> J
    E --> K
    
    F --> L
    G --> L
    G --> M
    H --> N
    I --> O
    J --> L
    
    O --> P
    O --> Q
```

---

## 3. 系统架构设计

### 3.1 整体架构

```mermaid
graph TB
    subgraph "客户端"
        WebApp[Web应用]
        MobileApp[移动端<br/>响应式适配]
    end
    
    subgraph "负载均衡"
        Nginx[Nginx反向代理]
    end
    
    subgraph "后端单体服务"
        Gateway[API网关层]
        Business[业务逻辑层]
        Data[数据访问层]
        
        subgraph "业务模块"
            AuthMod[认证模块]
            TaskMod[任务模块]
            FileMod[文件模块]
            AIMod[AI分析模块]
            ReportMod[报告模块]
        end
    end
    
    subgraph "数据层"
        MainDB[(PostgreSQL<br/>主数据库)]
        Cache[(Redis<br/>缓存/队列)]
        FileStorage[本地文件存储]
    end
    
    subgraph "外部服务"
        SSO[企业SSO]
        AIGateway[AI模型网关]
        AIGeneral[通用AI API]
        AIStructured[结构化AI API]
        Email[邮件服务]
    end

    WebApp --> Nginx
    MobileApp --> Nginx
    Nginx --> Gateway
    Gateway --> Business
    Business --> Data
    
    AuthMod --> SSO
    TaskMod --> Cache
    FileMod --> FileStorage
    AIMod --> AIGateway
    ReportMod --> Email
    
    AIGateway --> AIGeneral
    AIGateway --> AIStructured
    
    Data --> MainDB
    Data --> Cache
```

### 3.2 服务内部架构

```mermaid
graph TD
    subgraph "FastAPI应用"
        Router[路由层<br/>API Routes]
        Middleware[中间件层<br/>Auth/CORS/Log]
        Service[服务层<br/>Business Logic]
        Repository[仓储层<br/>Data Access]
        Model[模型层<br/>Domain Models]
    end
    
    subgraph "外部适配器"
        AIAdapter[AI模型适配器]
        SSOAdapter[SSO适配器] 
        FileAdapter[文件存储适配器]
        EmailAdapter[邮件服务适配器]
    end
    
    subgraph "核心组件"
        TaskManager[任务管理器]
        AIEngine[AI分析引擎]
        ReportGenerator[报告生成器]
        QueueProcessor[队列处理器]
    end

    Router --> Middleware
    Middleware --> Service
    Service --> Repository
    Service --> TaskManager
    Service --> AIEngine
    Service --> ReportGenerator
    
    TaskManager --> QueueProcessor
    AIEngine --> AIAdapter
    Service --> SSOAdapter
    Service --> FileAdapter
    Service --> EmailAdapter
    
    Repository --> Model
```

**架构说明**：

🔧 **分层设计**：
- **路由层**：处理HTTP请求和响应
- **中间件层**：处理横切关注点（认证、日志、CORS）
- **服务层**：核心业务逻辑，协调各个模块
- **仓储层**：数据访问抽象，隔离数据库细节
- **模型层**：领域模型和数据传输对象

🔌 **适配器模式**：
- **AI适配器**：统一不同AI服务的接口
- **存储适配器**：抽象文件存储操作
- **外部服务适配器**：集成第三方服务

⚙️ **核心组件**：
- **任务管理器**：处理任务生命周期
- **AI分析引擎**：执行文档质量分析
- **报告生成器**：生成和导出报告
- **队列处理器**：处理异步任务

---

## 4. 模块化设计

### 4.1 目录结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI应用入口
│   ├── config.py              # 配置管理
│   ├── dependencies.py        # 依赖注入
│   │
│   ├── api/                   # API路由层
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py        # 认证接口
│   │   │   ├── tasks.py       # 任务接口  
│   │   │   ├── files.py       # 文件接口
│   │   │   ├── analysis.py    # 分析接口
│   │   │   ├── reports.py     # 报告接口
│   │   │   └── system.py      # 系统接口
│   │   └── middleware.py      # 中间件
│   │
│   ├── services/              # 业务服务层
│   │   ├── __init__.py
│   │   ├── auth_service.py    # 认证服务
│   │   ├── task_service.py    # 任务服务
│   │   ├── file_service.py    # 文件服务
│   │   ├── ai_service.py      # AI分析服务
│   │   └── report_service.py  # 报告服务
│   │
│   ├── repositories/          # 数据访问层
│   │   ├── __init__.py
│   │   ├── base.py           # 基础仓储
│   │   ├── user_repo.py      # 用户仓储
│   │   ├── task_repo.py      # 任务仓储
│   │   ├── file_repo.py      # 文件仓储
│   │   └── analysis_repo.py  # 分析结果仓储
│   │
│   ├── models/               # 数据模型
│   │   ├── __init__.py
│   │   ├── database.py       # 数据库模型
│   │   ├── schemas.py        # Pydantic模型
│   │   └── enums.py          # 枚举定义
│   │
│   ├── core/                 # 核心组件
│   │   ├── __init__.py
│   │   ├── task_manager.py   # 任务管理器
│   │   ├── ai_engine.py      # AI分析引擎
│   │   ├── report_generator.py # 报告生成器
│   │   └── queue_processor.py  # 队列处理器
│   │
│   ├── adapters/             # 外部适配器
│   │   ├── __init__.py
│   │   ├── ai_adapter.py     # AI模型适配器
│   │   ├── sso_adapter.py    # SSO适配器
│   │   ├── file_adapter.py   # 文件适配器
│   │   └── email_adapter.py  # 邮件适配器
│   │
│   └── utils/                # 工具函数
│       ├── __init__.py
│       ├── security.py       # 安全工具
│       ├── helpers.py        # 辅助函数
│       └── exceptions.py     # 异常定义
│
├── tests/                    # 测试用例
├── migrations/               # 数据库迁移
├── scripts/                  # 部署脚本
├── requirements.txt          # Python依赖
└── Dockerfile               # 容器配置
```

### 4.2 模块依赖关系

```mermaid
graph TD
    A[API路由层] --> B[业务服务层]
    B --> C[数据访问层]
    B --> D[核心组件]
    B --> E[外部适配器]
    C --> F[数据模型]
    D --> E
    D --> F
    
    subgraph "依赖方向"
        G[高层模块] --> H[低层模块]
        I[抽象接口] --> J[具体实现]
    end
```

**设计原则**：
- 🔄 **依赖倒置**：高层模块不依赖低层模块，都依赖抽象
- 🔒 **单一职责**：每个模块只负责一个业务领域
- 🔗 **接口隔离**：使用抽象接口定义模块间合约
- 📦 **开闭原则**：对扩展开放，对修改关闭

---

## 5. 数据库设计

### 5.1 简化的数据模型

```mermaid
erDiagram
    USERS {
        uuid user_id PK
        varchar username
        varchar email
        varchar display_name
        varchar sso_provider
        varchar sso_user_id
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    TASKS {
        uuid task_id PK
        uuid user_id FK
        varchar task_name
        varchar task_type
        enum status
        integer progress
        jsonb config
        timestamp created_at
        timestamp updated_at
        timestamp completed_at
    }

    FILES {
        uuid file_id PK
        uuid task_id FK
        varchar original_name
        varchar file_path
        bigint file_size
        varchar file_type
        varchar checksum
        enum status
        timestamp created_at
    }

    ANALYSIS_RESULTS {
        uuid analysis_id PK
        uuid task_id FK
        uuid file_id FK
        varchar model_name
        jsonb analysis_data
        decimal confidence_score
        enum result_type
        timestamp created_at
    }

    ISSUES {
        uuid issue_id PK
        uuid analysis_id FK
        varchar issue_type
        enum severity
        varchar title
        text description
        jsonb location_info
        text suggestion
        timestamp created_at
    }

    USER_FEEDBACK {
        uuid feedback_id PK
        uuid issue_id FK
        uuid user_id FK
        enum action_type
        text feedback_text
        integer rating
        timestamp created_at
    }

    REPORTS {
        uuid report_id PK
        uuid task_id FK
        varchar report_type
        jsonb content
        varchar file_path
        timestamp created_at
    }

    USERS ||--o{ TASKS : "creates"
    TASKS ||--o{ FILES : "contains"
    TASKS ||--o{ ANALYSIS_RESULTS : "has"
    FILES ||--o{ ANALYSIS_RESULTS : "analyzed"
    ANALYSIS_RESULTS ||--o{ ISSUES : "identifies"
    ISSUES ||--o{ USER_FEEDBACK : "receives"
    TASKS ||--o{ REPORTS : "generates"
    USERS ||--o{ USER_FEEDBACK : "provides"
```

### 5.2 Redis数据结构设计

#### Redis数据类型和用途

| 数据类型 | 键名模式 | 用途说明 | 过期时间 | 示例 |
|----------|----------|----------|----------|------|
| **Hash** | `session:user:{user_id}` | 用户会话信息存储 | 30分钟 | `session:user:123` |
| **List** | `queue:tasks` | AI分析任务队列 | 持久化 | `queue:tasks` |
| **String** | `cache:analysis:{file_hash}` | 文件分析结果缓存 | 24小时 | `cache:analysis:abc123` |
| **Hash** | `status:task:{task_id}` | 任务实时状态 | 任务完成时 | `status:task:456` |
| **String** | `ratelimit:{user_id}` | API调用限流计数 | 1分钟 | `ratelimit:user:123` |
| **Hash** | `upload:progress:{file_id}` | 文件上传进度 | 1小时 | `upload:progress:789` |
| **Set** | `active:users` | 在线用户集合 | 1小时 | `active:users` |
| **ZSet** | `task:priority` | 任务优先级队列 | 持久化 | `task:priority` |

#### 数据结构详细设计

**会话存储结构**：
```redis
session:user:123 = {
  "user_id": "123",
  "username": "admin",
  "email": "admin@example.com",
  "login_time": "2024-01-01T10:00:00Z",
  "permissions": ["read", "write"]
}
TTL: 1800 (30分钟)
```

**任务队列结构**：
```redis
queue:tasks = [
  "{\"task_id\": \"456\", \"priority\": 1, \"created_at\": \"2024-01-01T10:00:00Z\"}",
  "{\"task_id\": \"457\", \"priority\": 2, \"created_at\": \"2024-01-01T10:01:00Z\"}"
]
```

**分析缓存结构**：
```redis
cache:analysis:abc123 = "{\"result\": {\"issues\": [], \"score\": 0.85}, \"model\": \"qwen-7b\"}"
TTL: 86400 (24小时)
```

**任务状态结构**：
```redis
status:task:456 = {
  "status": "processing",
  "progress": 65,
  "current_step": "ai_analysis",
  "updated_at": "2024-01-01T10:30:00Z"
}
TTL: 动态设置，任务完成时删除
```

**限流计数结构**：
```redis
ratelimit:user:123 = "45"  # 当前分钟内的请求次数
TTL: 60 (1分钟)
```

---

## 6. API接口设计

### 6.1 RESTful API接口列表

**基础路径**: `/api/v1`

#### 认证模块 (`/api/v1/auth`)

| 方法 | 路径 | 功能描述 | 请求参数 | 响应说明 |
|------|------|----------|----------|----------|
| POST | `/login` | SSO登录 | `{redirect_url, state}` | 返回JWT令牌 |
| POST | `/logout` | 用户登出 | `Authorization: Bearer <token>` | 登出成功确认 |
| GET | `/profile` | 获取用户信息 | `Authorization: Bearer <token>` | 用户基本信息 |
| PUT | `/profile` | 更新用户信息 | `{display_name, avatar_url}` | 更新成功确认 |
| POST | `/refresh` | 刷新令牌 | `{refresh_token}` | 新的访问令牌 |

#### 任务模块 (`/api/v1/tasks`)

| 方法 | 路径 | 功能描述 | 请求参数 | 响应说明 |
|------|------|----------|----------|----------|
| GET | `/` | 获取任务列表 | `?page=1&size=20&status=all` | 分页任务列表 |
| POST | `/` | 创建新任务 | `{task_name, task_type, description, config}` | 新建任务信息 |
| GET | `/{id}` | 获取任务详情 | 路径参数: `task_id` | 任务详细信息 |
| PUT | `/{id}` | 更新任务信息 | `{task_name, description}` | 更新成功确认 |
| DELETE | `/{id}` | 删除任务 | 路径参数: `task_id` | 删除成功确认 |
| POST | `/{id}/start` | 启动任务 | 路径参数: `task_id` | 启动状态确认 |
| POST | `/{id}/stop` | 停止任务 | 路径参数: `task_id` | 停止状态确认 |
| GET | `/{id}/progress` | 获取任务进度 | 路径参数: `task_id` | 进度百分比和状态 |

#### 文件模块 (`/api/v1/files`)

| 方法 | 路径 | 功能描述 | 请求参数 | 响应说明 |
|------|------|----------|----------|----------|
| POST | `/upload` | 文件上传 | `multipart/form-data: files[], task_id` | 上传文件列表 |
| GET | `/{id}` | 获取文件信息 | 路径参数: `file_id` | 文件元数据信息 |
| GET | `/{id}/download` | 下载文件 | 路径参数: `file_id` | 文件二进制流 |
| DELETE | `/{id}` | 删除文件 | 路径参数: `file_id` | 删除成功确认 |
| POST | `/{id}/parse` | 解析文件内容 | 路径参数: `file_id` | 解析后的文本内容 |
| GET | `/upload/progress/{id}` | 上传进度 | 路径参数: `file_id` | 上传进度百分比 |

#### 分析模块 (`/api/v1/analysis`)

| 方法 | 路径 | 功能描述 | 请求参数 | 响应说明 |
|------|------|----------|----------|----------|
| POST | `/start` | 开始AI分析 | `{task_id, analysis_type, config}` | 分析任务ID |
| GET | `/{id}/status` | 分析状态 | 路径参数: `analysis_id` | 分析进度和状态 |
| GET | `/{id}/results` | 分析结果 | 路径参数: `analysis_id` | 分析结果详情 |
| GET | `/{id}/issues` | 获取问题列表 | 路径参数: `analysis_id` | 识别的问题列表 |
| POST | `/{id}/reanalyze` | 重新分析 | 路径参数: `analysis_id` | 重新分析确认 |
| GET | `/models` | 获取可用模型 | 无 | 可用AI模型列表 |

#### 报告模块 (`/api/v1/reports`)

| 方法 | 路径 | 功能描述 | 请求参数 | 响应说明 |
|------|------|----------|----------|----------|
| GET | `/{taskId}` | 获取报告内容 | 路径参数: `task_id` | 报告结构化数据 |
| POST | `/{taskId}/feedback` | 提交用户反馈 | `{issue_id, action_type, feedback_text, rating}` | 反馈提交确认 |
| POST | `/{taskId}/generate` | 生成最终报告 | 路径参数: `task_id` | 报告生成状态 |
| GET | `/{taskId}/download` | 下载报告 | 路径参数: `task_id` | Excel文件流 |
| GET | `/{taskId}/history` | 报告历史版本 | 路径参数: `task_id` | 历史版本列表 |

#### 系统模块 (`/api/v1/system`)

| 方法 | 路径 | 功能描述 | 请求参数 | 响应说明 |
|------|------|----------|----------|----------|
| GET | `/health` | 健康检查 | 无 | 服务健康状态 |
| GET | `/metrics` | 系统指标 | 无 | 性能监控数据 |
| GET | `/config` | 系统配置 | 无 | 配置信息（脱敏） |
| GET | `/version` | 版本信息 | 无 | 系统版本号 |

### 6.2 核心API设计

#### 6.2.1 任务管理API
```python
# POST /api/v1/tasks - 创建任务
{
    "task_name": "文档质量检测",
    "task_type": "quality_check",
    "description": "检测产品文档的质量问题",
    "config": {
        "check_types": ["grammar", "logic", "clarity"],
        "ai_model": "gpt-3.5-turbo"
    }
}

# Response
{
    "code": 200,
    "message": "Task created successfully",
    "data": {
        "task_id": "uuid",
        "status": "created",
        "created_at": "2024-01-01T00:00:00Z"
    }
}
```

#### 6.2.2 文件上传API
```python
# POST /api/v1/files/upload
Content-Type: multipart/form-data

{
    "task_id": "uuid",
    "files": [file1, file2, ...],
    "metadata": {
        "upload_source": "web",
        "batch_name": "batch_001"
    }
}
```

#### 6.2.3 AI分析API
```python
# POST /api/v1/analysis/start
{
    "task_id": "uuid",
    "analysis_type": "static",
    "config": {
        "model_preference": "cost_effective",
        "quality_threshold": 0.8
    }
}
```

---

## 7. AI模型服务集成

### 7.1 外部AI服务架构

系统采用外部AI模型API服务，由专门团队提供和维护，简化了部署复杂度并确保模型性能。

### 7.2 AI服务集成架构

```mermaid
graph TD
    subgraph "AI引擎层"
        AIRouter[AI路由器]
        TaskAnalyzer[任务分析器]
        ResultMerger[结果合并器]
        APIAdapter[API适配器]
    end
    
    subgraph "外部AI服务"
        GeneralAPI[通用AI API]
        StructuredAPI[结构化AI API]
        ModelGateway[模型网关]
    end
    
    subgraph "服务管理"
        LoadBalancer[负载均衡]
        RateLimiter[限流控制]
        HealthChecker[健康检查]
    end

    AIRouter --> TaskAnalyzer
    TaskAnalyzer --> APIAdapter
    APIAdapter --> LoadBalancer
    
    LoadBalancer --> GeneralAPI
    LoadBalancer --> StructuredAPI
    LoadBalancer --> ModelGateway
    
    RateLimiter --> LoadBalancer
    HealthChecker --> GeneralAPI
    HealthChecker --> StructuredAPI
    
    GeneralAPI --> ResultMerger
    StructuredAPI --> ResultMerger
```

### 7.3 API调用策略

```python
class AIServiceClient:
    """外部AI服务客户端"""
    
    def __init__(self):
        self.services = {
            "general": {
                "endpoint": "http://ai-model-gateway/api/v1/general",
                "models": ["qwen2.5-14b", "qwen2.5-32b", "glm-4-9b"],
                "best_for": ["chinese_analysis", "document_processing", "general_text"]
            },
            "structured": {
                "endpoint": "http://ai-model-gateway/api/v1/structured", 
                "models": ["qwen2.5-32b", "deepseek-v2.5"],
                "best_for": ["structured_analysis", "complex_reasoning", "chinese_classification"]
            }
        }
    
    def select_service(self, task_type: str, content_length: int) -> str:
        """根据任务类型选择AI服务"""
        if task_type in ["document_analysis", "quality_check"]:
            # 文档分析类任务使用结构化服务
            return "structured"
        elif content_length > 8000:
            # 长文本使用通用服务的高效处理
            return "general"
        else:
            # 默认使用通用服务
            return "general"
    
    async def analyze_document(self, content: str, analysis_type: str):
        """文档分析入口"""
        service = self.select_service(analysis_type, len(content))
        
        if service == "structured":
            return await self._structured_analysis(content, analysis_type)
        else:
            return await self._general_analysis(content, analysis_type)
    
    async def _call_ai_api(self, endpoint: str, payload: dict):
        """统一的API调用方法"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                endpoint,
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30.0
            )
            return response.json()
```

### 7.4 AI服务接口设计

系统通过标准化的API接口与外部AI服务集成，确保服务的可靠性和可扩展性。

**主要接口类型**：
- **通用AI API**：处理常规文档分析和文本处理
- **结构化AI API**：专门处理复杂推理和结构化分析任务
- **模型网关**：提供模型选择和负载均衡功能

**接口特性**：
- 🔄 **自动重试**：网络异常时自动重试机制
- 📊 **负载均衡**：智能分发请求到最优服务节点
- 🛡️ **限流保护**：防止服务过载的限流机制
- 📈 **监控告警**：实时监控API调用状态和性能

### 7.5 服务集成优势

🎯 **专业运维**：
- 🔧 **专业团队**：由专门的AI团队负责模型维护和优化
- 📈 **性能保障**：专业的模型调优和性能监控
- 🔄 **持续更新**：模型版本的持续升级和改进
- 🛠️ **技术支持**：专业的技术支持和问题解决

⚡ **部署简化**：
- 🚀 **快速启动**：无需复杂的模型部署配置
- 💻 **硬件节省**：不需要高性能GPU硬件投入
- 🔧 **运维简化**：减少AI模型相关的运维工作量
- 📦 **开箱即用**：API调用即可使用最新AI能力

🔒 **服务可靠性**：
- 🛡️ **高可用性**：专业团队保障服务稳定性
- 📊 **SLA保证**：明确的服务等级协议
- 🔄 **故障恢复**：快速的故障检测和恢复机制
- 📈 **扩展性**：根据业务需求弹性扩展

---

## 8. 部署方案

### 8.1 Docker Compose部署

```yaml
version: '3.8'
services:
  # 前端服务
  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
    environment:
      - REACT_APP_API_BASE_URL=http://backend:8000

  # 后端API服务
  backend:
    build: ./backend
    ports:
      - "8080:8000"
    depends_on:
      - postgres
      - redis
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/aitest
      - REDIS_URL=redis://redis:6379
      - AI_API_GATEWAY_URL=http://ai-model-gateway/api/v1
      - AI_API_KEY=${AI_API_KEY}
    volumes:
      - ./data/files:/app/data/files
      - ./data/reports:/app/data/reports

  # PostgreSQL数据库
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=aitest
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql

  # Redis缓存和队列
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data


  # Nginx反向代理
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - frontend
      - backend

volumes:
  postgres_data:
  redis_data:
```

### 8.2 环境配置

```python
# config.py - 环境配置
from pydantic import BaseSettings

class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "AI Document Testing System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # 数据库配置
    DATABASE_URL: str = "postgresql://user:pass@localhost:5432/aitest"
    
    # Redis配置
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_QUEUE_NAME: str = "ai_analysis_tasks"
    
    # 文件存储配置
    FILE_STORAGE_PATH: str = "./data/files"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_FILE_TYPES: list = [".pdf", ".docx", ".md"]
    
    # AI服务配置
    AI_API_GATEWAY_URL: str = "http://ai-model-gateway/api/v1"
    AI_API_KEY: str = ""
    AI_API_TIMEOUT: int = 30
    
    # AI调用参数
    MAX_TOKENS: int = 4096
    TEMPERATURE: float = 0.7
    TOP_P: float = 0.9
    MAX_CONCURRENT_REQUESTS: int = 10
    
    # 安全配置
    SECRET_KEY: str = "your-secret-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 30
    
    # SSO配置
    SSO_PROVIDER_URL: str = ""
    SSO_CLIENT_ID: str = ""
    SSO_CLIENT_SECRET: str = ""

    class Config:
        env_file = ".env"
```

### 8.3 AI服务配置

在部署前需要配置AI服务访问：

```bash
# 创建环境配置文件
cat > .env << EOF
# AI服务配置
AI_API_GATEWAY_URL=http://ai-model-gateway/api/v1
AI_API_KEY=your-ai-api-key-here
AI_API_TIMEOUT=30

# 数据库配置  
DATABASE_URL=postgresql://user:pass@postgres:5432/aitest
REDIS_URL=redis://redis:6379

# 应用配置
SECRET_KEY=your-secret-key
DEBUG=false
EOF
```

**AI服务要求**：
- **API网关地址**：由AI团队提供的统一网关地址
- **API密钥**：用于身份验证的访问密钥
- **服务可用性**：要求99.9%以上的服务可用性
- **响应时间**：平均响应时间 < 2秒

**硬件需求**（仅应用服务）：
- **CPU**：4核心以上
- **内存**：8GB RAM以上
- **存储**：50GB磁盘空间（用于文件存储）
- **网络**：稳定的网络连接到AI服务

### 8.4 一键部署脚本

```bash
#!/bin/bash
# deploy.sh - 一键部署脚本

set -e

echo "🚀 开始部署AI文档测试系统..."

# 1. 检查依赖
echo "📋 检查系统依赖..."
command -v docker >/dev/null 2>&1 || { echo "请先安装Docker"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "请先安装Docker Compose"; exit 1; }

# 2. 创建必要目录
echo "📁 创建数据目录..."
mkdir -p data/{files,reports,backups}
mkdir -p logs

# 3. 生成配置文件
echo "⚙️ 生成配置文件..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "请编辑 .env 文件配置相关参数"
fi

# 4. 构建镜像
echo "🔨 构建Docker镜像..."
docker-compose build

# 5. 启动服务
echo "🚀 启动服务..."
docker-compose up -d

# 6. 等待服务就绪
echo "⏳ 等待服务启动..."
sleep 30

# 7. 初始化数据库
echo "💾 初始化数据库..."
docker-compose exec backend python -m alembic upgrade head

# 8. 配置AI服务
echo "🤖 配置AI服务访问..."
if [ -z "$AI_API_KEY" ]; then
    echo "⚠️  请设置AI_API_KEY环境变量"
    echo "export AI_API_KEY=your-api-key"
    exit 1
fi

# 9. 等待服务启动
echo "⏳ 等待应用服务启动..."
sleep 30

# 10. 健康检查
echo "🔍 服务健康检查..."
curl -f http://localhost:8080/api/v1/system/health || exit 1

# 11. AI服务连通性检查
echo "🤖 AI服务连通性检查..."
curl -f "$AI_API_GATEWAY_URL/health" -H "Authorization: Bearer $AI_API_KEY" || echo "⚠️  AI服务连接异常，请联系AI团队"

echo "✅ 部署完成！"
echo "🌐 前端地址: http://localhost:3000"
echo "🔗 API地址: http://localhost:8080" 
echo "📊 API文档: http://localhost:8080/docs"
echo "🤖 AI服务网关: $AI_API_GATEWAY_URL"
```

---

## 📊 总结

### 🎯 MVP设计优势
1. **快速部署**：无需AI模型部署，专注业务逻辑开发
2. **专业AI服务**：由专门团队提供高质量AI模型服务
3. **易于维护**：单体架构+模块化设计+清晰分层
4. **可扩展性**：预留微服务拆分接口+云原生就绪

### 🔧 关键技术选择
- **后端**：FastAPI + PostgreSQL + Redis（简单可靠）
- **前端**：React 18 + Ant Design（快速开发）
- **AI集成**：外部AI API服务（专业运维保障）
- **部署**：Docker Compose（一键部署）

### 🚀 核心特性
- **AI服务集成**：通过API调用专业AI团队提供的模型服务
- **智能路由**：根据任务类型选择最适合的AI服务接口
- **专业运维**：AI模型由专门团队负责维护和优化
- **开箱即用**：无需复杂的AI模型部署配置
- **成本可控**：按需调用，避免高额硬件投入

### 📈 后期扩展路径
1. **服务拆分**：按模块拆分为微服务
2. **性能优化**：引入缓存+CDN+负载均衡
3. **功能增强**：动态检测+多租户+高级分析
4. **AI升级**：随AI团队模型升级自动获得新能力

本MVP设计专注于业务逻辑实现，将AI模型服务交由专业团队负责，确保系统的快速交付和稳定运行。
