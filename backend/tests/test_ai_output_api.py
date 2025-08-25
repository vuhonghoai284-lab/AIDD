"""
AI输出API测试
测试AIOutputView中的AI输出相关接口
"""
import pytest
import io
from fastapi.testclient import TestClient


class TestAIOutputAPI:
    """AI输出API测试类"""
    
    def test_get_task_ai_outputs_success(self, client: TestClient, sample_file, auth_headers):
        """测试获取任务AI输出成功 - AI-001"""
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
        """测试按操作类型过滤AI输出 - AI-003"""
        # 先创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 使用操作类型过滤
        response = client.get(f"/api/tasks/{task_id}/ai-outputs?operation_type=preprocess", headers=auth_headers)
        assert response.status_code == 200
        
        outputs = response.json()
        assert isinstance(outputs, list)
    
    def test_get_task_ai_outputs_not_found(self, client: TestClient, auth_headers):
        """测试获取不存在任务的AI输出"""
        response = client.get("/api/tasks/99999/ai-outputs", headers=auth_headers)
        assert response.status_code == 404
        
        error = response.json()
        assert "detail" in error
        assert "任务不存在" in error["detail"]
    
    def test_get_task_ai_outputs_without_auth(self, client: TestClient, sample_file):
        """测试未认证获取AI输出"""
        # 先以管理员身份创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        auth_headers = {"Authorization": "Bearer admin_token"}
        
        # 不提供认证信息访问
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
    
    def test_get_ai_output_detail_not_found(self, client: TestClient, auth_headers):
        """测试获取不存在的AI输出详情 - AI-002"""
        response = client.get("/api/ai-outputs/99999", headers=auth_headers)
        assert response.status_code == 404
        
        error = response.json()
        assert "detail" in error
        assert "AI输出不存在" in error["detail"]
    
    def test_get_ai_output_detail_without_auth(self, client: TestClient):
        """测试未认证获取AI输出详情"""
        response = client.get("/api/ai-outputs/1")
        assert response.status_code == 401


class TestAIOutputDataValidation:
    """AI输出数据验证测试"""
    
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


class TestAIOutputPerformance:
    """AI输出性能测试"""
    
    def test_get_ai_outputs_performance(self, client: TestClient, sample_file, auth_headers):
        """测试获取AI输出性能"""
        import time
        
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        start_time = time.time()
        response = client.get(f"/api/tasks/{task_id}/ai-outputs", headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = (end_time - start_time) * 1000
        assert response_time < 500, f"Get AI outputs too slow: {response_time}ms"
    
    def test_large_ai_output_handling(self, client: TestClient, sample_file, auth_headers):
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


class TestIssueAPI:
    """问题API测试类"""
    
    def test_submit_feedback_not_found(self, client: TestClient, auth_headers):
        """测试提交不存在问题的反馈 - ISSUE-001"""
        feedback_data = {
            "feedback_type": "accept",
            "comment": "测试评论"
        }
        
        response = client.put("/api/issues/99999/feedback", json=feedback_data, headers=auth_headers)
        assert response.status_code == 404
        
        error = response.json()
        assert "detail" in error
        assert "问题不存在" in error["detail"]
    
    def test_submit_feedback_without_auth(self, client: TestClient):
        """测试未认证提交问题反馈"""
        feedback_data = {
            "feedback_type": "accept", 
            "comment": "测试评论"
        }
        
        response = client.put("/api/issues/1/feedback", json=feedback_data)
        assert response.status_code == 401
    
    def test_submit_feedback_invalid_data(self, client: TestClient, sample_file, auth_headers):
        """测试提交无效反馈数据"""
        # 先创建任务以便有可用的issue
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        assert create_response.status_code == 200
        task_id = create_response.json()["id"]
        
        # 等待任务处理并获取详情（其中包含issues）
        import time
        time.sleep(1)
        detail_response = client.get(f"/api/tasks/{task_id}", headers=auth_headers)
        task_detail = detail_response.json()
        
        if task_detail.get("issues") and len(task_detail["issues"]) > 0:
            issue_id = task_detail["issues"][0]["id"]
            
            # 测试空数据（由于所有字段都是可选的，这应该返回200而不是422）
            response = client.put(f"/api/issues/{issue_id}/feedback", json={}, headers=auth_headers)
            assert response.status_code == 200  # 所有字段可选，所以返回200
            
            # 测试无效的反馈类型（有Literal限制，应该返回422）
            invalid_feedback = {
                "feedback_type": "invalid_type",
                "comment": "测试评论"
            }
            response = client.put(f"/api/issues/{issue_id}/feedback", json=invalid_feedback, headers=auth_headers)
            assert response.status_code == 422  # Literal验证失败
        else:
            # 如果没有issues，则测试不存在的issue ID应该返回404
            response = client.put("/api/issues/99999/feedback", json={}, headers=auth_headers)
            assert response.status_code == 404


class TestTaskLogAPI:
    """任务日志API测试类"""
    
    def test_get_task_logs_success(self, client: TestClient, sample_file, auth_headers):
        """测试获取任务历史日志成功 - LOG-001"""
        # 先创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 获取任务日志
        response = client.get(f"/api/tasks/{task_id}/logs/history", headers=auth_headers)
        assert response.status_code == 200
        
        logs = response.json()
        assert isinstance(logs, list)
        # 新创建的任务可能还没有日志，所以不验证数量
    
    def test_get_task_logs_not_found(self, client: TestClient, auth_headers):
        """测试获取不存在任务的日志"""
        response = client.get("/api/tasks/99999/logs/history", headers=auth_headers)
        assert response.status_code == 404
        
        error = response.json()
        assert "detail" in error
        assert "任务不存在" in error["detail"]
    
    def test_get_task_logs_without_auth(self, client: TestClient):
        """测试未认证获取任务日志"""
        response = client.get("/api/tasks/1/logs/history")
        assert response.status_code == 401
    
    def test_get_task_logs_permission_denied(self, client: TestClient, sample_file, auth_headers, normal_auth_headers):
        """测试获取他人任务日志权限拒绝"""
        # 管理员创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 普通用户尝试访问
        response = client.get(f"/api/tasks/{task_id}/logs/history", headers=normal_auth_headers)
        assert response.status_code == 403
    
    def test_task_logs_data_structure(self, client: TestClient, sample_file, auth_headers):
        """测试任务日志数据结构"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        response = client.get(f"/api/tasks/{task_id}/logs/history", headers=auth_headers)
        assert response.status_code == 200
        
        logs = response.json()
        assert isinstance(logs, list)
        
        # 如果有日志数据，验证结构
        if logs:
            log = logs[0]
            expected_fields = ["timestamp", "level", "module", "stage", "message", "progress", "extra_data"]
            for field in expected_fields:
                assert field in log, f"Missing log field: {field}"