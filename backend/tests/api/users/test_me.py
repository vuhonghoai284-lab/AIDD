"""
当前用户信息API测试
测试 /api/users/me 端点
"""
import pytest
from fastapi.testclient import TestClient


class TestCurrentUserAPI:
    """当前用户信息API测试类"""
    
    def test_get_current_user_info_success(self, client: TestClient, auth_headers):
        """测试获取当前用户信息成功 - GET /api/users/me"""
        response = client.get("/api/users/me", headers=auth_headers)
        assert response.status_code == 200
        
        user = response.json()
        required_fields = ["uid", "display_name", "email", "avatar_url", "is_admin", "is_system_admin", "created_at", "last_login_at"]
        
        for field in required_fields:
            assert field in user, f"Missing user field: {field}"
        
        # 验证管理员用户信息（可能是test_admin或sys_admin）
        assert user["uid"] in ["test_admin", "sys_admin"]
        if user["uid"] == "sys_admin":
            assert user["display_name"] == "系统管理员"
        else:
            assert user["display_name"] == "测试管理员"
        assert user["is_admin"] is True
        assert user["is_system_admin"] is True
    
    def test_get_current_user_info_normal_user(self, client: TestClient, normal_auth_headers, normal_user_token):
        """测试普通用户获取自己信息"""
        response = client.get("/api/users/me", headers=normal_auth_headers)
        assert response.status_code == 200
        
        user = response.json()
        # 获取用户对象，可能是dict格式
        normal_user = normal_user_token["user"]
        if hasattr(normal_user, 'uid'):
            # 模型对象
            assert user["uid"] == normal_user.uid
            assert user["display_name"] == normal_user.display_name
        else:
            # dict对象
            assert user["uid"] == normal_user["uid"]
            assert user["display_name"] == normal_user["display_name"]
        assert user["is_admin"] is False
        assert user["is_system_admin"] is False
    
    def test_get_current_user_info_without_auth(self, client: TestClient):
        """测试未认证获取当前用户信息"""
        response = client.get("/api/users/me")
        assert response.status_code == 401
        
        error = response.json()
        assert "detail" in error
    
    def test_get_current_user_info_with_invalid_token(self, client: TestClient):
        """测试无效token获取用户信息"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/users/me", headers=headers)
        assert response.status_code == 401
    
    def test_user_info_data_types(self, client: TestClient, auth_headers):
        """测试用户信息数据类型"""
        response = client.get("/api/users/me", headers=auth_headers)
        assert response.status_code == 200
        
        user = response.json()
        
        # 验证数据类型
        assert isinstance(user["uid"], str)
        assert isinstance(user["display_name"], str)
        assert isinstance(user["email"], str) 
        assert isinstance(user["is_admin"], bool)
        assert isinstance(user["is_system_admin"], bool)
        assert isinstance(user["created_at"], str)  # ISO格式时间字符串
        
        # avatar_url和last_login_at可能为null
        if user["avatar_url"] is not None:
            assert isinstance(user["avatar_url"], str)
        if user["last_login_at"] is not None:
            assert isinstance(user["last_login_at"], str)
    
    def test_user_datetime_fields(self, client: TestClient, auth_headers):
        """测试用户时间字段格式"""
        response = client.get("/api/users/me", headers=auth_headers)
        user = response.json()
        
        # 验证时间字段格式
        import datetime
        
        created_at = user["created_at"]
        try:
            datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        except ValueError:
            pytest.fail(f"Invalid created_at format: {created_at}")
        
        if user["last_login_at"]:
            last_login_at = user["last_login_at"]
            try:
                datetime.datetime.fromisoformat(last_login_at.replace('Z', '+00:00'))
            except ValueError:
                pytest.fail(f"Invalid last_login_at format: {last_login_at}")
    
    def test_sensitive_data_exclusion(self, client: TestClient, auth_headers):
        """测试敏感数据不被返回"""
        response = client.get("/api/users/me", headers=auth_headers)
        user = response.json()
        
        # 确保敏感字段不在返回数据中
        sensitive_fields = ["password", "password_hash", "secret_key", "private_key"]
        for field in sensitive_fields:
            assert field not in user, f"Sensitive field {field} should not be returned"
    
    def test_get_user_info_performance(self, client: TestClient, auth_headers):
        """测试获取用户信息性能"""
        import time
        
        start_time = time.time()
        response = client.get("/api/users/me", headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = (end_time - start_time) * 1000
        assert response_time < 300, f"Get user info too slow: {response_time}ms"
    
    def test_user_info_consistency(self, client: TestClient, auth_headers):
        """测试用户信息一致性"""
        # 多次请求应该返回一致的用户信息
        response1 = client.get("/api/users/me", headers=auth_headers)
        response2 = client.get("/api/users/me", headers=auth_headers)
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        user1 = response1.json()
        user2 = response2.json()
        
        # 核心字段应该相同（last_login_at等动态字段可能不同）
        stable_fields = ["uid", "display_name", "email", "is_admin", "is_system_admin"]
        for field in stable_fields:
            assert user1[field] == user2[field], f"Field {field} should be consistent"


class TestCurrentUserAPIMethods:
    """当前用户API HTTP方法测试"""
    
    def test_user_me_invalid_methods(self, client: TestClient, auth_headers):
        """测试当前用户端点无效HTTP方法"""
        # POST方法不被支持
        response = client.post("/api/users/me", headers=auth_headers)
        assert response.status_code == 405
        
        # PUT方法不被支持
        response = client.put("/api/users/me", headers=auth_headers)
        assert response.status_code == 405
        
        # DELETE方法不被支持
        response = client.delete("/api/users/me", headers=auth_headers)
        assert response.status_code == 405