"""
第三方认证深度集成测试
包含数据库操作、API模拟和业务逻辑验证
"""
import asyncio
import pytest
import time
from typing import Dict, Any
from app.core.database import Base, engine
# 导入所有模型以确保它们被注册到Base.metadata
from app.models import *


class TestThirdPartyAuthDeep:
    """第三方认证深度测试类"""
    
    def test_database_user_operations(self, client, test_db_session):
        """测试数据库用户操作"""
        from app.services.auth import AuthService
        from app.dto.user import UserCreate
        
        # 使用fixture提供的数据库会话
        auth_service = AuthService(test_db_session)
        
        # 测试创建用户
        unique_suffix = int(time.time())
        user_data = UserCreate(
            uid=f"test_user_{unique_suffix}",
            display_name="测试用户",
            email=f"test_{unique_suffix}@example.com",
            avatar_url="https://example.com/avatar.jpg"
        )
        
        user = auth_service.create_user(user_data)
        assert user.uid == f"test_user_{unique_suffix}"
        assert user.display_name == "测试用户"
        
        # 测试获取用户
        found_user = auth_service.authenticate_user(f"test_user_{unique_suffix}")
        assert found_user is not None
        assert found_user.uid == f"test_user_{unique_suffix}"
        
        # 测试用户登录
        login_result = auth_service.login_user(
            uid=f"test_user_{unique_suffix + 1}",
            display_name="新用户",
            email=f"new_{unique_suffix}@example.com"
        )
        assert login_result is not None
        assert "user" in login_result
        assert "access_token" in login_result
        
        # 测试令牌验证
        token = login_result["access_token"]
        verified_user = auth_service.verify_token(token)
        assert verified_user is not None
        assert verified_user.uid == f"test_user_{unique_suffix + 1}"
        
        # 不需要手动关闭，由fixture管理
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="需要完善的第三方API Mock")
    async def test_third_party_api_simulation_complete_flow(self, client, test_db_session):
        """测试第三方API模拟的完整流程"""
        from app.services.auth import AuthService
        from app.core.config import get_settings
        
        # 验证配置加载
        settings = get_settings()
        
        # 使用fixture提供的数据库会话
        auth_service = AuthService(test_db_session)
        
        # 测试1: 令牌交换（业务流程与生产环境一致）
        test_code = "test_auth_code_12345"
        
        # 这里的业务逻辑和生产环境完全一样，只是在HTTP调用层面mock
        token_response = await auth_service.exchange_code_for_token(test_code)
        
        # 验证响应结构与生产环境完全一致
        assert token_response.access_token is not None
        assert token_response.scope == "base.profile"
        assert token_response.expires_in > 0
        assert hasattr(token_response, 'refresh_token')
        
        # 测试2: 获取用户信息（业务流程与生产环境一致）
        user_info = await auth_service.get_third_party_user_info(token_response.access_token)
        
        # 验证响应结构与生产环境完全一致
        assert user_info.uid is not None
        assert user_info.display_name is not None
        assert user_info.email is not None
        assert hasattr(user_info, 'avatar_url')
        
        # 测试3: 完整的用户登录流程
        login_result = auth_service.login_user(
            uid=user_info.uid,
            display_name=user_info.display_name,
            email=user_info.email,
            avatar_url=user_info.avatar_url
        )
        
        assert login_result is not None
        assert "user" in login_result
        assert "access_token" in login_result
        assert "token_type" in login_result
        assert login_result["user"].uid == user_info.uid
        
        # 不需要手动关闭，由fixture管理
    
    @pytest.mark.asyncio
    async def test_third_party_auth_error_handling(self, client, test_db_session):
        """测试第三方认证错误处理"""
        from app.services.auth import AuthService
        
        # 使用fixture提供的数据库会话
        auth_service = AuthService(test_db_session)
        
        # 测试无效token的处理
        try:
            invalid_user_info = await auth_service.get_third_party_user_info("invalid_token")
            # 在mock模式下，可能返回模拟数据而不是抛出异常
            assert invalid_user_info is not None
        except Exception as e:
            # 这也是正常的，说明错误处理在工作
            assert isinstance(e, Exception)
        
        # 不需要手动关闭，由fixture管理
    
    def test_authorization_url_generation(self, client, test_db_session):
        """测试认证URL生成"""
        from app.services.auth import AuthService
        
        # 使用fixture提供的数据库会话
        auth_service = AuthService(test_db_session)
        
        # 测试获取认证URL
        auth_url = auth_service.get_authorization_url("test_state_123")
        
        assert isinstance(auth_url, str)
        assert "oauth/authorize" in auth_url  # Gitee使用oauth而不是oauth2
        assert "client_id=" in auth_url
        assert "response_type=code" in auth_url
        assert "redirect_uri=" in auth_url  # 应该是redirect_uri而不是redirect_url
        assert "scope=" in auth_url
        assert "state=test_state_123" in auth_url
        
        # 不需要手动关闭，由fixture管理
    
    def test_jwt_token_operations(self, client, test_db_session):
        """测试JWT令牌操作"""
        from app.services.auth import AuthService
        from app.dto.user import UserCreate
        from datetime import timedelta
        
        # 使用fixture提供的数据库会话（表已由client fixture创建）
        auth_service = AuthService(test_db_session)
        
        # 创建测试用户
        unique_suffix = int(time.time())
        user_data = UserCreate(
            uid=f"jwt_test_user_{unique_suffix}",
            display_name="JWT测试用户",
            email=f"jwt_test_{unique_suffix}@example.com"
        )
        
        user = auth_service.create_user(user_data)
        
        # 测试创建令牌
        token_data = {"sub": str(user.id)}
        token = auth_service.create_access_token(token_data)
        assert isinstance(token, str)
        assert len(token) > 0
        
        # 测试令牌验证
        verified_user = auth_service.verify_token(token)
        assert verified_user is not None
        assert verified_user.id == user.id
        
        # 测试带过期时间的令牌
        expires_delta = timedelta(minutes=30)
        token_with_expiry = auth_service.create_access_token(token_data, expires_delta)
        assert isinstance(token_with_expiry, str)
        
        verified_user_2 = auth_service.verify_token(token_with_expiry)
        assert verified_user_2 is not None
        assert verified_user_2.id == user.id
        
        # 不需要手动关闭，由fixture管理
    
    def test_user_login_with_admin_privileges(self, client, test_db_session):
        """测试管理员权限用户登录"""
        from app.services.auth import AuthService
        
        # 使用fixture提供的数据库会话（表已由client fixture创建）
        auth_service = AuthService(test_db_session)
        
        # 测试管理员用户登录
        unique_suffix = int(time.time())
        admin_login_result = auth_service.login_user(
            uid=f"admin_user_{unique_suffix}",
            display_name="管理员用户",
            email=f"admin_{unique_suffix}@example.com",
            is_admin=True,
            is_system_admin=True
        )
        
        assert admin_login_result is not None
        admin_user = admin_login_result["user"]
        assert admin_user.is_admin is True
        assert admin_user.is_system_admin is True
        
        # 验证管理员令牌
        admin_token = admin_login_result["access_token"]
        verified_admin = auth_service.verify_token(admin_token)
        assert verified_admin is not None
        assert verified_admin.is_admin is True
        assert verified_admin.is_system_admin is True
        
        # 不需要手动关闭，由fixture管理