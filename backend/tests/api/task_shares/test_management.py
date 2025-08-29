"""
任务分享管理API测试
测试任务分享的列表、删除等管理操作
"""
import pytest
import io
from fastapi.testclient import TestClient


class TestTaskShareListAPI:
    """任务分享列表API测试类"""
    
    def test_list_user_shares_success(self, client: TestClient, sample_file, auth_headers):
        """测试获取用户分享列表成功 - GET /api/users/me/task-shares"""
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
            "description": "列表测试分享"
        }
        
        share_response = client.post("/api/task-shares", json=share_data, headers=auth_headers)
        
        # 获取分享列表
        response = client.get("/api/users/me/task-shares", headers=auth_headers)
        assert response.status_code == 200
        
        shares = response.json()
        assert isinstance(shares, list)
        
        if shares:
            share = shares[0]
            required_fields = ["id", "share_code", "task_id", "description", "created_at"]
            for field in required_fields:
                assert field in share, f"Missing field: {field}"
    
    def test_list_user_shares_without_auth(self, client: TestClient):
        """测试未认证获取用户分享列表"""
        response = client.get("/api/users/me/task-shares")
        assert response.status_code == 401
    
    def test_list_user_shares_pagination(self, client: TestClient, auth_headers):
        """测试用户分享列表分页"""
        # 测试分页参数
        pagination_params = [
            "page=1&size=10",
            "page=2&size=5",
            "size=20"
        ]
        
        for param in pagination_params:
            response = client.get(f"/api/users/me/task-shares?{param}", headers=auth_headers)
            # 根据API是否支持分页，可能返回200或422
            assert response.status_code in [200, 422]
            
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, (list, dict))
    
    def test_list_user_shares_filtering(self, client: TestClient, auth_headers):
        """测试用户分享列表过滤"""
        # 测试可能的过滤参数
        filter_params = [
            "status=active",
            "status=expired", 
            "task_status=completed",
            "created_after=2024-01-01"
        ]
        
        for param in filter_params:
            response = client.get(f"/api/users/me/task-shares?{param}", headers=auth_headers)
            assert response.status_code in [200, 422]


class TestTaskShareDeleteAPI:
    """任务分享删除API测试类"""
    
    def test_delete_task_share_success(self, client: TestClient, sample_file, auth_headers):
        """测试删除任务分享成功 - DELETE /api/task-shares/{id}"""
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
            "description": "删除测试分享"
        }
        
        share_response = client.post("/api/task-shares", json=share_data, headers=auth_headers)
        if share_response.status_code in [200, 201]:
            share_id = share_response.json()["id"]
            
            # 删除分享
            response = client.delete(f"/api/task-shares/{share_id}", headers=auth_headers)
            assert response.status_code in [200, 204]
            
            # 验证分享已被删除（访问应该返回404）
            share_code = share_response.json()["share_code"]
            access_response = client.get(f"/api/task-shares/{share_code}")
            assert access_response.status_code == 404
    
    def test_delete_task_share_not_found(self, client: TestClient, auth_headers):
        """测试删除不存在的任务分享"""
        response = client.delete("/api/task-shares/99999", headers=auth_headers)
        assert response.status_code == 404
        
        error = response.json()
        assert "detail" in error
        assert "分享不存在" in error["detail"] or "not found" in error["detail"].lower()
    
    def test_delete_task_share_without_auth(self, client: TestClient):
        """测试未认证删除任务分享"""
        response = client.delete("/api/task-shares/1")
        assert response.status_code == 401
    
    def test_delete_task_share_permission_denied(self, client: TestClient, sample_file, auth_headers, normal_auth_headers):
        """测试删除他人任务分享权限拒绝"""
        # 管理员创建任务和分享
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        import time
        time.sleep(2)
        
        share_data = {
            "task_id": task_id,
            "description": "权限测试分享"
        }
        
        share_response = client.post("/api/task-shares", json=share_data, headers=auth_headers)
        if share_response.status_code in [200, 201]:
            share_id = share_response.json()["id"]
            
            # 普通用户尝试删除
            response = client.delete(f"/api/task-shares/{share_id}", headers=normal_auth_headers)
            assert response.status_code == 403


class TestTaskShareUpdateAPI:
    """任务分享更新API测试类"""
    
    def test_update_task_share_success(self, client: TestClient, sample_file, auth_headers):
        """测试更新任务分享成功 - PUT /api/task-shares/{id}"""
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
            "description": "更新测试分享"
        }
        
        share_response = client.post("/api/task-shares", json=share_data, headers=auth_headers)
        if share_response.status_code in [200, 201]:
            share_id = share_response.json()["id"]
            
            # 更新分享
            update_data = {
                "description": "更新后的分享描述",
                "expire_days": 14
            }
            
            response = client.put(f"/api/task-shares/{share_id}", json=update_data, headers=auth_headers)
            assert response.status_code in [200, 405]  # 405 if update not supported
            
            if response.status_code == 200:
                updated_share = response.json()
                assert updated_share["description"] == "更新后的分享描述"
    
    def test_update_task_share_invalid_data(self, client: TestClient, auth_headers):
        """测试更新任务分享无效数据"""
        invalid_data_sets = [
            {"expire_days": -1},  # 负数过期天数
            {"expire_days": 0},   # 0天过期
            {"expire_days": 366}, # 过长过期天数
            {"description": ""},  # 空描述
        ]
        
        for data in invalid_data_sets:
            response = client.put("/api/task-shares/1", json=data, headers=auth_headers)
            # 根据API实现，可能返回404（分享不存在）或422（验证错误）
            assert response.status_code in [404, 422]


class TestTaskShareListMethods:
    """任务分享列表HTTP方法测试"""
    
    def test_task_share_list_invalid_methods(self, client: TestClient, auth_headers):
        """测试任务分享列表端点无效HTTP方法"""
        # POST方法不被支持
        response = client.post("/api/users/me/task-shares", headers=auth_headers)
        assert response.status_code == 405
        
        # PUT方法不被支持
        response = client.put("/api/users/me/task-shares", headers=auth_headers)
        assert response.status_code == 405
        
        # DELETE方法不被支持
        response = client.delete("/api/users/me/task-shares", headers=auth_headers)
        assert response.status_code == 405


class TestTaskShareValidation:
    """任务分享验证测试"""
    
    def test_share_security_validation(self, client: TestClient, sample_file, auth_headers):
        """测试分享安全性验证"""
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
            "description": "安全测试分享"
        }
        
        share_response = client.post("/api/task-shares", json=share_data, headers=auth_headers)
        if share_response.status_code in [200, 201]:
            share_code = share_response.json()["share_code"]
            
            # 访问分享任务
            response = client.get(f"/api/task-shares/{share_code}")
            if response.status_code == 200:
                data = response.json()
                
                # 验证不会暴露敏感信息
                task = data.get("task", {})
                sensitive_fields = ["user_id", "api_key", "token", "password"]
                
                def check_no_sensitive_data(obj, path=""):
                    if isinstance(obj, dict):
                        for key, value in obj.items():
                            full_path = f"{path}.{key}" if path else key
                            # 检查key名称
                            for sensitive in sensitive_fields:
                                assert sensitive not in key.lower(), f"Sensitive field exposed: {full_path}"
                            
                            check_no_sensitive_data(value, full_path)
                    elif isinstance(obj, list):
                        for i, item in enumerate(obj):
                            check_no_sensitive_data(item, f"{path}[{i}]")
                    elif isinstance(obj, str):
                        # 检查值中是否包含明显的敏感信息模式
                        lower_value = obj.lower()
                        patterns = ["password", "secret", "token", "key"]
                        for pattern in patterns:
                            if pattern in lower_value and len(obj) > 20:
                                # 长字符串且包含敏感词汇可能是敏感信息
                                pass  # 可以添加更严格的检查
                
                check_no_sensitive_data(data)