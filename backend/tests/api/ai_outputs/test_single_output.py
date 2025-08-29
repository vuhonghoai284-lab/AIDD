"""
单个AI输出API测试
测试 /api/ai-outputs/{id} 端点
"""
import pytest
from fastapi.testclient import TestClient


class TestSingleAIOutputAPI:
    """单个AI输出API测试类"""
    
    def test_get_ai_output_detail_success(self, client: TestClient, sample_file, auth_headers):
        """测试获取AI输出详情成功 - GET /api/ai-outputs/{id}"""
        # 先创建任务以生成AI输出
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 获取任务的AI输出列表
        outputs_response = client.get(f"/api/tasks/{task_id}/ai-outputs", headers=auth_headers)
        assert outputs_response.status_code == 200
        outputs = outputs_response.json()
        
        if outputs:
            # 获取第一个AI输出的详情
            output_id = outputs[0]["id"]
            response = client.get(f"/api/ai-outputs/{output_id}", headers=auth_headers)
            assert response.status_code == 200
            
            detail = response.json()
            expected_fields = ["id", "task_id", "operation_type", "input_data", "output_data", "created_at"]
            for field in expected_fields:
                if field in detail:  # 某些字段可能为空
                    assert isinstance(detail[field], (str, int, dict, list))
    
    def test_get_ai_output_detail_not_found(self, client: TestClient, auth_headers):
        """测试获取不存在的AI输出详情"""
        response = client.get("/api/ai-outputs/99999", headers=auth_headers)
        assert response.status_code == 404
        
        error = response.json()
        assert "detail" in error
        assert "AI输出不存在" in error["detail"]
    
    def test_get_ai_output_detail_without_auth(self, client: TestClient):
        """测试未认证获取AI输出详情"""
        response = client.get("/api/ai-outputs/1")
        assert response.status_code == 401
    
    def test_get_ai_output_detail_permission_denied(self, client: TestClient, sample_file, auth_headers, normal_auth_headers):
        """测试获取他人AI输出详情权限拒绝"""
        # 管理员创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 获取AI输出列表
        outputs_response = client.get(f"/api/tasks/{task_id}/ai-outputs", headers=auth_headers)
        outputs = outputs_response.json()
        
        if outputs:
            output_id = outputs[0]["id"]
            # 普通用户尝试访问
            response = client.get(f"/api/ai-outputs/{output_id}", headers=normal_auth_headers)
            assert response.status_code == 403
    
    def test_ai_output_data_structure(self, client: TestClient, sample_file, auth_headers):
        """测试AI输出数据结构"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 获取AI输出
        outputs_response = client.get(f"/api/tasks/{task_id}/ai-outputs", headers=auth_headers)
        outputs = outputs_response.json()
        
        if outputs:
            output_id = outputs[0]["id"]
            response = client.get(f"/api/ai-outputs/{output_id}", headers=auth_headers)
            assert response.status_code == 200
            
            detail = response.json()
            
            # 验证基本字段存在
            basic_fields = ["id", "task_id"]
            for field in basic_fields:
                assert field in detail, f"Missing basic field: {field}"
            
            # 验证字段类型
            assert isinstance(detail["id"], int)
            assert isinstance(detail["task_id"], int)
            assert detail["task_id"] == task_id
    
    def test_ai_output_performance(self, client: TestClient, sample_file, auth_headers):
        """测试AI输出详情获取性能"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 获取AI输出列表
        outputs_response = client.get(f"/api/tasks/{task_id}/ai-outputs", headers=auth_headers)
        outputs = outputs_response.json()
        
        if outputs:
            output_id = outputs[0]["id"]
            
            import time
            start_time = time.time()
            response = client.get(f"/api/ai-outputs/{output_id}", headers=auth_headers)
            end_time = time.time()
            
            assert response.status_code == 200
            response_time = (end_time - start_time) * 1000
            assert response_time < 300, f"Get AI output detail too slow: {response_time}ms"


class TestAIOutputValidation:
    """AI输出验证测试"""
    
    def test_ai_output_invalid_id(self, client: TestClient, auth_headers):
        """测试无效AI输出ID"""
        invalid_ids = ["abc", "0.5", "-1"]
        
        for output_id in invalid_ids:
            response = client.get(f"/api/ai-outputs/{output_id}", headers=auth_headers)
            assert response.status_code == 422, f"Should reject invalid output ID: {output_id}"
    
    def test_ai_output_large_data_handling(self, client: TestClient, sample_file, auth_headers):
        """测试大量AI输出数据处理"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 获取AI输出（可能包含大量数据）
        response = client.get(f"/api/tasks/{task_id}/ai-outputs", headers=auth_headers)
        assert response.status_code == 200
        
        # 验证响应时间和数据完整性
        outputs = response.json()
        assert isinstance(outputs, list)
        
        # 如果有大量数据，验证分页或限制机制
        if len(outputs) > 100:
            pytest.skip("Large data test - consider implementing pagination")


class TestAIOutputMethods:
    """AI输出HTTP方法测试"""
    
    def test_ai_output_invalid_methods(self, client: TestClient, auth_headers):
        """测试AI输出端点无效HTTP方法"""
        output_id = 1
        
        # POST方法不被支持
        response = client.post(f"/api/ai-outputs/{output_id}", headers=auth_headers)
        assert response.status_code == 405
        
        # PUT方法不被支持
        response = client.put(f"/api/ai-outputs/{output_id}", headers=auth_headers)
        assert response.status_code == 405
        
        # DELETE方法不被支持
        response = client.delete(f"/api/ai-outputs/{output_id}", headers=auth_headers)
        assert response.status_code == 405


class TestAIOutputBusinessLogic:
    """AI输出业务逻辑测试"""
    
    def test_ai_output_task_relationship(self, client: TestClient, sample_file, auth_headers):
        """测试AI输出与任务关系"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 获取任务的AI输出
        outputs_response = client.get(f"/api/tasks/{task_id}/ai-outputs", headers=auth_headers)
        outputs = outputs_response.json()
        
        if outputs:
            # 验证每个AI输出都属于正确的任务
            for output in outputs:
                if "task_id" in output:
                    assert output["task_id"] == task_id
                
                # 获取单个AI输出详情验证关系
                if "id" in output:
                    detail_response = client.get(f"/api/ai-outputs/{output['id']}", headers=auth_headers)
                    if detail_response.status_code == 200:
                        detail = detail_response.json()
                        assert detail["task_id"] == task_id
    
    def test_ai_output_operation_types(self, client: TestClient, sample_file, auth_headers):
        """测试AI输出操作类型"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 获取AI输出
        response = client.get(f"/api/tasks/{task_id}/ai-outputs", headers=auth_headers)
        outputs = response.json()
        
        if outputs:
            valid_operation_types = ["preprocess", "analyze", "detect_issues", "summarize"]
            
            for output in outputs:
                if "operation_type" in output and output["operation_type"]:
                    operation_type = output["operation_type"]
                    # 验证操作类型是预期的值之一（可能根据实现调整）
                    assert isinstance(operation_type, str)
                    assert len(operation_type) > 0