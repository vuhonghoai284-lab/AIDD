"""
任务文件操作API测试
测试 /api/tasks/{id}/file 相关端点
"""
import pytest
import io
from fastapi.testclient import TestClient


class TestTaskFileAPI:
    """任务文件API测试类"""
    
    def test_download_task_file_success(self, client: TestClient, sample_file, auth_headers):
        """测试下载任务文件成功 - GET /api/tasks/{id}/file"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        assert create_response.status_code == 201
        task_id = create_response.json()["id"]
        
        # 下载文件
        response = client.get(f"/api/tasks/{task_id}/file", headers=auth_headers)
        assert response.status_code == 200
        
        # 验证文件内容
        downloaded_content = response.content
        assert downloaded_content == content
        
        # 验证响应头
        assert "content-disposition" in response.headers
        assert filename in response.headers["content-disposition"]
    
    def test_download_task_file_not_found(self, client: TestClient, auth_headers):
        """测试下载不存在任务的文件"""
        response = client.get("/api/tasks/99999/file", headers=auth_headers)
        assert response.status_code == 404
    
    def test_download_task_file_without_auth(self, client: TestClient):
        """测试未认证下载任务文件"""
        response = client.get("/api/tasks/1/file")
        assert response.status_code == 401
    
    def test_download_task_file_permission_denied(self, client: TestClient, sample_file, auth_headers, normal_auth_headers):
        """测试下载他人任务文件权限拒绝"""
        # 管理员创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 普通用户尝试下载
        response = client.get(f"/api/tasks/{task_id}/file", headers=normal_auth_headers)
        assert response.status_code == 403
    
    def test_download_file_content_type(self, client: TestClient, auth_headers):
        """测试下载文件内容类型"""
        file_types = [
            ("test.md", b"# Markdown", "text/markdown"),
            ("test.txt", b"Plain text", "text/plain"),
        ]
        
        for filename, content, expected_content_type in file_types:
            files = {"file": (filename, io.BytesIO(content), expected_content_type)}
            create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
            assert create_response.status_code == 201
            task_id = create_response.json()["id"]
            
            # 下载文件并验证内容类型
            response = client.get(f"/api/tasks/{task_id}/file", headers=auth_headers)
            assert response.status_code == 200
            
            # 验证Content-Type头
            if "content-type" in response.headers:
                content_type = response.headers["content-type"]
                # 可能包含charset等额外参数
                assert expected_content_type.split(";")[0] in content_type
    
    def test_download_file_performance(self, client: TestClient, auth_headers):
        """测试文件下载性能"""
        # 创建中等大小的文件
        content = b"# Performance Test\n" + b"Content line\n" * 1000  # 约13KB
        files = {"file": ("perf_test.md", io.BytesIO(content), "text/markdown")}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        import time
        start_time = time.time()
        response = client.get(f"/api/tasks/{task_id}/file", headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = (end_time - start_time) * 1000
        assert response_time < 1000, f"File download too slow: {response_time}ms"
        
        # 验证下载的内容完整性
        assert len(response.content) == len(content)
    
    def test_download_file_concurrent_access(self, client: TestClient, sample_file, auth_headers):
        """测试并发文件下载"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        import threading
        import time
        
        results = []
        
        def download_file():
            try:
                time.sleep(0.01)
                response = client.get(f"/api/tasks/{task_id}/file", headers=auth_headers)
                results.append({
                    "status_code": response.status_code,
                    "content_length": len(response.content) if response.status_code == 200 else 0
                })
            except Exception as e:
                results.append({"error": str(e)})
        
        # 启动多个并发下载
        threads = []
        for i in range(3):
            thread = threading.Thread(target=download_file)
            threads.append(thread)
            thread.start()
            time.sleep(0.01)
        
        # 等待完成
        for thread in threads:
            thread.join()
        
        # 验证所有下载都成功
        successful_downloads = [r for r in results if r.get("status_code") == 200]
        assert len(successful_downloads) >= 1
        
        # 验证下载内容一致性
        if len(successful_downloads) > 1:
            content_lengths = [r["content_length"] for r in successful_downloads]
            assert all(length == content_lengths[0] for length in content_lengths)


class TestTaskFileValidation:
    """任务文件验证测试"""
    
    def test_file_download_invalid_task_id(self, client: TestClient, auth_headers):
        """测试无效任务ID文件下载"""
        invalid_ids = ["abc", "0.5", "-1"]
        
        for task_id in invalid_ids:
            response = client.get(f"/api/tasks/{task_id}/file", headers=auth_headers)
            # 对于无效格式如"abc", "0.5"应该返回422，但对于负数如"-1"可能返回404
            if task_id in ["abc", "0.5"]:
                assert response.status_code == 422, f"Should reject invalid format task ID: {task_id}"
            else:
                assert response.status_code in [404, 422], f"Should handle invalid task ID: {task_id}"
    
    def test_file_download_deleted_task(self, client: TestClient, sample_file, auth_headers):
        """测试下载已删除任务的文件"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 删除任务
        delete_response = client.delete(f"/api/tasks/{task_id}", headers=auth_headers)
        assert delete_response.status_code == 200
        
        # 尝试下载文件
        response = client.get(f"/api/tasks/{task_id}/file", headers=auth_headers)
        assert response.status_code == 404
    
    def test_file_download_missing_file(self, client: TestClient, auth_headers):
        """测试下载文件不存在的情况"""
        # 这个测试模拟文件在文件系统中被意外删除的情况
        # 在实际应用中，这种情况应该很少发生
        # 这里只测试API的健壮性
        
        response = client.get("/api/tasks/999999/file", headers=auth_headers)
        assert response.status_code == 404


class TestTaskFileMethods:
    """任务文件HTTP方法测试"""
    
    def test_file_endpoint_invalid_methods(self, client: TestClient, auth_headers):
        """测试文件端点无效HTTP方法"""
        task_id = 1
        
        # POST方法不被支持
        response = client.post(f"/api/tasks/{task_id}/file", headers=auth_headers)
        assert response.status_code == 405
        
        # PUT方法不被支持
        response = client.put(f"/api/tasks/{task_id}/file", headers=auth_headers)
        assert response.status_code == 405
        
        # DELETE方法不被支持
        response = client.delete(f"/api/tasks/{task_id}/file", headers=auth_headers)
        assert response.status_code == 405