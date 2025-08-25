"""
Gitee OAuth 2.0提供商实现
"""
import httpx
import time
import hashlib
import asyncio
from urllib.parse import urlencode
from typing import Optional

from app.dto.user import ThirdPartyTokenResponse, ThirdPartyUserInfoResponse
from .interfaces import IOAuthProvider


class GiteeOAuthProvider(IOAuthProvider):
    """Gitee OAuth 2.0提供商实现"""
    
    # Gitee OAuth标准端点
    GITEE_AUTHORIZATION_URL = "https://gitee.com/oauth/authorize"
    GITEE_TOKEN_URL = "https://gitee.com/oauth/token"
    GITEE_USERINFO_URL = "https://gitee.com/api/v5/user"
    
    def get_provider_name(self) -> str:
        """获取提供商名称"""
        return "gitee_oauth"
    
    def validate_config(self) -> bool:
        """验证Gitee OAuth配置"""
        required_fields = [
            "client_id", 
            "client_secret", 
            "frontend_domain"
        ]
        
        for field in required_fields:
            value = self.get_config_value(field)
            if not value:
                print(f"Gitee OAuth配置缺失: {field}")
                return False
        
        # 检查API端点是否使用Gitee标准端点（可选检查，给出警告）
        api_endpoints = self.get_config_value("api_endpoints", {})
        if api_endpoints:
            expected_endpoints = {
                "authorization_url": self.GITEE_AUTHORIZATION_URL,
                "token_url": self.GITEE_TOKEN_URL,
                "userinfo_url": self.GITEE_USERINFO_URL
            }
            
            for key, expected_url in expected_endpoints.items():
                configured_url = api_endpoints.get(key)
                if configured_url and configured_url != expected_url:
                    print(f"警告: Gitee {key} 不是标准端点: {configured_url}，建议使用: {expected_url}")
        
        return True
    
    def get_authorization_url(self, state: str = "12345678") -> str:
        """构造Gitee授权URL"""
        if not self.validate_config():
            raise ValueError("Gitee OAuth配置不完整")
        
        # 优先使用配置中的端点，如果没有则使用标准端点
        auth_url = self.get_config_value("api_endpoints.authorization_url", self.GITEE_AUTHORIZATION_URL)
        client_id = self.get_config_value("client_id")
        redirect_uri = self.get_redirect_url()
        scope = self.get_config_value("scope", "user_info")
        
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,  # Gitee使用redirect_uri
            "response_type": "code",
            "scope": scope,
            "state": state
        }
        
        return f"{auth_url}?{urlencode(params)}"
    
    async def exchange_code_for_token(self, code: str) -> ThirdPartyTokenResponse:
        """Gitee令牌交换"""
        if self.is_mock_enabled():
            return await self._mock_token_exchange(code)
        
        return await self._real_token_exchange(code)
    
    async def _real_token_exchange(self, code: str) -> ThirdPartyTokenResponse:
        """真实的Gitee令牌交换"""
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.get_config_value("client_id"),
            "client_secret": self.get_config_value("client_secret"),
            "redirect_uri": self.get_redirect_url(),  # Gitee使用redirect_uri
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"  # Gitee使用form格式
        }
        
        # 优先使用配置中的端点，如果没有则使用标准端点
        token_url = self.get_config_value("api_endpoints.token_url", self.GITEE_TOKEN_URL)
        timeout = self.get_config_value("request_timeout", 30)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data=payload,  # 使用data而不是json
                headers=headers,
                timeout=float(timeout)
            )
            response.raise_for_status()
            data = response.json()
        
        return ThirdPartyTokenResponse(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            scope=data.get("scope", "user_info"),
            expires_in=data.get("expires_in", 86400)
        )
    
    async def get_user_info(self, access_token: str) -> ThirdPartyUserInfoResponse:
        """获取Gitee用户信息"""
        if self.is_mock_enabled():
            return await self._mock_user_info(access_token)
        
        return await self._real_user_info(access_token)
    
    async def _real_user_info(self, access_token: str) -> ThirdPartyUserInfoResponse:
        """真实的Gitee用户信息获取"""
        # 优先使用配置中的端点，如果没有则使用标准端点
        userinfo_url = self.get_config_value("api_endpoints.userinfo_url", self.GITEE_USERINFO_URL)
        timeout = self.get_config_value("request_timeout", 30)
        
        # Gitee使用GET请求，access_token作为查询参数
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{userinfo_url}?access_token={access_token}",
                timeout=float(timeout)
            )
            response.raise_for_status()
            data = response.json()
        
        return ThirdPartyUserInfoResponse(
            uid=str(data["id"]),  # Gitee返回的id是数字，转为字符串
            display_name=data.get("name") or data.get("login", "Gitee用户"),
            email=data.get("email") or f"{data.get('login', 'user')}@gitee.local",
            avatar_url=data.get("avatar_url", "")
        )
    
    async def _mock_token_exchange(self, code: str) -> ThirdPartyTokenResponse:
        """模拟Gitee令牌交换"""
        mock_config = self.settings.get_mock_config('third_party_auth')
        delay = mock_config.get('mock_delay', 0.1)
        
        await asyncio.sleep(delay)
        
        return ThirdPartyTokenResponse(
            access_token=f"mock_gitee_token_{code}_{int(time.time())}",
            token_type="bearer",
            expires_in=86400,
            refresh_token=f"mock_gitee_refresh_{code}",
            scope="user_info"
        )
    
    async def _mock_user_info(self, access_token: str) -> ThirdPartyUserInfoResponse:
        """模拟Gitee用户信息获取"""
        mock_config = self.settings.get_mock_config('third_party_auth')
        delay = mock_config.get('mock_delay', 0.1)
        
        await asyncio.sleep(delay)
        
        # 基于access_token生成一致的模拟用户信息
        hash_obj = hashlib.md5(access_token.encode())
        user_hash = hash_obj.hexdigest()[:8]
        
        return ThirdPartyUserInfoResponse(
            uid=str(int(user_hash, 16) % 1000000),  # 模拟数字ID转字符串
            display_name=f"Gitee用户_{user_hash[:4]}",
            email=f"gitee_user_{user_hash[:4]}@gitee.example.com",
            avatar_url=f"https://api.dicebear.com/7.x/avataaars/svg?seed=gitee_{user_hash}"
        )