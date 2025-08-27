"""
通用OAuth 2.0提供商实现
"""
import httpx
import time
import hashlib
import asyncio
from urllib.parse import urlencode
from typing import Optional

from app.dto.user import ThirdPartyTokenResponse, ThirdPartyUserInfoResponse
from .interfaces import IOAuthProvider


class GenericOAuthProvider(IOAuthProvider):
    """通用OAuth 2.0提供商实现"""
    
    def get_provider_name(self) -> str:
        """获取提供商名称"""
        return "generic_oauth"
    
    def validate_config(self) -> bool:
        """验证通用OAuth配置"""
        required_fields = [
            "client_id", 
            "client_secret", 
            "frontend_domain",
            "api_endpoints.authorization_url",
            "api_endpoints.token_url", 
            "api_endpoints.userinfo_url"
        ]
        
        for field in required_fields:
            value = self.get_config_value(field)
            if not value:
                print(f"通用OAuth配置缺失: {field}")
                return False
        
        return True
    
    def get_authorization_url(self, state: str = "12345678") -> str:
        """构造通用OAuth授权URL"""
        if not self.validate_config():
            raise ValueError("通用OAuth配置不完整")
        
        auth_url = self.get_config_value("api_endpoints.authorization_url")
        client_id = self.get_config_value("client_id")
        redirect_url = self.get_redirect_url()
        scope = self.get_config_value("scope", "base.profile")
        
        params = {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_url,  # OAuth 2.0标准参数名
            "scope": scope,
            "display": "page",
            "state": state
        }
        
        return f"{auth_url}?{urlencode(params)}"
    
    async def exchange_code_for_token(self, code: str) -> ThirdPartyTokenResponse:
        """通用OAuth令牌交换"""
        if self.is_mock_enabled():
            return await self._mock_token_exchange(code)
        
        return await self._real_token_exchange(code)
    
    async def _real_token_exchange(self, code: str) -> ThirdPartyTokenResponse:
        """真实的令牌交换"""
        payload = {
            "client_id": self.get_config_value("client_id"),
            "client_secret": self.get_config_value("client_secret"),
            "redirect_uri": self.get_redirect_url(),  # OAuth 2.0标准参数名
            "grant_type": "authorization_code",
            "code": code
        }
        
        headers = {
            "Content-Type": "application/json"  # 通用OAuth使用JSON格式
        }
        
        token_url = self.get_config_value("api_endpoints.token_url")
        timeout = self.get_config_value("request_timeout", 30)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                json=payload,  # 使用JSON格式
                headers=headers,
                timeout=float(timeout)
            )
            response.raise_for_status()
            data = response.json()
        
        return ThirdPartyTokenResponse(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            scope=data["scope"],
            expires_in=data["expires_in"]
        )
    
    async def get_user_info(self, access_token: str) -> ThirdPartyUserInfoResponse:
        """获取通用OAuth用户信息"""
        if self.is_mock_enabled():
            return await self._mock_user_info(access_token)
        
        return await self._real_user_info(access_token)
    
    async def _real_user_info(self, access_token: str) -> ThirdPartyUserInfoResponse:
        """真实的用户信息获取"""
        payload = {
            "client_id": self.get_config_value("client_id"),
            "access_token": access_token,
            "scope": self.get_config_value("scope", "base.profile")
        }
        
        userinfo_url = self.get_config_value("api_endpoints.userinfo_url")
        timeout = self.get_config_value("request_timeout", 30)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(  # 通用OAuth使用POST
                userinfo_url,
                json=payload,
                timeout=float(timeout)
            )
            response.raise_for_status()
            data = response.json()
        
        return ThirdPartyUserInfoResponse(
            uid=data["uid"],
            display_name=data.get("displayNameCn"),
            email=data.get("email", f"{data['uid']}@example.com"),
            avatar_url=None  # 移除外部头像链接，使用默认头像或空值
        )
    
    async def _mock_token_exchange(self, code: str) -> ThirdPartyTokenResponse:
        """模拟令牌交换"""
        mock_config = self.settings.get_mock_config('third_party_auth')
        delay = mock_config.get('mock_delay', 0.1)
        
        await asyncio.sleep(delay)
        
        return ThirdPartyTokenResponse(
            access_token=f"mock_generic_token_{code}_{int(time.time())}",
            refresh_token=f"mock_refresh_{code}_{int(time.time())}",
            scope="base.profile",
            expires_in=3600
        )
    
    async def _mock_user_info(self, access_token: str) -> ThirdPartyUserInfoResponse:
        """模拟用户信息获取"""
        mock_config = self.settings.get_mock_config('third_party_auth')
        delay = mock_config.get('mock_delay', 0.1)
        
        await asyncio.sleep(delay)
        
        # 基于access_token生成一致的模拟用户信息
        hash_obj = hashlib.md5(access_token.encode())
        user_hash = hash_obj.hexdigest()[:8]
        
        return ThirdPartyUserInfoResponse(
            uid=f"generic_user_{user_hash}",
            display_name=f"通用用户_{user_hash[:4]}",
            email=f"user_{user_hash[:4]}@example.com",
            avatar_url=f"https://api.dicebear.com/7.x/avataaars/svg?seed={user_hash}"
        )