"""
认证服务接口
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict

from app.models.user import User
from app.dto.user import ThirdPartyTokenResponse, ThirdPartyUserInfoResponse
from app.services.interfaces.base import BaseService


class IAuthService(BaseService[User, int]):
    """认证服务接口"""
    
    @abstractmethod
    def get_authorization_url(self) -> str:
        """获取第三方认证URL"""
        pass
    
    @abstractmethod
    async def exchange_code_for_token(self, code: str) -> ThirdPartyTokenResponse:
        """使用授权码交换访问令牌"""
        pass
    
    @abstractmethod
    async def get_third_party_user_info(self, access_token: str) -> ThirdPartyUserInfoResponse:
        """获取第三方用户信息"""
        pass
    
    @abstractmethod
    def login_user(self, uid: str, display_name: str, email: str, 
                   avatar_url: Optional[str] = None, is_system_admin: bool = False,
                   is_admin: bool = False) -> Optional[Dict]:
        """登录用户"""
        pass
    
    @abstractmethod
    def verify_token(self, token: str) -> Optional[User]:
        """验证访问令牌"""
        pass
    
    @abstractmethod
    def generate_token(self, user: User) -> str:
        """生成访问令牌"""
        pass