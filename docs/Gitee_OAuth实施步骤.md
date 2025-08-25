# Gitee OAuth 2.0 接入实施步骤

## 阶段规划

### 阶段一：准备工作 (预计1天)
- [ ] Gitee应用注册配置
- [ ] 开发环境准备
- [ ] 备份现有代码

### 阶段二：后端实施 (预计2天)  
- [ ] 修改配置文件
- [ ] 修改认证服务代码
- [ ] 单元测试和调试

### 阶段三：前端适配 (预计1天)
- [ ] 前端回调页面调试
- [ ] 集成测试

### 阶段四：测试验证 (预计1天)
- [ ] 完整流程测试
- [ ] 错误场景测试
- [ ] 性能测试

---

## 详细实施步骤

### 第一步：Gitee应用注册

#### 1.1 创建Gitee应用
1. 登录 [Gitee](https://gitee.com)
2. 进入 个人设置 → 第三方应用 → 创建应用
3. 填写应用信息：
   ```
   应用名称: AI资料测试系统
   应用描述: AI文档质量测试和评估系统
   应用主页: http://localhost:5173 (开发环境)
   回调地址: http://localhost:5173/callback
   权限范围: user_info
   ```
4. 提交申请，获得 `Client ID` 和 `Client Secret`

#### 1.2 记录关键信息
```bash
# 记录以下信息用于后续配置
GITEE_CLIENT_ID=你的Client_ID
GITEE_CLIENT_SECRET=你的Client_Secret
回调地址=http://localhost:5173/callback
```

### 第二步：备份现有代码

#### 2.1 创建功能分支
```bash
cd /mnt/d/projects/ai_docs/ai_doc_test
git checkout -b gitee-oauth-integration
git push -u origin gitee-oauth-integration
```

#### 2.2 备份关键文件
```bash
cp backend/app/services/auth.py backend/app/services/auth.py.backup
cp backend/config.yaml backend/config.yaml.backup
```

### 第三步：修改配置文件

#### 3.1 更新 `backend/config.yaml`
```yaml
# 第三方登录配置 - 修改为Gitee OAuth 2.0
third_party_auth:
  # Gitee OAuth2配置
  client_id: "${GITEE_CLIENT_ID}"
  client_secret: "${GITEE_CLIENT_SECRET}"
  
  # 重定向URL配置
  frontend_domain: "${FRONTEND_DOMAIN:http://localhost:5173}"
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

# 更新环境变量映射
env_mapping:
  # 现有配置保持不变...
  GITEE_CLIENT_ID: "GITEE_CLIENT_ID"
  GITEE_CLIENT_SECRET: "GITEE_CLIENT_SECRET"
  FRONTEND_DOMAIN: "FRONTEND_DOMAIN"
```

#### 3.2 创建 `.env.gitee` 环境配置文件
```bash
# Gitee OAuth配置
GITEE_CLIENT_ID=你的_Client_ID
GITEE_CLIENT_SECRET=你的_Client_Secret  
FRONTEND_DOMAIN=http://localhost:5173

# 现有配置
JWT_SECRET_KEY=ai_doc_test_secret_key
OPENAI_API_KEY=your_openai_api_key
```

### 第四步：修改后端认证服务

#### 4.1 修改授权URL构造方法
在 `backend/app/services/auth.py` 的 `get_authorization_url` 方法中：
```python
def get_authorization_url(self, state: str = "12345678") -> str:
    """获取Gitee认证授权URL"""
    api_endpoints = self.third_party_config.get("api_endpoints", {})
    auth_url = api_endpoints.get("authorization_url")
    client_id = self.third_party_config.get("client_id")
    redirect_url = self._get_redirect_url()
    scope = self.third_party_config.get("scope", "user_info")
    
    if not auth_url or not client_id or not redirect_url:
        raise ValueError("Gitee OAuth配置不完整，请检查authorization_url、client_id和redirect_url配置")
    
    return (
        f"{auth_url}?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_url}&"  # 注意：Gitee使用redirect_uri
        f"response_type=code&"
        f"scope={scope}&"
        f"state={state}"
    )
```

#### 4.2 修改令牌交换方法
在 `_call_third_party_token_api` 方法中：
```python
async def _call_third_party_token_api(self, payload: dict, headers: dict) -> dict:
    """调用Gitee令牌交换API"""
    if self.settings.is_service_mocked('third_party_auth'):
        # Mock逻辑保持不变
        import asyncio
        await asyncio.sleep(0.1)
        return {
            "access_token": f"mock_gitee_token_{payload['code']}_{int(time.time())}",
            "token_type": "bearer", 
            "expires_in": 86400,
            "refresh_token": f"mock_refresh_{payload['code']}",
            "scope": "user_info"
        }
    
    import httpx
    api_endpoints = self.third_party_config.get("api_endpoints", {})
    token_url = api_endpoints.get("token_url")
    timeout = self.third_party_config.get("request_timeout", 30)
    
    if not token_url:
        raise ValueError("Gitee token_url配置缺失")
    
    # Gitee要求使用form-encoded格式
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

#### 4.3 修改用户信息获取方法
在 `_call_third_party_userinfo_api` 方法中：
```python
async def _call_third_party_userinfo_api(self, payload: dict) -> dict:
    """调用Gitee用户信息API"""
    if self.settings.is_service_mocked('third_party_auth'):
        import asyncio
        await asyncio.sleep(0.1)
        
        import hashlib
        hash_obj = hashlib.md5(payload["access_token"].encode())
        user_hash = hash_obj.hexdigest()[:8]
        return {
            "id": int(user_hash, 16) % 1000000,  # 模拟数字ID
            "login": f"gitee_user_{user_hash[:6]}",
            "name": f"Gitee用户_{user_hash[:4]}",
            "avatar_url": f"https://api.dicebear.com/7.x/avataaars/svg?seed={user_hash}",
            "email": f"user_{user_hash[:4]}@gitee.example.com"
        }
    
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
```

#### 4.4 修改用户信息映射
在 `get_third_party_user_info` 方法中：
```python
async def get_third_party_user_info(self, access_token: str) -> ThirdPartyUserInfoResponse:
    """获取Gitee用户信息"""
    payload = {"access_token": access_token}
    
    try:
        user_data = await self._call_third_party_userinfo_api(payload)
        return ThirdPartyUserInfoResponse(
            uid=str(user_data["id"]),  # Gitee返回的id是数字，转为字符串
            display_name=user_data.get("name") or user_data.get("login", "Gitee用户"),
            email=user_data.get("email") or f"{user_data.get('login', 'user')}@gitee.local",
            avatar_url=user_data.get("avatar_url", "")
        )
    except Exception as e:
        print(f"获取Gitee用户信息失败: {e}")
        if not self.settings.is_test_mode:
            raise
        return self._mock_user_info(access_token)
```

#### 4.5 修改exchange_code_for_token方法的payload构造
在 `exchange_code_for_token` 方法中：
```python
async def exchange_code_for_token(self, code: str) -> ThirdPartyTokenResponse:
    """使用authorization code交换access token"""
    # Gitee的令牌交换参数格式
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": self.third_party_config.get("client_id"),
        "client_secret": self.third_party_config.get("client_secret"),
        "redirect_uri": self._get_redirect_url(),  # Gitee使用redirect_uri
    }
    
    # 验证必需的配置
    if not payload["client_id"] or not payload["client_secret"] or not payload["redirect_uri"]:
        raise ValueError("Gitee OAuth配置不完整，请检查client_id、client_secret和redirect_uri配置")
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"  # Gitee要求form格式
    }
    
    try:
        response_data = await self._call_third_party_token_api(payload, headers)
        return ThirdPartyTokenResponse(
            access_token=response_data["access_token"],
            refresh_token=response_data.get("refresh_token"),
            scope=response_data.get("scope", "user_info"),
            expires_in=response_data.get("expires_in", 86400)
        )
    except Exception as e:
        print(f"Gitee令牌交换失败: {e}")
        if not self.settings.is_test_mode:
            raise
        return self._mock_token_response(code)
```

### 第五步：创建测试脚本

#### 5.1 创建Gitee OAuth测试脚本
```python
# 创建 tmp/test_gitee_oauth.py
"""
Gitee OAuth 2.0 测试脚本
"""
import asyncio
import os
import sys
sys.path.append('/mnt/d/projects/ai_docs/ai_doc_test/backend')

from app.core.database import get_db
from app.services.auth import AuthService

async def test_gitee_oauth():
    """测试Gitee OAuth流程"""
    db = next(get_db())
    auth_service = AuthService(db)
    
    print("=== Gitee OAuth 2.0 测试 ===")
    
    try:
        # 1. 测试获取授权URL
        print("1. 获取授权URL...")
        auth_url = auth_service.get_authorization_url()
        print(f"授权URL: {auth_url}")
        
        # 2. 测试Mock模式的令牌交换
        print("\\n2. 测试Mock模式令牌交换...")
        mock_code = "test_code_12345"
        token_response = await auth_service.exchange_code_for_token(mock_code)
        print(f"Token Response: {token_response}")
        
        # 3. 测试Mock模式的用户信息获取
        print("\\n3. 测试Mock模式用户信息获取...")
        user_info = await auth_service.get_third_party_user_info(token_response.access_token)
        print(f"User Info: {user_info}")
        
        # 4. 测试用户登录
        print("\\n4. 测试用户登录...")
        login_result = auth_service.login_user(
            uid=user_info.uid,
            display_name=user_info.display_name,
            email=user_info.email,
            avatar_url=user_info.avatar_url
        )
        print(f"Login Result: {login_result['user'].display_name}")
        print(f"Access Token: {login_result['access_token'][:20]}...")
        
        print("\\n=== 测试完成 ===")
        
    except Exception as e:
        print(f"测试失败: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_gitee_oauth())
```

### 第六步：运行和验证

#### 6.1 设置环境变量并启动服务
```bash
# 设置环境变量
export GITEE_CLIENT_ID=你的Client_ID
export GITEE_CLIENT_SECRET=你的Client_Secret
export FRONTEND_DOMAIN=http://localhost:5173
export JWT_SECRET_KEY=ai_doc_test_secret_key

# 启动后端服务（测试模式）
cd backend
PYTHONPATH=. CONFIG_FILE=config.yaml python app/main.py
```

#### 6.2 运行测试脚本
```bash
# 运行Gitee OAuth测试
python tmp/test_gitee_oauth.py
```

#### 6.3 验证API端点
```bash
# 1. 测试获取授权URL
curl -X GET "http://localhost:8080/api/auth/thirdparty/url"

# 2. 测试登录API（使用mock数据）  
curl -X POST "http://localhost:8080/api/auth/thirdparty/login" \\
  -H "Content-Type: application/json" \\
  -d '{"code": "test_code_12345"}'
```

### 第七步：前端集成测试

#### 7.1 验证前端回调处理
1. 启动前端服务：`npm run dev`
2. 访问授权URL（从第六步获得）
3. 在Gitee完成授权
4. 验证回调页面能正确处理authorization code

#### 7.2 完整流程测试
1. 前端调用获取授权URL
2. 用户访问Gitee授权页面
3. 授权后回调到前端
4. 前端提取code调用登录API
5. 验证用户成功登录并获得token

### 第八步：生产环境部署准备

#### 8.1 更新生产环境配置
```bash
# 生产环境变量
GITEE_CLIENT_ID=生产环境Client_ID
GITEE_CLIENT_SECRET=生产环境Client_Secret
FRONTEND_DOMAIN=https://your-domain.com
JWT_SECRET_KEY=生产环境密钥
```

#### 8.2 更新Gitee应用配置
- 回调地址改为：`https://your-domain.com/callback`
- 应用主页改为：`https://your-domain.com`

### 第九步：测试验收

#### 9.1 功能测试清单
- [ ] Mock模式下所有API正常工作
- [ ] 真实Gitee授权流程正常
- [ ] 用户信息正确映射和存储
- [ ] JWT token正常生成和验证
- [ ] 错误处理机制正常（网络错误、无效code等）
- [ ] 并发登录场景测试

#### 9.2 性能测试
- [ ] 授权流程响应时间 < 3秒
- [ ] 并发用户登录测试
- [ ] 内存和CPU使用率正常

#### 9.3 安全测试
- [ ] Client Secret不泄露到前端
- [ ] 无效authorization code处理
- [ ] Token有效期验证
- [ ] CSRF攻击防护（state参数）

### 第十步：上线部署

#### 10.1 代码合并
```bash
# 确认测试通过后合并代码
git add .
git commit -m "feat: 接入Gitee OAuth 2.0授权登录

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>"
git checkout main
git merge gitee-oauth-integration
git push origin main
```

#### 10.2 生产部署
- 更新生产环境配置
- 部署新版本
- 验证生产环境功能正常

## 风险控制与回滚方案

### 风险预防
1. **配置验证**：启动时验证所有必需配置项
2. **Mock测试**：开发阶段使用Mock避免API依赖
3. **错误监控**：关键步骤记录详细日志
4. **降级策略**：真实API失败时的fallback机制

### 回滚方案
```bash
# 快速回滚到原始版本
git checkout main
git reset --hard HEAD~1  # 回到上一个版本
git push --force origin main

# 或者回滚到备份分支
git checkout backup-before-gitee-oauth
git checkout -b hotfix-rollback
git push -u origin hotfix-rollback
```

## 预期效果

### 功能效果
- 用户可以使用Gitee账号快速登录系统
- 登录流程符合OAuth 2.0标准，安全可靠  
- 支持开发和生产环境不同配置

### 技术效果
- 代码改动最小化，架构保持稳定
- 保持良好的可测试性和可维护性
- 完善的错误处理和监控机制

### 用户体验
- 登录步骤简化，无需注册账号
- 支持Gitee头像和昵称自动同步
- 登录状态管理保持一致