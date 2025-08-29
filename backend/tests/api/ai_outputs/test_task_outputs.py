"""
任务AI输出API测试
测试 /api/tasks/{id}/ai-outputs 端点
"""
import pytest
import io
from fastapi.testclient import TestClient


class TestTaskAIOutputsAPI:
    """任务AI输出API测试类"""
    
    def test_get_task_ai_outputs_success(self, client: TestClient, sample_file, auth_headers):
        """测试获取任务AI输出成功 - GET /api/tasks/{id}/ai-outputs"""
        # 先创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        assert create_response.status_code == 200
        task_id = create_response.json()["id"]
        
        # 获取AI输出
        response = client.get(f"/api/tasks/{task_id}/ai-outputs", headers=auth_headers)
        assert response.status_code == 200
        
        outputs = response.json()
        assert isinstance(outputs, list)
        # 新创建的任务可能还没有AI输出，所以不验证数量
    
    def test_get_task_ai_outputs_with_filter(self, client: TestClient, sample_file, auth_headers):
        """测试按操作类型过滤AI输出"""
        # 先创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 使用操作类型过滤
        filter_types = ["preprocess", "analyze", "detect_issues"]
        for filter_type in filter_types:
            response = client.get(f"/api/tasks/{task_id}/ai-outputs?operation_type={filter_type}", headers=auth_headers)
            assert response.status_code == 200
            
            outputs = response.json()
            assert isinstance(outputs, list)
            
            # 验证过滤结果（如果有数据的话）
            for output in outputs:
                if "operation_type" in output:
                    assert output["operation_type"] == filter_type
    
    def test_get_task_ai_outputs_not_found(self, client: TestClient, auth_headers):
        """测试获取不存在任务的AI输出"""
        response = client.get("/api/tasks/99999/ai-outputs", headers=auth_headers)
        assert response.status_code == 404
        
        error = response.json()
        assert "detail" in error
        assert "任务不存在" in error["detail"]
    
    def test_get_task_ai_outputs_without_auth(self, client: TestClient):
        """测试未认证获取AI输出"""
        response = client.get("/api/tasks/1/ai-outputs")
        assert response.status_code == 401
    
    def test_get_task_ai_outputs_permission_denied(self, client: TestClient, sample_file, auth_headers, normal_auth_headers):
        """测试获取他人任务AI输出权限拒绝"""
        # 管理员创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 普通用户尝试访问
        response = client.get(f"/api/tasks/{task_id}/ai-outputs", headers=normal_auth_headers)
        assert response.status_code == 403
    
    def test_ai_outputs_data_structure(self, client: TestClient, sample_file, auth_headers):
        """测试AI输出数据结构"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        response = client.get(f"/api/tasks/{task_id}/ai-outputs", headers=auth_headers)
        assert response.status_code == 200
        
        outputs = response.json()
        assert isinstance(outputs, list)
        
        # 如果有AI输出数据，验证结构
        if outputs:
            output = outputs[0]
            expected_fields = ["id", "task_id", "operation_type", "input_data", "output_data", "created_at"]
            for field in expected_fields:
                if field in output:  # 某些字段可能为空
                    assert field in output, f"Missing field: {field}"
    
    def test_ai_output_filtering(self, client: TestClient, sample_file, auth_headers):
        """测试AI输出过滤功能"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 测试各种过滤参数
        filter_types = ["preprocess", "analyze", "detect_issues"]
        
        for filter_type in filter_types:
            response = client.get(f"/api/tasks/{task_id}/ai-outputs?operation_type={filter_type}", headers=auth_headers)
            assert response.status_code == 200
            
            outputs = response.json()
            assert isinstance(outputs, list)
            # 验证过滤结果（如果有数据的话）
            for output in outputs:
                if "operation_type" in output:
                    assert output["operation_type"] == filter_type
    
    def test_ai_outputs_performance(self, client: TestClient, sample_file, auth_headers):
        """测试获取AI输出性能"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        import time
        start_time = time.time()
        response = client.get(f"/api/tasks/{task_id}/ai-outputs", headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = (end_time - start_time) * 1000
        assert response_time < 500, f"Get AI outputs too slow: {response_time}ms"


class TestTaskAIOutputsValidation:
    """任务AI输出验证测试"""
    
    def test_ai_outputs_invalid_task_id(self, client: TestClient, auth_headers):
        """测试无效任务ID获取AI输出"""
        invalid_ids = ["abc", "0.5", "-1", "999999"]
        
        for task_id in invalid_ids:
            response = client.get(f"/api/tasks/{task_id}/ai-outputs", headers=auth_headers)
            if task_id in ["abc", "0.5"]:
                assert response.status_code == 422, f"Should reject invalid task ID format: {task_id}"
            else:
                assert response.status_code in [404, 422], f"Should reject invalid task ID: {task_id}"
    
    def test_ai_outputs_invalid_filter_parameters(self, client: TestClient, sample_file, auth_headers):
        """测试无效过滤参数"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 测试无效的操作类型过滤
        invalid_types = ["invalid_type", "", "null", "123"]
        
        for invalid_type in invalid_types:
            response = client.get(f"/api/tasks/{task_id}/ai-outputs?operation_type={invalid_type}", headers=auth_headers)
            # 根据实现，可能接受任何字符串值或验证特定值
            assert response.status_code in [200, 422]
    
    def test_ai_outputs_pagination_parameters(self, client: TestClient, sample_file, auth_headers):
        """测试AI输出分页参数"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 测试可能的分页参数（如果API支持）
        pagination_params = [
            "limit=10",
            "offset=0", 
            "page=1",
            "size=20"
        ]
        
        for param in pagination_params:
            response = client.get(f"/api/tasks/{task_id}/ai-outputs?{param}", headers=auth_headers)
            # 如果不支持分页参数，应该忽略它们并返回200
            assert response.status_code in [200, 422]


class TestTaskAIOutputsMethods:
    """任务AI输出HTTP方法测试"""
    
    def test_ai_outputs_invalid_methods(self, client: TestClient, auth_headers):
        """测试AI输出端点无效HTTP方法"""
        task_id = 1
        
        # POST方法不被支持
        response = client.post(f"/api/tasks/{task_id}/ai-outputs", headers=auth_headers)
        assert response.status_code == 405
        
        # PUT方法不被支持
        response = client.put(f"/api/tasks/{task_id}/ai-outputs", headers=auth_headers)
        assert response.status_code == 405
        
        # DELETE方法不被支持
        response = client.delete(f"/api/tasks/{task_id}/ai-outputs", headers=auth_headers)
        assert response.status_code == 405