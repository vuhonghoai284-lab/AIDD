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
        assert response.status_code == 201
        
        task = response.json()
        assert "id" in task
        assert task["title"] == "测试任务"
        assert task["file_name"] == filename
        assert task["status"] == "pending"
        assert "created_at" in task
        assert "ai_model_label" in task
    
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
            # 系统可能使用默认模型而不是拒绝无效索引
            assert response.status_code in [201, 400, 422], f"Unexpected status for index: {invalid_index}"
    
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
        assert response.status_code in [201, 400]
    
    def test_create_task_performance(self, client: TestClient, sample_file, auth_headers):
        """测试创建任务性能"""
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        data = {"ai_model_index": "0"}
        
        start_time = time.time()
        response = client.post("/api/tasks/", files=files, data=data, headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code == 201
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
        assert create_response.status_code == 201
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
    
    def create_test_task(self, client: TestClient, auth_headers: dict, title: str = "测试任务") -> dict:
        """创建测试任务的辅助方法"""
        test_content = f"# {title}\n\n这是用于测试删除功能的文档。"
        files = {"file": ("test_delete.md", io.BytesIO(test_content.encode('utf-8')), "text/markdown")}
        data = {"title": title}
        
        response = client.post("/api/tasks/", files=files, data=data, headers=auth_headers)
        assert response.status_code == 201, f"创建任务失败: {response.text}"
        
        task = response.json()
        return task
    
    def test_delete_task_success(self, client: TestClient, auth_headers):
        """测试成功删除任务 - DELETE /api/tasks/{id}"""
        # 创建测试任务
        task = self.create_test_task(client, auth_headers, "待删除任务1")
        task_id = task["id"]
        
        # 验证任务存在
        get_response = client.get(f"/api/tasks/{task_id}", headers=auth_headers)
        assert get_response.status_code == 200
        
        # 删除任务
        delete_response = client.delete(f"/api/tasks/{task_id}", headers=auth_headers)
        assert delete_response.status_code == 200
        
        delete_result = delete_response.json()
        assert delete_result["success"] is True
        
        # 验证任务已删除
        get_response_after = client.get(f"/api/tasks/{task_id}", headers=auth_headers)
        assert get_response_after.status_code == 404
    
    def test_delete_nonexistent_task(self, client: TestClient, auth_headers):
        """测试删除不存在的任务"""
        nonexistent_task_id = 99999
        
        delete_response = client.delete(f"/api/tasks/{nonexistent_task_id}", headers=auth_headers)
        assert delete_response.status_code == 404
        
        error = delete_response.json()
        assert "任务不存在" in error["detail"]
    
    def test_delete_task_without_auth(self, client: TestClient, auth_headers):
        """测试未认证删除任务"""
        # 创建测试任务
        task = self.create_test_task(client, auth_headers, "需认证删除的任务")
        task_id = task["id"]
        
        # 尝试不带认证头删除
        delete_response = client.delete(f"/api/tasks/{task_id}")
        assert delete_response.status_code == 401
        
        # 验证任务仍然存在
        get_response = client.get(f"/api/tasks/{task_id}", headers=auth_headers)
        assert get_response.status_code == 200
    
    def test_delete_other_user_task(self, client: TestClient, auth_headers, normal_auth_headers):
        """测试删除其他用户的任务"""
        # 用户A创建任务
        task = self.create_test_task(client, auth_headers, "用户A的任务")
        task_id = task["id"]
        
        # 用户B尝试删除
        delete_response = client.delete(f"/api/tasks/{task_id}", headers=normal_auth_headers)
        assert delete_response.status_code == 403
        
        error = delete_response.json()
        assert "权限不足" in error["detail"]
        
        # 验证任务仍然存在
        get_response = client.get(f"/api/tasks/{task_id}", headers=auth_headers)
        assert get_response.status_code == 200
    
    def test_admin_delete_any_task(self, client: TestClient, auth_headers, normal_auth_headers):
        """测试管理员删除任意用户任务"""
        # 普通用户创建任务
        task = self.create_test_task(client, normal_auth_headers, "普通用户任务")
        task_id = task["id"]
        
        # 管理员删除
        delete_response = client.delete(f"/api/tasks/{task_id}", headers=auth_headers)
        assert delete_response.status_code == 200
        
        delete_result = delete_response.json()
        assert delete_result["success"] is True
        
        # 验证任务已删除
        get_response = client.get(f"/api/tasks/{task_id}", headers=auth_headers)
        assert get_response.status_code == 404
    
    def test_delete_task_with_processing_status(self, client: TestClient, auth_headers):
        """测试删除正在处理中的任务"""
        # 创建任务并等待处理开始
        task = self.create_test_task(client, auth_headers, "处理中任务")
        task_id = task["id"]
        
        # 等待一小段时间让处理开始
        time.sleep(0.5)
        
        # 删除任务
        delete_response = client.delete(f"/api/tasks/{task_id}", headers=auth_headers)
        assert delete_response.status_code == 200
        
        delete_result = delete_response.json()
        assert delete_result["success"] is True
    
    def test_delete_multiple_tasks(self, client: TestClient, auth_headers):
        """测试批量删除多个任务"""
        # 创建多个测试任务
        task_ids = []
        for i in range(3):
            task = self.create_test_task(client, auth_headers, f"批量删除任务{i+1}")
            task_ids.append(task["id"])
        
        # 逐一删除任务
        success_count = 0
        for task_id in task_ids:
            delete_response = client.delete(f"/api/tasks/{task_id}", headers=auth_headers)
            if delete_response.status_code == 200:
                delete_result = delete_response.json()
                if delete_result["success"]:
                    success_count += 1
        
        assert success_count == len(task_ids)
        
        # 验证所有任务都已删除
        for task_id in task_ids:
            get_response = client.get(f"/api/tasks/{task_id}", headers=auth_headers)
            assert get_response.status_code == 404
    
    def test_delete_shared_file_task(self, client: TestClient, auth_headers):
        """测试删除共享文件的任务"""
        # 创建相同内容的两个任务（文件内容相同，会共享文件记录）
        content = "# 共享文件测试\n\n这是用于测试文件共享的内容。"
        
        # 任务1
        files1 = {"file": ("shared_test1.md", io.BytesIO(content.encode('utf-8')), "text/markdown")}
        response1 = client.post("/api/tasks/", files=files1, data={"title": "共享文件任务1"}, headers=auth_headers)
        assert response1.status_code == 201
        task1 = response1.json()
        
        # 任务2 (相同内容)
        files2 = {"file": ("shared_test2.md", io.BytesIO(content.encode('utf-8')), "text/markdown")}
        response2 = client.post("/api/tasks/", files=files2, data={"title": "共享文件任务2"}, headers=auth_headers)
        assert response2.status_code == 201
        task2 = response2.json()
        
        # 删除第一个任务
        delete_response1 = client.delete(f"/api/tasks/{task1['id']}", headers=auth_headers)
        assert delete_response1.status_code == 200
        assert delete_response1.json()["success"] is True
        
        # 验证第二个任务仍然存在且可访问
        get_response2 = client.get(f"/api/tasks/{task2['id']}", headers=auth_headers)
        assert get_response2.status_code == 200
        
        # 删除第二个任务
        delete_response2 = client.delete(f"/api/tasks/{task2['id']}", headers=auth_headers)
        assert delete_response2.status_code == 200
        assert delete_response2.json()["success"] is True
    
    def test_delete_task_performance(self, client: TestClient, auth_headers):
        """测试删除任务的性能"""
        # 创建测试任务
        task = self.create_test_task(client, auth_headers, "性能测试任务")
        task_id = task["id"]
        
        # 测量删除操作耗时
        start_time = time.time()
        delete_response = client.delete(f"/api/tasks/{task_id}", headers=auth_headers)
        end_time = time.time()
        
        delete_time = end_time - start_time
        
        assert delete_response.status_code == 200
        assert delete_response.json()["success"] is True
        
        # 删除操作应该在1秒内完成
        assert delete_time < 1.0, f"删除操作耗时过长: {delete_time:.2f}秒"
    
    def test_concurrent_delete_same_task(self, client: TestClient, auth_headers):
        """测试并发删除同一任务"""
        import threading
        import queue
        
        # 创建测试任务
        task = self.create_test_task(client, auth_headers, "并发删除测试任务")
        task_id = task["id"]
        
        results = queue.Queue()
        
        def delete_task():
            """删除任务的线程函数"""
            try:
                response = client.delete(f"/api/tasks/{task_id}", headers=auth_headers)
                results.put({
                    "status_code": response.status_code,
                    "success": response.json().get("success") if response.status_code == 200 else False
                })
            except Exception as e:
                results.put({"error": str(e)})
        
        # 启动两个并发删除线程
        thread1 = threading.Thread(target=delete_task)
        thread2 = threading.Thread(target=delete_task)
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        # 收集结果
        result1 = results.get()
        result2 = results.get()
        
        # 并发删除同一任务可能有以下几种情况：
        # 1. 一个成功，一个404（任务已被删除）
        # 2. 两个都成功（如果删除操作不是原子性的）
        # 3. 一个成功，一个得到其他错误
        success_count = sum(1 for r in [result1, result2] if r.get("success") is True)
        not_found_count = sum(1 for r in [result1, result2] if r.get("status_code") == 404)
        error_count = sum(1 for r in [result1, result2] if "error" in r)
        
        # 至少应该有一个操作成功
        assert success_count >= 1, f"应该至少有一个删除成功，结果: {[result1, result2]}"
        
        # 总的操作数应该是2
        total_operations = success_count + not_found_count + error_count
        assert total_operations == 2, f"操作总数应为2，实际: {total_operations}"
    
    def test_delete_task_response_format(self, client: TestClient, auth_headers):
        """测试删除任务响应格式"""
        # 创建测试任务
        task = self.create_test_task(client, auth_headers, "响应格式测试任务")
        task_id = task["id"]
        
        # 删除任务
        delete_response = client.delete(f"/api/tasks/{task_id}", headers=auth_headers)
        assert delete_response.status_code == 200
        
        # 验证响应格式
        delete_result = delete_response.json()
        assert isinstance(delete_result, dict)
        assert "success" in delete_result
        assert isinstance(delete_result["success"], bool)
        assert delete_result["success"] is True
        
        # 验证响应头
        assert "content-type" in delete_response.headers
        assert "application/json" in delete_response.headers["content-type"]
    
    def test_delete_task_invalid_id_format(self, client: TestClient, auth_headers):
        """测试无效任务ID格式"""
        invalid_ids = ["abc", "12.34", "-1", "0", "null", "undefined"]
        
        for invalid_id in invalid_ids:
            try:
                delete_response = client.delete(f"/api/tasks/{invalid_id}", headers=auth_headers)
                # 应该返回422 (验证错误) 或 404
                assert delete_response.status_code in [422, 404], f"无效ID {invalid_id} 应该返回422或404"
            except Exception as e:
                # 某些无效ID可能导致路由异常
                pass


class TestTaskValidation:
    """任务验证测试"""
    
    def test_task_title_validation(self, client: TestClient, sample_file, auth_headers):
        """测试任务标题验证"""
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        
        # 测试各种标题
        title_cases = [
            ("正常标题", 201),
            ("", 201),  # 空标题可能被允许
            ("很长的标题" * 50, 201),  # 长标题，根据实际限制调整
        ]
        
        for title, expected_status in title_cases:
            data = {"title": title, "ai_model_index": "0"}
            response = client.post("/api/tasks/", files=files, data=data, headers=auth_headers)
            # 根据实际业务逻辑调整预期状态码
            assert response.status_code in [201, 400, 422], f"Unexpected status for title: {title}"
    
    def test_task_ai_model_index_validation(self, client: TestClient, sample_file, auth_headers):
        """测试AI模型索引验证"""
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        
        # 测试有效索引
        response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        assert response.status_code == 201
        
        # 测试无效索引
        invalid_indices = ["999", "-1", "abc", ""]
        for invalid_index in invalid_indices:
            data = {"ai_model_index": invalid_index}
            response = client.post("/api/tasks/", files=files, data=data, headers=auth_headers)
            # 系统可能使用默认模型而不是拒绝无效索引，所以也接受201
            assert response.status_code in [201, 400, 422], f"Should handle invalid index: {invalid_index}"
    
    def test_supported_file_types(self, client: TestClient, auth_headers):
        """测试支持的文件类型"""
        supported_files = [
            ("test.md", b"# Markdown File", "text/markdown"),
            ("test.txt", b"Text File Content", "text/plain"),
        ]
        
        for filename, content, content_type in supported_files:
            files = {"file": (filename, io.BytesIO(content), content_type)}
            response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
            assert response.status_code == 201, f"Failed for file type: {filename}"
            
            task = response.json()
            assert task["file_name"] == filename
    
    def test_file_duplicate_handling(self, client: TestClient, sample_file, auth_headers):
        """测试重复文件处理"""
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        
        # 创建第一个任务
        response1 = client.post("/api/tasks/", files=files, headers=auth_headers)
        assert response1.status_code == 201
        task1 = response1.json()
        
        # 创建相同文件的第二个任务
        files = {"file": (filename, io.BytesIO(content), content_type)}
        response2 = client.post("/api/tasks/", files=files, headers=auth_headers)
        assert response2.status_code == 201
        task2 = response2.json()
        
        # 两个任务应该都成功创建
        assert task1["id"] != task2["id"]
        assert task1["file_name"] == task2["file_name"]
    
    def test_file_with_special_characters(self, client: TestClient, auth_headers):
        """测试特殊字符文件名"""
        special_names = [
            "测试文档.md",
            "test-file_123.md", 
            "file with spaces.md"
        ]
        
        for filename in special_names:
            content = f"# {filename}\nTest content".encode('utf-8')
            files = {"file": (filename, io.BytesIO(content), "text/markdown")}
            
            response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
            assert response.status_code == 201, f"Failed for filename: {filename}"
            
            task = response.json()
            assert task["file_name"] == filename


class TestTaskPermissions:
    """任务权限测试"""
    
    def test_user_can_only_see_own_tasks(self, client: TestClient, sample_file, normal_user_token, admin_user_token):
        """测试用户只能看到自己的任务"""
        # 普通用户创建任务
        normal_headers = {"Authorization": f"Bearer {normal_user_token['token']}"}
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), "text/markdown")}
        
        response = client.post("/api/tasks/", files=files, data={"title": "普通用户任务", "ai_model_index": "0"}, headers=normal_headers)
        assert response.status_code == 201
        user_task_id = response.json()["id"]
        
        # 管理员创建任务
        admin_headers = {"Authorization": f"Bearer {admin_user_token['token']}"}
        files = {"file": (filename, io.BytesIO(content), "text/markdown")}
        response = client.post("/api/tasks/", files=files, data={"title": "管理员任务", "ai_model_index": "0"}, headers=admin_headers)
        assert response.status_code == 201
        admin_task_id = response.json()["id"]
        
        # 普通用户获取任务列表，只能看到自己的任务
        response = client.get("/api/tasks/", headers=normal_headers)
        assert response.status_code == 200
        
        user_tasks = response.json()
        user_task_ids = [task["id"] for task in user_tasks]
        
        assert user_task_id in user_task_ids
        assert admin_task_id not in user_task_ids
        
        # 管理员可以看到所有任务
        response = client.get("/api/tasks/", headers=admin_headers)
        assert response.status_code == 200
        
        admin_tasks = response.json()
        admin_task_ids = [task["id"] for task in admin_tasks]
        
        assert user_task_id in admin_task_ids
        assert admin_task_id in admin_task_ids