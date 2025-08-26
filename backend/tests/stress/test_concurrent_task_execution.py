"""
高并发任务执行测试
模拟真实高并发场景下的任务创建、执行和管理
"""
import asyncio
import json
import pytest
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
import tempfile
from pathlib import Path

# 导入必要的模块
from app.services.auth import AuthService
from app.dto.user import UserCreate
from app.core.database import SessionLocal
from app.models.task import Task
from app.models.user import User


class TestConcurrentTaskExecution:
    """高并发任务执行测试类"""
    
    @pytest.fixture(autouse=True)
    def setup_concurrent_users(self, client):
        """设置多个并发用户"""
        self.concurrent_users = []
        
        # 创建10个测试用户用于并发测试
        for i in range(10):
            # 通过API创建用户并获取token
            auth_data = {"code": f"concurrent_user_{i}_auth_code"}
            response = client.post("/api/auth/thirdparty/login", json=auth_data)
            
            if response.status_code == 200:
                result = response.json()
                self.concurrent_users.append({
                    "user_id": result["user"]["id"],
                    "token": result["access_token"],
                    "headers": {"Authorization": f"Bearer {result['access_token']}"}
                })
        
        assert len(self.concurrent_users) >= 5, "至少需要5个用户进行并发测试"
        
        yield
        
        # 清理工作
        self.concurrent_users.clear()
    
    def create_test_document(self, size_kb: int = 1) -> tuple:
        """
        创建测试文档
        
        Args:
            size_kb: 文档大小（KB）
        
        Returns:
            (filename, content, content_type)
        """
        # 创建指定大小的测试文档
        base_content = "这是一个用于高并发测试的文档内容。" * 50  # 约1KB
        content = base_content * size_kb
        
        # 添加一些结构化内容
        structured_content = f"""
# 测试文档标题

## 第一节：介绍
{content}

## 第二节：详细内容
{content}

## 第三节：总结
这是文档的总结部分，包含了重要的结论和建议。

### 3.1 子章节
更多详细信息和分析内容。

### 3.2 建议
基于分析的具体建议和行动计划。
        """
        
        return ("concurrent_test.md", structured_content.encode('utf-8'), "text/markdown")
    
    @pytest.mark.stress
    def test_concurrent_task_creation(self, client):
        """测试并发任务创建"""
        print(f"\n🚀 开始并发任务创建测试 - {len(self.concurrent_users)}个用户")
        
        def create_task(user_info: Dict) -> Dict:
            """单个用户创建任务"""
            start_time = time.time()
            
            try:
                # 创建测试文档
                filename, content, content_type = self.create_test_document(size_kb=2)
                
                # 通过API创建任务
                response = client.post(
                    "/api/tasks/",
                    files={"file": (filename, content, content_type)},
                    data={"description": f"并发测试任务 - 用户{user_info['user_id']}"},
                    headers=user_info["headers"]
                )
                
                end_time = time.time()
                
                return {
                    "user_id": user_info["user_id"],
                    "status_code": response.status_code,
                    "response_time": end_time - start_time,
                    "success": response.status_code == 201,
                    "task_id": response.json().get("id") if response.status_code == 201 else None,
                    "error": response.text if response.status_code != 201 else None
                }
                
            except Exception as e:
                end_time = time.time()
                return {
                    "user_id": user_info["user_id"],
                    "status_code": 500,
                    "response_time": end_time - start_time,
                    "success": False,
                    "task_id": None,
                    "error": str(e)
                }
        
        # 使用线程池执行并发任务创建
        start_time = time.time()
        results = []
        
        with ThreadPoolExecutor(max_workers=len(self.concurrent_users)) as executor:
            # 提交所有任务
            future_to_user = {
                executor.submit(create_task, user): user 
                for user in self.concurrent_users
            }
            
            # 收集结果
            for future in as_completed(future_to_user):
                result = future.result()
                results.append(result)
        
        total_time = time.time() - start_time
        
        # 分析结果
        successful_tasks = [r for r in results if r["success"]]
        failed_tasks = [r for r in results if not r["success"]]
        
        avg_response_time = sum(r["response_time"] for r in results) / len(results)
        max_response_time = max(r["response_time"] for r in results)
        min_response_time = min(r["response_time"] for r in results)
        
        print(f"📊 并发任务创建测试结果:")
        print(f"   总用户数: {len(self.concurrent_users)}")
        print(f"   成功任务: {len(successful_tasks)}")
        print(f"   失败任务: {len(failed_tasks)}")
        print(f"   总耗时: {total_time:.2f}秒")
        print(f"   平均响应时间: {avg_response_time:.2f}秒")
        print(f"   最大响应时间: {max_response_time:.2f}秒")
        print(f"   最小响应时间: {min_response_time:.2f}秒")
        print(f"   成功率: {len(successful_tasks)/len(results)*100:.1f}%")
        
        # 断言：至少80%的任务创建成功
        assert len(successful_tasks) >= len(self.concurrent_users) * 0.8, \
            f"并发任务创建成功率过低: {len(successful_tasks)}/{len(self.concurrent_users)}"
        
        # 断言：平均响应时间不超过5秒
        assert avg_response_time <= 5.0, \
            f"平均响应时间过长: {avg_response_time:.2f}秒"
        
        # 保存成功的任务ID供后续测试使用
        self.created_task_ids = [r["task_id"] for r in successful_tasks if r["task_id"]]
    
    @pytest.mark.stress 
    def test_concurrent_task_execution(self, client):
        """测试并发任务执行"""
        print(f"\n⚡ 开始并发任务执行测试")
        
        # 先创建一些任务
        task_ids = []
        for i, user in enumerate(self.concurrent_users[:5]):  # 只用前5个用户
            filename, content, content_type = self.create_test_document(size_kb=1)
            
            response = client.post(
                "/api/tasks/",
                files={"file": (filename, content, content_type)},
                data={"description": f"并发执行测试任务 {i}"},
                headers=user["headers"]
            )
            
            if response.status_code == 201:
                task_ids.append(response.json()["id"])
        
        assert len(task_ids) >= 3, "需要至少3个任务用于并发执行测试"
        
        def execute_task(task_id: int, user_info: Dict) -> Dict:
            """执行单个任务"""
            start_time = time.time()
            
            try:
                # 通过API执行任务
                response = client.post(
                    f"/api/tasks/{task_id}/retry",
                    headers=user_info["headers"]
                )
                
                end_time = time.time()
                
                return {
                    "task_id": task_id,
                    "user_id": user_info["user_id"],
                    "status_code": response.status_code,
                    "response_time": end_time - start_time,
                    "success": response.status_code == 200,
                    "error": response.text if response.status_code != 200 else None
                }
                
            except Exception as e:
                end_time = time.time()
                return {
                    "task_id": task_id,
                    "user_id": user_info["user_id"],
                    "status_code": 500,
                    "response_time": end_time - start_time,
                    "success": False,
                    "error": str(e)
                }
        
        # 执行并发任务
        start_time = time.time()
        results = []
        
        with ThreadPoolExecutor(max_workers=len(task_ids)) as executor:
            # 每个任务分配给一个用户执行
            future_to_task = {}
            for i, task_id in enumerate(task_ids):
                user = self.concurrent_users[i % len(self.concurrent_users)]
                future_to_task[executor.submit(execute_task, task_id, user)] = task_id
            
            # 收集结果
            for future in as_completed(future_to_task):
                result = future.result()
                results.append(result)
        
        total_time = time.time() - start_time
        
        # 分析结果
        successful_executions = [r for r in results if r["success"]]
        failed_executions = [r for r in results if not r["success"]]
        
        avg_response_time = sum(r["response_time"] for r in results) / len(results)
        
        print(f"📊 并发任务执行测试结果:")
        print(f"   执行任务数: {len(task_ids)}")
        print(f"   成功执行: {len(successful_executions)}")
        print(f"   执行失败: {len(failed_executions)}")
        print(f"   总耗时: {total_time:.2f}秒")
        print(f"   平均响应时间: {avg_response_time:.2f}秒")
        
        # 断言：至少70%的任务执行成功
        assert len(successful_executions) >= len(task_ids) * 0.7, \
            f"并发任务执行成功率过低: {len(successful_executions)}/{len(task_ids)}"
    
    @pytest.mark.stress
    def test_concurrent_task_status_checking(self, client):
        """测试并发任务状态查询"""
        print(f"\n📊 开始并发任务状态查询测试")
        
        # 创建一些任务用于状态查询
        task_ids = []
        for i, user in enumerate(self.concurrent_users[:3]):
            filename, content, content_type = self.create_test_document()
            
            response = client.post(
                "/api/tasks/",
                files={"file": (filename, content, content_type)},
                data={"description": f"状态查询测试任务 {i}"},
                headers=user["headers"]
            )
            
            if response.status_code == 201:
                task_ids.append(response.json()["id"])
        
        assert len(task_ids) >= 2, "需要至少2个任务用于状态查询测试"
        
        def check_task_status(task_id: int, user_info: Dict, check_count: int = 10) -> Dict:
            """检查任务状态多次"""
            start_time = time.time()
            successful_checks = 0
            total_checks = 0
            
            try:
                for _ in range(check_count):
                    response = client.get(
                        f"/api/tasks/{task_id}",
                        headers=user_info["headers"]
                    )
                    
                    total_checks += 1
                    if response.status_code == 200:
                        successful_checks += 1
                    
                    # 短暂延迟模拟真实查询间隔
                    time.sleep(0.1)
                
                end_time = time.time()
                
                return {
                    "task_id": task_id,
                    "user_id": user_info["user_id"],
                    "total_checks": total_checks,
                    "successful_checks": successful_checks,
                    "response_time": end_time - start_time,
                    "success_rate": successful_checks / total_checks if total_checks > 0 else 0
                }
                
            except Exception as e:
                end_time = time.time()
                return {
                    "task_id": task_id,
                    "user_id": user_info["user_id"],
                    "total_checks": total_checks,
                    "successful_checks": successful_checks,
                    "response_time": end_time - start_time,
                    "success_rate": 0,
                    "error": str(e)
                }
        
        # 并发状态查询
        start_time = time.time()
        results = []
        
        with ThreadPoolExecutor(max_workers=len(task_ids) * 2) as executor:
            # 每个任务由两个不同用户同时查询
            futures = []
            for task_id in task_ids:
                for user in self.concurrent_users[:2]:  # 前两个用户
                    future = executor.submit(check_task_status, task_id, user, 5)
                    futures.append(future)
            
            # 收集结果
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
        
        total_time = time.time() - start_time
        
        # 分析结果
        total_checks = sum(r["total_checks"] for r in results)
        total_successful_checks = sum(r["successful_checks"] for r in results)
        avg_success_rate = sum(r["success_rate"] for r in results) / len(results)
        
        print(f"📊 并发状态查询测试结果:")
        print(f"   并发查询数: {len(results)}")
        print(f"   总查询次数: {total_checks}")
        print(f"   成功查询次数: {total_successful_checks}")
        print(f"   总耗时: {total_time:.2f}秒")
        print(f"   平均成功率: {avg_success_rate*100:.1f}%")
        
        # 断言：成功率至少90%
        assert avg_success_rate >= 0.9, \
            f"并发状态查询成功率过低: {avg_success_rate*100:.1f}%"
    
    @pytest.mark.stress
    def test_mixed_concurrent_operations(self, client):
        """测试混合并发操作（创建、执行、查询）"""
        print(f"\n🔄 开始混合并发操作测试")
        
        results = {
            "create": [],
            "execute": [],
            "query": []
        }
        
        def create_tasks(user_info: Dict, count: int = 3) -> List[Dict]:
            """创建多个任务"""
            task_results = []
            for i in range(count):
                try:
                    filename, content, content_type = self.create_test_document()
                    start_time = time.time()
                    
                    response = client.post(
                        "/api/tasks/",
                        files={"file": (filename, content, content_type)},
                        data={"description": f"混合测试任务 {i}"},
                        headers=user_info["headers"]
                    )
                    
                    end_time = time.time()
                    
                    task_results.append({
                        "operation": "create",
                        "user_id": user_info["user_id"],
                        "success": response.status_code == 201,
                        "response_time": end_time - start_time,
                        "task_id": response.json().get("id") if response.status_code == 201 else None
                    })
                    
                except Exception as e:
                    task_results.append({
                        "operation": "create",
                        "user_id": user_info["user_id"],
                        "success": False,
                        "response_time": 0,
                        "error": str(e)
                    })
            
            return task_results
        
        def query_tasks(user_info: Dict, count: int = 5) -> List[Dict]:
            """查询任务列表"""
            query_results = []
            for i in range(count):
                try:
                    start_time = time.time()
                    
                    response = client.get(
                        "/api/tasks/",
                        headers=user_info["headers"]
                    )
                    
                    end_time = time.time()
                    
                    query_results.append({
                        "operation": "query",
                        "user_id": user_info["user_id"],
                        "success": response.status_code == 200,
                        "response_time": end_time - start_time
                    })
                    
                    time.sleep(0.2)  # 查询间隔
                    
                except Exception as e:
                    query_results.append({
                        "operation": "query", 
                        "user_id": user_info["user_id"],
                        "success": False,
                        "response_time": 0,
                        "error": str(e)
                    })
            
            return query_results
        
        # 执行混合并发操作
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=len(self.concurrent_users)) as executor:
            futures = []
            
            # 一半用户创建任务
            for user in self.concurrent_users[:len(self.concurrent_users)//2]:
                future = executor.submit(create_tasks, user, 2)
                futures.append(future)
            
            # 另一半用户查询任务
            for user in self.concurrent_users[len(self.concurrent_users)//2:]:
                future = executor.submit(query_tasks, user, 3)
                futures.append(future)
            
            # 收集结果
            for future in as_completed(futures):
                operation_results = future.result()
                for result in operation_results:
                    results[result["operation"]].append(result)
        
        total_time = time.time() - start_time
        
        # 分析混合操作结果
        for operation, operation_results in results.items():
            if operation_results:
                successful = [r for r in operation_results if r["success"]]
                avg_time = sum(r["response_time"] for r in operation_results) / len(operation_results)
                
                print(f"📊 {operation.upper()}操作结果:")
                print(f"   操作次数: {len(operation_results)}")
                print(f"   成功次数: {len(successful)}")
                print(f"   成功率: {len(successful)/len(operation_results)*100:.1f}%")
                print(f"   平均响应时间: {avg_time:.2f}秒")
        
        print(f"🎯 混合操作总耗时: {total_time:.2f}秒")
        
        # 断言：各类操作的成功率都不低于75%
        for operation, operation_results in results.items():
            if operation_results:
                successful = [r for r in operation_results if r["success"]]
                success_rate = len(successful) / len(operation_results)
                assert success_rate >= 0.75, \
                    f"{operation}操作成功率过低: {success_rate*100:.1f}%"
    
    @pytest.mark.stress
    def test_database_connection_pool_under_load(self, client):
        """测试负载下的数据库连接池性能"""
        print(f"\n🗄️ 开始数据库连接池负载测试")
        
        def db_intensive_operation(user_info: Dict, operation_id: int) -> Dict:
            """数据库密集型操作"""
            start_time = time.time()
            
            try:
                # 执行一系列数据库密集型操作
                operations = []
                
                # 1. 查询任务列表
                response1 = client.get("/api/tasks/", headers=user_info["headers"])
                operations.append(("list_tasks", response1.status_code == 200))
                
                # 2. 查询用户信息
                response2 = client.get("/api/users/me", headers=user_info["headers"])
                operations.append(("get_user", response2.status_code == 200))
                
                # 3. 查询AI输出（如果有任务的话）
                if response1.status_code == 200:
                    tasks = response1.json()
                    if tasks:
                        task_id = tasks[0]["id"]
                        response3 = client.get(f"/api/ai-outputs/task/{task_id}", headers=user_info["headers"])
                        operations.append(("get_ai_outputs", response3.status_code == 200))
                
                end_time = time.time()
                
                successful_ops = [op for op in operations if op[1]]
                
                return {
                    "operation_id": operation_id,
                    "user_id": user_info["user_id"],
                    "total_operations": len(operations),
                    "successful_operations": len(successful_ops),
                    "response_time": end_time - start_time,
                    "success": len(successful_ops) == len(operations)
                }
                
            except Exception as e:
                end_time = time.time()
                return {
                    "operation_id": operation_id,
                    "user_id": user_info["user_id"],
                    "total_operations": 0,
                    "successful_operations": 0,
                    "response_time": end_time - start_time,
                    "success": False,
                    "error": str(e)
                }
        
        # 高强度数据库操作
        start_time = time.time()
        results = []
        
        with ThreadPoolExecutor(max_workers=len(self.concurrent_users) * 2) as executor:
            futures = []
            
            # 每个用户执行多次数据库操作
            operation_id = 0
            for user in self.concurrent_users:
                for i in range(3):  # 每用户3次操作
                    future = executor.submit(db_intensive_operation, user, operation_id)
                    futures.append(future)
                    operation_id += 1
            
            # 收集结果
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
        
        total_time = time.time() - start_time
        
        # 分析数据库连接池性能
        successful_operations = [r for r in results if r["success"]]
        total_db_operations = sum(r["total_operations"] for r in results)
        successful_db_operations = sum(r["successful_operations"] for r in results)
        
        avg_response_time = sum(r["response_time"] for r in results) / len(results)
        max_response_time = max(r["response_time"] for r in results)
        
        print(f"📊 数据库连接池负载测试结果:")
        print(f"   并发操作组数: {len(results)}")
        print(f"   成功操作组: {len(successful_operations)}")
        print(f"   总数据库操作数: {total_db_operations}")
        print(f"   成功数据库操作数: {successful_db_operations}")
        print(f"   操作组成功率: {len(successful_operations)/len(results)*100:.1f}%")
        print(f"   数据库操作成功率: {successful_db_operations/total_db_operations*100:.1f}%")
        print(f"   平均响应时间: {avg_response_time:.2f}秒")
        print(f"   最大响应时间: {max_response_time:.2f}秒")
        print(f"   总耗时: {total_time:.2f}秒")
        
        # 断言：数据库操作成功率至少85%
        db_success_rate = successful_db_operations / total_db_operations if total_db_operations > 0 else 0
        assert db_success_rate >= 0.85, \
            f"数据库操作成功率过低: {db_success_rate*100:.1f}%"
        
        # 断言：平均响应时间不超过3秒
        assert avg_response_time <= 3.0, \
            f"数据库操作平均响应时间过长: {avg_response_time:.2f}秒"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "stress"])