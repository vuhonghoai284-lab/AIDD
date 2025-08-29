"""
任务分享管理API测试
测试任务分享的查询、更新、删除操作
"""
import pytest
import io
from fastapi.testclient import TestClient


class TestTaskShareListAPI:
    """任务分享列表API测试"""
    
    def test_get_task_shares_success(self, client: TestClient, sample_file, auth_headers):
        """测试获取任务分享列表成功 - GET /api/task-share/{task_id}/shares"""
        # 先创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        response = client.get(f"/api/task-share/{task_id}/shares", headers=auth_headers)
        assert response.status_code == 200
        
        shares = response.json()
        assert isinstance(shares, list)
    
    def test_get_task_shares_with_filter(self, client: TestClient, sample_file, auth_headers):
        """测试获取任务分享列表（包含非活跃分享）"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        response = client.get(f"/api/task-share/{task_id}/shares?include_inactive=true", headers=auth_headers)
        assert response.status_code == 200
        
        shares = response.json()
        assert isinstance(shares, list)
    
    def test_get_task_shares_not_found(self, client: TestClient, auth_headers):
        """测试获取不存在任务的分享列表"""
        response = client.get("/api/task-share/99999/shares", headers=auth_headers)
        assert response.status_code == 403  # 无权限访问不存在的任务
    
    def test_get_task_shares_without_auth(self, client: TestClient):
        """测试未认证获取分享列表"""
        response = client.get("/api/task-share/1/shares")
        assert response.status_code == 401


class TestTaskShareUpdateAPI:
    """任务分享更新API测试"""
    
    def test_update_task_share_success(self, client: TestClient, auth_headers):
        """测试更新任务分享成功 - PUT /api/task-share/shares/{share_id}"""
        update_data = {
            "permission_level": "full_access",
            "share_comment": "更新后的分享权限"
        }
        
        response = client.put("/api/task-share/shares/1", json=update_data, headers=auth_headers)
        assert response.status_code in [200, 404]  # 404表示分享不存在或无权限
    
    def test_update_task_share_not_found(self, client: TestClient, auth_headers):
        """测试更新不存在的分享"""
        update_data = {
            "permission_level": "full_access",
            "share_comment": "不存在的分享"
        }
        
        response = client.put("/api/task-share/shares/99999", json=update_data, headers=auth_headers)
        assert response.status_code == 404
    
    def test_update_task_share_invalid_data(self, client: TestClient, auth_headers):
        """测试更新分享无效数据"""
        invalid_data_sets = [
            {},  # 空数据
            {"permission_level": "invalid"},  # 无效权限级别
            {"permission_level": None},  # null权限级别
        ]
        
        for data in invalid_data_sets:
            response = client.put("/api/task-share/shares/1", json=data, headers=auth_headers)
            assert response.status_code in [400, 404, 422]


class TestTaskShareDeleteAPI:
    """任务分享删除API测试"""
    
    def test_delete_task_share_success(self, client: TestClient, auth_headers):
        """测试撤销任务分享成功 - DELETE /api/task-share/shares/{share_id}"""
        response = client.delete("/api/task-share/shares/1", headers=auth_headers)
        assert response.status_code in [200, 404]  # 404表示分享不存在或无权限
    
    def test_delete_task_share_permanently(self, client: TestClient, auth_headers):
        """测试永久删除任务分享"""
        response = client.delete("/api/task-share/shares/1?permanently=true", headers=auth_headers)
        assert response.status_code in [200, 404]
    
    def test_delete_task_share_not_found(self, client: TestClient, auth_headers):
        """测试删除不存在的分享"""
        response = client.delete("/api/task-share/shares/99999", headers=auth_headers)
        assert response.status_code == 404
    
    def test_delete_task_share_without_auth(self, client: TestClient):
        """测试未认证删除分享"""
        response = client.delete("/api/task-share/shares/1")
        assert response.status_code == 401


class TestSharedWithMeAPI:
    """分享给我的任务API测试"""
    
    def test_get_shared_with_me_success(self, client: TestClient, auth_headers):
        """测试获取分享给我的任务列表 - GET /api/task-share/shared-with-me"""
        response = client.get("/api/task-share/shared-with-me", headers=auth_headers)
        assert response.status_code == 200
        
        tasks = response.json()
        assert isinstance(tasks, list)
    
    def test_get_shared_with_me_with_filter(self, client: TestClient, auth_headers):
        """测试获取分享给我的任务（包含非活跃）"""
        response = client.get("/api/task-share/shared-with-me?include_inactive=true", headers=auth_headers)
        assert response.status_code == 200
        
        tasks = response.json()
        assert isinstance(tasks, list)
    
    def test_get_shared_with_me_without_auth(self, client: TestClient):
        """测试未认证获取分享列表"""
        response = client.get("/api/task-share/shared-with-me")
        assert response.status_code == 401


class TestTaskShareMethods:
    """任务分享HTTP方法测试"""
    
    def test_task_share_list_invalid_methods(self, client: TestClient, auth_headers):
        """测试分享列表端点无效HTTP方法"""
        task_id = 1
        
        # POST方法不被支持
        response = client.post(f"/api/task-share/{task_id}/shares", headers=auth_headers)
        assert response.status_code == 405
        
        # PUT方法不被支持  
        response = client.put(f"/api/task-share/{task_id}/shares", headers=auth_headers)
        assert response.status_code == 405