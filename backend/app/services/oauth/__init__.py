"""
OAuth提供商模块

该模块提供了统一的OAuth 2.0认证接口，支持多种OAuth提供商：
- 通用OAuth 2.0提供商 (GenericOAuthProvider)
- Gitee OAuth 2.0提供商 (GiteeOAuthProvider)

主要组件：
- IOAuthProvider: OAuth提供商抽象接口
- OAuthProviderFactory: OAuth提供商工厂类
- GenericOAuthProvider: 通用OAuth 2.0实现
- GiteeOAuthProvider: Gitee OAuth 2.0实现

使用示例：
```python
from app.services.oauth import create_oauth_provider

# 创建Gitee OAuth提供商
provider = create_oauth_provider("gitee", config, settings)

# 获取授权URL
auth_url = provider.get_authorization_url("state123")

# 交换令牌
token_response = await provider.exchange_code_for_token("auth_code")

# 获取用户信息
user_info = await provider.get_user_info(token_response.access_token)
```
"""

from .interfaces import IOAuthProvider
from .factory import (
    OAuthProviderFactory, 
    create_oauth_provider, 
    get_available_oauth_providers,
    register_oauth_provider
)
from .generic_provider import GenericOAuthProvider
from .gitee_provider import GiteeOAuthProvider

__all__ = [
    # 抽象接口
    'IOAuthProvider',
    
    # 工厂类和便捷函数
    'OAuthProviderFactory',
    'create_oauth_provider',
    'get_available_oauth_providers',
    'register_oauth_provider',
    
    # 具体实现类
    'GenericOAuthProvider',
    'GiteeOAuthProvider'
]

# 版本信息
__version__ = '1.0.0'

# 支持的提供商类型
SUPPORTED_PROVIDERS = [
    'generic',
    'gitee'
]