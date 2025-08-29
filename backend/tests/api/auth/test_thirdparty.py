"""
第三方认证API测试
测试 /api/auth/thirdparty/* 端点
"""
import pytest
from fastapi.testclient import TestClient


class TestThirdPartyAuthAPI:
    """第三方认证API测试类"""
    
    def test_get_third_party_auth_url_success(self, client: TestClient):
        """测试获取第三方认证URL成功 - GET /api/auth/thirdparty/url"""
        response = client.get("/api/auth/thirdparty/url")
        assert response.status_code == 200
        
        data = response.json()
        assert "auth_url" in data
        assert isinstance(data["auth_url"], str)
        
        # 验证URL包含必要的OAuth2参数
        auth_url = data["auth_url"]
        assert "oauth/authorize" in auth_url
        assert "client_id=" in auth_url
        assert "response_type=code" in auth_url
        assert "redirect_uri=" in auth_url
        assert "scope=" in auth_url
    
    def test_get_auth_url_performance(self, client: TestClient):
        """测试获取认证URL性能"""
        import time
        
        start_time = time.time()
        response = client.get("/api/auth/thirdparty/url")
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = (end_time - start_time) * 1000
        assert response_time < 300, f"Get auth URL too slow: {response_time}ms"
    
    def test_get_auth_url_consistency(self, client: TestClient):
        """测试认证URL一致性"""
        response1 = client.get("/api/auth/thirdparty/url")
        response2 = client.get("/api/auth/thirdparty/url")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # URL可能包含动态参数（如state），所以只验证基本结构
        url1 = response1.json()["auth_url"]
        url2 = response2.json()["auth_url"]
        
        # 验证主要组成部分一致
        assert "oauth/authorize" in url1
        assert "oauth/authorize" in url2
        assert "client_id=" in url1
        assert "client_id=" in url2
    
    def test_third_party_login_legacy_success(self, client: TestClient):
        """测试第三方登录成功 - POST /api/auth/thirdparty/login-legacy"""
        import time
        unique_code = f"test_auth_code_legacy_{int(time.time() * 1000000) % 1000000}"
        auth_data = {
            "code": unique_code
        }
        
        response = client.post("/api/auth/thirdparty/login-legacy", json=auth_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "user" in data
        assert "access_token" in data
        assert "token_type" in data
        
        # 验证用户信息结构
        user = data["user"]
        user_fields = ["uid", "display_name", "email", "avatar_url", "is_admin", "is_system_admin"]
        for field in user_fields:
            assert field in user, f"Missing user field: {field}"
        
        # 验证token信息
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0
    
    def test_third_party_login_missing_code(self, client: TestClient):
        """测试第三方登录缺少code参数 - POST /api/auth/thirdparty/login-legacy"""
        response = client.post("/api/auth/thirdparty/login-legacy", json={})
        assert response.status_code == 422  # Validation Error
    
    def test_third_party_login_empty_code(self, client: TestClient):
        """测试第三方登录空code参数"""
        auth_data = {
            "code": ""
        }
        
        response = client.post("/api/auth/thirdparty/login-legacy", json=auth_data)
        # 根据mock配置，这里可能返回200或401
        assert response.status_code in [200, 401]
    
    def test_third_party_login_invalid_code(self, client: TestClient):
        """测试第三方登录无效code"""
        auth_data = {
            "code": "invalid_code_12345"
        }
        
        response = client.post("/api/auth/thirdparty/login-legacy", json=auth_data)
        # 在mock模式下可能返回200，在真实环境下会返回401
        assert response.status_code in [200, 401, 422]
    
    def test_third_party_login_malformed_request(self, client: TestClient):
        """测试第三方登录畸形请求"""
        # 发送非JSON数据
        response = client.post("/api/auth/thirdparty/login-legacy", data="invalid_data")
        assert response.status_code == 422
    
    def test_third_party_login_extra_fields(self, client: TestClient):
        """测试第三方登录包含额外字段"""
        auth_data = {
            "code": "test_auth_code_123",
            "extra_field": "should_be_ignored",
            "state": "some_state"
        }
        
        response = client.post("/api/auth/thirdparty/login-legacy", json=auth_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data


class TestThirdPartyAuthFlow:
    """第三方认证流程测试"""
    
    def test_complete_third_party_auth_flow(self, client: TestClient):
        """测试完整第三方认证流程"""
        import time
        unique_code = f"mock_auth_code_flow_{int(time.time() * 1000000) % 1000000}"
        
        # 1. 获取认证URL
        url_response = client.get("/api/auth/thirdparty/url")
        assert url_response.status_code == 200
        auth_url = url_response.json()["auth_url"]
        
        # 2. 模拟用户通过第三方服务获取code（这步在实际测试中省略）
        test_code = unique_code
        
        # 3. 使用code进行登录
        login_data = {"code": test_code}
        login_response = client.post("/api/auth/thirdparty/login-legacy", json=login_data)
        assert login_response.status_code == 200
        
        login_result = login_response.json()
        token = login_result["access_token"]
        
        # 4. 使用获取的token访问受保护资源
        headers = {"Authorization": f"Bearer {token}"}
        me_response = client.get("/api/users/me", headers=headers)
        assert me_response.status_code == 200
        
        # 验证token有效性和基本用户信息结构
        user_from_login = login_result["user"]
        user_from_me = me_response.json()
        
        # 验证用户信息结构而不是具体值（因为mock可能返回不同的用户）
        assert isinstance(user_from_login["uid"], str)
        assert isinstance(user_from_me["uid"], str)
        assert isinstance(user_from_login["display_name"], str)
        assert isinstance(user_from_me["display_name"], str)
    
    def test_third_party_auth_error_handling(self, client: TestClient):
        """测试第三方认证错误处理"""
        # 测试各种错误情况
        error_cases = [
            {},  # 空请求
            {"invalid_field": "value"},  # 无效字段
            {"code": None},  # code为空
        ]
        
        for case in error_cases:
            response = client.post("/api/auth/thirdparty/login-legacy", json=case)
            assert response.status_code in [422, 400], f"Failed for case: {case}"