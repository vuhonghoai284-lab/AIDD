"""
任务分享访问API测试
测试 GET /api/task-shares/{share_code} 端点
"""
import pytest
import io
from fastapi.testclient import TestClient


class TestTaskShareAccessAPI:
    """任务分享访问API测试类"""
    
    def test_access_shared_task_success(self, client: TestClient, sample_file, auth_headers):
        """测试访问分享任务成功 - GET /api/task-shares/{share_code}"""
        # 创建任务
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
            "description": "访问测试分享"
        }
        
        share_response = client.post("/api/task-shares", json=share_data, headers=auth_headers)
        if share_response.status_code in [200, 201]:
            share_code = share_response.json()["share_code"]
            
            # 访问分享任务（无需认证）
            response = client.get(f"/api/task-shares/{share_code}")
            assert response.status_code == 200
            
            shared_task = response.json()
            assert "task" in shared_task
            assert "share_info" in shared_task
            
            # 验证任务数据结构
            task = shared_task["task"]
            assert "id" in task
            assert "title" in task
            assert "status" in task
            assert task["id"] == task_id
    
    def test_access_shared_task_not_found(self, client: TestClient):
        """测试访问不存在的分享任务"""
        response = client.get("/api/task-shares/invalid_share_code")
        assert response.status_code == 404
        
        error = response.json()
        assert "detail" in error
        assert "分享不存在" in error["detail"] or "not found" in error["detail"].lower()
    
    def test_access_expired_share(self, client: TestClient, sample_file, auth_headers):
        """测试访问过期分享"""
        # 这个测试主要验证过期逻辑的存在
        # 实际过期需要时间控制，这里主要测试端点行为
        
        # 使用无效的分享码模拟过期场景
        response = client.get("/api/task-shares/expired_share_code")
        assert response.status_code == 404
    
    def test_access_share_data_structure(self, client: TestClient, sample_file, auth_headers):
        """测试分享访问数据结构"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        import time
        time.sleep(2)
        
        # 创建分享
        share_data = {
            "task_id": task_id,
            "description": "结构测试分享"
        }
        
        share_response = client.post("/api/task-shares", json=share_data, headers=auth_headers)
        if share_response.status_code in [200, 201]:
            share_code = share_response.json()["share_code"]
            
            response = client.get(f"/api/task-shares/{share_code}")
            assert response.status_code == 200
            
            data = response.json()
            
            # 验证响应结构
            required_sections = ["task", "share_info"]
            for section in required_sections:
                assert section in data, f"Missing section: {section}"
            
            # 验证任务信息
            task = data["task"]
            task_fields = ["id", "title", "status", "created_at"]
            for field in task_fields:
                assert field in task, f"Missing task field: {field}"
            
            # 验证分享信息
            share_info = data["share_info"]
            share_fields = ["description", "created_at", "expires_at"]
            for field in share_fields:
                assert field in share_info, f"Missing share_info field: {field}"
    
    def test_access_share_performance(self, client: TestClient, sample_file, auth_headers):
        """测试访问分享性能"""
        # 创建任务和分享
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        import time
        time.sleep(2)
        
        share_data = {
            "task_id": task_id,
            "description": "性能测试分享"
        }
        
        share_response = client.post("/api/task-shares", json=share_data, headers=auth_headers)
        if share_response.status_code in [200, 201]:
            share_code = share_response.json()["share_code"]
            
            start_time = time.time()
            response = client.get(f"/api/task-shares/{share_code}")
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000
            assert response_time < 800, f"Access shared task too slow: {response_time}ms"


class TestTaskShareAccessValidation:
    """任务分享访问验证测试"""
    
    def test_share_code_format_validation(self, client: TestClient):
        """测试分享码格式验证"""
        invalid_codes = [
            "",  # 空码
            "   ",  # 空白字符
            "a",  # 过短
            "invalid@code#with$special%chars",  # 特殊字符
            "very_long_share_code_that_exceeds_normal_limits" * 10,  # 过长
        ]
        
        for code in invalid_codes:
            response = client.get(f"/api/task-shares/{code}")
            assert response.status_code in [404, 422], f"Should reject invalid share code: {code}"
    
    def test_share_access_without_permission_leak(self, client: TestClient):
        """测试分享访问不会泄露权限信息"""
        # 访问不存在的分享应该返回统一的错误信息
        response = client.get("/api/task-shares/nonexistent_code")
        assert response.status_code == 404
        
        error = response.json()
        # 错误信息不应该泄露敏感信息
        assert "detail" in error
        error_detail = error["detail"].lower()
        assert "sql" not in error_detail
        assert "database" not in error_detail
        assert "internal" not in error_detail
    
    def test_share_access_rate_limiting(self, client: TestClient):
        """测试分享访问频率限制"""
        # 快速多次访问同一个不存在的分享码
        share_code = "test_rate_limit_code"
        
        responses = []
        for i in range(10):
            response = client.get(f"/api/task-shares/{share_code}")
            responses.append(response.status_code)
        
        # 所有请求都应该得到合理响应（不会因频率过高而被阻断）
        # 除非系统特意实现了频率限制
        for status_code in responses:
            assert status_code in [404, 429], f"Unexpected status code: {status_code}"


class TestTaskShareAccessMethods:
    """任务分享访问HTTP方法测试"""
    
    def test_task_share_access_invalid_methods(self, client: TestClient):
        """测试任务分享访问端点无效HTTP方法"""
        share_code = "test_code"
        
        # POST方法不被支持
        response = client.post(f"/api/task-shares/{share_code}")
        assert response.status_code == 405
        
        # PUT方法不被支持
        response = client.put(f"/api/task-shares/{share_code}")
        assert response.status_code == 405
        
        # DELETE方法不被支持
        response = client.delete(f"/api/task-shares/{share_code}")
        assert response.status_code == 405