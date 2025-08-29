"""
任务CRUD API测试
测试任务的创建、读取、更新、删除操作
"""
import pytest
import time
import io
from fastapi.testclient import TestClient


class TestTaskCreateAPI:
    """任务创建API测试类"""
    
    def test_create_task_success(self, client: TestClient, sample_file, auth_headers):
        """测试创建任务成功 - POST /api/tasks/"""
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        data = {"title": "测试任务", "ai_model_index": "0"}
        
        response = client.post("/api/tasks/", files=files, data=data, headers=auth_headers)
        assert response.status_code == 200  # 根据实际实现调整
        
        task = response.json()
        assert "id" in task
        assert task["title"] == "测试任务"
        assert task["file_name"] == filename
        assert task["status"] == "pending"
        assert "created_at" in task
        assert "ai_model_label" in task
        
        return task["id"]
    
    def test_create_task_without_auth(self, client: TestClient, sample_file):
        """测试未认证创建任务"""
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        
        response = client.post("/api/tasks/", files=files)
        assert response.status_code == 401
    
    def test_create_task_missing_file(self, client: TestClient, auth_headers):
        """测试创建任务缺少文件"""
        data = {"title": "测试任务", "ai_model_index": "0"}
        
        response = client.post("/api/tasks/", data=data, headers=auth_headers)
        assert response.status_code == 422  # Validation error
    
    def test_create_task_invalid_ai_model_index(self, client: TestClient, sample_file, auth_headers):
        """测试创建任务无效AI模型索引"""
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        
        # 测试无效索引
        invalid_indices = ["999", "-1", "abc", ""]
        
        for invalid_index in invalid_indices:
            data = {"ai_model_index": invalid_index}
            response = client.post("/api/tasks/", files=files, data=data, headers=auth_headers)
            assert response.status_code in [400, 422], f"Should reject invalid index: {invalid_index}"
    
    def test_create_task_with_invalid_file_type(self, client: TestClient, invalid_file, auth_headers):
        """测试不支持的文件类型"""
        filename, content, content_type = invalid_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        
        response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        assert response.status_code == 400
        
        error = response.json()
        assert "detail" in error
        assert "不支持的文件类型" in error["detail"]
    
    def test_create_task_with_large_file(self, client: TestClient, auth_headers):
        """测试超大文件上传"""
        # 创建超过10MB的文件
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB
        files = {"file": ("large.md", io.BytesIO(large_content), "text/markdown")}
        
        response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        assert response.status_code == 400
        
        error = response.json()
        assert "detail" in error
        assert "文件大小超过限制" in error["detail"]
    
    def test_create_task_with_empty_file(self, client: TestClient, auth_headers):
        """测试空文件上传"""
        files = {"file": ("empty.md", io.BytesIO(b""), "text/markdown")}
        
        response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        # 根据业务逻辑，空文件可能被接受或拒绝
        assert response.status_code in [200, 400]
    
    def test_create_task_performance(self, client: TestClient, sample_file, auth_headers):
        """测试创建任务性能"""
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        data = {"ai_model_index": "0"}
        
        start_time = time.time()
        response = client.post("/api/tasks/", files=files, data=data, headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = (end_time - start_time) * 1000
        assert response_time < 2000, f"Task creation too slow: {response_time}ms"


class TestTaskReadAPI:
    """任务读取API测试类"""
    
    def test_get_tasks_list_success(self, client: TestClient, auth_headers):
        """测试获取任务列表成功 - GET /api/tasks/"""
        response = client.get("/api/tasks/", headers=auth_headers)
        assert response.status_code == 200
        
        tasks = response.json()
        assert isinstance(tasks, list)
        
        # 如果有任务，验证任务数据结构
        if tasks:
            task = tasks[0]
            required_fields = ["id", "title", "status", "created_at", "file_name"]
            for field in required_fields:
                assert field in task, f"Missing task field: {field}"
    
    def test_get_tasks_without_auth(self, client: TestClient):
        """测试未认证获取任务列表"""
        response = client.get("/api/tasks/")
        assert response.status_code == 401
    
    def test_get_task_detail_success(self, client: TestClient, sample_file, auth_headers):
        """测试获取任务详情成功 - GET /api/tasks/{id}"""
        # 先创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        assert create_response.status_code == 200
        task_id = create_response.json()["id"]
        
        # 获取任务详情
        response = client.get(f"/api/tasks/{task_id}", headers=auth_headers)
        assert response.status_code == 200
        
        detail = response.json()
        assert "task" in detail
        assert "issue_summary" in detail
        assert detail["task"]["id"] == task_id
        assert isinstance(detail["issue_summary"], dict)
    
    def test_get_task_detail_not_found(self, client: TestClient, auth_headers):
        """测试获取不存在的任务详情"""
        response = client.get("/api/tasks/99999", headers=auth_headers)
        assert response.status_code == 404
        
        error = response.json()
        assert "detail" in error
    
    def test_get_task_detail_permission_denied(self, client: TestClient, sample_file, auth_headers, normal_auth_headers):
        """测试获取他人任务详情权限拒绝"""
        # 管理员创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 普通用户尝试访问
        response = client.get(f"/api/tasks/{task_id}", headers=normal_auth_headers)
        assert response.status_code == 403
    
    def test_get_tasks_list_performance(self, client: TestClient, auth_headers):
        """测试获取任务列表性能"""
        start_time = time.time()
        response = client.get("/api/tasks/", headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = (end_time - start_time) * 1000
        assert response_time < 1000, f"Get tasks list too slow: {response_time}ms"
    
    def test_task_list_data_structure(self, client: TestClient, auth_headers):
        """测试任务列表数据结构"""
        response = client.get("/api/tasks/", headers=auth_headers)
        assert response.status_code == 200
        
        tasks = response.json()
        assert isinstance(tasks, list)
        
        if tasks:
            for task in tasks:
                assert isinstance(task, dict)
                assert "id" in task
                assert "title" in task
                assert "status" in task
                assert isinstance(task["id"], int)
                assert isinstance(task["title"], str)
                assert isinstance(task["status"], str)


class TestTaskDeleteAPI:
    """任务删除API测试类"""
    
    def test_delete_task_success(self, client: TestClient, sample_file, auth_headers):
        """测试删除任务成功 - DELETE /api/tasks/{id}"""
        # 先创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 删除任务
        response = client.delete(f"/api/tasks/{task_id}", headers=auth_headers)
        assert response.status_code == 200
        
        result = response.json()
        assert result["success"] is True
        
        # 验证任务已删除
        response = client.get(f"/api/tasks/{task_id}", headers=auth_headers)
        assert response.status_code == 404
    
    def test_delete_task_not_found(self, client: TestClient, auth_headers):
        """测试删除不存在的任务"""
        response = client.delete("/api/tasks/99999", headers=auth_headers)
        assert response.status_code == 404
    
    def test_delete_task_without_auth(self, client: TestClient):
        """测试未认证删除任务"""
        response = client.delete("/api/tasks/1")
        assert response.status_code == 401
    
    def test_delete_task_permission_denied(self, client: TestClient, sample_file, auth_headers, normal_auth_headers):
        """测试删除他人任务权限拒绝"""
        # 管理员创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 普通用户尝试删除
        response = client.delete(f"/api/tasks/{task_id}", headers=normal_auth_headers)
        assert response.status_code == 403
    
    def test_delete_task_performance(self, client: TestClient, sample_file, auth_headers):
        """测试删除任务性能"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 测试删除性能
        start_time = time.time()
        response = client.delete(f"/api/tasks/{task_id}", headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = (end_time - start_time) * 1000
        assert response_time < 1000, f"Task deletion too slow: {response_time}ms"


class TestTaskValidation:
    """任务验证测试"""
    
    def test_task_title_validation(self, client: TestClient, sample_file, auth_headers):
        """测试任务标题验证"""
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        
        # 测试各种标题
        title_cases = [
            ("正常标题", 200),
            ("", 200),  # 空标题可能被允许
            ("很长的标题" * 50, 200),  # 长标题，根据实际限制调整
        ]
        
        for title, expected_status in title_cases:
            data = {"title": title, "ai_model_index": "0"}
            response = client.post("/api/tasks/", files=files, data=data, headers=auth_headers)
            # 根据实际业务逻辑调整预期状态码
            assert response.status_code in [200, 400, 422], f"Unexpected status for title: {title}"
    
    def test_task_ai_model_index_validation(self, client: TestClient, sample_file, auth_headers):
        """测试AI模型索引验证"""
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        
        # 测试有效索引
        response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        assert response.status_code == 200
        
        # 测试无效索引
        invalid_indices = ["999", "-1", "abc", ""]
        for invalid_index in invalid_indices:
            data = {"ai_model_index": invalid_index}
            response = client.post("/api/tasks/", files=files, data=data, headers=auth_headers)
            assert response.status_code in [400, 422], f"Should reject invalid index: {invalid_index}"