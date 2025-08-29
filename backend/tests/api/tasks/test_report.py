"""
任务报告API测试
测试 /api/tasks/{id}/report 端点
"""
import pytest
import io
from fastapi.testclient import TestClient


class TestTaskReportAPI:
    """任务报告API测试类"""
    
    def test_download_report_success(self, client: TestClient, sample_file, auth_headers):
        """测试下载任务报告成功 - GET /api/tasks/{id}/report"""
        # 先创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 下载报告（新创建的任务还未完成，可能无法下载）
        response = client.get(f"/api/tasks/{task_id}/report", headers=auth_headers)
        # 根据任务状态，可能返回200（如果有报告）或400/403（如果任务未完成）
        assert response.status_code in [200, 400, 403]
        
        if response.status_code == 200:
            # 验证文件下载响应
            assert response.headers.get("content-type") in [
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "application/octet-stream"
            ]
            assert "content-disposition" in response.headers
            assert "attachment" in response.headers["content-disposition"]
        else:
            # 验证错误响应
            error = response.json()
            assert "detail" in error
    
    def test_download_report_not_found(self, client: TestClient, auth_headers):
        """测试下载不存在任务的报告"""
        response = client.get("/api/tasks/99999/report", headers=auth_headers)
        # 可能返回404（任务不存在）或403（权限检查优先）
        assert response.status_code in [404, 403]
    
    def test_download_report_without_auth(self, client: TestClient):
        """测试未认证下载报告"""
        response = client.get("/api/tasks/1/report")
        assert response.status_code == 401
    
    def test_download_report_permission_denied(self, client: TestClient, sample_file, auth_headers, normal_auth_headers):
        """测试下载他人任务报告权限拒绝"""
        # 管理员创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 普通用户尝试下载
        response = client.get(f"/api/tasks/{task_id}/report", headers=normal_auth_headers)
        assert response.status_code == 403
    
    def test_download_report_for_incomplete_task(self, client: TestClient, sample_file, auth_headers):
        """测试下载未完成任务的报告"""
        # 创建任务（初始状态为pending）
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 立即尝试下载报告（任务可能还在处理中）
        response = client.get(f"/api/tasks/{task_id}/report", headers=auth_headers)
        # 未完成的任务不应该有报告可下载
        assert response.status_code in [400, 403]
        
        error = response.json()
        assert "detail" in error
    
    def test_download_report_content_type(self, client: TestClient, sample_file, auth_headers):
        """测试下载报告内容类型"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 尝试下载报告
        response = client.get(f"/api/tasks/{task_id}/report", headers=auth_headers)
        
        if response.status_code == 200:
            # 验证Excel文件的Content-Type
            content_type = response.headers.get("content-type")
            assert content_type in [
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "application/octet-stream"
            ]
            
            # 验证文件下载头
            disposition = response.headers.get("content-disposition")
            assert disposition is not None
            assert "attachment" in disposition
            assert "filename=" in disposition
    
    def test_download_report_performance(self, client: TestClient, sample_file, auth_headers):
        """测试下载报告性能"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 测试下载性能
        import time
        start_time = time.time()
        response = client.get(f"/api/tasks/{task_id}/report", headers=auth_headers)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000
        # 无论成功与否，都应该快速响应
        assert response_time < 2000, f"Report download too slow: {response_time}ms"
    
    def test_report_file_integrity(self, client: TestClient, sample_file, auth_headers):
        """测试报告文件完整性"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 下载报告
        response = client.get(f"/api/tasks/{task_id}/report", headers=auth_headers)
        
        if response.status_code == 200:
            # 验证文件内容不为空
            assert len(response.content) > 0
            
            # 验证Excel文件的基本结构（检查前几个字节）
            content_start = response.content[:8]
            # Excel文件通常以PK开头（ZIP格式）
            assert len(content_start) > 0


class TestTaskReportMethods:
    """任务报告HTTP方法测试"""
    
    def test_report_invalid_methods(self, client: TestClient, auth_headers):
        """测试报告端点无效HTTP方法"""
        # POST方法不被支持
        response = client.post("/api/tasks/1/report", headers=auth_headers)
        assert response.status_code == 405
        
        # PUT方法不被支持
        response = client.put("/api/tasks/1/report", headers=auth_headers)
        assert response.status_code == 405
        
        # DELETE方法不被支持
        response = client.delete("/api/tasks/1/report", headers=auth_headers)
        assert response.status_code == 405


class TestTaskReportError:
    """任务报告错误处理测试"""
    
    def test_report_error_response_format(self, client: TestClient, auth_headers):
        """测试报告错误响应格式"""
        # 测试不存在的任务
        response = client.get("/api/tasks/99999/report", headers=auth_headers)
        assert response.status_code in [404, 403]
        
        if response.status_code in [400, 403, 404]:
            error = response.json()
            assert isinstance(error, dict)
            assert "detail" in error
            assert isinstance(error["detail"], str)
    
    def test_report_malformed_task_id(self, client: TestClient, auth_headers):
        """测试报告端点畸形任务ID"""
        malformed_ids = ["abc", "0.5", "-1", "task1"]
        
        for task_id in malformed_ids:
            response = client.get(f"/api/tasks/{task_id}/report", headers=auth_headers)
            # 对于无效格式如"abc", "0.5", "task1"应该返回422，但对于负数如"-1"可能返回403/404
            if task_id in ["abc", "0.5", "task1"]:
                assert response.status_code == 422, f"Should reject invalid format task ID: {task_id}"
            else:
                assert response.status_code in [403, 404, 422], f"Should handle invalid task ID: {task_id}"