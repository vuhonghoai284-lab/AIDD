# AI文档测试系统 - 部署配置指南

本指南说明如何配置不同环境下的系统部署，已完全移除localhost硬编码。

## 概述

系统已完全支持通过环境变量进行配置，支持：
- 开发环境
- 测试环境
- 生产环境
- 多实例部署
- 容器化部署

## 配置方式

### 1. 环境变量配置

所有配置都通过环境变量进行，支持默认值语法：`${VAR_NAME:default_value}`

### 2. 配置文件层级

1. **环境变量** (优先级最高)
2. **配置文件** (config.yaml, config.*.yaml)
3. **默认值** (代码中定义)

## 主要配置项

### 后端配置

#### 服务器配置
```bash
SERVER_HOST=0.0.0.0                    # 监听地址
SERVER_PORT=8080                       # 监听端口
EXTERNAL_HOST=localhost                 # 外部访问主机名
EXTERNAL_PORT=8080                      # 外部访问端口
EXTERNAL_PROTOCOL=http                  # 外部访问协议
DEBUG=false                             # 调试模式
RELOAD=false                            # 自动重载
WORKERS=1                               # 工作进程数
```

#### 前端URL配置 (CORS)
```bash
FRONTEND_URL_1=http://localhost:3000    # 主前端地址
FRONTEND_URL_2=http://localhost:3001    # 备用前端地址1
FRONTEND_URL_3=http://localhost:3002    # 备用前端地址2
FRONTEND_URL_4=http://localhost:3003    # 备用前端地址3
FRONTEND_URL_5=http://localhost:5173    # Vite开发服务器
FRONTEND_URL_6=http://127.0.0.1:3000    # 本地IP访问
FRONTEND_URL_7=http://127.0.0.1:5173    # 本地IP Vite
FRONTEND_PRODUCTION_URL=https://your-frontend-domain.com  # 生产环境
```

#### OAuth配置
```bash
FRONTEND_DOMAIN=http://localhost:3000   # OAuth回调域名
OAUTH_REDIRECT_PATH=/third-login/callback  # OAuth回调路径
```

#### CORS配置
```bash
CORS_DEVELOPMENT_MODE=false             # 开发模式CORS
```

### 前端配置

#### Vite环境变量
```bash
VITE_API_BASE_URL=http://localhost:8080/api    # API基础URL
VITE_WS_BASE_URL=ws://localhost:8080           # WebSocket URL
VITE_APP_TITLE=AI文档测试系统                  # 应用标题
VITE_APP_VERSION=2.0.0                         # 应用版本
VITE_BACKEND_HOST=localhost                    # 后端主机
VITE_BACKEND_PORT=8080                         # 后端端口
VITE_BACKEND_PROTOCOL=http                     # 后端协议
```

#### 测试配置
```bash
PLAYWRIGHT_BASE_URL=http://localhost:3000     # E2E测试基础URL
```

## 部署场景

### 1. 本地开发环境

```bash
# 使用默认值，无需设置环境变量
# 或者设置：
export CORS_DEVELOPMENT_MODE=true
export DEBUG=true
```

启动命令：
```bash
# 后端
cd backend && python app/main.py

# 前端
cd frontend && npm run dev
```

### 2. 内网测试环境

```bash
export EXTERNAL_HOST=test-server
export EXTERNAL_PORT=8080
export EXTERNAL_PROTOCOL=http
export FRONTEND_DOMAIN=http://test-frontend:3000
export FRONTEND_URL_1=http://test-frontend:3000
export VITE_API_BASE_URL=http://test-server:8080/api
export VITE_WS_BASE_URL=ws://test-server:8080
```

### 3. 生产环境

```bash
export EXTERNAL_HOST=api.yourcompany.com
export EXTERNAL_PORT=443
export EXTERNAL_PROTOCOL=https
export FRONTEND_DOMAIN=https://app.yourcompany.com
export FRONTEND_PRODUCTION_URL=https://app.yourcompany.com
export CORS_DEVELOPMENT_MODE=false
export DEBUG=false
export VITE_API_BASE_URL=https://api.yourcompany.com/api
export VITE_WS_BASE_URL=wss://api.yourcompany.com
```

### 4. 容器化部署

#### Docker Compose 示例

```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    environment:
      - EXTERNAL_HOST=api.yourcompany.com
      - EXTERNAL_PORT=443
      - EXTERNAL_PROTOCOL=https
      - FRONTEND_DOMAIN=https://app.yourcompany.com
      - CORS_DEVELOPMENT_MODE=false
    ports:
      - "8080:8080"

  frontend:
    build: ./frontend
    environment:
      - VITE_API_BASE_URL=https://api.yourcompany.com/api
      - VITE_WS_BASE_URL=wss://api.yourcompany.com
      - VITE_BACKEND_HOST=api.yourcompany.com
      - VITE_BACKEND_PORT=443
      - VITE_BACKEND_PROTOCOL=https
    ports:
      - "3000:3000"
```

### 5. Kubernetes部署

#### ConfigMap 示例

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ai-docs-config
data:
  EXTERNAL_HOST: "api.yourcompany.com"
  EXTERNAL_PORT: "443"
  EXTERNAL_PROTOCOL: "https"
  FRONTEND_DOMAIN: "https://app.yourcompany.com"
  CORS_DEVELOPMENT_MODE: "false"
  VITE_API_BASE_URL: "https://api.yourcompany.com/api"
  VITE_WS_BASE_URL: "wss://api.yourcompany.com"
```

## 配置验证

### 后端配置验证

```bash
cd backend
python -c "
from app.core.config import get_settings
settings = get_settings()
print('服务器外部URL:', settings.server_external_url)
print('前端域名:', settings.third_party_auth_config.get('frontend_domain'))
print('CORS源数量:', len(settings.cors_origins))
"
```

### 前端配置验证

```bash
cd frontend
npm run dev
# 查看浏览器控制台中的配置日志
```

## 常见问题

### 1. CORS错误
- 确保 `FRONTEND_DOMAIN` 和 `FRONTEND_URL_*` 配置正确
- 开发环境可设置 `CORS_DEVELOPMENT_MODE=true`

### 2. API连接失败
- 检查 `EXTERNAL_HOST`、`EXTERNAL_PORT`、`EXTERNAL_PROTOCOL` 配置
- 确保 `VITE_API_BASE_URL` 与后端外部URL匹配

### 3. OAuth回调失败
- 确保 `FRONTEND_DOMAIN` 与OAuth配置的回调域名一致
- 检查 `OAUTH_REDIRECT_PATH` 路径配置

### 4. WebSocket连接失败
- 确保 `VITE_WS_BASE_URL` 配置正确
- 检查防火墙和负载均衡器WebSocket支持

## 配置模板

### 开发环境模板 (.env.development)
```bash
CORS_DEVELOPMENT_MODE=true
DEBUG=true
VITE_API_BASE_URL=http://localhost:8080/api
VITE_WS_BASE_URL=ws://localhost:8080
```

### 生产环境模板 (.env.production)
```bash
EXTERNAL_HOST=api.yourcompany.com
EXTERNAL_PORT=443
EXTERNAL_PROTOCOL=https
FRONTEND_DOMAIN=https://app.yourcompany.com
FRONTEND_PRODUCTION_URL=https://app.yourcompany.com
CORS_DEVELOPMENT_MODE=false
DEBUG=false
VITE_API_BASE_URL=https://api.yourcompany.com/api
VITE_WS_BASE_URL=wss://api.yourcompany.com
VITE_BACKEND_HOST=api.yourcompany.com
VITE_BACKEND_PORT=443
VITE_BACKEND_PROTOCOL=https
```

## 总结

通过环境变量配置，系统现在可以灵活部署到任何环境，无需修改代码。所有localhost硬编码已完全移除，支持多种部署方式和环境配置。