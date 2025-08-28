# Gitee OAuth 2.0 接入方案设计文档

## 项目概述

将当前系统的第三方登录功能从通用OAuth实现改为具体接入Gitee的OAuth 2.0授权码模式，实现用户使用Gitee账号登录系统。

## 当前系统分析

### 现有认证架构
- **认证服务**: `backend/app/services/auth.py`
- **认证视图**: `backend/app/views/auth_view.py`
- **认证接口**: `backend/app/services/interfaces/auth_service.py`
- **配置系统**: `backend/config.yaml` 支持环境变量动态配置

### 现有OAuth流程
1. 前端调用 `/auth/thirdparty/url` 获取授权URL
2. 用户访问授权URL完成授权，获得authorization code
3. 前端调用 `/auth/thirdparty/login` 传递code
4. 后端使用code交换access_token，再获取用户信息
5. 系统创建/更新用户，返回JWT token

## Gitee OAuth 2.0 技术规范

### API端点
- **授权URL**: `https://gitee.com/oauth/authorize`
- **令牌交换**: `https://gitee.com/oauth/token`
- **用户信息**: `https://gitee.com/api/v5/user`

### 授权URL参数
```
https://gitee.com/oauth/authorize?
    client_id={CLIENT_ID}&
    redirect_uri={REDIRECT_URI}&
    response_type=code&
    scope={SCOPE}&
    state={STATE}
```

### 令牌交换参数 (POST)
```json
{
    "grant_type": "authorization_code",
    "code": "{AUTHORIZATION_CODE}",
    "client_id": "{CLIENT_ID}",
    "client_secret": "{CLIENT_SECRET}",
    "redirect_uri": "{REDIRECT_URI}"
}
```

### 令牌交换响应
```json
{
    "access_token": "...",
    "token_type": "bearer",
    "expires_in": 86400,
    "refresh_token": "...",
    "scope": "user_info"
}
```

### 用户信息API
```
GET https://gitee.com/api/v5/user?access_token={ACCESS_TOKEN}
```

### 用户信息响应
```json
{
    "id": 123456,
    "login": "username",
    "name": "User Name",
    "avatar_url": "https://...",
    "email": "user@example.com",
    "html_url": "https://gitee.com/username"
}
```

## 设计方案

### 方案选择
**推荐方案：最小化改动方案**
- 保持现有架构不变
- 仅修改配置参数和API端点
- 调整数据映射逻辑

### 核心修改点

#### 1. 配置文件修改 (`config.yaml`)
```yaml
# 第三方登录配置 - Gitee OAuth 2.0
third_party_auth:
  # Gitee OAuth2配置
  client_id: "${GITEE_CLIENT_ID}"
  client_secret: "${GITEE_CLIENT_SECRET}"
  
  # 重定向URL配置
  frontend_domain: "${FRONTEND_DOMAIN}"
  redirect_path: "/callback"
  
  scope: "user_info"
  
  # Gitee API端点
  api_endpoints:
    authorization_url: "https://gitee.com/oauth/authorize"
    token_url: "https://gitee.com/oauth/token"
    userinfo_url: "https://gitee.com/api/v5/user"
  
  # 请求配置
  request_timeout: 30
  max_retries: 3
```

#### 2. 认证服务修改 (`auth.py`)

**A. 授权URL构造方法修改**
```python
def get_authorization_url(self, state: str = "12345678") -> str:
    """获取Gitee认证授权URL"""
    api_endpoints = self.third_party_config.get("api_endpoints", {})
    auth_url = api_endpoints.get("authorization_url")
    client_id = self.third_party_config.get("client_id")
    redirect_url = self._get_redirect_url()
    scope = self.third_party_config.get("scope", "user_info")
    
    if not auth_url or not client_id or not redirect_url:
        raise ValueError("Gitee OAuth配置不完整")
    
    return (
        f"{auth_url}?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_url}&"
        f"response_type=code&"
        f"scope={scope}&"
        f"state={state}"
    )
```

**B. 令牌交换方法修改**
```python
async def _call_third_party_token_api(self, payload: dict, headers: dict) -> dict:
    """调用Gitee令牌交换API"""
    if self.settings.is_service_mocked('third_party_auth'):
        # Mock逻辑保持不变
        return self._generate_mock_token_response(payload)
    
    import httpx
    api_endpoints = self.third_party_config.get("api_endpoints", {})
    token_url = api_endpoints.get("token_url")
    timeout = self.third_party_config.get("request_timeout", 30)
    
    if not token_url:
        raise ValueError("Gitee token_url配置缺失")
    
    # Gitee要求使用form-encoded格式，不是JSON
    async with httpx.AsyncClient() as client:
        response = await client.post(
            token_url,
            data=payload,  # 使用data而不是json
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=float(timeout)
        )
        response.raise_for_status()
        return response.json()
```

**C. 用户信息获取方法修改**
```python
async def _call_third_party_userinfo_api(self, payload: dict) -> dict:
    """调用Gitee用户信息API"""
    if self.settings.is_service_mocked('third_party_auth'):
        # Mock逻辑保持不变
        return self._generate_mock_user_info(payload)
    
    import httpx
    api_endpoints = self.third_party_config.get("api_endpoints", {})
    userinfo_url = api_endpoints.get("userinfo_url")
    timeout = self.third_party_config.get("request_timeout", 30)
    
    if not userinfo_url:
        raise ValueError("Gitee userinfo_url配置缺失")
    
    # Gitee使用GET请求，access_token作为查询参数
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{userinfo_url}?access_token={payload['access_token']}",
            timeout=float(timeout)
        )
        response.raise_for_status()
        return response.json()

async def get_third_party_user_info(self, access_token: str) -> ThirdPartyUserInfoResponse:
    """获取Gitee用户信息"""
    payload = {"access_token": access_token}
    
    try:
        user_data = await self._call_third_party_userinfo_api(payload)
        return ThirdPartyUserInfoResponse(
            uid=str(user_data["id"]),  # Gitee返回的id是数字
            display_name=user_data.get("name") or user_data.get("login"),
            email=user_data.get("email", f"{user_data['login']}@gitee.local"),
            avatar_url=user_data.get("avatar_url", "")
        )
    except Exception as e:
        print(f"获取Gitee用户信息失败: {e}")
        if not self.settings.is_test_mode:
            raise
        return self._mock_user_info(access_token)
```

#### 3. 环境变量配置
```bash
# Gitee OAuth配置
GITEE_CLIENT_ID=your_gitee_client_id
GITEE_CLIENT_SECRET=your_gitee_client_secret
FRONTEND_DOMAIN=http://localhost:5173

# 通用配置（保持不变）
JWT_SECRET_KEY=your_jwt_secret_key
```

#### 4. 前端回调页面
前端需要处理Gitee授权回调，提取code参数并调用后端登录API。

### 数据映射对比

| 数据字段 | 当前系统字段 | Gitee API字段 | 映射方式 |
|---------|-------------|--------------|----------|
| 用户ID | uid | id | str(data["id"]) |
| 显示名称 | display_name | name/login | data.get("name") or data.get("login") |
| 邮箱 | email | email | data.get("email", f"{login}@gitee.local") |
| 头像 | avatar_url | avatar_url | data.get("avatar_url", "") |

## 兼容性设计

### 向后兼容
- 保持现有API接口不变
- 保持现有数据模型不变
- 支持配置切换（通过环境变量）

### Mock支持
- 开发和测试环境支持Mock模式
- Mock数据格式与Gitee API格式一致

### 错误处理
- API调用失败时的降级策略
- 配置错误的友好提示
- 网络超时重试机制

## 部署注意事项

### Gitee应用配置
1. 在Gitee个人中心创建第三方应用
2. 配置正确的回调地址：`{FRONTEND_DOMAIN}/callback`
3. 获取Client ID和Client Secret

### 环境配置
1. 设置正确的环境变量
2. 确保前端域名配置正确
3. 验证网络连接到Gitee API

### 安全考虑
- Client Secret不应暴露给前端
- 使用HTTPS部署生产环境
- 设置合理的token过期时间

## 测试策略

### 单元测试
- 测试授权URL构造
- 测试令牌交换逻辑
- 测试用户信息映射

### 集成测试
- 测试完整OAuth流程
- 测试错误处理机制
- 测试Mock模式

### 手工测试
- 真实Gitee账号登录
- 边界情况测试
- 性能测试

## 风险评估

### 技术风险
- **低**: 现有架构支持良好，改动量小
- **中**: Gitee API变更风险
- **低**: 数据迁移风险（无需迁移）

### 业务风险  
- **低**: 不影响现有用户数据
- **中**: 用户需重新授权
- **低**: 功能完全兼容

## 总结

本方案采用最小化改动策略，仅需修改配置和少量业务逻辑代码，即可完成Gitee OAuth 2.0的接入。方案保持了系统的架构稳定性，同时提供了良好的可测试性和向后兼容性。