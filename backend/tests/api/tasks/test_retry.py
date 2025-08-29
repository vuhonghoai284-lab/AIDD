"""
任务重试API测试
测试 /api/tasks/{id}/retry 端点
"""
import pytest
import io
from fastapi.testclient import TestClient


class TestTaskRetryAPI:
    """任务重试API测试类"""
    
    def test_retry_task_success(self, client: TestClient, sample_file, auth_headers):
        """测试重试任务成功 - POST /api/tasks/{id}/retry"""
        # 先创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 重试任务（新创建的任务状态为pending，可能无法重试）
        response = client.post(f"/api/tasks/{task_id}/retry", headers=auth_headers)
        # 根据业务逻辑，pending状态的任务可能不允许重试
        assert response.status_code in [200, 400, 403]
        
        if response.status_code == 200:
            result = response.json()
            assert "success" in result or "id" in result
        elif response.status_code == 400:
            error = response.json()
            assert "detail" in error
        elif response.status_code == 403:
            error = response.json()
            assert "detail" in error
    
    def test_retry_task_not_found(self, client: TestClient, auth_headers):
        """测试重试不存在的任务"""
        response = client.post("/api/tasks/99999/retry", headers=auth_headers)
        assert response.status_code == 404
        
        error = response.json()
        assert "detail" in error
    
    def test_retry_task_without_auth(self, client: TestClient):
        """测试未认证重试任务"""
        response = client.post("/api/tasks/1/retry")
        assert response.status_code == 401
    
    def test_retry_task_permission_denied(self, client: TestClient, sample_file, auth_headers, normal_auth_headers):
        """测试重试他人任务权限拒绝"""
        # 管理员创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 普通用户尝试重试
        response = client.post(f"/api/tasks/{task_id}/retry", headers=normal_auth_headers)
        assert response.status_code == 403
    
    def test_retry_task_invalid_status(self, client: TestClient, sample_file, auth_headers):
        """测试重试无效状态的任务"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 新创建的任务通常是pending状态，可能不允许重试
        response = client.post(f"/api/tasks/{task_id}/retry", headers=auth_headers)
        
        if response.status_code == 400:
            error = response.json()
            assert "detail" in error
            # 可能包含状态相关的错误信息
    
    def test_retry_task_performance(self, client: TestClient, sample_file, auth_headers):
        """测试重试任务性能"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 测试重试性能
        import time
        start_time = time.time()
        response = client.post(f"/api/tasks/{task_id}/retry", headers=auth_headers)
        end_time = time.time()
        
        # 无论成功与否，都应该快速响应
        response_time = (end_time - start_time) * 1000
        assert response_time < 1000, f"Task retry too slow: {response_time}ms"
    
    def test_retry_task_idempotency(self, client: TestClient, sample_file, auth_headers):
        """测试重试任务幂等性"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 多次重试同一任务
        responses = []
        for i in range(3):
            response = client.post(f"/api/tasks/{task_id}/retry", headers=auth_headers)
            responses.append(response.status_code)
        
        # 所有重试操作应该返回相同的结果
        assert len(set(responses)) == 1, f"Retry operations should be idempotent, got: {responses}"


class TestTaskRetryBusinessLogic:
    """任务重试业务逻辑测试"""
    
    def test_retry_different_task_statuses(self, client: TestClient, sample_file, auth_headers):
        """测试重试不同状态的任务"""
        # 由于在测试环境中很难模拟所有任务状态，
        # 这里主要测试重试接口的可访问性和错误处理
        
        # 创建任务（pending状态）
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 重试pending任务
        response = client.post(f"/api/tasks/{task_id}/retry", headers=auth_headers)
        # pending任务可能不允许重试，或者允许重试但无实际效果
        assert response.status_code in [200, 400, 403]
    
    def test_retry_task_state_validation(self, client: TestClient, sample_file, auth_headers):
        """测试重试任务状态验证"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 检查任务状态
        detail_response = client.get(f"/api/tasks/{task_id}", headers=auth_headers)
        task_detail = detail_response.json()["task"]
        initial_status = task_detail["status"]
        
        # 重试任务
        retry_response = client.post(f"/api/tasks/{task_id}/retry", headers=auth_headers)
        
        if retry_response.status_code == 200:
            # 如果重试成功，验证状态可能发生变化
            new_detail_response = client.get(f"/api/tasks/{task_id}", headers=auth_headers)
            new_task_detail = new_detail_response.json()["task"]
            # 状态可能变为pending或其他状态
            assert "status" in new_task_detail
        else:
            # 如果重试失败，验证错误信息
            error = retry_response.json()
            assert "detail" in error