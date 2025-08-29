"""
任务分享API测试
测试 /api/task-shares/ 相关端点
"""
import pytest
from fastapi.testclient import TestClient


class TestTaskSharingAPI:
    """任务分享API测试类"""
    
    def test_create_task_share_success(self, client: TestClient, sample_file, auth_headers):
        """测试创建任务分享成功 - POST /api/task-shares/"""
        # 先创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        assert create_response.status_code == 200
        task_id = create_response.json()["id"]
        
        # 创建分享
        share_data = {
            "task_id": task_id,
            "share_type": "public",
            "description": "测试任务分享"
        }
        response = client.post("/api/task-shares/", json=share_data, headers=auth_headers)
        assert response.status_code == 200
        
        share = response.json()
        assert "id" in share
        assert "share_token" in share
        assert share["task_id"] == task_id
        assert share["share_type"] == "public"
    
    def test_get_task_shares_list(self, client: TestClient, auth_headers):
        """测试获取任务分享列表 - GET /api/task-shares/"""
        response = client.get("/api/task-shares/", headers=auth_headers)
        assert response.status_code == 200
        
        shares = response.json()
        assert isinstance(shares, list)
    
    def test_get_task_share_detail(self, client: TestClient, sample_file, auth_headers):
        """测试获取任务分享详情 - GET /api/task-shares/{id}"""
        # 先创建任务和分享
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        share_data = {"task_id": task_id, "share_type": "public"}
        share_response = client.post("/api/task-shares/", json=share_data, headers=auth_headers)
        share_id = share_response.json()["id"]
        
        # 获取分享详情
        response = client.get(f"/api/task-shares/{share_id}", headers=auth_headers)
        assert response.status_code == 200
        
        share = response.json()
        assert share["id"] == share_id
        assert share["task_id"] == task_id
    
    def test_update_task_share(self, client: TestClient, sample_file, auth_headers):
        """测试更新任务分享 - PUT /api/task-shares/{id}"""
        # 先创建任务和分享
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        share_data = {"task_id": task_id, "share_type": "public"}
        share_response = client.post("/api/task-shares/", json=share_data, headers=auth_headers)
        share_id = share_response.json()["id"]
        
        # 更新分享
        update_data = {"description": "更新的分享描述", "share_type": "private"}
        response = client.put(f"/api/task-shares/{share_id}", json=update_data, headers=auth_headers)
        assert response.status_code == 200
        
        updated_share = response.json()
        assert updated_share["description"] == "更新的分享描述"
        assert updated_share["share_type"] == "private"
    
    def test_delete_task_share(self, client: TestClient, sample_file, auth_headers):
        """测试删除任务分享 - DELETE /api/task-shares/{id}"""
        # 先创建任务和分享
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        share_data = {"task_id": task_id, "share_type": "public"}
        share_response = client.post("/api/task-shares/", json=share_data, headers=auth_headers)
        share_id = share_response.json()["id"]
        
        # 删除分享
        response = client.delete(f"/api/task-shares/{share_id}", headers=auth_headers)
        assert response.status_code == 200
        
        # 验证删除成功
        get_response = client.get(f"/api/task-shares/{share_id}", headers=auth_headers)
        assert get_response.status_code == 404
    
    def test_task_share_not_found(self, client: TestClient, auth_headers):
        """测试访问不存在的任务分享"""
        response = client.get("/api/task-shares/99999", headers=auth_headers)
        assert response.status_code == 404
    
    def test_task_share_without_auth(self, client: TestClient):
        """测试未认证访问任务分享"""
        response = client.get("/api/task-shares/")
        assert response.status_code == 401
    
    def test_task_share_permission_control(self, client: TestClient, sample_file, auth_headers, normal_auth_headers):
        """测试任务分享权限控制"""
        # 管理员创建任务和分享
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        share_data = {"task_id": task_id, "share_type": "private"}
        share_response = client.post("/api/task-shares/", json=share_data, headers=auth_headers)
        share_id = share_response.json()["id"]
        
        # 普通用户尝试访问私有分享
        response = client.get(f"/api/task-shares/{share_id}", headers=normal_auth_headers)
        assert response.status_code == 403


class TestTaskSharingValidation:
    """任务分享数据验证测试"""
    
    def test_create_share_invalid_data(self, client: TestClient, auth_headers):
        """测试创建分享无效数据"""
        # 无效的任务ID
        invalid_share_data = {"task_id": 99999, "share_type": "public"}
        response = client.post("/api/task-shares/", json=invalid_share_data, headers=auth_headers)
        assert response.status_code == 404  # 任务不存在
        
        # 无效的分享类型
        invalid_type_data = {"task_id": 1, "share_type": "invalid_type"}
        response = client.post("/api/task-shares/", json=invalid_type_data, headers=auth_headers)
        assert response.status_code == 422  # 数据验证失败
    
    def test_share_data_structure(self, client: TestClient, sample_file, auth_headers):
        """测试分享数据结构"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 创建分享
        share_data = {"task_id": task_id, "share_type": "public"}
        response = client.post("/api/task-shares/", json=share_data, headers=auth_headers)
        assert response.status_code == 200
        
        share = response.json()
        expected_fields = ["id", "task_id", "share_type", "share_token", "created_at"]
        for field in expected_fields:
            assert field in share, f"Missing share field: {field}"
        
        # 验证字段类型
        assert isinstance(share["id"], int)
        assert isinstance(share["task_id"], int)
        assert isinstance(share["share_type"], str)
        assert isinstance(share["share_token"], str)
        assert isinstance(share["created_at"], str)
    
    def test_share_token_uniqueness(self, client: TestClient, sample_file, auth_headers):
        """测试分享token唯一性"""
        # 创建两个不同的任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        
        create_response1 = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id1 = create_response1.json()["id"]
        
        create_response2 = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id2 = create_response2.json()["id"]
        
        # 为两个任务创建分享
        share1_response = client.post("/api/task-shares/", json={"task_id": task_id1, "share_type": "public"}, headers=auth_headers)
        share2_response = client.post("/api/task-shares/", json={"task_id": task_id2, "share_type": "public"}, headers=auth_headers)
        
        if share1_response.status_code == 200 and share2_response.status_code == 200:
            share1 = share1_response.json()
            share2 = share2_response.json()
            
            # 验证分享token不同
            assert share1["share_token"] != share2["share_token"]
            assert len(share1["share_token"]) > 10  # 应该是足够长的token
            assert len(share2["share_token"]) > 10


class TestTaskSharingSecurity:
    """任务分享安全测试"""
    
    def test_share_access_by_token(self, client: TestClient, sample_file, auth_headers):
        """测试通过token访问分享"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 创建公开分享
        share_data = {"task_id": task_id, "share_type": "public"}
        share_response = client.post("/api/task-shares/", json=share_data, headers=auth_headers)
        
        if share_response.status_code == 200:
            share = share_response.json()
            share_token = share["share_token"]
            
            # 通过token访问分享（如果有此功能）
            # 这个测试根据实际API实现可能需要调整
            response = client.get(f"/api/public/shares/{share_token}")
            # 如果API不支持公开访问，跳过此测试
            if response.status_code == 404:
                pytest.skip("Public share access endpoint not implemented")
    
    def test_share_permission_isolation(self, client: TestClient, sample_file, auth_headers, normal_auth_headers):
        """测试分享权限隔离"""
        # 管理员创建任务和私有分享
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        share_data = {"task_id": task_id, "share_type": "private"}
        share_response = client.post("/api/task-shares/", json=share_data, headers=auth_headers)
        
        if share_response.status_code == 200:
            share_id = share_response.json()["id"]
            
            # 普通用户无法访问其他人的私有分享
            response = client.get(f"/api/task-shares/{share_id}", headers=normal_auth_headers)
            assert response.status_code == 403
    
    def test_share_data_sanitization(self, client: TestClient, sample_file, auth_headers):
        """测试分享数据安全性"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 尝试创建包含恶意内容的分享
        malicious_data = {
            "task_id": task_id,
            "share_type": "public",
            "description": "<script>alert('xss')</script>恶意描述"
        }
        response = client.post("/api/task-shares/", json=malicious_data, headers=auth_headers)
        
        if response.status_code == 200:
            share = response.json()
            # 验证恶意内容被适当处理
            if "description" in share:
                description = share["description"]
                # 应该转义或清理恶意脚本
                assert "<script>" not in description or "&lt;script&gt;" in description


class TestTaskSharingMethods:
    """任务分享HTTP方法测试"""
    
    def test_task_shares_invalid_methods(self, client: TestClient, auth_headers):
        """测试任务分享端点无效HTTP方法"""
        # PATCH方法可能不被支持
        response = client.patch("/api/task-shares/1", headers=auth_headers)
        assert response.status_code == 405
    
    def test_task_shares_list_invalid_methods(self, client: TestClient, auth_headers):
        """测试任务分享列表端点无效HTTP方法"""
        # PUT方法不被支持
        response = client.put("/api/task-shares/", headers=auth_headers)
        assert response.status_code == 405
        
        # DELETE方法不被支持
        response = client.delete("/api/task-shares/", headers=auth_headers)
        assert response.status_code == 405


class TestTaskSharingBusiness:
    """任务分享业务逻辑测试"""
    
    def test_share_expiration(self, client: TestClient, sample_file, auth_headers):
        """测试分享过期机制"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 创建有过期时间的分享（如果API支持）
        share_data = {
            "task_id": task_id,
            "share_type": "public",
            "expires_in": 3600  # 1小时过期
        }
        response = client.post("/api/task-shares/", json=share_data, headers=auth_headers)
        
        # 根据API实现，可能支持或不支持过期时间
        assert response.status_code in [200, 422]
    
    def test_duplicate_share_prevention(self, client: TestClient, sample_file, auth_headers):
        """测试防重复分享"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 创建第一个分享
        share_data = {"task_id": task_id, "share_type": "public"}
        response1 = client.post("/api/task-shares/", json=share_data, headers=auth_headers)
        
        # 尝试创建重复分享
        response2 = client.post("/api/task-shares/", json=share_data, headers=auth_headers)
        
        # 根据业务逻辑，可能允许多个分享或阻止重复
        assert response1.status_code == 200
        assert response2.status_code in [200, 409]  # 409 Conflict for duplicate
    
    def test_share_statistics(self, client: TestClient, auth_headers):
        """测试分享统计功能"""
        # 如果API提供分享统计端点
        response = client.get("/api/task-shares/stats", headers=auth_headers)
        
        # 根据API实现，可能有或没有统计端点
        if response.status_code == 200:
            stats = response.json()
            assert isinstance(stats, dict)
            expected_stats = ["total_shares", "public_shares", "private_shares"]
            for stat in expected_stats:
                if stat in stats:
                    assert isinstance(stats[stat], int)
        else:
            # 如果没有统计端点，应该返回404
            assert response.status_code == 404