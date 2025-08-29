"""
任务分享访问API测试
测试用户搜索和分享统计功能
"""
import pytest
import io
from fastapi.testclient import TestClient


class TestUserSearchAPI:
    """用户搜索API测试"""
    
    def test_search_users_success(self, client: TestClient, auth_headers):
        """测试用户搜索成功 - GET /api/task-share/users/search"""
        response = client.get("/api/task-share/users/search?q=test", headers=auth_headers)
        assert response.status_code == 200
        
        users = response.json()
        assert isinstance(users, list)
    
    def test_search_users_with_limit(self, client: TestClient, auth_headers):
        """测试用户搜索带限制"""
        response = client.get("/api/task-share/users/search?q=user&limit=5", headers=auth_headers)
        assert response.status_code == 200
        
        users = response.json()
        assert isinstance(users, list)
        assert len(users) <= 5
    
    def test_search_users_invalid_query(self, client: TestClient, auth_headers):
        """测试用户搜索无效查询"""
        # 查询字符串太短
        response = client.get("/api/task-share/users/search?q=a", headers=auth_headers)
        assert response.status_code == 422
        
        # 缺少查询参数
        response = client.get("/api/task-share/users/search", headers=auth_headers)
        assert response.status_code == 422
    
    def test_search_users_without_auth(self, client: TestClient):
        """测试未认证搜索用户"""
        response = client.get("/api/task-share/users/search?q=test")
        assert response.status_code == 401


class TestShareStatsAPI:
    """分享统计API测试"""
    
    def test_get_share_stats_success(self, client: TestClient, auth_headers):
        """测试获取分享统计成功 - GET /api/task-share/stats"""
        response = client.get("/api/task-share/stats", headers=auth_headers)
        assert response.status_code == 200
        
        stats = response.json()
        expected_fields = ["total_shares", "active_shares", "permission_breakdown"]
        for field in expected_fields:
            assert field in stats, f"Missing stats field: {field}"
        
        assert isinstance(stats["total_shares"], int)
        assert isinstance(stats["active_shares"], int)
        assert isinstance(stats["permission_breakdown"], dict)
    
    def test_get_share_stats_without_auth(self, client: TestClient):
        """测试未认证获取分享统计"""
        response = client.get("/api/task-share/stats")
        assert response.status_code == 401
    
    def test_share_stats_data_structure(self, client: TestClient, auth_headers):
        """测试分享统计数据结构"""
        response = client.get("/api/task-share/stats", headers=auth_headers)
        assert response.status_code == 200
        
        stats = response.json()
        
        # 验证权限分布结构
        permission_breakdown = stats["permission_breakdown"]
        for permission, count in permission_breakdown.items():
            assert isinstance(permission, str)
            assert isinstance(count, int)
            assert count >= 0


class TestTaskShareValidation:
    """任务分享验证测试"""
    
    def test_share_permission_levels(self, client: TestClient, sample_file, auth_headers):
        """测试分享权限级别验证"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        valid_permissions = ["read_only", "full_access", "feedback_only"]
        
        for permission in valid_permissions:
            share_data = {
                "shared_user_ids": [2],
                "permission_level": permission,
                "share_comment": f"测试{permission}权限"
            }
            
            response = client.post(f"/api/task-share/{task_id}/share", json=share_data, headers=auth_headers)
            # 权限级别有效，应该成功或返回业务错误（如用户不存在）
            assert response.status_code in [200, 201, 400]
    
    def test_share_user_validation(self, client: TestClient, sample_file, auth_headers):
        """测试分享用户验证"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 测试分享给不存在的用户
        share_data = {
            "shared_user_ids": [99999],
            "permission_level": "read_only",
            "share_comment": "分享给不存在用户"
        }
        
        response = client.post(f"/api/task-share/{task_id}/share", json=share_data, headers=auth_headers)
        assert response.status_code == 400  # 应该返回用户不存在错误


class TestShareMethodsValidation:
    """分享方法验证测试"""
    
    def test_user_search_methods(self, client: TestClient, auth_headers):
        """测试用户搜索HTTP方法"""
        # POST方法不被支持
        response = client.post("/api/task-share/users/search", headers=auth_headers)
        assert response.status_code == 405
        
        # PUT方法不被支持
        response = client.put("/api/task-share/users/search", headers=auth_headers)
        assert response.status_code == 405
        
        # DELETE方法不被支持
        response = client.delete("/api/task-share/users/search", headers=auth_headers)
        assert response.status_code == 405
    
    def test_stats_methods(self, client: TestClient, auth_headers):
        """测试分享统计HTTP方法"""
        # POST方法不被支持
        response = client.post("/api/task-share/stats", headers=auth_headers)
        assert response.status_code == 405
        
        # PUT方法不被支持
        response = client.put("/api/task-share/stats", headers=auth_headers)
        assert response.status_code == 405
        
        # DELETE方法不被支持
        response = client.delete("/api/task-share/stats", headers=auth_headers)
        assert response.status_code == 405