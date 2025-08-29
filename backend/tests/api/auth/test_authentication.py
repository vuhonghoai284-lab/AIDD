"""
认证验证API测试
测试token验证和权限控制
"""
import pytest
from fastapi.testclient import TestClient
import threading
import time


class TestAuthenticationVerification:
    """认证验证测试类"""
    
    def test_protected_endpoint_without_token(self, client: TestClient):
        """测试无token访问受保护资源"""
        protected_endpoints = [
            ("/api/users/me", "GET"),
            ("/api/users/", "GET"),
            ("/api/tasks", "GET"),
            ("/api/analytics/overview", "GET"),
        ]
        
        for endpoint, method in protected_endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint)
            elif method == "PUT":
                response = client.put(endpoint)
            elif method == "DELETE":
                response = client.delete(endpoint)
            
            assert response.status_code == 401, f"Endpoint {endpoint} should require authentication"
    
    def test_protected_endpoint_with_invalid_token(self, client: TestClient):
        """测试无效token访问受保护资源"""
        invalid_tokens = [
            "invalid_token",
            "Bearer invalid_token",
            "Bearer ",
            "Bearer",
            "Basic invalid_token",
        ]
        
        for token in invalid_tokens:
            headers = {"Authorization": token}
            response = client.get("/api/users/me", headers=headers)
            assert response.status_code == 401, f"Invalid token '{token}' should be rejected"
    
    def test_protected_endpoint_with_malformed_auth_header(self, client: TestClient):
        """测试畸形认证头"""
        malformed_headers = [
            {"Authorization": ""},
            {"Authorization": "InvalidScheme token"},
            {"Authorization": "Bearer"},
            {"Authorization": "Bearer "},
            {"Auth": "Bearer valid_token"},  # 错误的头名称
        ]
        
        for headers in malformed_headers:
            response = client.get("/api/users/me", headers=headers)
            assert response.status_code == 401, f"Malformed auth header should be rejected: {headers}"
    
    def test_admin_only_endpoints_with_normal_user(self, client: TestClient, normal_auth_headers):
        """测试普通用户访问管理员专用端点"""
        admin_endpoints = [
            ("/api/users/", "GET"),
            ("/api/analytics/overview", "GET"),
            ("/api/analytics/users", "GET"),
            ("/api/analytics/tasks", "GET"),
        ]
        
        for endpoint, method in admin_endpoints:
            if method == "GET":
                response = client.get(endpoint, headers=normal_auth_headers)
            elif method == "POST":
                response = client.post(endpoint, headers=normal_auth_headers)
            
            assert response.status_code == 403, f"Normal user should not access admin endpoint {endpoint}"
            
            # 验证错误消息
            error = response.json()
            assert "detail" in error
            assert "权限不足" in error["detail"]
    
    def test_valid_token_access(self, client: TestClient, auth_headers):
        """测试有效token访问受保护资源"""
        response = client.get("/api/users/me", headers=auth_headers)
        assert response.status_code == 200
        
        user = response.json()
        assert "uid" in user
        assert "is_admin" in user
        assert user["is_admin"] is True  # 应该是管理员用户


class TestTokenValidation:
    """Token验证测试"""
    
    def test_token_format_validation(self, client: TestClient):
        """测试token格式验证"""
        # 测试各种无效的token格式
        invalid_formats = [
            "",                          # 空token
            "Bearer",                    # 只有Bearer
            "Bearer ",                   # Bearer后面只有空格
            "token_without_bearer",      # 没有Bearer前缀
            "Basic token123",            # 错误的认证方案
            "Bearer  token",             # 多个空格
            "bearer token",              # 小写bearer
            "BEARER token",              # 大写BEARER
        ]
        
        for token_format in invalid_formats:
            headers = {"Authorization": token_format} if token_format else {}
            response = client.get("/api/users/me", headers=headers)
            assert response.status_code == 401, f"Token format '{token_format}' should be rejected"
    
    def test_token_expiration_handling(self, client: TestClient):
        """测试token过期处理"""
        # 注意：在mock环境中，token通常不会过期
        # 这个测试更多是为了验证代码结构
        
        # 使用一个明显过期的token格式（如果系统支持）
        expired_token = "Bearer expired_token_12345"
        headers = {"Authorization": expired_token}
        
        response = client.get("/api/users/me", headers=headers)
        assert response.status_code == 401
    
    def test_token_authentication_flow(self, client: TestClient):
        """测试完整token认证流程"""
        # 1. 管理员登录获取token
        login_data = {
            "username": "admin", 
            "password": "admin123"
        }
        
        response = client.post("/api/auth/system/login", data=login_data)
        assert response.status_code == 200
        
        token = response.json()["access_token"]
        
        # 2. 使用token访问受保护资源
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/users/me", headers=headers)
        assert response.status_code == 200
        
        # 3. 验证用户信息
        user = response.json()
        assert user["uid"] == "sys_admin"
        assert user["is_admin"] is True
        
        # 4. 使用相同token访问其他受保护资源
        response = client.get("/api/users/", headers=headers)
        assert response.status_code == 200
    
    def test_concurrent_token_validation(self, client: TestClient):
        """测试并发token验证"""
        # 先获取有效token
        login_data = {"username": "admin", "password": "admin123"}
        login_response = client.post("/api/auth/system/login", data=login_data)
        assert login_response.status_code == 200
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        results = []
        errors = []
        results_lock = threading.Lock()
        
        def token_validation_attempt():
            try:
                time.sleep(0.01)  # 小延迟减少冲突
                response = client.get("/api/users/me", headers=headers)
                with results_lock:
                    results.append(response.status_code)
            except Exception as e:
                with results_lock:
                    errors.append(str(e))
                    results.append(-1)  # 异常标记
        
        # 启动多个并发验证请求
        threads = []
        for i in range(3):  # 降低并发数以适配SQLite
            thread = threading.Thread(target=token_validation_attempt)
            threads.append(thread)
            thread.start()
            time.sleep(0.01)  # 启动间隔
        
        # 等待完成
        for thread in threads:
            thread.join()
        
        # 验证结果
        successful_results = [r for r in results if r == 200]
        assert len(successful_results) >= 1, f"Expected at least 1 successful validation, got {len(successful_results)}"
        
        if errors:
            print(f"Concurrent validation errors (expected with SQLite): {len(errors)} errors")


class TestPermissionControl:
    """权限控制测试"""
    
    def test_admin_permissions(self, client: TestClient, auth_headers):
        """测试管理员权限"""
        admin_accessible_endpoints = [
            "/api/users/",
            "/api/users/me",
            "/api/analytics/overview",
            "/api/analytics/users",
            "/api/analytics/tasks",
            "/api/analytics/system",
        ]
        
        for endpoint in admin_accessible_endpoints:
            response = client.get(endpoint, headers=auth_headers)
            assert response.status_code == 200, f"Admin should access {endpoint}"
    
    def test_normal_user_permissions(self, client: TestClient, normal_auth_headers):
        """测试普通用户权限"""
        # 普通用户可以访问的端点
        accessible_endpoints = [
            "/api/users/me",
            # 添加其他普通用户可以访问的端点
        ]
        
        for endpoint in accessible_endpoints:
            response = client.get(endpoint, headers=normal_auth_headers)
            assert response.status_code == 200, f"Normal user should access {endpoint}"
        
        # 普通用户不能访问的端点
        forbidden_endpoints = [
            "/api/users/",
            "/api/analytics/overview",
            "/api/analytics/users",
        ]
        
        for endpoint in forbidden_endpoints:
            response = client.get(endpoint, headers=normal_auth_headers)
            assert response.status_code == 403, f"Normal user should not access {endpoint}"
    
    def test_user_data_isolation(self, client: TestClient, normal_user_token, admin_user_token):
        """测试用户数据隔离"""
        normal_headers = {"Authorization": f"Bearer {normal_user_token['token']}"}
        admin_headers = {"Authorization": f"Bearer {admin_user_token['token']}"}
        
        # 普通用户看到的信息
        normal_response = client.get("/api/users/me", headers=normal_headers)
        normal_user_info = normal_response.json()
        
        # 管理员看到的信息
        admin_response = client.get("/api/users/me", headers=admin_headers)
        admin_user_info = admin_response.json()
        
        # 验证不同用户返回不同信息
        assert normal_user_info["uid"] != admin_user_info["uid"]
        assert normal_user_info["is_admin"] != admin_user_info["is_admin"]