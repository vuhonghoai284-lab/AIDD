"""
OAuth提供商抽象接口定义
"""
from abc import ABC, abstractmethod
from typing import Optional
from app.dto.user import ThirdPartyTokenResponse, ThirdPartyUserInfoResponse


class IOAuthProvider(ABC):
    """OAuth 2.0提供商抽象接口"""
    
    def __init__(self, config: dict, settings):
        """
        初始化OAuth提供商
        
        Args:
            config: OAuth提供商配置
            settings: 系统设置对象
        """
        self.config = config
        self.settings = settings
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """获取提供商名称"""
        pass
    
    @abstractmethod
    def get_authorization_url(self, state: str = "12345678") -> str:
        """
        构造授权URL
        
        Args:
            state: 状态参数，用于防止CSRF攻击
            
        Returns:
            完整的授权URL
        """
        pass
    
    @abstractmethod
    async def exchange_code_for_token(self, code: str) -> ThirdPartyTokenResponse:
        """
        使用授权码交换访问令牌
        
        Args:
            code: 授权码
            
        Returns:
            令牌响应对象
        """
        pass
    
    @abstractmethod
    async def get_user_info(self, access_token: str) -> ThirdPartyUserInfoResponse:
        """
        获取用户信息
        
        Args:
            access_token: 访问令牌
            
        Returns:
            用户信息响应对象
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """
        验证配置完整性
        
        Returns:
            配置是否有效
        """
        pass
    
    # 公共方法实现
    def is_mock_enabled(self) -> bool:
        """检查是否启用Mock模式"""
        return self.settings.is_service_mocked('third_party_auth')
    
    def get_redirect_url(self) -> str:
        """
        获取重定向URL
        
        Returns:
            完整的重定向URL
            
        Raises:
            ValueError: 当配置缺失时
        """
        frontend_domain = self.config.get("frontend_domain")
        redirect_path = self.config.get("redirect_path", "/callback")
        
        if not frontend_domain:
            raise ValueError("OAuth配置缺失: frontend_domain 未配置")
        
        # 清理域名格式
        if frontend_domain.endswith('/'):
            frontend_domain = frontend_domain[:-1]
        
        # 确保路径格式正确
        if not redirect_path.startswith('/'):
            redirect_path = '/' + redirect_path
            
        return f"{frontend_domain}{redirect_path}"
    
    def get_config_value(self, key: str, default=None):
        """
        获取配置值，支持嵌套键
        
        Args:
            key: 配置键，支持"."分隔的嵌套键
            default: 默认值
            
        Returns:
            配置值
        """
        if "." in key:
            keys = key.split(".")
            value = self.config
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k, {})
                else:
                    return default
            return value if value != {} else default
        else:
            return self.config.get(key, default)