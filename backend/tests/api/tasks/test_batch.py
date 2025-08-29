"""
任务批量操作API测试
测试 /api/tasks/batch 端点
"""
import pytest
import io
from fastapi.testclient import TestClient


class TestTaskBatchAPI:
    """任务批量操作API测试类"""
    
    def test_batch_create_tasks_success(self, client: TestClient, auth_headers):
        """测试批量创建任务成功 - POST /api/tasks/batch"""
        # 准备多个测试文件
        files = [
            ("task1.md", b"# Task 1\n\nContent for task 1", "text/markdown"),
            ("task2.txt", b"Task 2 content", "text/plain"),
            ("task3.md", b"# Task 3\n\nContent for task 3", "text/markdown")
        ]
        
        # 构建批量创建请求
        file_data = []
        for i, (filename, content, content_type) in enumerate(files):
            file_data.append(("files", (filename, io.BytesIO(content), content_type)))
        
        data = {"ai_model_index": "0"}
        
        response = client.post("/api/tasks/batch", files=file_data, data=data, headers=auth_headers)
        assert response.status_code == 201
        
        tasks = response.json()
        assert isinstance(tasks, list)
        assert len(tasks) == 3
        
        for i, task in enumerate(tasks):
            assert "id" in task
            assert task["file_name"] == files[i][0]
            assert task["status"] == "pending"
    
    def test_batch_create_tasks_without_auth(self, client: TestClient):
        """测试未认证批量创建任务"""
        files = {"files": ("test.md", io.BytesIO(b"test"), "text/markdown")}
        response = client.post("/api/tasks/batch", files=files)
        assert response.status_code == 401
    
    def test_batch_create_tasks_empty_files(self, client: TestClient, auth_headers):
        """测试批量创建任务空文件列表"""
        response = client.post("/api/tasks/batch", files=[], data={"ai_model_index": "0"}, headers=auth_headers)
        assert response.status_code == 422  # 应该要求至少一个文件
    
    def test_batch_create_tasks_invalid_file_types(self, client: TestClient, auth_headers):
        """测试批量创建任务包含无效文件类型"""
        files = [
            ("files", ("valid.md", io.BytesIO(b"# Valid"), "text/markdown")),
            ("files", ("invalid.exe", io.BytesIO(b"invalid"), "application/x-executable"))
        ]
        
        response = client.post("/api/tasks/batch", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        # 批量操作可能部分成功，返回201并在响应中标明失败的文件
        assert response.status_code in [201, 400]
        
        if response.status_code == 201:
            # 验证响应包含成功和失败的信息
            result = response.json()
            assert isinstance(result, (list, dict))
    
    def test_batch_create_tasks_concurrency_limit(self, client: TestClient, auth_headers):
        """测试批量创建任务并发限制"""
        # 创建大量文件测试并发限制
        files = []
        for i in range(20):  # 创建20个文件
            files.append(("files", (f"test{i}.md", io.BytesIO(f"# Test {i}".encode()), "text/markdown")))
        
        response = client.post("/api/tasks/batch", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        # 可能触发并发限制，返回429或部分成功
        assert response.status_code in [201, 429]
        
        if response.status_code == 429:
            error = response.json()
            assert "error" in error
            assert "concurrency" in error["error"]
    
    def test_batch_create_tasks_performance(self, client: TestClient, auth_headers):
        """测试批量创建任务性能"""
        files = []
        for i in range(5):  # 适中的文件数量
            files.append(("files", (f"perf_test{i}.md", io.BytesIO(f"# Performance Test {i}".encode()), "text/markdown")))
        
        import time
        start_time = time.time()
        response = client.post("/api/tasks/batch", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000
        assert response_time < 3000, f"Batch creation too slow: {response_time}ms"
        
        if response.status_code == 201:
            tasks = response.json()
            assert len(tasks) == 5


class TestTaskBatchValidation:
    """任务批量操作验证测试"""
    
    def test_batch_file_size_validation(self, client: TestClient, auth_headers):
        """测试批量文件大小验证"""
        # 创建一个正常文件和一个过大文件
        normal_file = ("normal.md", io.BytesIO(b"# Normal file"), "text/markdown")
        large_file = ("large.md", io.BytesIO(b"x" * (11 * 1024 * 1024)), "text/markdown")  # 11MB
        
        files = [("files", normal_file), ("files", large_file)]
        
        response = client.post("/api/tasks/batch", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        assert response.status_code == 400
        
        error = response.json()
        assert "detail" in error
        assert "文件大小" in error["detail"]
    
    def test_batch_duplicate_filenames(self, client: TestClient, auth_headers):
        """测试批量上传重复文件名"""
        files = [
            ("files", ("duplicate.md", io.BytesIO(b"# Content 1"), "text/markdown")),
            ("files", ("duplicate.md", io.BytesIO(b"# Content 2"), "text/markdown"))
        ]
        
        response = client.post("/api/tasks/batch", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        # 根据业务逻辑，可能允许重复文件名或拒绝
        assert response.status_code in [201, 400]
    
    def test_batch_mixed_file_formats(self, client: TestClient, auth_headers):
        """测试批量上传混合文件格式"""
        files = [
            ("files", ("doc1.md", io.BytesIO(b"# Markdown"), "text/markdown")),
            ("files", ("doc2.txt", io.BytesIO(b"Plain text"), "text/plain")),
        ]
        
        response = client.post("/api/tasks/batch", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        assert response.status_code == 201
        
        tasks = response.json()
        assert len(tasks) == 2
        assert tasks[0]["file_name"] == "doc1.md"
        assert tasks[1]["file_name"] == "doc2.txt"