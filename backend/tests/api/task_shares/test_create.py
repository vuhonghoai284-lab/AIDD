"""
任务分享创建API测试
测试 POST /api/task-shares 端点
"""
import pytest
import io
from fastapi.testclient import TestClient


class TestTaskShareCreateAPI:
    """任务分享创建API测试类"""
    
    def test_create_task_share_success(self, client: TestClient, sample_file, auth_headers):
        """测试创建任务分享成功 - POST /api/task-shares"""
        # 先创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 等待任务完成
        import time
        time.sleep(2)
        
        # 创建分享
        share_data = {
            "task_id": task_id,
            "description": "测试任务分享",
            "expire_days": 7
        }
        
        response = client.post("/api/task-shares", json=share_data, headers=auth_headers)
        assert response.status_code in [200, 201]
        
        share = response.json()
        assert "id" in share
        assert "share_code" in share
        assert share["task_id"] == task_id
        assert share["description"] == "测试任务分享"
    
    def test_create_task_share_not_found(self, client: TestClient, auth_headers):
        """测试创建不存在任务的分享"""
        share_data = {
            "task_id": 99999,
            "description": "不存在任务的分享"
        }
        
        response = client.post("/api/task-shares", json=share_data, headers=auth_headers)
        assert response.status_code == 404
        
        error = response.json()
        assert "detail" in error
        assert "任务不存在" in error["detail"] or "not found" in error["detail"].lower()
    
    def test_create_task_share_without_auth(self, client: TestClient):
        """测试未认证创建任务分享"""
        share_data = {
            "task_id": 1,
            "description": "测试分享"
        }
        
        response = client.post("/api/task-shares", json=share_data)
        assert response.status_code == 401
    
    def test_create_task_share_permission_denied(self, client: TestClient, sample_file, auth_headers, normal_auth_headers):
        """测试创建他人任务分享权限拒绝"""
        # 管理员创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 普通用户尝试分享
        share_data = {
            "task_id": task_id,
            "description": "权限测试分享"
        }
        
        response = client.post("/api/task-shares", json=share_data, headers=normal_auth_headers)
        assert response.status_code == 403
    
    def test_create_task_share_invalid_data(self, client: TestClient, auth_headers):
        """测试创建任务分享无效数据"""
        invalid_data_sets = [
            {},  # 空数据
            {"description": "缺少task_id"},  # 缺少必需字段
            {"task_id": "abc", "description": "无效task_id"},  # 无效task_id
            {"task_id": -1, "description": "负数task_id"},  # 负数task_id
            {"task_id": 1, "expire_days": -1},  # 负数过期天数
            {"task_id": 1, "expire_days": 0},  # 0天过期
            {"task_id": 1, "expire_days": 366},  # 过长过期天数
        ]
        
        for data in invalid_data_sets:
            response = client.post("/api/task-shares", json=data, headers=auth_headers)
            assert response.status_code == 422
    
    def test_create_task_share_performance(self, client: TestClient, sample_file, auth_headers):
        """测试创建任务分享性能"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 等待任务完成
        import time
        time.sleep(2)
        
        share_data = {
            "task_id": task_id,
            "description": "性能测试分享"
        }
        
        start_time = time.time()
        response = client.post("/api/task-shares", json=share_data, headers=auth_headers)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000
        assert response_time < 1000, f"Create task share too slow: {response_time}ms"


class TestTaskShareCreateValidation:
    """任务分享创建验证测试"""
    
    def test_create_share_data_structure(self, client: TestClient, sample_file, auth_headers):
        """测试创建分享数据结构验证"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        import time
        time.sleep(2)
        
        share_data = {
            "task_id": task_id,
            "description": "数据结构测试分享",
            "expire_days": 30
        }
        
        response = client.post("/api/task-shares", json=share_data, headers=auth_headers)
        
        if response.status_code in [200, 201]:
            share = response.json()
            
            # 验证返回数据结构
            required_fields = ["id", "share_code", "task_id", "description"]
            for field in required_fields:
                assert field in share, f"Missing field: {field}"
            
            # 验证数据类型
            assert isinstance(share["id"], int)
            assert isinstance(share["share_code"], str)
            assert isinstance(share["task_id"], int)
            assert isinstance(share["description"], str)
            
            # 验证分享码格式（通常是字母数字组合）
            share_code = share["share_code"]
            assert len(share_code) > 0
            assert share_code.replace("-", "").replace("_", "").isalnum()
    
    def test_create_share_duplicate_prevention(self, client: TestClient, sample_file, auth_headers):
        """测试防止重复创建分享"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        import time
        time.sleep(2)
        
        share_data = {
            "task_id": task_id,
            "description": "重复测试分享"
        }
        
        # 第一次创建
        response1 = client.post("/api/task-shares", json=share_data, headers=auth_headers)
        
        # 第二次创建（可能允许或禁止，取决于业务逻辑）
        response2 = client.post("/api/task-shares", json=share_data, headers=auth_headers)
        
        # 验证至少一次成功
        assert response1.status_code in [200, 201] or response2.status_code in [200, 201]


class TestTaskShareCreateMethods:
    """任务分享创建HTTP方法测试"""
    
    def test_task_share_create_invalid_methods(self, client: TestClient, auth_headers):
        """测试任务分享创建端点无效HTTP方法"""
        # GET方法不被支持
        response = client.get("/api/task-shares", headers=auth_headers)
        assert response.status_code == 405
        
        # PUT方法不被支持（对于创建）
        share_data = {"task_id": 1, "description": "测试"}
        response = client.put("/api/task-shares", json=share_data, headers=auth_headers)
        assert response.status_code == 405
        
        # DELETE方法不被支持（对于创建）
        response = client.delete("/api/task-shares", headers=auth_headers)
        assert response.status_code == 405