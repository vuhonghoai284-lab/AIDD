"""
测试登录页面UI美化功能
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
# fixtures从conftest.py自动导入


class TestLoginPageUI:
    """登录页面UI美化功能测试"""
    
    def test_login_page_accessibility(self, client: TestClient):
        """测试登录页面可访问性"""
        # 访问登录页面时后端应该提供正确的认证端点
        response = client.get("/api/auth/thirdparty/url")
        assert response.status_code == 200
        data = response.json()
        assert "auth_url" in data
        
        # 验证认证URL格式正确
        auth_url = data["auth_url"]
        assert auth_url.startswith("http")
    
    def test_third_party_login_functionality(self, client: TestClient):
        """测试第三方登录功能"""
        # 模拟第三方登录回调
        response = client.post("/api/auth/thirdparty/login-legacy", json={
            "code": "ui_test_auth_code"
        })
        assert response.status_code == 200
        
        result = response.json()
        assert "access_token" in result
        assert "user" in result
        
        # 验证返回的用户信息包含显示所需的字段
        user_data = result["user"]
        assert "uid" in user_data
        assert "display_name" in user_data or "uid" in user_data  # 至少有一个显示名称
    
    def test_system_admin_login_functionality(self, client: TestClient, admin_user_token):
        """测试系统管理员登录功能"""
        response = client.post("/api/auth/system/login", data={
            "username": "admin",
            "password": "admin123"
        })
        assert response.status_code == 200
        
        result = response.json()
        assert "access_token" in result
        assert "user" in result
        
        user_data = result["user"]
        assert user_data["is_system_admin"] == True
        assert "uid" in user_data
    
    def test_login_form_validation_backend(self, client: TestClient):
        """测试登录表单后端验证"""
        # 测试空用户名密码
        response = client.post("/api/auth/system/login", data={
            "username": "",
            "password": ""
        })
        assert response.status_code in [400, 422]  # 验证失败
        
        # 测试错误密码
        response = client.post("/api/auth/system/login", data={
            "username": "admin",
            "password": "wrong_password"
        })
        assert response.status_code == 401  # 认证失败
    
    def test_development_mode_detection(self, client: TestClient):
        """测试开发模式检测功能"""
        # 在测试环境中，第三方登录应该支持开发模式
        # 这里测试模拟的第三方登录流程
        
        # 使用模拟的authorization code进行登录
        mock_code = f"mock_auth_code_{pytest.current_test_id if hasattr(pytest, 'current_test_id') else 'test'}"
        
        response = client.post("/api/auth/thirdparty/login-legacy", json={
            "code": mock_code
        })
        assert response.status_code == 200
        
        result = response.json()
        assert "access_token" in result
        assert "user" in result
    
    def test_user_display_info_for_ui(self, client: TestClient):
        """测试用户显示信息用于UI展示"""
        # 测试第三方用户的显示信息
        response = client.post("/api/auth/thirdparty/login-legacy", json={
            "code": "display_test_code"
        })
        assert response.status_code == 200
        
        result = response.json()
        user_data = result["user"]
        
        # 验证用户信息包含UI所需的字段
        assert "uid" in user_data
        # display_name 可能来自 user_info 或者是 uid 的默认值
        assert user_data.get("display_name") or user_data.get("uid")
        
        # 如果有头像URL，应该被保存
        if "avatar_url" in user_data:
            assert user_data["avatar_url"].startswith("http")
    
    def test_login_error_messages(self, client: TestClient):
        """测试登录错误消息"""
        # 测试无效凭证
        response = client.post("/api/auth/system/login", data={
            "username": "invalid_user",
            "password": "invalid_password"
        })
        assert response.status_code == 401
        
        # 验证错误响应格式
        error_data = response.json()
        assert "detail" in error_data or "message" in error_data
    
    def test_login_success_response_format(self, client: TestClient):
        """测试登录成功响应格式"""
        response = client.post("/api/auth/system/login", data={
            "username": "admin",
            "password": "admin123"
        })
        assert response.status_code == 200
        
        result = response.json()
        
        # 验证响应包含前端所需的所有字段
        assert "access_token" in result
        assert "token_type" in result
        assert "user" in result
        
        user_data = result["user"]
        required_fields = ["id", "uid", "is_admin", "is_system_admin"]
        for field in required_fields:
            assert field in user_data
        
        # 验证token格式
        token = result["access_token"]
        assert len(token) > 10  # JWT token应该是一个较长的字符串
        assert result["token_type"] == "bearer"