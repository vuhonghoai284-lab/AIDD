# 统一OAuth配置指南

## 概述

本指南介绍如何使用统一的配置结构来支持多种OAuth 2.0提供商，包括通用OAuth和Gitee OAuth。无论选择哪种提供商，配置和部署体验完全一致。

## 配置结构

### 核心配置项

```yaml
third_party_auth:
  # 提供商类型选择 - 唯一的区别配置项
  provider_type: "${OAUTH_PROVIDER_TYPE:generic}"  # generic | gitee
  
  # 通用配置项 - 所有提供商都使用
  client_id: "${OAUTH_CLIENT_ID}"
  client_secret: "${OAUTH_CLIENT_SECRET}"
  frontend_domain: "${FRONTEND_DOMAIN:http://localhost:5173}"
  redirect_path: "/callback"
  scope: "${OAUTH_SCOPE:base.profile}"
  request_timeout: 30
```

### 环境变量配置

#### 必需的环境变量

```bash
# 核心配置 - 所有提供商都需要
export OAUTH_PROVIDER_TYPE=generic    # 或 gitee
export OAUTH_CLIENT_ID=your_client_id
export OAUTH_CLIENT_SECRET=your_client_secret
export FRONTEND_DOMAIN=http://localhost:5173
```

#### 通用OAuth额外变量

```bash
# 仅当OAUTH_PROVIDER_TYPE=generic时需要
export OAUTH_AUTH_URL=https://your-provider.com/oauth/authorize
export OAUTH_TOKEN_URL=https://your-provider.com/oauth/token
export OAUTH_USERINFO_URL=https://your-provider.com/oauth/userinfo
export OAUTH_SCOPE=base.profile
```

#### Gitee OAuth额外变量

```bash
# 当OAUTH_PROVIDER_TYPE=gitee时，可选配置
export OAUTH_SCOPE=user_info
# 注意：Gitee的API端点会自动设置，无需配置URL
```

## 部署方案

### 方案一：使用通用OAuth

#### 1. 设置环境变量

```bash
# 核心配置
export OAUTH_PROVIDER_TYPE=generic
export OAUTH_CLIENT_ID=your_generic_client_id
export OAUTH_CLIENT_SECRET=your_generic_client_secret
export FRONTEND_DOMAIN=http://localhost:5173

# 通用OAuth端点
export OAUTH_AUTH_URL=https://auth-provider.com/oauth2/authorize
export OAUTH_TOKEN_URL=https://auth-provider.com/oauth2/accesstoken
export OAUTH_USERINFO_URL=https://auth-provider.com/oauth2/userinfo
export OAUTH_SCOPE=base.profile
```

#### 2. 启动服务

```bash
# 使用统一配置启动
CONFIG_FILE=config.unified-oauth.yaml python app/main.py
```

#### 3. 验证配置

```bash
# 获取授权URL
curl -X GET "http://localhost:8080/api/auth/thirdparty/url"
# 响应示例: {"auth_url": "https://auth-provider.com/oauth2/authorize?client_id=..."}

# 测试登录
curl -X POST "http://localhost:8080/api/auth/thirdparty/login" \
  -H "Content-Type: application/json" \
  -d '{"code": "test_code"}'
```

### 方案二：使用Gitee OAuth

#### 1. 设置环境变量

```bash
# 核心配置（与通用OAuth几乎一致）
export OAUTH_PROVIDER_TYPE=gitee
export OAUTH_CLIENT_ID=your_gitee_client_id
export OAUTH_CLIENT_SECRET=your_gitee_client_secret
export FRONTEND_DOMAIN=http://localhost:5173
export OAUTH_SCOPE=user_info

# 注意：Gitee不需要配置API端点URL，系统自动使用标准端点
```

#### 2. 启动服务

```bash
# 使用完全相同的启动命令
CONFIG_FILE=config.unified-oauth.yaml python app/main.py
```

#### 3. 验证配置

```bash
# 获取授权URL
curl -X GET "http://localhost:8080/api/auth/thirdparty/url"
# 响应示例: {"auth_url": "https://gitee.com/oauth/authorize?client_id=..."}

# 测试登录
curl -X POST "http://localhost:8080/api/auth/thirdparty/login" \
  -H "Content-Type: application/json" \
  -d '{"code": "test_code"}'
```

## 运行时切换

### 无需重新配置的切换

由于配置结构统一，可以通过环境变量轻松切换提供商：

```bash
# 当前使用通用OAuth
export OAUTH_PROVIDER_TYPE=generic

# 切换到Gitee OAuth
export OAUTH_PROVIDER_TYPE=gitee
# 重启服务即可，其他配置保持不变

# 切换回通用OAuth
export OAUTH_PROVIDER_TYPE=generic
# 重启服务即可
```

### 动态切换脚本

```bash
#!/bin/bash
# switch_oauth.sh

PROVIDER_TYPE=$1

if [ "$PROVIDER_TYPE" = "generic" ]; then
    echo "切换到通用OAuth..."
    export OAUTH_PROVIDER_TYPE=generic
    export OAUTH_SCOPE=base.profile
    echo "请确保设置了通用OAuth端点URL"
elif [ "$PROVIDER_TYPE" = "gitee" ]; then
    echo "切换到Gitee OAuth..."
    export OAUTH_PROVIDER_TYPE=gitee
    export OAUTH_SCOPE=user_info
    echo "Gitee OAuth端点将自动设置"
else
    echo "用法: $0 {generic|gitee}"
    exit 1
fi

echo "重启服务以应用更改..."
# 这里可以添加重启服务的命令
```

## 配置示例

### 开发环境配置

```bash
# .env.development
OAUTH_PROVIDER_TYPE=generic
OAUTH_CLIENT_ID=dev_client_id
OAUTH_CLIENT_SECRET=dev_client_secret
FRONTEND_DOMAIN=http://localhost:5173
OAUTH_AUTH_URL=https://dev-auth.example.com/oauth/authorize
OAUTH_TOKEN_URL=https://dev-auth.example.com/oauth/token
OAUTH_USERINFO_URL=https://dev-auth.example.com/oauth/userinfo
OAUTH_SCOPE=base.profile
```

### 生产环境配置

```bash
# .env.production
OAUTH_PROVIDER_TYPE=gitee
OAUTH_CLIENT_ID=prod_gitee_client_id
OAUTH_CLIENT_SECRET=prod_gitee_client_secret
FRONTEND_DOMAIN=https://yourdomain.com
OAUTH_SCOPE=user_info
# Gitee端点自动配置，无需设置URL
```

### 测试环境配置

```bash
# .env.test
OAUTH_PROVIDER_TYPE=generic
OAUTH_CLIENT_ID=test_client_id
OAUTH_CLIENT_SECRET=test_client_secret
FRONTEND_DOMAIN=http://test.localhost:5173
OAUTH_AUTH_URL=https://test-auth.example.com/oauth/authorize
OAUTH_TOKEN_URL=https://test-auth.example.com/oauth/token
OAUTH_USERINFO_URL=https://test-auth.example.com/oauth/userinfo
OAUTH_SCOPE=base.profile
```

## 向后兼容

### 现有环境变量继续支持

为了保持向后兼容，系统仍然支持现有的环境变量名：

```bash
# 旧的变量名（继续支持）
THIRD_PARTY_CLIENT_ID=your_client_id
THIRD_PARTY_CLIENT_SECRET=your_client_secret
GITEE_CLIENT_ID=your_gitee_client_id
GITEE_CLIENT_SECRET=your_gitee_client_secret

# 会自动映射到新的变量名
# THIRD_PARTY_CLIENT_ID -> OAUTH_CLIENT_ID
# THIRD_PARTY_CLIENT_SECRET -> OAUTH_CLIENT_SECRET
# 等等...
```

## 故障排除

### 常见配置错误

#### 1. 提供商类型配置错误

```
错误: 不支持的OAuth提供商类型: generic_oauth
解决: 检查OAUTH_PROVIDER_TYPE环境变量，应该是 "generic" 或 "gitee"
```

#### 2. 通用OAuth端点缺失

```
错误: 通用OAuth配置缺失: api_endpoints.authorization_url
解决: 当使用generic提供商时，必须设置OAUTH_AUTH_URL等端点URL
```

#### 3. Gitee OAuth配置警告

```
警告: Gitee authorization_url 不是标准端点: https://custom-gitee.com/oauth/authorize
说明: 建议使用Gitee标准端点，除非你有自定义的Gitee服务
```

### 调试命令

#### 检查当前配置

```bash
# 检查OAuth提供商信息
curl -X GET "http://localhost:8080/api/auth/provider-info"

# 检查授权URL生成
curl -X GET "http://localhost:8080/api/auth/thirdparty/url"

# 检查系统健康状态
curl -X GET "http://localhost:8080/api/system/health"
```

#### 日志调试

在配置文件中启用调试日志：

```yaml
logging:
  level: "DEBUG"  # 启用详细日志
```

然后查看日志中的OAuth相关信息：

```bash
tail -f ./data/logs/app.log | grep -i oauth
```

## 最佳实践

### 1. 环境分离

不同环境使用不同的提供商：
- 开发环境：通用OAuth + Mock数据
- 测试环境：通用OAuth + 真实API
- 生产环境：Gitee OAuth

### 2. 配置验证

在部署前验证配置：

```python
# config_validator.py
from app.services.oauth import create_oauth_provider
from app.core.config import get_settings

settings = get_settings()
config = settings.third_party_auth_config
provider_type = config.get("provider_type", "generic")

try:
    provider = create_oauth_provider(provider_type, config, settings)
    print(f"✓ OAuth配置有效: {provider.get_provider_name()}")
except Exception as e:
    print(f"✗ OAuth配置错误: {e}")
```

### 3. 安全配置

- Client Secret不要硬编码在配置文件中
- 生产环境使用HTTPS
- 定期轮换Client Secret
- 限制回调域名白名单

### 4. 监控告警

监控关键OAuth指标：
- 认证成功/失败率
- API响应时间
- Token有效期管理
- 用户转化率

这个统一配置方案确保了无论选择哪种OAuth提供商，部署和维护体验都完全一致，同时保持了良好的扩展性和向后兼容性。