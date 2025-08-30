# AI文档测试系统 - 部署配置加载方式

## 📋 配置架构概述

本系统采用**分层配置架构**，确保开发和生产环境的一致性：

```
🏗️ 构建阶段（镜像构建）
├── 基础配置和依赖
└── 不包含敏感信息

🚀 部署阶段（运行时）
├── 环境变量 (.env)
├── 配置文件 (config.yaml)
└── 动态配置加载
```

## 🔧 配置加载优先级

### 后端配置优先级（高到低）
1. **环境变量** - 运行时直接注入
2. **配置文件** - config.yaml（支持环境变量插值）
3. **默认值** - 代码中的fallback值

### 前端配置优先级（高到低）
1. **构建时环境变量** - VITE_* 变量
2. **运行时检测** - 基于window.location自动适配
3. **默认配置** - 内置默认值

## 📁 配置文件结构

### 1. 环境变量文件 (.env)
```bash
# 应用基础配置
VERSION=v2.0.0
ENVIRONMENT=production

# 服务端口
FRONTEND_PORT=3000
BACKEND_PORT=8080

# 数据库配置
DATABASE_TYPE=postgresql
POSTGRES_HOST=db.example.com
POSTGRES_PORT=5432
POSTGRES_USER=aidd_user
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=aidd_production

# Redis配置
REDIS_HOST=redis.example.com
REDIS_PORT=6379
REDIS_DATABASE=0

# AI服务配置
OPENAI_API_KEY=sk-your-openai-key
BAIDU_API_KEY=your-baidu-key
DEEPSEEK_API_KEY=your-deepseek-key

# OAuth配置
OAUTH_CLIENT_ID=your-oauth-client-id
OAUTH_CLIENT_SECRET=your-oauth-client-secret
FRONTEND_DOMAIN=https://aidd.example.com

# 安全配置
JWT_SECRET_KEY=your-super-secure-jwt-key

# 数据路径配置
CONFIG_PATH=./config.yaml
DATA_PATH=./data
LOG_PATH=./logs
```

### 2. 应用配置文件 (config.yaml)
```yaml
# 服务器配置 - 支持环境变量插值
server:
  host: "0.0.0.0"
  port: ${SERVER_PORT:8000}
  debug: ${DEBUG:false}
  workers: ${WORKERS:4}
  external_host: ${EXTERNAL_HOST:localhost}
  external_port: ${EXTERNAL_PORT:8080}
  external_protocol: ${EXTERNAL_PROTOCOL:http}

# 数据库配置
database:
  type: ${DATABASE_TYPE:postgresql}
  postgresql:
    host: ${POSTGRES_HOST:localhost}
    port: ${POSTGRES_PORT:5432}
    username: ${POSTGRES_USER:aidd}
    password: ${POSTGRES_PASSWORD}
    database: ${POSTGRES_DB:aidd_db}

# 缓存配置
cache:
  strategy: ${CACHE_STRATEGY:redis}
  redis:
    host: ${REDIS_HOST:localhost}
    port: ${REDIS_PORT:6379}
    password: ${REDIS_PASSWORD:}
    database: ${REDIS_DATABASE:0}

# AI模型配置
ai_models:
  default_index: 0
  models:
    - label: "GPT-4o Mini (快速)"
      provider: "openai"
      config:
        api_key: ${OPENAI_API_KEY}
        model: "gpt-4o-mini"
    - label: "Baidu Ernie Speed (官方)"
      provider: "BaiDu"
      config:
        api_key: ${BAIDU_API_KEY}
        model: "ernie-speed-pro-128k"

# JWT配置
jwt:
  secret_key: ${JWT_SECRET_KEY}
  algorithm: "HS256"
  access_token_expire_minutes: 30

# 第三方登录配置
third_party_auth:
  provider_type: "gitee"
  client_id: ${OAUTH_CLIENT_ID}
  client_secret: ${OAUTH_CLIENT_SECRET}
  frontend_domain: ${FRONTEND_DOMAIN}
  scope: "user_info"
```

## 🐳 Docker部署配置

### 1. Docker Compose配置
```yaml
version: '3.8'

services:
  backend:
    image: ${REGISTRY}/backend:${VERSION}
    container_name: aidd-backend
    restart: unless-stopped
    ports:
      - "${BACKEND_PORT:-8080}:8000"
    environment:
      # 传递运行时环境变量
      - CONFIG_FILE=${CONFIG_FILE:-config.yaml}
      - WAIT_FOR_DB=${WAIT_FOR_DB:-true}
      - RUN_MIGRATIONS=${RUN_MIGRATIONS:-true}
    env_file:
      - .env  # 加载环境变量文件
    volumes:
      # 外部配置文件挂载
      - ${CONFIG_PATH:-./config.yaml}:/app/config.yaml:ro
      - ${DATA_PATH:-./data}:/app/data
      - ${LOG_PATH:-./logs}:/app/logs
    depends_on:
      - redis
      - postgres
    networks:
      - aidd-network

  frontend:
    image: ${REGISTRY}/frontend:${VERSION}
    container_name: aidd-frontend
    restart: unless-stopped
    ports:
      - "${FRONTEND_PORT:-3000}:80"
    environment:
      # 前端运行时环境变量（可选）
      - BACKEND_URL=${EXTERNAL_PROTOCOL:-http}://${EXTERNAL_HOST:-localhost}:${BACKEND_PORT:-8080}
    depends_on:
      - backend
    networks:
      - aidd-network

  postgres:
    image: postgres:15-alpine
    container_name: aidd-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - aidd-network

  redis:
    image: redis:7-alpine
    container_name: aidd-redis
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - aidd-network

volumes:
  postgres_data:
  redis_data:

networks:
  aidd-network:
    driver: bridge
```

## 🔄 配置加载流程

### 后端配置加载流程
```python
# app/core/config.py
from pydantic import BaseSettings
import os
import yaml

class Settings(BaseSettings):
    # 1. 从环境变量加载（最高优先级）
    database_type: str = "postgresql"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    
    # 2. 从配置文件加载（支持环境变量插值）
    @classmethod
    def load_from_yaml(cls, config_file: str = "config.yaml"):
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)
                # 执行环境变量插值
                config_data = cls.interpolate_env_vars(config_data)
                return cls(**config_data)
        return cls()
    
    @staticmethod
    def interpolate_env_vars(data):
        """递归处理环境变量插值 ${VAR_NAME:default_value}"""
        import re
        if isinstance(data, dict):
            return {k: Settings.interpolate_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [Settings.interpolate_env_vars(item) for item in data]
        elif isinstance(data, str):
            def replace_env_var(match):
                var_name = match.group(1)
                default_value = match.group(2) if match.group(2) else ""
                return os.getenv(var_name, default_value)
            return re.sub(r'\$\{([^}:]+)(?::([^}]*))?\}', replace_env_var, data)
        return data

# 配置加载
def get_settings():
    config_file = os.getenv("CONFIG_FILE", "config.yaml")
    return Settings.load_from_yaml(config_file)
```

### 前端配置加载流程
```typescript
// src/config/index.ts
interface AppConfig {
  apiBaseUrl: string;
  wsBaseUrl: string;
  appTitle: string;
  appVersion: string;
}

const getConfig = (): AppConfig => {
  // 1. 优先使用构建时环境变量
  if (import.meta.env.VITE_API_BASE_URL) {
    return {
      apiBaseUrl: import.meta.env.VITE_API_BASE_URL,
      wsBaseUrl: import.meta.env.VITE_WS_BASE_URL,
      appTitle: import.meta.env.VITE_APP_TITLE || 'AI文档测试系统',
      appVersion: import.meta.env.VITE_APP_VERSION || '2.0.0',
    };
  }
  
  // 2. 生产环境自动检测
  if (import.meta.env.PROD) {
    return {
      apiBaseUrl: `${window.location.protocol}//${window.location.host}/api`,
      wsBaseUrl: `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`,
      appTitle: 'AI文档测试系统',
      appVersion: '2.0.0',
    };
  }
  
  // 3. 开发环境默认配置
  const backendPort = import.meta.env.VITE_BACKEND_PORT || '8080';
  return {
    apiBaseUrl: `${window.location.protocol}//${window.location.hostname}:${backendPort}/api`,
    wsBaseUrl: `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.hostname}:${backendPort}/ws`,
    appTitle: 'AI文档测试系统',
    appVersion: '2.0.0',
  };
};

export default getConfig();
```

## 🚀 部署最佳实践

### 1. 环境变量管理
```bash
# 生产环境 - 使用外部密钥管理
export POSTGRES_PASSWORD=$(cat /run/secrets/postgres_password)
export JWT_SECRET_KEY=$(cat /run/secrets/jwt_secret)
export OPENAI_API_KEY=$(cat /run/secrets/openai_key)

# 开发环境 - 使用.env文件
cp .env.template .env
# 编辑 .env 文件
```

### 2. 配置文件管理
```bash
# 使用配置模板
cp config-template.yaml config.yaml

# 针对不同环境的配置文件
config.development.yaml  # 开发环境
config.staging.yaml      # 测试环境  
config.production.yaml   # 生产环境

# 运行时指定配置文件
export CONFIG_FILE=config.production.yaml
```

### 3. Docker运行命令示例
```bash
# 使用环境变量
docker run -d \
  -p 8080:8000 \
  -e DATABASE_TYPE=postgresql \
  -e POSTGRES_HOST=db.example.com \
  -e POSTGRES_PASSWORD=secure_password \
  -e OPENAI_API_KEY=sk-your-key \
  -v ./config.yaml:/app/config.yaml:ro \
  -v ./data:/app/data \
  ghcr.io/your-org/aidd/backend:latest

# 使用env文件
docker run -d \
  -p 8080:8000 \
  --env-file .env \
  -v ./config.yaml:/app/config.yaml:ro \
  -v ./data:/app/data \
  ghcr.io/your-org/aidd/backend:latest
```

## 🔒 安全考虑

### 1. 敏感信息处理
- **密钥轮换**: 支持运行时密钥更新
- **权限最小化**: 容器以非root用户运行
- **密钥管理**: 使用Docker Secrets或外部密钥管理服务

### 2. 配置验证
```python
# 配置验证示例
def validate_config(settings: Settings):
    required_fields = [
        'database_type', 'jwt_secret_key', 
        'openai_api_key', 'oauth_client_id'
    ]
    
    missing_fields = []
    for field in required_fields:
        if not getattr(settings, field, None):
            missing_fields.append(field)
    
    if missing_fields:
        raise ValueError(f"缺少必需配置: {', '.join(missing_fields)}")
```

## 📊 配置监控

### 1. 配置变更检测
```python
# 支持配置热重载
import watchdog
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ConfigReloadHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('config.yaml'):
            logger.info("检测到配置文件变更，重新加载...")
            reload_config()
```

### 2. 健康检查
```python
# 健康检查端点包含配置状态
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "config": {
            "database_connected": await check_db_connection(),
            "redis_connected": await check_redis_connection(),
            "ai_service_configured": bool(settings.openai_api_key),
        }
    }
```

这套配置体系确保了：
- ✅ **一致性**: 本地开发和生产环境配置方式一致
- ✅ **灵活性**: 支持多种配置方式和环境
- ✅ **安全性**: 敏感信息外部化管理
- ✅ **可维护性**: 清晰的配置优先级和加载流程
- ✅ **可观测性**: 配置状态监控和验证