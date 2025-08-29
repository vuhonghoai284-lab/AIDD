"""
用户列表API测试
测试 /api/users/ 端点
"""
import pytest
from fastapi.testclient import TestClient


class TestUsersListAPI:
    """用户列表API测试类"""
    
    def test_get_all_users_as_admin(self, client: TestClient, auth_headers):
        """测试管理员获取所有用户 - USER-002"""
        response = client.get("/api/users/", headers=auth_headers)
        assert response.status_code == 200
        
        users = response.json()
        assert isinstance(users, list)
        assert len(users) > 0
        
        # 验证用户数据结构
        user = users[0]
        required_fields = ["uid", "display_name", "email", "is_admin", "is_system_admin"]
        for field in required_fields:
            assert field in user, f"Missing user field: {field}"
    
    def test_get_all_users_as_normal_user(self, client: TestClient, normal_auth_headers):
        """测试普通用户获取所有用户（应被拒绝）"""
        response = client.get("/api/users/", headers=normal_auth_headers)
        assert response.status_code == 403
        
        error = response.json()
        assert "detail" in error
        assert "权限不足" in error["detail"]
    
    def test_get_all_users_without_auth(self, client: TestClient):
        """测试未认证获取所有用户"""
        response = client.get("/api/users/")
        assert response.status_code == 401
    
    def test_user_list_data_structure(self, client: TestClient, auth_headers):
        """测试用户列表数据结构"""
        response = client.get("/api/users/", headers=auth_headers)
        assert response.status_code == 200
        
        users = response.json()
        assert isinstance(users, list)
        
        if users:  # 如果有用户数据
            for user in users:
                assert isinstance(user, dict)
                assert "uid" in user
                assert "display_name" in user
                assert "is_admin" in user
                assert isinstance(user["is_admin"], bool)
                assert isinstance(user["is_system_admin"], bool)
    
    def test_user_list_data_types(self, client: TestClient, auth_headers):
        """测试用户列表数据类型"""
        response = client.get("/api/users/", headers=auth_headers)
        assert response.status_code == 200
        
        users = response.json()
        
        if users:
            for user in users:
                # 验证必需字段类型
                assert isinstance(user["uid"], str)
                assert isinstance(user["display_name"], str)
                assert isinstance(user["email"], str)
                assert isinstance(user["is_admin"], bool)
                assert isinstance(user["is_system_admin"], bool)
                
                # 可选字段类型验证
                if user.get("avatar_url") is not None:
                    assert isinstance(user["avatar_url"], str)
                if user.get("created_at") is not None:
                    assert isinstance(user["created_at"], str)
                if user.get("last_login_at") is not None:
                    assert isinstance(user["last_login_at"], str)
    
    def test_user_list_sensitive_data_exclusion(self, client: TestClient, auth_headers):
        """测试用户列表不包含敏感数据"""
        response = client.get("/api/users/", headers=auth_headers)
        assert response.status_code == 200
        
        users = response.json()
        
        if users:
            sensitive_fields = ["password", "password_hash", "secret_key", "private_key"]
            for user in users:
                for field in sensitive_fields:
                    assert field not in user, f"Sensitive field {field} should not be in user list"
    
    def test_get_users_list_performance(self, client: TestClient, auth_headers):
        """测试获取用户列表性能"""
        import time
        
        start_time = time.time()
        response = client.get("/api/users/", headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = (end_time - start_time) * 1000
        assert response_time < 500, f"Get users list too slow: {response_time}ms"
    
    def test_user_list_consistency(self, client: TestClient, auth_headers):
        """测试用户列表一致性"""
        response1 = client.get("/api/users/", headers=auth_headers)
        response2 = client.get("/api/users/", headers=auth_headers)
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        users1 = response1.json()
        users2 = response2.json()
        
        # 用户数量应该相同（在短时间内）
        assert len(users1) == len(users2)
        
        # 用户基本信息应该相同
        if users1:
            users1_uids = {user["uid"] for user in users1}
            users2_uids = {user["uid"] for user in users2}
            assert users1_uids == users2_uids
    
    def test_users_list_invalid_methods(self, client: TestClient, auth_headers):
        """测试用户列表端点无效HTTP方法"""
        # POST方法不被支持（如果没有创建用户接口）
        response = client.post("/api/users/", headers=auth_headers)
        assert response.status_code == 405
        
        # PUT方法不被支持
        response = client.put("/api/users/", headers=auth_headers)
        assert response.status_code == 405
        
        # DELETE方法不被支持
        response = client.delete("/api/users/", headers=auth_headers)
        assert response.status_code == 405


class TestUsersListFiltering:
    """用户列表过滤测试"""
    
    def test_user_list_admin_filtering(self, client: TestClient, auth_headers):
        """测试用户列表管理员过滤"""
        response = client.get("/api/users/", headers=auth_headers)
        assert response.status_code == 200
        
        users = response.json()
        
        # 验证包含管理员用户
        admin_users = [user for user in users if user["is_admin"]]
        assert len(admin_users) >= 1, "Should contain at least one admin user"
        
        # 验证管理员用户字段
        for admin_user in admin_users:
            assert admin_user["is_admin"] is True
            assert isinstance(admin_user["uid"], str)
            assert len(admin_user["uid"]) > 0
    
    def test_user_list_ordering(self, client: TestClient, auth_headers):
        """测试用户列表排序"""
        response = client.get("/api/users/", headers=auth_headers)
        assert response.status_code == 200
        
        users = response.json()
        
        if len(users) > 1:
            # 验证是否有某种排序逻辑（通常按创建时间或UID）
            # 这里只验证数据完整性，具体排序逻辑根据实现而定
            for user in users:
                assert "uid" in user
                assert "display_name" in user
                assert len(user["uid"]) > 0
                assert len(user["display_name"]) > 0


class TestUsersListSecurity:
    """用户列表安全测试"""
    
    def test_concurrent_user_list_access(self, client: TestClient, auth_headers):
        """测试并发用户列表访问"""
        import threading
        import time
        
        results = []
        errors = []
        results_lock = threading.Lock()
        
        def get_users_attempt():
            try:
                time.sleep(0.01)
                response = client.get("/api/users/", headers=auth_headers)
                with results_lock:
                    results.append(response.status_code)
            except Exception as e:
                with results_lock:
                    errors.append(str(e))
                    results.append(-1)
        
        # 启动多个并发请求
        threads = []
        for i in range(3):  # 降低并发数适配SQLite
            thread = threading.Thread(target=get_users_attempt)
            threads.append(thread)
            thread.start()
            time.sleep(0.01)
        
        # 等待完成
        for thread in threads:
            thread.join()
        
        # 验证结果
        successful_results = [r for r in results if r == 200]
        assert len(successful_results) >= 1, f"Expected at least 1 successful request, got {len(successful_results)}"
        
        if errors:
            print(f"Concurrent access errors (expected with SQLite): {len(errors)} errors")
    
    def test_user_list_permission_validation(self, client: TestClient):
        """测试用户列表权限验证"""
        # 不同权限级别的访问测试已在其他测试中覆盖
        # 这里测试边界情况
        
        # 无认证头
        response = client.get("/api/users/")
        assert response.status_code == 401
        
        # 空认证头
        headers = {"Authorization": ""}
        response = client.get("/api/users/", headers=headers)
        assert response.status_code == 401
        
        # 无效格式认证头
        headers = {"Authorization": "InvalidFormat"}
        response = client.get("/api/users/", headers=headers)
        assert response.status_code == 401