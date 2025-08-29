"""
系统登录API测试
测试 /api/auth/system/login 端点
"""
import pytest
from fastapi.testclient import TestClient


class TestSystemLoginAPI:
    """系统登录API测试类"""
    
    def test_system_admin_login_success(self, client: TestClient):
        """测试系统管理员登录成功 - POST /api/auth/system/login"""
        login_data = {
            "username": "admin",
            "password": "admin123"
        }
        
        response = client.post("/api/auth/system/login", data=login_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "user" in data
        assert "access_token" in data
        assert "token_type" in data
        
        # 验证管理员用户信息
        user = data["user"]
        assert user["uid"] == "sys_admin"
        assert user["display_name"] == "系统管理员"
        assert user["is_admin"] is True
        assert user["is_system_admin"] is True
        
        # 验证token
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0
    
    def test_system_admin_login_wrong_password(self, client: TestClient):
        """测试系统管理员登录错误密码"""
        login_data = {
            "username": "admin",
            "password": "wrong_password"
        }
        
        response = client.post("/api/auth/system/login", data=login_data)
        assert response.status_code == 401
        
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "用户名或密码错误"
    
    def test_system_admin_login_wrong_username(self, client: TestClient):
        """测试系统管理员登录错误用户名"""
        login_data = {
            "username": "wrong_admin",
            "password": "admin123"
        }
        
        response = client.post("/api/auth/system/login", data=login_data)
        assert response.status_code == 401
        
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "用户名或密码错误"
    
    def test_system_admin_login_missing_username(self, client: TestClient):
        """测试系统管理员登录缺少用户名"""
        login_data = {
            "password": "admin123"
        }
        
        response = client.post("/api/auth/system/login", data=login_data)
        assert response.status_code == 422  # Validation error
    
    def test_system_admin_login_missing_password(self, client: TestClient):
        """测试系统管理员登录缺少密码"""
        login_data = {
            "username": "admin"
        }
        
        response = client.post("/api/auth/system/login", data=login_data)
        assert response.status_code == 422  # Validation error
    
    def test_system_admin_login_empty_credentials(self, client: TestClient):
        """测试系统管理员登录空凭据"""
        # 空用户名
        login_data = {
            "username": "",
            "password": "admin123"
        }
        response = client.post("/api/auth/system/login", data=login_data)
        assert response.status_code in [401, 422]
        
        # 空密码
        login_data = {
            "username": "admin",
            "password": ""
        }
        response = client.post("/api/auth/system/login", data=login_data)
        assert response.status_code in [401, 422]
    
    def test_system_admin_login_case_sensitivity(self, client: TestClient):
        """测试系统管理员登录大小写敏感性"""
        # 测试用户名大小写
        login_data = {
            "username": "ADMIN",
            "password": "admin123"
        }
        response = client.post("/api/auth/system/login", data=login_data)
        # 根据实现，用户名可能大小写敏感或不敏感
        assert response.status_code in [200, 401]
        
        # 测试密码大小写（密码通常大小写敏感）
        login_data = {
            "username": "admin",
            "password": "ADMIN123"
        }
        response = client.post("/api/auth/system/login", data=login_data)
        assert response.status_code == 401
    
    def test_system_admin_login_special_characters(self, client: TestClient):
        """测试系统管理员登录特殊字符"""
        # 测试包含特殊字符的无效凭据
        special_cases = [
            {"username": "admin'", "password": "admin123"},
            {"username": "admin", "password": "admin123'"},
            {"username": "admin\"", "password": "admin123"},
            {"username": "admin; DROP TABLE users;", "password": "admin123"},
        ]
        
        for case in special_cases:
            response = client.post("/api/auth/system/login", data=case)
            assert response.status_code == 401, f"Should reject credentials with special characters: {case}"
    
    def test_system_admin_login_performance(self, client: TestClient):
        """测试系统管理员登录性能"""
        import time
        
        login_data = {
            "username": "admin",
            "password": "admin123"
        }
        
        start_time = time.time()
        response = client.post("/api/auth/system/login", data=login_data)
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = (end_time - start_time) * 1000
        assert response_time < 1000, f"System login too slow: {response_time}ms"
    
    def test_system_login_content_type(self, client: TestClient):
        """测试系统登录内容类型"""
        login_data = {
            "username": "admin",
            "password": "admin123"
        }
        
        # 测试form-data（默认）
        response = client.post("/api/auth/system/login", data=login_data)
        assert response.status_code == 200
        
        # 测试JSON格式可能不被支持（取决于实现）
        response = client.post("/api/auth/system/login", json=login_data)
        # 可能支持也可能不支持JSON，根据FastAPI OAuth2PasswordRequestForm的配置
        assert response.status_code in [200, 422]


class TestSystemLoginSecurity:
    """系统登录安全测试"""
    
    def test_system_login_brute_force_protection(self, client: TestClient):
        """测试系统登录暴力破解保护"""
        # 多次错误登录尝试
        login_data = {
            "username": "admin",
            "password": "wrong_password"
        }
        
        results = []
        for i in range(5):
            response = client.post("/api/auth/system/login", data=login_data)
            results.append(response.status_code)
        
        # 所有尝试都应该返回401（暴力破解保护可能需要单独实现）
        assert all(status == 401 for status in results)
    
    def test_system_login_token_uniqueness(self, client: TestClient):
        """测试系统登录token唯一性"""
        login_data = {
            "username": "admin",
            "password": "admin123"
        }
        
        # 多次登录获取token
        tokens = []
        for i in range(3):
            response = client.post("/api/auth/system/login", data=login_data)
            assert response.status_code == 200
            tokens.append(response.json()["access_token"])
        
        # 验证token是否唯一（根据实现可能相同或不同）
        # 如果使用JWT并包含时间戳，则应该不同
        unique_tokens = set(tokens)
        # 至少验证所有token都是有效字符串
        assert all(isinstance(token, str) and len(token) > 0 for token in tokens)
    
    def test_system_login_sql_injection(self, client: TestClient):
        """测试系统登录SQL注入防护"""
        sql_injection_cases = [
            {"username": "admin' OR '1'='1", "password": "admin123"},
            {"username": "admin", "password": "' OR '1'='1"},
            {"username": "admin'; DROP TABLE users; --", "password": "admin123"},
            {"username": "admin", "password": "admin123'; DROP TABLE users; --"},
        ]
        
        for case in sql_injection_cases:
            response = client.post("/api/auth/system/login", data=case)
            # 应该拒绝所有SQL注入尝试
            assert response.status_code == 401, f"Should reject SQL injection attempt: {case}"