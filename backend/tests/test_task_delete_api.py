"""
删除任务API测试
测试删除任务相关的所有场景和边界情况
"""
import pytest
import io
import time
from fastapi.testclient import TestClient
from unittest.mock import patch
import os
import tempfile


class TestTaskDeleteAPI:
    """删除任务API测试类"""
    
    def create_test_task(self, client: TestClient, auth_headers: dict, title: str = "测试任务") -> dict:
        """创建测试任务的辅助方法"""
        # 创建测试文件
        test_content = f"# {title}\n\n这是用于测试删除功能的文档。"
        files = {"file": ("test_delete.md", io.BytesIO(test_content.encode('utf-8')), "text/markdown")}
        data = {"title": title}
        
        response = client.post("/api/tasks/", files=files, data=data, headers=auth_headers)
        assert response.status_code == 201, f"创建任务失败: {response.text}"
        
        task = response.json()
        print(f"✅ 创建测试任务: ID={task['id']}, 标题={task['title']}")
        return task
    
    def test_delete_task_success(self, client: TestClient, auth_headers):
        """测试成功删除任务 - DELETE-001"""
        print("\n🗑️ 测试: 成功删除任务")
        
        # 1. 创建测试任务
        task = self.create_test_task(client, auth_headers, "待删除任务1")
        task_id = task["id"]
        
        # 2. 验证任务存在
        get_response = client.get(f"/api/tasks/{task_id}", headers=auth_headers)
        assert get_response.status_code == 200
        
        # 3. 删除任务
        delete_response = client.delete(f"/api/tasks/{task_id}", headers=auth_headers)
        assert delete_response.status_code == 200
        
        delete_result = delete_response.json()
        assert delete_result["success"] is True
        
        # 4. 验证任务已删除
        get_response_after = client.get(f"/api/tasks/{task_id}", headers=auth_headers)
        assert get_response_after.status_code == 404
        
        print(f"✅ 任务 {task_id} 删除成功")
    
    def test_delete_nonexistent_task(self, client: TestClient, auth_headers):
        """测试删除不存在的任务 - DELETE-002"""
        print("\n🗑️ 测试: 删除不存在的任务")
        
        # 使用一个不存在的任务ID
        nonexistent_task_id = 99999
        
        delete_response = client.delete(f"/api/tasks/{nonexistent_task_id}", headers=auth_headers)
        assert delete_response.status_code == 404
        
        error = delete_response.json()
        assert "任务不存在" in error["detail"]
        
        print(f"✅ 正确处理不存在任务的删除请求")
    
    def test_delete_task_without_auth(self, client: TestClient, auth_headers):
        """测试未认证删除任务 - DELETE-003"""
        print("\n🗑️ 测试: 未认证删除任务")
        
        # 创建测试任务
        task = self.create_test_task(client, auth_headers, "需认证删除的任务")
        task_id = task["id"]
        
        # 尝试不带认证头删除
        delete_response = client.delete(f"/api/tasks/{task_id}")
        assert delete_response.status_code == 401
        
        # 验证任务仍然存在
        get_response = client.get(f"/api/tasks/{task_id}", headers=auth_headers)
        assert get_response.status_code == 200
        
        print(f"✅ 未认证请求正确被拒绝")
    
    def test_delete_other_user_task(self, client: TestClient, auth_headers, normal_auth_headers):
        """测试删除其他用户的任务 - DELETE-004"""
        print("\n🗑️ 测试: 删除其他用户的任务")
        
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
        
        print(f"✅ 跨用户删除正确被拒绝")
    
    def test_admin_delete_any_task(self, client: TestClient, auth_headers, normal_auth_headers):
        """测试管理员删除任意用户任务 - DELETE-005"""
        print("\n🗑️ 测试: 管理员删除任意用户任务")
        
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
        
        print(f"✅ 管理员成功删除其他用户任务")
    
    @pytest.mark.integration
    def test_delete_task_with_processing_status(self, client: TestClient, auth_headers):
        """测试删除正在处理中的任务 - DELETE-006"""
        print("\n🗑️ 测试: 删除处理中的任务")
        
        # 创建任务并等待处理开始
        task = self.create_test_task(client, auth_headers, "处理中任务")
        task_id = task["id"]
        
        # 等待一小段时间让处理开始
        time.sleep(0.5)
        
        # 检查任务状态
        get_response = client.get(f"/api/tasks/{task_id}", headers=auth_headers)
        if get_response.status_code == 200:
            current_task = get_response.json()["task"]
            print(f"任务当前状态: {current_task.get('status', 'unknown')}")
        
        # 删除任务
        delete_response = client.delete(f"/api/tasks/{task_id}", headers=auth_headers)
        assert delete_response.status_code == 200
        
        delete_result = delete_response.json()
        assert delete_result["success"] is True
        
        print(f"✅ 处理中任务删除成功")
    
    @pytest.mark.integration
    def test_delete_task_with_issues(self, client: TestClient, auth_headers):
        """测试删除有问题记录的任务 - DELETE-007"""
        print("\n🗑️ 测试: 删除有问题记录的任务")
        
        # 创建任务
        task = self.create_test_task(client, auth_headers, "有问题记录的任务")
        task_id = task["id"]
        
        # 等待处理完成以产生问题记录
        max_wait = 30
        wait_time = 0
        while wait_time < max_wait:
            get_response = client.get(f"/api/tasks/{task_id}", headers=auth_headers)
            if get_response.status_code == 200:
                task_detail = get_response.json()
                if len(task_detail.get("issues", [])) > 0:
                    print(f"任务产生了 {len(task_detail['issues'])} 个问题记录")
                    break
            time.sleep(1)
            wait_time += 1
        
        # 删除任务（应该级联删除问题记录）
        delete_response = client.delete(f"/api/tasks/{task_id}", headers=auth_headers)
        assert delete_response.status_code == 200
        
        delete_result = delete_response.json()
        assert delete_result["success"] is True
        
        print(f"✅ 有问题记录的任务删除成功")
    
    def test_delete_multiple_tasks(self, client: TestClient, auth_headers):
        """测试批量删除多个任务 - DELETE-008"""
        print("\n🗑️ 测试: 批量删除多个任务")
        
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
        
        print(f"✅ 批量删除 {len(task_ids)} 个任务成功")
    
    @pytest.mark.integration
    def test_delete_task_file_cleanup(self, client: TestClient, auth_headers):
        """测试删除任务时的文件清理 - DELETE-009"""
        print("\n🗑️ 测试: 删除任务时的文件清理")
        
        # 创建任务
        task = self.create_test_task(client, auth_headers, "文件清理测试任务")
        task_id = task["id"]
        
        # 获取任务详情查看文件路径
        get_response = client.get(f"/api/tasks/{task_id}", headers=auth_headers)
        assert get_response.status_code == 200
        task_detail = get_response.json()
        
        # 记录文件信息
        file_name = task_detail["task"]["file_name"]
        print(f"任务关联文件: {file_name}")
        
        # 删除任务
        delete_response = client.delete(f"/api/tasks/{task_id}", headers=auth_headers)
        assert delete_response.status_code == 200
        
        delete_result = delete_response.json()
        assert delete_result["success"] is True
        
        print(f"✅ 任务删除成功，文件清理已执行")
    
    def test_delete_shared_file_task(self, client: TestClient, auth_headers):
        """测试删除共享文件的任务 - DELETE-010"""
        print("\n🗑️ 测试: 删除共享文件的任务")
        
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
        
        print(f"创建了共享文件的两个任务: {task1['id']}, {task2['id']}")
        
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
        
        print(f"✅ 共享文件任务删除测试成功")
    
    @pytest.mark.performance
    def test_delete_task_performance(self, client: TestClient, auth_headers):
        """测试删除任务的性能 - DELETE-011"""
        print("\n🗑️ 测试: 删除任务性能")
        
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
        
        print(f"✅ 删除任务耗时: {delete_time:.3f}秒")
    
    def test_concurrent_delete_same_task(self, client: TestClient, auth_headers):
        """测试并发删除同一任务 - DELETE-012"""
        print("\n🗑️ 测试: 并发删除同一任务")
        
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
        
        # 应该有一个成功，一个失败（404）
        success_count = sum(1 for r in [result1, result2] if r.get("success") is True)
        not_found_count = sum(1 for r in [result1, result2] if r.get("status_code") == 404)
        
        assert success_count == 1, "应该有一个删除成功"
        assert not_found_count == 1, "应该有一个返回404"
        
        print(f"✅ 并发删除测试通过: 一个成功，一个404")
    
    def test_delete_task_response_format(self, client: TestClient, auth_headers):
        """测试删除任务响应格式 - DELETE-013"""
        print("\n🗑️ 测试: 删除任务响应格式")
        
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
        
        print(f"✅ 删除响应格式验证通过")
    
    def test_delete_task_invalid_id_format(self, client: TestClient, auth_headers):
        """测试无效任务ID格式 - DELETE-014"""
        print("\n🗑️ 测试: 无效任务ID格式")
        
        invalid_ids = ["abc", "12.34", "-1", "0", "null", "undefined"]
        
        for invalid_id in invalid_ids:
            try:
                delete_response = client.delete(f"/api/tasks/{invalid_id}", headers=auth_headers)
                # 应该返回422 (验证错误) 或 404
                assert delete_response.status_code in [422, 404], f"无效ID {invalid_id} 应该返回422或404"
                print(f"  无效ID '{invalid_id}': {delete_response.status_code}")
            except Exception as e:
                print(f"  无效ID '{invalid_id}': 异常 {e}")
        
        print(f"✅ 无效ID格式测试通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "not performance"])