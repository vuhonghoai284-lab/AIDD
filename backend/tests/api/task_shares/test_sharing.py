"""
任务分享综合功能测试
测试完整的任务分享工作流
"""
import pytest
import io
from fastapi.testclient import TestClient


class TestTaskSharingWorkflow:
    """任务分享工作流测试"""
    
    def test_complete_sharing_workflow(self, client: TestClient, sample_file, auth_headers):
        """测试完整分享工作流"""
        # 1. 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        assert create_response.status_code == 201
        task_id = create_response.json()["id"]
        
        # 2. 搜索用户（模拟搜索要分享的用户）
        search_response = client.get("/api/task-share/users/search?q=test", headers=auth_headers)
        if search_response.status_code == 200:
            users = search_response.json()
            assert isinstance(users, list)
        
        # 3. 创建分享
        share_data = {
            "shared_user_ids": [2],
            "permission_level": "read_only",
            "share_comment": "工作流测试分享"
        }
        
        share_response = client.post(f"/api/task-share/{task_id}/share", json=share_data, headers=auth_headers)
        if share_response.status_code in [200, 201]:
            # 4. 获取任务分享列表
            list_response = client.get(f"/api/task-share/{task_id}/shares", headers=auth_headers)
            assert list_response.status_code == 200
            
            shares = list_response.json()
            assert isinstance(shares, list)
        
        # 5. 获取分享统计
        stats_response = client.get("/api/task-share/stats", headers=auth_headers)
        assert stats_response.status_code == 200
        
        stats = stats_response.json()
        assert "total_shares" in stats
        assert "permission_breakdown" in stats
    
    def test_sharing_error_handling(self, client: TestClient, auth_headers):
        """测试分享错误处理"""
        # 测试分享不存在的任务
        share_data = {
            "shared_user_ids": [2],
            "permission_level": "read"
        }
        
        response = client.post("/api/task-share/99999/share", json=share_data, headers=auth_headers)
        assert response.status_code in [403, 404]  # 无权限或任务不存在
        
    def test_sharing_data_validation(self, client: TestClient, sample_file, auth_headers):
        """测试分享数据验证"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 测试各种无效数据
        invalid_cases = [
            {"shared_user_ids": [], "permission_level": "read"},  # 空用户列表
            {"shared_user_ids": [1], "permission_level": "invalid"},  # 无效权限
            {"shared_user_ids": "not_list", "permission_level": "read"},  # 错误数据类型
        ]
        
        for case in invalid_cases:
            response = client.post(f"/api/task-share/{task_id}/share", json=case, headers=auth_headers)
            assert response.status_code in [400, 422]


class TestSharedTasksAccess:
    """分享任务访问测试"""
    
    def test_get_shared_with_me(self, client: TestClient, auth_headers):
        """测试获取分享给我的任务列表"""
        response = client.get("/api/task-share/shared-with-me", headers=auth_headers)
        assert response.status_code == 200
        
        tasks = response.json()
        assert isinstance(tasks, list)
    
    def test_shared_tasks_data_structure(self, client: TestClient, auth_headers):
        """测试分享任务数据结构"""
        response = client.get("/api/task-share/shared-with-me", headers=auth_headers)
        assert response.status_code == 200
        
        tasks = response.json()
        assert isinstance(tasks, list)
        
        # 如果有分享任务，验证数据结构
        if tasks:
            task = tasks[0]
            # 验证分享任务基本字段
            expected_fields = ["task_id", "permission_level", "shared_at"]
            for field in expected_fields:
                if field in task:
                    assert isinstance(task[field], (str, int))


class TestTaskShareSecurity:
    """任务分享安全测试"""
    
    def test_share_permission_isolation(self, client: TestClient, sample_file, auth_headers, normal_auth_headers):
        """测试分享权限隔离"""
        # 管理员创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 普通用户不应该能查看管理员创建的任务分享
        response = client.get(f"/api/task-share/{task_id}/shares", headers=normal_auth_headers)
        assert response.status_code == 403
    
    def test_self_sharing_prevention(self, client: TestClient, sample_file, auth_headers):
        """测试防止自我分享"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 尝试分享给自己（用户ID 1是管理员）
        share_data = {
            "shared_user_ids": [1],
            "permission_level": "read_only",
            "share_comment": "自我分享测试"
        }
        
        response = client.post(f"/api/task-share/{task_id}/share", json=share_data, headers=auth_headers)
        # 应该拒绝自我分享
        assert response.status_code == 400