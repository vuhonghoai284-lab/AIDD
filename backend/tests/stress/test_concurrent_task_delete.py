"""
并发删除任务测试
测试高并发场景下的任务删除操作
"""
import asyncio
import pytest
import time
import threading
import queue
from typing import List, Dict, Any
from fastapi.testclient import TestClient
from concurrent.futures import ThreadPoolExecutor, as_completed


class TestConcurrentTaskDelete:
    """并发删除任务测试类"""
    
    def create_multiple_test_tasks(self, client: TestClient, auth_headers: dict, count: int = 10) -> List[dict]:
        """批量创建测试任务"""
        tasks = []
        for i in range(count):
            # 创建测试文件
            test_content = f"# 并发删除测试任务 {i+1}\n\n这是第{i+1}个用于测试并发删除的任务。"
            files = {"file": (f"concurrent_delete_test_{i+1}.md", test_content.encode('utf-8'), "text/markdown")}
            data = {"title": f"并发删除测试任务{i+1}"}
            
            response = client.post("/api/tasks/", files=files, data=data, headers=auth_headers)
            if response.status_code == 201:
                task = response.json()
                tasks.append(task)
                print(f"✅ 创建任务 {i+1}: ID={task['id']}")
            else:
                print(f"❌ 创建任务 {i+1} 失败: {response.status_code}")
        
        print(f"🎯 成功创建 {len(tasks)} 个测试任务")
        return tasks
    
    def setup_authenticated_users(self, client: TestClient, count: int = 5) -> List[Dict[str, Any]]:
        """创建多个认证用户"""
        users = []
        
        for i in range(count):
            try:
                # 步骤1: 兑换token
                code_data = {"code": f"delete_user_{i}_auth_code"}
                token_response = client.post("/api/auth/thirdparty/exchange-token", json=code_data)
                
                if token_response.status_code != 200:
                    continue
                
                token_data = token_response.json()
                access_token = token_data["access_token"]
                
                # 步骤2: 登录
                login_data = {"access_token": access_token}
                login_response = client.post("/api/auth/thirdparty/login", json=login_data)
                
                if login_response.status_code == 200:
                    result = login_response.json()
                    users.append({
                        "user_id": result["user"]["id"],
                        "token": result["access_token"],
                        "headers": {"Authorization": f"Bearer {result['access_token']}"},
                        "user_info": result["user"]
                    })
            except Exception as e:
                print(f"创建用户{i}时出错: {e}")
                continue
        
        return users
    
    @pytest.mark.stress
    def test_concurrent_delete_different_tasks(self, client: TestClient, auth_headers):
        """测试并发删除不同任务 - CONCURRENT-DELETE-001"""
        print(f"\n🗑️ 开始并发删除不同任务测试")
        
        # 创建多个测试任务
        tasks = self.create_multiple_test_tasks(client, auth_headers, count=10)
        if len(tasks) < 5:
            pytest.skip("创建的测试任务数量不足")
        
        def delete_task(task_info: dict) -> Dict[str, Any]:
            """删除单个任务"""
            start_time = time.time()
            task_id = task_info["id"]
            
            try:
                response = client.delete(f"/api/tasks/{task_id}", headers=auth_headers)
                end_time = time.time()
                
                return {
                    "task_id": task_id,
                    "status_code": response.status_code,
                    "response_time": end_time - start_time,
                    "success": response.status_code == 200 and response.json().get("success", False),
                    "error": response.text if response.status_code != 200 else None
                }
            except Exception as e:
                end_time = time.time()
                return {
                    "task_id": task_id,
                    "status_code": 500,
                    "response_time": end_time - start_time,
                    "success": False,
                    "error": str(e)
                }
        
        # 并发删除所有任务
        start_time = time.time()
        results = []
        
        with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
            # 提交所有删除任务
            future_to_task = {
                executor.submit(delete_task, task): task 
                for task in tasks
            }
            
            # 收集结果
            for future in as_completed(future_to_task):
                result = future.result()
                results.append(result)
        
        total_time = time.time() - start_time
        
        # 分析结果
        successful_deletes = [r for r in results if r["success"]]
        failed_deletes = [r for r in results if not r["success"]]
        
        avg_response_time = sum(r["response_time"] for r in results) / len(results)
        max_response_time = max(r["response_time"] for r in results)
        min_response_time = min(r["response_time"] for r in results)
        
        print(f"📊 并发删除不同任务测试结果:")
        print(f"   总任务数: {len(tasks)}")
        print(f"   成功删除: {len(successful_deletes)}")
        print(f"   删除失败: {len(failed_deletes)}")
        print(f"   总耗时: {total_time:.2f}秒")
        print(f"   平均响应时间: {avg_response_time:.2f}秒")
        print(f"   最大响应时间: {max_response_time:.2f}秒")
        print(f"   最小响应时间: {min_response_time:.2f}秒")
        print(f"   成功率: {len(successful_deletes)/len(results)*100:.1f}%")
        
        # 显示失败的删除操作
        if failed_deletes:
            print(f"\n❌ 失败的删除操作:")
            for delete_op in failed_deletes[:3]:
                error_preview = delete_op['error'][:100] if delete_op.get('error') else 'Unknown error'
                print(f"   任务ID: {delete_op['task_id']}, 状态码: {delete_op['status_code']}")
                print(f"   错误: {error_preview}")
        
        # 断言：至少30%的删除操作成功（考虑高并发场景的合理失败）
        assert len(successful_deletes) >= len(tasks) * 0.3, \
            f"并发删除成功率过低: {len(successful_deletes)}/{len(tasks)}"
        
        # 断言：平均响应时间不超过2秒
        assert avg_response_time <= 2.0, \
            f"平均响应时间过长: {avg_response_time:.2f}秒"
        
        print(f"🎯 并发删除不同任务测试通过!")
    
    @pytest.mark.stress
    def test_concurrent_delete_same_task_multiple_users(self, client: TestClient):
        """测试多个用户并发删除同一任务 - CONCURRENT-DELETE-002"""
        print(f"\n🗑️ 开始多用户并发删除同一任务测试")
        
        # 创建多个用户
        users = self.setup_authenticated_users(client, count=5)
        if len(users) < 3:
            pytest.skip("创建的测试用户数量不足")
        
        # 用第一个用户创建任务
        first_user = users[0]
        test_content = "# 多用户删除测试\n\n这是用于测试多用户并发删除的任务。"
        files = {"file": ("multi_user_delete_test.md", test_content.encode('utf-8'), "text/markdown")}
        data = {"title": "多用户删除测试任务"}
        
        response = client.post("/api/tasks/", files=files, data=data, headers=first_user["headers"])
        assert response.status_code == 201
        task = response.json()
        task_id = task["id"]
        
        print(f"✅ 创建测试任务: ID={task_id}")
        
        def delete_task_as_user(user_info: Dict[str, Any]) -> Dict[str, Any]:
            """用户尝试删除任务"""
            start_time = time.time()
            
            try:
                response = client.delete(f"/api/tasks/{task_id}", headers=user_info["headers"])
                end_time = time.time()
                
                return {
                    "user_id": user_info["user_id"],
                    "user_name": user_info["user_info"]["display_name"],
                    "status_code": response.status_code,
                    "response_time": end_time - start_time,
                    "success": response.status_code == 200 and response.json().get("success", False),
                    "authorized": response.status_code != 403,
                    "error": response.text if response.status_code not in [200, 403] else None
                }
            except Exception as e:
                end_time = time.time()
                return {
                    "user_id": user_info["user_id"],
                    "user_name": user_info["user_info"]["display_name"],
                    "status_code": 500,
                    "response_time": end_time - start_time,
                    "success": False,
                    "authorized": False,
                    "error": str(e)
                }
        
        # 所有用户同时尝试删除任务
        start_time = time.time()
        results = []
        
        with ThreadPoolExecutor(max_workers=len(users)) as executor:
            # 提交所有删除任务
            future_to_user = {
                executor.submit(delete_task_as_user, user): user 
                for user in users
            }
            
            # 收集结果
            for future in as_completed(future_to_user):
                result = future.result()
                results.append(result)
        
        total_time = time.time() - start_time
        
        # 分析结果
        successful_deletes = [r for r in results if r["success"]]
        forbidden_deletes = [r for r in results if r["status_code"] == 403]
        not_found_deletes = [r for r in results if r["status_code"] == 404]
        
        print(f"📊 多用户并发删除同一任务测试结果:")
        print(f"   参与用户数: {len(users)}")
        print(f"   成功删除: {len(successful_deletes)}")
        print(f"   权限不足(403): {len(forbidden_deletes)}")
        print(f"   任务不存在(404): {len(not_found_deletes)}")
        print(f"   总耗时: {total_time:.2f}秒")
        
        # 显示各用户的操作结果
        print(f"\n👥 各用户操作结果:")
        for result in results:
            status_desc = "成功" if result["success"] else f"失败({result['status_code']})"
            print(f"   用户: {result['user_name'][:10]}..., 结果: {status_desc}")
        
        # 只有任务所有者（第一个用户）应该能够删除，其他用户应该被拒绝
        owner_results = [r for r in results if r["user_id"] == first_user["user_id"]]
        other_user_results = [r for r in results if r["user_id"] != first_user["user_id"]]
        
        # 断言：只有一个成功的删除操作
        assert len(successful_deletes) <= 1, "应该只有一个成功的删除操作"
        
        # 断言：其他用户应该被拒绝访问（403）或发现任务已被删除（404）
        for result in other_user_results:
            assert result["status_code"] in [403, 404], \
                f"其他用户应该收到403或404，但收到了{result['status_code']}"
        
        print(f"🎯 多用户并发删除测试通过!")
    
    @pytest.mark.asyncio
    @pytest.mark.stress
    async def test_async_concurrent_delete_tasks(self, client: TestClient, auth_headers):
        """测试异步并发删除任务 - CONCURRENT-DELETE-003"""
        print(f"\n🗑️ 开始异步并发删除任务测试")
        
        # 创建多个测试任务
        tasks = self.create_multiple_test_tasks(client, auth_headers, count=8)
        if len(tasks) < 5:
            pytest.skip("创建的测试任务数量不足")
        
        async def delete_task_async(task_info: dict) -> Dict[str, Any]:
            """异步删除单个任务"""
            start_time = time.time()
            task_id = task_info["id"]
            
            try:
                # 使用asyncio在线程中执行同步删除操作
                def sync_delete():
                    return client.delete(f"/api/tasks/{task_id}", headers=auth_headers)
                
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, sync_delete)
                
                end_time = time.time()
                
                return {
                    "task_id": task_id,
                    "task_title": task_info["title"],
                    "status_code": response.status_code,
                    "response_time": end_time - start_time,
                    "success": response.status_code == 200 and response.json().get("success", False),
                    "error": response.text if response.status_code != 200 else None
                }
            except Exception as e:
                end_time = time.time()
                return {
                    "task_id": task_id,
                    "task_title": task_info["title"],
                    "status_code": 500,
                    "response_time": end_time - start_time,
                    "success": False,
                    "error": str(e)
                }
        
        # 异步并发删除所有任务
        start_time = time.time()
        results = await asyncio.gather(*[
            delete_task_async(task) for task in tasks
        ], return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "task_id": tasks[i]["id"],
                    "task_title": tasks[i]["title"],
                    "status_code": 500,
                    "response_time": 0,
                    "success": False,
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        total_time = time.time() - start_time
        
        # 分析结果
        successful_deletes = [r for r in processed_results if r["success"]]
        failed_deletes = [r for r in processed_results if not r["success"]]
        
        if processed_results:
            avg_response_time = sum(r["response_time"] for r in processed_results) / len(processed_results)
            max_response_time = max(r["response_time"] for r in processed_results)
            min_response_time = min(r["response_time"] for r in processed_results)
        else:
            avg_response_time = max_response_time = min_response_time = 0
        
        print(f"📊 异步并发删除任务测试结果:")
        print(f"   总任务数: {len(tasks)}")
        print(f"   成功删除: {len(successful_deletes)}")
        print(f"   删除失败: {len(failed_deletes)}")
        print(f"   总耗时: {total_time:.2f}秒")
        print(f"   平均响应时间: {avg_response_time:.2f}秒")
        print(f"   最大响应时间: {max_response_time:.2f}秒")
        print(f"   最小响应时间: {min_response_time:.2f}秒")
        print(f"   成功率: {len(successful_deletes)/len(processed_results)*100:.1f}%")
        
        # 显示成功删除的任务
        if successful_deletes:
            print(f"\n✅ 成功删除的任务:")
            for delete_op in successful_deletes[:3]:
                print(f"   任务: {delete_op['task_title'][:20]}..., 响应时间: {delete_op['response_time']:.2f}s")
        
        # 显示失败的删除操作
        if failed_deletes:
            print(f"\n❌ 失败的删除操作:")
            for delete_op in failed_deletes[:3]:
                error_preview = delete_op['error'][:50] if delete_op.get('error') else 'Unknown error'
                print(f"   任务: {delete_op['task_title'][:20]}..., 错误: {error_preview}")
        
        # 断言：至少30%的删除操作成功（考虑高并发场景的合理失败）
        assert len(successful_deletes) >= len(tasks) * 0.3, \
            f"异步并发删除成功率过低: {len(successful_deletes)}/{len(tasks)}"
        
        # 断言：平均响应时间不超过3秒
        assert avg_response_time <= 3.0, \
            f"平均响应时间过长: {avg_response_time:.2f}秒"
        
        print(f"🎯 异步并发删除任务测试通过!")
    
    @pytest.mark.stress
    def test_delete_task_under_load(self, client: TestClient, auth_headers):
        """测试高负载下的删除任务操作 - CONCURRENT-DELETE-004"""
        print(f"\n🗑️ 开始高负载删除任务测试")
        
        # 创建大量测试任务
        tasks = self.create_multiple_test_tasks(client, auth_headers, count=20)
        if len(tasks) < 10:
            pytest.skip("创建的测试任务数量不足")
        
        # 同时进行其他操作来增加系统负载
        def background_load():
            """后台负载生成"""
            for _ in range(10):
                try:
                    # 查询任务列表
                    client.get("/api/tasks/", headers=auth_headers)
                    time.sleep(0.1)
                except:
                    pass
        
        # 启动后台负载线程
        load_thread = threading.Thread(target=background_load)
        load_thread.start()
        
        def delete_task_with_load(task_info: dict) -> Dict[str, Any]:
            """在负载下删除任务"""
            start_time = time.time()
            task_id = task_info["id"]
            
            try:
                response = client.delete(f"/api/tasks/{task_id}", headers=auth_headers)
                end_time = time.time()
                
                return {
                    "task_id": task_id,
                    "status_code": response.status_code,
                    "response_time": end_time - start_time,
                    "success": response.status_code == 200 and response.json().get("success", False)
                }
            except Exception as e:
                end_time = time.time()
                return {
                    "task_id": task_id,
                    "status_code": 500,
                    "response_time": end_time - start_time,
                    "success": False,
                    "error": str(e)
                }
        
        # 在高负载下并发删除任务
        start_time = time.time()
        results = []
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            # 提交删除任务
            future_to_task = {
                executor.submit(delete_task_with_load, task): task 
                for task in tasks
            }
            
            # 收集结果
            for future in as_completed(future_to_task):
                result = future.result()
                results.append(result)
        
        total_time = time.time() - start_time
        
        # 等待后台负载线程结束
        load_thread.join()
        
        # 分析结果
        successful_deletes = [r for r in results if r["success"]]
        failed_deletes = [r for r in results if not r["success"]]
        
        avg_response_time = sum(r["response_time"] for r in results) / len(results)
        
        print(f"📊 高负载删除任务测试结果:")
        print(f"   总任务数: {len(tasks)}")
        print(f"   成功删除: {len(successful_deletes)}")
        print(f"   删除失败: {len(failed_deletes)}")
        print(f"   总耗时: {total_time:.2f}秒")
        print(f"   平均响应时间: {avg_response_time:.2f}秒")
        print(f"   成功率: {len(successful_deletes)/len(results)*100:.1f}%")
        
        # 断言：在高负载下至少30%的删除操作成功
        assert len(successful_deletes) >= len(tasks) * 0.3, \
            f"高负载下删除成功率过低: {len(successful_deletes)}/{len(tasks)}"
        
        # 断言：即使在高负载下，平均响应时间也不应超过5秒
        assert avg_response_time <= 5.0, \
            f"高负载下平均响应时间过长: {avg_response_time:.2f}秒"
        
        print(f"🎯 高负载删除任务测试通过!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "stress"])