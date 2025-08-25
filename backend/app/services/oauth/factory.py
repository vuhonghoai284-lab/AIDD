"""
OAuth提供商工厂类
"""
from typing import Dict, Type, List, Optional

from .interfaces import IOAuthProvider
from .generic_provider import GenericOAuthProvider
from .gitee_provider import GiteeOAuthProvider


class OAuthProviderFactory:
    """OAuth提供商工厂类"""
    
    # 注册的提供商类型映射
    _providers: Dict[str, Type[IOAuthProvider]] = {
        "generic": GenericOAuthProvider,
        "gitee": GiteeOAuthProvider
    }
    
    @classmethod
    def create_provider(cls, provider_type: str, config: dict, settings) -> IOAuthProvider:
        """
        创建OAuth提供商实例
        
        Args:
            provider_type: 提供商类型 (generic, gitee)
            config: OAuth提供商配置
            settings: 系统设置对象
            
        Returns:
            OAuth提供商实例
            
        Raises:
            ValueError: 当提供商类型不支持或配置验证失败时
        """
        if provider_type not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ValueError(f"不支持的OAuth提供商类型: {provider_type}. 可用类型: {available}")
        
        provider_class = cls._providers[provider_type]
        
        try:
            # 创建提供商实例
            provider = provider_class(config, settings)
            
            # 验证配置
            if not provider.validate_config():
                raise ValueError(f"{provider_type} OAuth配置验证失败")
            
            print(f"成功创建OAuth提供商: {provider.get_provider_name()}")
            return provider
            
        except Exception as e:
            print(f"创建OAuth提供商失败 ({provider_type}): {e}")
            raise
    
    @classmethod
    def get_available_providers(cls) -> List[str]:
        """
        获取所有可用的提供商类型
        
        Returns:
            提供商类型列表
        """
        return list(cls._providers.keys())
    
    @classmethod
    def register_provider(cls, provider_type: str, provider_class: Type[IOAuthProvider]):
        """
        注册新的OAuth提供商
        
        Args:
            provider_type: 提供商类型标识
            provider_class: 提供商实现类
        """
        if not issubclass(provider_class, IOAuthProvider):
            raise ValueError("提供商类必须继承自IOAuthProvider")
        
        cls._providers[provider_type] = provider_class
        print(f"已注册OAuth提供商: {provider_type} -> {provider_class.__name__}")
    
    @classmethod
    def unregister_provider(cls, provider_type: str):
        """
        注销OAuth提供商
        
        Args:
            provider_type: 提供商类型标识
        """
        if provider_type in cls._providers:
            del cls._providers[provider_type]
            print(f"已注销OAuth提供商: {provider_type}")
        else:
            print(f"OAuth提供商不存在: {provider_type}")
    
    @classmethod
    def get_provider_info(cls) -> Dict[str, dict]:
        """
        获取所有提供商信息
        
        Returns:
            提供商信息字典
        """
        info = {}
        
        for provider_type, provider_class in cls._providers.items():
            try:
                # 创建临时实例以获取提供商信息（使用空配置）
                temp_instance = provider_class({}, None)
                provider_name = temp_instance.get_provider_name()
            except Exception:
                # 如果无法创建实例，使用类名
                provider_name = provider_class.__name__
            
            info[provider_type] = {
                "name": provider_name,
                "class": provider_class.__name__,
                "module": provider_class.__module__
            }
        
        return info
    
    @classmethod
    def validate_provider_type(cls, provider_type: str) -> bool:
        """
        验证提供商类型是否有效
        
        Args:
            provider_type: 提供商类型
            
        Returns:
            是否有效
        """
        return provider_type in cls._providers
    
    @classmethod
    def get_provider_class(cls, provider_type: str) -> Optional[Type[IOAuthProvider]]:
        """
        获取提供商类
        
        Args:
            provider_type: 提供商类型
            
        Returns:
            提供商类，如果不存在则返回None
        """
        return cls._providers.get(provider_type)


# 提供便捷的函数接口
def create_oauth_provider(provider_type: str, config: dict, settings) -> IOAuthProvider:
    """
    创建OAuth提供商实例的便捷函数
    
    Args:
        provider_type: 提供商类型
        config: 配置字典
        settings: 设置对象
        
    Returns:
        OAuth提供商实例
    """
    return OAuthProviderFactory.create_provider(provider_type, config, settings)


def get_available_oauth_providers() -> List[str]:
    """
    获取可用OAuth提供商类型的便捷函数
    
    Returns:
        提供商类型列表
    """
    return OAuthProviderFactory.get_available_providers()


def register_oauth_provider(provider_type: str, provider_class: Type[IOAuthProvider]):
    """
    注册OAuth提供商的便捷函数
    
    Args:
        provider_type: 提供商类型
        provider_class: 提供商类
    """
    OAuthProviderFactory.register_provider(provider_type, provider_class)