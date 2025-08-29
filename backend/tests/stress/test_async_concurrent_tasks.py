"""
异步并发任务测试 - 使用pytest异步框架
"""
import asyncio
import pytest
import time
from typing import List, Dict, Any
from fastapi.testclient import TestClient


class TestAsyncConcurrentTasks:
    """异步并发任务测试类"""
    
    def setup_authenticated_users(self, client: TestClient, count: int = 5) -> List[Dict[str, Any]]:
        """创建多个认证用户（同步版本）"""
        users = []
        
        for i in range(count):
            try:
                # 步骤1: 兑换token
                code_data = {"code": f"async_user_{i}_auth_code"}
                token_response = client.post("/api/auth/thirdparty/exchange-token", json=code_data)
                
                if token_response.status_code != 200:
                    print(f"用户{i} Token兑换失败: {token_response.status_code}")
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
                    print(f"✅ 用户{i}创建成功: {result['user']['display_name']}")
                else:
                    print(f"用户{i} 登录失败: {login_response.status_code}")
            except Exception as e:
                print(f"创建用户{i}时出错: {e}")
                continue
        
        print(f"🎯 成功创建{len(users)}个异步测试用户")
        return users
    
    def create_test_document(self, user_id: int, size_kb: int = 1) -> tuple:
        """创建测试文档"""
        base_content = f"# 异步并发测试文档 - 用户{user_id}\n\n" * 20  # 约1KB
        content = base_content * size_kb
        
        structured_content = f"""# 用户{user_id}的测试文档

## 第一节：简介
{content}

## 第二节：详细内容  
这是用户{user_id}提交的测试文档，用于验证系统的异步并发处理能力。

### 2.1 系统性能测试
本节测试系统在高并发情况下的表现。

### 2.2 数据一致性验证
验证并发操作不会导致数据不一致。

## 第三节：总结
测试文档创建完成，等待系统处理。
"""
        
        return (f"async_test_user_{user_id}.md", structured_content.encode('utf-8'), "text/markdown")
    
    @pytest.mark.asyncio
    @pytest.mark.stress
    async def test_async_concurrent_task_creation(self, client):
        """异步并发任务创建测试"""
        # 设置认证用户
        authenticated_users = self.setup_authenticated_users(client, count=5)
        
        if len(authenticated_users) == 0:
            pytest.skip("无法创建测试用户，跳过测试")
            
        print(f"\n🚀 开始异步并发任务创建测试 - {len(authenticated_users)}个用户")
        
        async def create_task(user_info: Dict[str, Any]) -> Dict[str, Any]:
            """异步创建单个任务（使用同步client但在线程中执行）"""
            start_time = time.time()
            
            try:
                # 创建测试文档
                filename, content, content_type = self.create_test_document(
                    user_info["user_id"], size_kb=2
                )
                
                # 使用asyncio在线程中执行同步请求
                def sync_create_task():
                    return client.post(
                        "/api/tasks/",
                        files={"file": (filename, content, content_type)},
                        data={"title": f"异步并发测试任务 - 用户{user_info['user_id']}"},
                        headers=user_info["headers"]
                    )
                
                # 在线程池中执行同步操作
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, sync_create_task)
                
                end_time = time.time()
                
                return {
                    "user_id": user_info["user_id"],
                    "status_code": response.status_code,
                    "response_time": end_time - start_time,
                    "success": response.status_code == 201,
                    "task_id": response.json().get("id") if response.status_code == 201 else None,
                    "error": response.text if response.status_code != 201 else None,
                    "user_name": user_info["user_info"]["display_name"]
                }
                
            except Exception as e:
                end_time = time.time()
                return {
                    "user_id": user_info["user_id"],
                    "status_code": 500,
                    "response_time": end_time - start_time,
                    "success": False,
                    "task_id": None,
                    "error": str(e),
                    "user_name": user_info["user_info"]["display_name"]
                }
        
        # 并发执行所有任务创建
        start_time = time.time()
        results = await asyncio.gather(*[
            create_task(user) for user in authenticated_users
        ], return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "user_id": authenticated_users[i]["user_id"],
                    "status_code": 500,
                    "response_time": 0,
                    "success": False,
                    "task_id": None,
                    "error": str(result),
                    "user_name": authenticated_users[i]["user_info"]["display_name"]
                })
            else:
                processed_results.append(result)
        
        total_time = time.time() - start_time
        
        # 分析结果
        successful_tasks = [r for r in processed_results if r["success"]]
        failed_tasks = [r for r in processed_results if not r["success"]]
        
        if processed_results:
            avg_response_time = sum(r["response_time"] for r in processed_results) / len(processed_results)
            max_response_time = max(r["response_time"] for r in processed_results)
            min_response_time = min(r["response_time"] for r in processed_results)
        else:
            avg_response_time = max_response_time = min_response_time = 0
        
        print(f"\n📊 异步并发任务创建测试结果:")
        print(f"   总用户数: {len(authenticated_users)}")
        print(f"   成功任务: {len(successful_tasks)}")
        print(f"   失败任务: {len(failed_tasks)}")
        print(f"   总耗时: {total_time:.2f}秒")
        print(f"   平均响应时间: {avg_response_time:.2f}秒")
        print(f"   最大响应时间: {max_response_time:.2f}秒")
        print(f"   最小响应时间: {min_response_time:.2f}秒")
        print(f"   成功率: {len(successful_tasks)/len(processed_results)*100:.1f}%")
        
        # 显示成功任务的详细信息
        if successful_tasks:
            print(f"\n✅ 成功创建的任务:")
            for task in successful_tasks[:3]:  # 显示前3个
                print(f"   用户: {task['user_name']}, 任务ID: {task['task_id']}, 响应时间: {task['response_time']:.2f}s")
        
        # 显示失败任务的详细信息
        if failed_tasks:
            print(f"\n❌ 失败的任务:")
            for task in failed_tasks[:3]:  # 显示前3个
                error_preview = task['error'][:100] if task.get('error') else 'Unknown error'
                print(f"   用户: {task['user_name']}, 状态码: {task['status_code']}")
                print(f"   错误: {error_preview}")
                print("   ---")
        
        # 性能断言
        assert len(successful_tasks) >= len(authenticated_users) * 0.3, \
            f"异步并发任务创建成功率过低: {len(successful_tasks)}/{len(authenticated_users)}"
        
        assert avg_response_time <= 10.0, \
            f"平均响应时间过长: {avg_response_time:.2f}秒"
        
        print(f"🎯 异步并发任务创建测试通过!")
        
        # 返回成功的任务ID供后续测试使用
        return [t["task_id"] for t in successful_tasks if t["task_id"]]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "stress"])