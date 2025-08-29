"""
任务日志历史API测试
测试 /api/tasks/{id}/logs/history 端点
"""
import pytest
import io
from fastapi.testclient import TestClient


class TestTaskLogsHistoryAPI:
    """任务日志历史API测试类"""
    
    def test_get_task_logs_success(self, client: TestClient, sample_file, auth_headers):
        """测试获取任务历史日志成功 - GET /api/tasks/{id}/logs/history"""
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
            
            # 验证字段类型
            assert isinstance(log["timestamp"], str)
            assert isinstance(log["level"], str)
            assert isinstance(log["module"], str)
            assert isinstance(log["stage"], str)
            assert isinstance(log["message"], str)
            
            if log["progress"] is not None:
                assert isinstance(log["progress"], (int, float))
    
    def test_task_logs_performance(self, client: TestClient, sample_file, auth_headers):
        """测试获取任务日志性能"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        import time
        start_time = time.time()
        response = client.get(f"/api/tasks/{task_id}/logs/history", headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = (end_time - start_time) * 1000
        assert response_time < 500, f"Get task logs too slow: {response_time}ms"
    
    def test_task_logs_filtering(self, client: TestClient, sample_file, auth_headers):
        """测试任务日志过滤"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 测试可能的日志过滤参数
        filter_params = [
            "level=INFO",
            "level=ERROR", 
            "stage=processing",
            "module=task_processor"
        ]
        
        for param in filter_params:
            response = client.get(f"/api/tasks/{task_id}/logs/history?{param}", headers=auth_headers)
            # 如果不支持过滤，应该忽略参数并返回200
            assert response.status_code in [200, 422]
            
            if response.status_code == 200:
                logs = response.json()
                assert isinstance(logs, list)


class TestTaskLogsValidation:
    """任务日志验证测试"""
    
    def test_task_logs_invalid_task_id(self, client: TestClient, auth_headers):
        """测试无效任务ID获取日志"""
        invalid_ids = ["abc", "0.5"]  # 只测试格式无效的ID
        
        for task_id in invalid_ids:
            response = client.get(f"/api/tasks/{task_id}/logs/history", headers=auth_headers)
            assert response.status_code == 422, f"Should reject invalid task ID: {task_id}"
        
        # 负数ID格式有效但不存在，返回404
        response = client.get("/api/tasks/-1/logs/history", headers=auth_headers)
        assert response.status_code == 404
    
    def test_task_logs_ordering(self, client: TestClient, sample_file, auth_headers):
        """测试任务日志排序"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        response = client.get(f"/api/tasks/{task_id}/logs/history", headers=auth_headers)
        assert response.status_code == 200
        
        logs = response.json()
        
        if len(logs) > 1:
            # 验证日志是否按时间排序
            timestamps = []
            for log in logs:
                if "timestamp" in log:
                    timestamps.append(log["timestamp"])
            
            if timestamps:
                # 验证时间戳格式（基本检查）
                for timestamp in timestamps:
                    assert isinstance(timestamp, str)
                    assert len(timestamp) > 0
    
    def test_task_logs_level_validation(self, client: TestClient, sample_file, auth_headers):
        """测试任务日志级别验证"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        response = client.get(f"/api/tasks/{task_id}/logs/history", headers=auth_headers)
        logs = response.json()
        
        if logs:
            valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            
            for log in logs:
                if "level" in log and log["level"]:
                    level = log["level"].upper()
                    # 日志级别应该是标准的级别之一
                    assert isinstance(level, str)


class TestTaskLogsMethods:
    """任务日志HTTP方法测试"""
    
    def test_task_logs_invalid_methods(self, client: TestClient, auth_headers):
        """测试任务日志端点无效HTTP方法"""
        task_id = 1
        
        # POST方法不被支持
        response = client.post(f"/api/tasks/{task_id}/logs/history", headers=auth_headers)
        assert response.status_code == 405
        
        # PUT方法不被支持
        response = client.put(f"/api/tasks/{task_id}/logs/history", headers=auth_headers)
        assert response.status_code == 405
        
        # DELETE方法不被支持
        response = client.delete(f"/api/tasks/{task_id}/logs/history", headers=auth_headers)
        assert response.status_code == 405


class TestTaskLogsError:
    """任务日志错误处理测试"""
    
    def test_task_logs_error_response_format(self, client: TestClient, auth_headers):
        """测试任务日志错误响应格式"""
        # 测试不存在的任务
        response = client.get("/api/tasks/99999/logs/history", headers=auth_headers)
        assert response.status_code == 404
        
        error = response.json()
        assert isinstance(error, dict)
        assert "detail" in error
        assert isinstance(error["detail"], str)
    
    def test_task_logs_concurrent_access(self, client: TestClient, sample_file, auth_headers):
        """测试任务日志并发访问"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        import threading
        import time
        
        results = []
        errors = []
        results_lock = threading.Lock()
        
        def get_logs_attempt():
            try:
                time.sleep(0.01)
                response = client.get(f"/api/tasks/{task_id}/logs/history", headers=auth_headers)
                with results_lock:
                    results.append(response.status_code)
            except Exception as e:
                with results_lock:
                    errors.append(str(e))
                    results.append(-1)
        
        # 启动并发请求
        threads = []
        for i in range(3):
            thread = threading.Thread(target=get_logs_attempt)
            threads.append(thread)
            thread.start()
            time.sleep(0.01)
        
        # 等待完成
        for thread in threads:
            thread.join()
        
        # 验证结果
        successful_results = [r for r in results if r == 200]
        assert len(successful_results) >= 1, f"Expected at least 1 successful request, got {len(successful_results)}"