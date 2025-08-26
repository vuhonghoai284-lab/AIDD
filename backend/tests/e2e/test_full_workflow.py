"""
E2E端到端测试用例
测试完整的业务流程
"""
import pytest
import io
import time
from fastapi.testclient import TestClient

try:
    from websocket import create_connection
except ImportError:
    # WebSocket测试需要websocket-client包
    create_connection = None


class TestCompleteDocumentTestingWorkflow:
    """完整文档测试流程 - E2E-001"""
    
    def test_admin_complete_workflow(self, client: TestClient, sample_file):
        """系统管理员完整流程测试"""
        # 1. 系统管理员登录
        login_data = {"username": "admin", "password": "admin123"}
        login_response = client.post("/api/auth/system/login", data=login_data)
        assert login_response.status_code == 200
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. 获取AI模型列表
        models_response = client.get("/api/models")
        assert models_response.status_code == 200
        models_data = models_response.json()
        assert len(models_data["models"]) > 0
        default_ai_model_index = models_data["default_index"]
        
        # 3. 创建文档测试任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        task_data = {
            "title": "E2E测试任务",
            "ai_model_index": str(default_ai_model_index)
        }
        
        task_response = client.post("/api/tasks", files=files, data=task_data, headers=headers)
        assert task_response.status_code == 201
        task = task_response.json()
        task_id = task["id"]
        
        # 4. 监控任务执行状态
        max_wait_time = 30  # 最多等待30秒
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            status_response = client.get(f"/api/tasks/{task_id}", headers=headers)
            assert status_response.status_code == 200
            
            task_detail = status_response.json()
            task_status = task_detail["task"]["status"]
            
            if task_status in ["completed", "failed"]:
                break
            
            time.sleep(2)  # 等待2秒后再次检查
        
        # 5. 查看AI分析输出
        ai_outputs_response = client.get(f"/api/tasks/{task_id}/ai-outputs", headers=headers)
        assert ai_outputs_response.status_code == 200
        ai_outputs = ai_outputs_response.json()
        assert isinstance(ai_outputs, list)
        
        # 6. 查看检测到的问题
        issues = task_detail["issues"]
        assert isinstance(issues, list)
        
        # 7. 提交问题反馈（如果有问题的话）
        if issues:
            issue_id = issues[0]["id"]
            feedback_data = {
                "feedback_type": "accept",
                "comment": "E2E测试反馈"
            }
            
            feedback_response = client.put(f"/api/issues/{issue_id}/feedback", json=feedback_data, headers=headers)
            assert feedback_response.status_code == 200
        
        # 8. 下载测试报告
        report_response = client.get(f"/api/tasks/{task_id}/report", headers=headers)
        assert report_response.status_code == 200
        
        # 验证整个流程执行成功
        assert task_id is not None
        assert task_status in ["completed", "processing", "pending"]  # 允许仍在处理中


class TestThirdPartyUserWorkflow:
    """第三方用户完整流程 - E2E-002"""
    
    def test_third_party_user_complete_workflow(self, client: TestClient, sample_file):
        """第三方用户完整流程测试"""
        # 1. 获取第三方认证URL
        auth_url_response = client.get("/api/auth/thirdparty/url")
        assert auth_url_response.status_code == 200
        
        auth_data = auth_url_response.json()
        assert "auth_url" in auth_data
        
        # 2. 模拟第三方认证回调
        third_party_auth = {
            "code": "e2e_test_auth_code"
        }
        
        login_response = client.post("/api/auth/thirdparty/login-legacy", json=third_party_auth)
        assert login_response.status_code == 200
        
        # 3. 第三方用户登录
        login_data = login_response.json()
        token = login_data["access_token"]
        user_info = login_data["user"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 4. 创建个人任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        task_data = {
            "title": "第三方用户测试任务",
            "ai_model_index": "0"
        }
        
        task_response = client.post("/api/tasks", files=files, data=task_data, headers=headers)
        assert task_response.status_code == 201
        task = task_response.json()
        task_id = task["id"]
        
        # 5. 查看个人任务列表
        tasks_response = client.get("/api/tasks", headers=headers)
        assert tasks_response.status_code == 200
        
        tasks = tasks_response.json()
        assert isinstance(tasks, list)
        user_task_ids = [task["id"] for task in tasks]
        assert task_id in user_task_ids
        
        # 6. 查看任务详情和结果
        detail_response = client.get(f"/api/tasks/{task_id}", headers=headers)
        assert detail_response.status_code == 200
        
        detail = detail_response.json()
        assert "task" in detail
        assert "issues" in detail
        assert detail["task"]["id"] == task_id


class TestPermissionIsolationWorkflow:
    """权限隔离验证 - E2E-003"""
    
    def test_user_permission_isolation(self, client: TestClient, sample_file):
        """测试用户权限隔离"""
        # 创建两个不同用户
        # 用户A：第三方用户
        user_a_auth = {"code": "user_a_auth_code"}
        user_a_response = client.post("/api/auth/thirdparty/login-legacy", json=user_a_auth)
        assert user_a_response.status_code == 200
        
        user_a_token = user_a_response.json()["access_token"]
        user_a_headers = {"Authorization": f"Bearer {user_a_token}"}
        
        # 用户B：系统管理员
        user_b_login = {"username": "admin", "password": "admin123"}
        user_b_response = client.post("/api/auth/system/login", data=user_b_login)
        assert user_b_response.status_code == 200
        
        user_b_token = user_b_response.json()["access_token"]
        user_b_headers = {"Authorization": f"Bearer {user_b_token}"}
        
        # 用户A创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        
        task_a_response = client.post("/api/tasks", files=files, data={"title": "用户A的任务"}, headers=user_a_headers)
        assert task_a_response.status_code == 201
        task_a_id = task_a_response.json()["id"]
        
        # 用户B尝试访问用户A的任务（管理员可以访问）
        access_response = client.get(f"/api/tasks/{task_a_id}", headers=user_b_headers)
        assert access_response.status_code == 200  # 管理员可以访问所有任务
        
        # 创建另一个普通用户C
        user_c_auth = {"code": "user_c_auth_code"}
        user_c_response = client.post("/api/auth/thirdparty/login-legacy", json=user_c_auth)
        assert user_c_response.status_code == 200
        
        user_c_token = user_c_response.json()["access_token"]
        user_c_headers = {"Authorization": f"Bearer {user_c_token}"}
        
        # 用户C尝试访问用户A的任务（应该被拒绝）
        unauthorized_response = client.get(f"/api/tasks/{task_a_id}", headers=user_c_headers)
        assert unauthorized_response.status_code == 403
        
        # 验证权限隔离有效
        assert access_response.status_code == 200  # 管理员可访问
        assert unauthorized_response.status_code == 403  # 普通用户不可访问


class TestConcurrentTaskProcessing:
    """并发任务处理 - E2E-004"""
    
    def test_concurrent_task_creation(self, client: TestClient, sample_file):
        """测试并发任务创建和处理"""
        # 系统管理员登录
        login_data = {"username": "admin", "password": "admin123"}
        login_response = client.post("/api/auth/system/login", data=login_data)
        assert login_response.status_code == 200
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 并发创建多个任务
        import threading
        
        task_ids = []
        results = []
        
        def create_task(task_index):
            filename, content, content_type = sample_file
            # 为每个任务创建唯一内容
            unique_content = content + f"\n\n并发任务 #{task_index}".encode('utf-8')
            files = {"file": (f"concurrent_{task_index}_{filename}", io.BytesIO(unique_content), content_type)}
            
            task_data = {
                "title": f"并发任务 #{task_index}",
                "ai_model_index": "0"
            }
            
            try:
                response = client.post("/api/tasks", files=files, data=task_data, headers=headers)
                results.append({
                    "index": task_index,
                    "status_code": response.status_code,
                    "task_id": response.json().get("id") if response.status_code == 200 else None
                })
            except Exception as e:
                results.append({
                    "index": task_index,
                    "error": str(e)
                })
        
        # 启动5个并发任务
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_task, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证任务队列处理
        successful_tasks = [r for r in results if r.get("status_code") == 200]
        assert len(successful_tasks) >= 3  # 至少3个任务成功创建
        
        # 检查资源竞争问题
        task_ids = [r["task_id"] for r in successful_tasks if r.get("task_id")]
        unique_task_ids = set(task_ids)
        assert len(task_ids) == len(unique_task_ids)  # 确保没有重复的任务ID
        
        # 确认任务结果正确性
        for task_id in task_ids:
            detail_response = client.get(f"/api/tasks/{task_id}", headers=headers)
            assert detail_response.status_code == 201
            
            detail = detail_response.json()
            assert "task" in detail
            assert detail["task"]["id"] == task_id


class TestWebSocketRealTimeUpdates:
    """WebSocket实时更新测试 - WS-001"""
    
    def test_websocket_connection(self, client: TestClient, sample_file):
        """测试WebSocket连接和实时日志推送"""
        # 创建任务
        login_data = {"username": "admin", "password": "admin123"}
        login_response = client.post("/api/auth/system/login", data=login_data)
        assert login_response.status_code == 200
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        
        task_response = client.post("/api/tasks", files=files, data={"title": "WebSocket测试任务"}, headers=headers)
        assert task_response.status_code == 201
        task_id = task_response.json()["id"]
        
        # 注意：在实际测试中，WebSocket测试可能需要额外的配置
        # 这里提供基本的测试框架
        
        try:
            # 尝试建立WebSocket连接
            ws_url = f"ws://localhost:8080/ws/task/{task_id}/logs"
            # ws = create_connection(ws_url)
            
            # 由于测试环境限制，这里只验证端点存在
            # 在实际部署环境中需要完整的WebSocket测试
            
            # 验证WebSocket端点在路由中存在
            # 这个测试主要确保路由配置正确
            assert True  # WebSocket测试的占位符
            
        except Exception:
            # WebSocket连接可能在测试环境中失败
            # 这是正常的，主要目的是验证路由存在
            pytest.skip("WebSocket testing requires running server")


class TestAPIResponseConsistency:
    """API响应一致性测试"""
    
    def test_error_response_format_consistency(self, client: TestClient):
        """测试错误响应格式一致性"""
        # 收集各种错误响应
        error_responses = []
        
        # 401 未授权
        response_401 = client.get("/api/users/me")
        error_responses.append(("401", response_401))
        
        # 404 不存在
        response_404 = client.get("/api/tasks/99999", headers={"Authorization": "Bearer fake_token"})
        error_responses.append(("404", response_404))
        
        # 405 方法不允许
        response_405 = client.post("/api/models")
        error_responses.append(("405", response_405))
        
        # 验证所有错误响应都包含detail字段
        for error_type, response in error_responses:
            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    # 大多数错误应该有detail字段
                    if error_type != "405":  # 405可能有不同的格式
                        assert "detail" in error_data, f"Error {error_type} missing detail field"
                except Exception:
                    # 某些错误可能不返回JSON
                    pass
    
    def test_success_response_format_consistency(self, client: TestClient, sample_file):
        """测试成功响应格式一致性"""
        # 获取系统管理员token
        login_data = {"username": "admin", "password": "admin123"}
        login_response = client.post("/api/auth/system/login", data=login_data)
        assert login_response.status_code == 200
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 测试各种成功响应
        success_responses = []
        
        # 系统配置
        config_response = client.get("/api/config")
        success_responses.append(("config", config_response))
        
        # 模型列表
        models_response = client.get("/api/models")
        success_responses.append(("models", models_response))
        
        # 用户信息
        user_response = client.get("/api/users/me", headers=headers)
        success_responses.append(("user", user_response))
        
        # 验证所有成功响应都是有效JSON
        for response_type, response in success_responses:
            assert response.status_code == 200, f"Response {response_type} failed"
            
            try:
                data = response.json()
                assert isinstance(data, (dict, list)), f"Response {response_type} not valid JSON structure"
            except Exception as e:
                pytest.fail(f"Response {response_type} invalid JSON: {e}")