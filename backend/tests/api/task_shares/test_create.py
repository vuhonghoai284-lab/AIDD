"""
任务分享创建API测试
测试 POST /api/task-share/{task_id}/share 端点
"""
import pytest
import io
from fastapi.testclient import TestClient


class TestTaskShareCreateAPI:
    """任务分享创建API测试类"""
    
    def test_create_task_share_success(self, client: TestClient, sample_file, auth_headers):
        """测试创建任务分享成功 - POST /api/task-share/{task_id}/share"""
        # 先创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        assert create_response.status_code == 201
        task_id = create_response.json()["id"]
        
        # 等待任务创建完成
        import time
        time.sleep(1)
        
        # 创建分享（分享给测试用户）
        share_data = {
            "shared_user_ids": [2],  # 假设存在用户ID为2的测试用户
            "permission_level": "read_only",
            "share_comment": "测试任务分享"
        }
        
        response = client.post(f"/api/task-share/{task_id}/share", json=share_data, headers=auth_headers)
        assert response.status_code in [200, 201]
        
        if response.status_code in [200, 201]:
            share = response.json()
            assert "success_count" in share
            assert "failed_count" in share
            assert "created_shares" in share
    
    def test_create_task_share_not_found(self, client: TestClient, auth_headers):
        """测试分享不存在任务"""
        share_data = {
            "shared_user_ids": [2],
            "permission_level": "read_only",
            "share_comment": "不存在任务的分享"
        }
        
        response = client.post("/api/task-share/99999/share", json=share_data, headers=auth_headers)
        assert response.status_code in [403, 404]  # 无权限或任务不存在
        
        error = response.json()
        assert "detail" in error
    
    def test_create_task_share_without_auth(self, client: TestClient):
        """测试未认证创建任务分享"""
        share_data = {
            "shared_user_ids": [2],
            "permission_level": "read_only",
            "share_comment": "测试分享"
        }
        
        response = client.post("/api/task-share/1/share", json=share_data)
        assert response.status_code == 401
    
    def test_create_task_share_permission_denied(self, client: TestClient, sample_file, auth_headers, normal_auth_headers):
        """测试分享他人任务权限拒绝"""
        # 管理员创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 普通用户尝试分享
        share_data = {
            "shared_user_ids": [3],
            "permission_level": "read_only",
            "share_comment": "权限测试分享"
        }
        
        response = client.post(f"/api/task-share/{task_id}/share", json=share_data, headers=normal_auth_headers)
        assert response.status_code == 403
    
    def test_create_task_share_invalid_data(self, client: TestClient, auth_headers):
        """测试创建任务分享无效数据"""
        invalid_data_sets = [
            {},  # 空数据
            {"permission_level": "read"},  # 缺少shared_user_ids
            {"shared_user_ids": []},  # 空用户列表
            {"shared_user_ids": [1], "permission_level": "invalid"},  # 无效权限级别
            {"shared_user_ids": ["abc"]},  # 无效用户ID格式
        ]
        
        for data in invalid_data_sets:
            response = client.post("/api/task-share/1/share", json=data, headers=auth_headers)
            assert response.status_code in [400, 422]


class TestTaskShareCreateValidation:
    """任务分享创建验证测试"""
    
    def test_create_share_data_structure(self, client: TestClient, sample_file, auth_headers):
        """测试创建分享响应数据结构"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        share_data = {
            "shared_user_ids": [2],
            "permission_level": "read_only",
            "share_comment": "数据结构测试"
        }
        
        response = client.post(f"/api/task-share/{task_id}/share", json=share_data, headers=auth_headers)
        
        if response.status_code in [200, 201]:
            data = response.json()
            required_fields = ["success_count", "failed_count", "created_shares"]
            for field in required_fields:
                assert field in data, f"Missing field: {field}"
            
            assert isinstance(data["success_count"], int)
            assert isinstance(data["failed_count"], int)
            assert isinstance(data["created_shares"], list)


class TestTaskShareCreateMethods:
    """任务分享创建HTTP方法测试"""
    
    def test_task_share_create_invalid_methods(self, client: TestClient, auth_headers):
        """测试任务分享创建端点无效HTTP方法"""
        task_id = 1
        
        # GET方法不被支持
        response = client.get(f"/api/task-share/{task_id}/share", headers=auth_headers)
        assert response.status_code == 405
        
        # PUT方法不被支持
        response = client.put(f"/api/task-share/{task_id}/share", headers=auth_headers)
        assert response.status_code == 405
        
        # DELETE方法不被支持
        response = client.delete(f"/api/task-share/{task_id}/share", headers=auth_headers)
        assert response.status_code == 405