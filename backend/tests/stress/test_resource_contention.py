"""
资源竞争和并发安全测试
测试系统在高并发情况下的资源竞争处理和数据一致性
"""
import asyncio
import json
import pytest
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Set
from collections import defaultdict, Counter
import random


class TestResourceContention:
    """资源竞争测试类"""
    
    @pytest.fixture(autouse=True)
    def setup_resource_test_users(self, client, create_stress_test_users):
        """设置资源竞争测试用户"""
        self.resource_users = []
        
        # 使用Mock系统创建50个用户用于资源竞争测试
        mock_users = create_stress_test_users(50)
        
        for i, user in enumerate(mock_users):
            auth_data = {"code": f"resource_test_user_{i}_auth_code_{user.uid}"}
            response = client.post("/api/auth/thirdparty/login-legacy", json=auth_data)
            
            if response.status_code == 200:
                result = response.json()
                self.resource_users.append({
                    "user_id": result["user"]["id"],
                    "username": f"resource_user_{i}",
                    "token": result["access_token"],
                    "headers": {"Authorization": f"Bearer {result['access_token']}"}
                })
        
        assert len(self.resource_users) >= 10, "需要至少10个用户进行资源竞争测试"
    
    @pytest.mark.stress
    def test_concurrent_task_id_generation(self, client):
        """测试并发任务ID生成的唯一性"""
        print(f"\n🔢 测试并发任务ID生成唯一性")
        
        created_task_ids: Set[int] = set()
        id_creation_results = []
        lock = threading.Lock()
        
        def create_task_get_id(user_info: Dict, task_index: int) -> Dict:
            """创建任务并获取ID"""
            try:
                # 创建任务
                filename = f"id_test_{task_index}.md"
                content = f"# 任务ID唯一性测试 {task_index}\n\n这是用于测试任务ID生成唯一性的文档内容。任务序号：{task_index}"
                
                response = client.post(
                    "/api/tasks/",
                    files={"file": (filename, content.encode('utf-8'), "text/markdown")},
                    data={"description": f"ID唯一性测试任务 {task_index}"},
                    headers=user_info["headers"]
                )
                
                if response.status_code == 201:
                    task_data = response.json()
                    task_id = task_data["id"]
                    
                    # 线程安全地检查ID唯一性
                    with lock:
                        is_duplicate = task_id in created_task_ids
                        if not is_duplicate:
                            created_task_ids.add(task_id)
                    
                    return {
                        "success": True,
                        "task_id": task_id,
                        "task_index": task_index,
                        "user_id": user_info["user_id"],
                        "is_duplicate": is_duplicate
                    }
                else:
                    return {
                        "success": False,
                        "task_index": task_index,
                        "user_id": user_info["user_id"],
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }
                    
            except Exception as e:
                return {
                    "success": False,
                    "task_index": task_index,
                    "user_id": user_info["user_id"],
                    "error": str(e)
                }
        
        # 并发创建任务
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=len(self.resource_users)) as executor:
            futures = []
            
            # 每个用户创建3个任务
            task_index = 0
            for user in self.resource_users:
                for i in range(3):
                    future = executor.submit(create_task_get_id, user, task_index)
                    futures.append(future)
                    task_index += 1
            
            # 收集结果
            for future in as_completed(futures):
                result = future.result()
                id_creation_results.append(result)
        
        total_time = time.time() - start_time
        
        # 分析ID唯一性
        successful_creations = [r for r in id_creation_results if r["success"]]
        duplicate_ids = [r for r in successful_creations if r.get("is_duplicate", False)]
        unique_ids = len(created_task_ids)
        
        print(f"📊 任务ID唯一性测试结果:")
        print(f"   尝试创建任务数: {len(id_creation_results)}")
        print(f"   成功创建任务数: {len(successful_creations)}")
        print(f"   唯一任务ID数: {unique_ids}")
        print(f"   发现重复ID: {len(duplicate_ids)}")
        print(f"   总耗时: {total_time:.2f}秒")
        
        if duplicate_ids:
            print(f"⚠️ 发现重复的任务ID:")
            for dup in duplicate_ids:
                print(f"     任务{dup['task_index']}: ID {dup['task_id']} (用户{dup['user_id']})")
        
        # 断言：不应该有重复的任务ID
        assert len(duplicate_ids) == 0, f"发现了{len(duplicate_ids)}个重复的任务ID"
        
        # 断言：唯一ID数量应该等于成功创建的任务数
        assert unique_ids == len(successful_creations), \
            f"唯一ID数量({unique_ids})不等于成功创建的任务数({len(successful_creations)})"
    
    @pytest.mark.stress
    def test_concurrent_user_session_management(self, client):
        """测试并发用户会话管理"""
        print(f"\n👥 测试并发用户会话管理")
        
        session_results = []
        
        def perform_user_operations(user_info: Dict, operation_count: int) -> Dict:
            """执行用户操作序列"""
            operations_performed = []
            errors = []
            
            try:
                for i in range(operation_count):
                    # 随机选择操作类型
                    operation_type = random.choice(["profile", "tasks", "create_task"])
                    
                    if operation_type == "profile":
                        # 获取用户资料
                        response = client.get("/api/users/me", headers=user_info["headers"])
                        operations_performed.append({
                            "operation": "profile",
                            "success": response.status_code == 200,
                            "response_time": 0  # 简化处理
                        })
                        
                    elif operation_type == "tasks":
                        # 获取任务列表
                        response = client.get("/api/tasks/", headers=user_info["headers"])
                        operations_performed.append({
                            "operation": "tasks",
                            "success": response.status_code == 200,
                            "task_count": len(response.json()) if response.status_code == 200 else 0
                        })
                        
                    elif operation_type == "create_task":
                        # 创建任务
                        content = f"会话测试任务 - 用户{user_info['user_id']} - 操作{i}"
                        response = client.post(
                            "/api/tasks/",
                            files={"file": (f"session_test_{i}.md", content.encode('utf-8'), "text/markdown")},
                            data={"description": content},
                            headers=user_info["headers"]
                        )
                        operations_performed.append({
                            "operation": "create_task",
                            "success": response.status_code == 201,
                            "task_id": response.json().get("id") if response.status_code == 201 else None
                        })
                    
                    # 随机延迟模拟真实用户行为
                    time.sleep(random.uniform(0.1, 0.3))
                
                successful_operations = [op for op in operations_performed if op.get("success", False)]
                
                return {
                    "user_id": user_info["user_id"],
                    "username": user_info["username"],
                    "total_operations": len(operations_performed),
                    "successful_operations": len(successful_operations),
                    "operations": operations_performed,
                    "success_rate": len(successful_operations) / len(operations_performed) if operations_performed else 0
                }
                
            except Exception as e:
                return {
                    "user_id": user_info["user_id"],
                    "username": user_info["username"],
                    "total_operations": len(operations_performed),
                    "successful_operations": 0,
                    "error": str(e),
                    "success_rate": 0
                }
        
        # 并发执行用户会话操作
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=len(self.resource_users)) as executor:
            futures = []
            
            for user in self.resource_users:
                # 每个用户执行5-10个随机操作
                operation_count = random.randint(5, 10)
                future = executor.submit(perform_user_operations, user, operation_count)
                futures.append(future)
            
            # 收集结果
            for future in as_completed(futures):
                result = future.result()
                session_results.append(result)
        
        total_time = time.time() - start_time
        
        # 分析会话管理结果
        total_operations = sum(r["total_operations"] for r in session_results)
        total_successful = sum(r["successful_operations"] for r in session_results)
        
        # 按操作类型统计
        operation_stats = defaultdict(lambda: {"total": 0, "successful": 0})
        for result in session_results:
            for op in result.get("operations", []):
                op_type = op["operation"]
                operation_stats[op_type]["total"] += 1
                if op.get("success", False):
                    operation_stats[op_type]["successful"] += 1
        
        avg_success_rate = sum(r["success_rate"] for r in session_results) / len(session_results)
        
        print(f"📊 并发用户会话管理测试结果:")
        print(f"   并发用户数: {len(self.resource_users)}")
        print(f"   总操作数: {total_operations}")
        print(f"   成功操作数: {total_successful}")
        print(f"   整体成功率: {total_successful/total_operations*100:.1f}%")
        print(f"   平均用户成功率: {avg_success_rate*100:.1f}%")
        print(f"   总耗时: {total_time:.2f}秒")
        
        print(f"   按操作类型统计:")
        for op_type, stats in operation_stats.items():
            success_rate = stats["successful"] / stats["total"] * 100 if stats["total"] > 0 else 0
            print(f"     {op_type}: {stats['successful']}/{stats['total']} ({success_rate:.1f}%)")
        
        # 断言：整体成功率应该大于90%
        overall_success_rate = total_successful / total_operations if total_operations > 0 else 0
        assert overall_success_rate >= 0.90, \
            f"并发用户会话管理整体成功率过低: {overall_success_rate*100:.1f}%"
        
        # 断言：每种操作的成功率都应该大于85%
        for op_type, stats in operation_stats.items():
            op_success_rate = stats["successful"] / stats["total"] if stats["total"] > 0 else 0
            assert op_success_rate >= 0.85, \
                f"{op_type}操作成功率过低: {op_success_rate*100:.1f}%"
    
    @pytest.mark.stress
    def test_database_transaction_consistency(self, client):
        """测试数据库事务一致性"""
        print(f"\n🗄️ 测试数据库事务一致性")
        
        # 首先为每个用户创建一个任务，用于后续并发操作
        base_task_ids = []
        for i, user in enumerate(self.resource_users[:5]):  # 只用前5个用户
            content = f"事务一致性测试基础任务 {i}"
            response = client.post(
                "/api/tasks/",
                files={"file": (f"transaction_test_{i}.md", content.encode('utf-8'), "text/markdown")},
                data={"description": content},
                headers=user["headers"]
            )
            
            if response.status_code == 201:
                base_task_ids.append(response.json()["id"])
        
        assert len(base_task_ids) >= 3, "需要至少3个基础任务进行事务一致性测试"
        
        transaction_results = []
        
        def perform_concurrent_task_operations(user_info: Dict, task_ids: List[int]) -> Dict:
            """执行并发任务操作"""
            operations = []
            
            try:
                for task_id in task_ids:
                    # 对同一个任务执行多种操作
                    
                    # 1. 查询任务详情
                    response1 = client.get(f"/api/tasks/{task_id}", headers=user_info["headers"])
                    operations.append({
                        "operation": "get_task",
                        "task_id": task_id,
                        "success": response1.status_code == 200,
                        "data": response1.json() if response1.status_code == 200 else None
                    })
                    
                    # 2. 查询任务的AI输出
                    response2 = client.get(f"/api/ai-outputs/task/{task_id}", headers=user_info["headers"])
                    operations.append({
                        "operation": "get_ai_outputs",
                        "task_id": task_id,
                        "success": response2.status_code == 200,
                        "output_count": len(response2.json()) if response2.status_code == 200 else 0
                    })
                    
                    # 短暂延迟
                    time.sleep(0.05)
                
                successful_ops = [op for op in operations if op["success"]]
                
                return {
                    "user_id": user_info["user_id"],
                    "operations": operations,
                    "successful_operations": len(successful_ops),
                    "total_operations": len(operations),
                    "consistency_issues": []  # 稍后分析
                }
                
            except Exception as e:
                return {
                    "user_id": user_info["user_id"],
                    "operations": operations,
                    "successful_operations": 0,
                    "total_operations": len(operations),
                    "error": str(e),
                    "consistency_issues": []
                }
        
        # 并发执行事务操作
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=len(self.resource_users[:10])) as executor:
            futures = []
            
            # 多个用户并发操作相同的任务集合
            for user in self.resource_users[:10]:
                future = executor.submit(perform_concurrent_task_operations, user, base_task_ids)
                futures.append(future)
            
            # 收集结果
            for future in as_completed(futures):
                result = future.result()
                transaction_results.append(result)
        
        total_time = time.time() - start_time
        
        # 分析事务一致性
        total_operations = sum(r["total_operations"] for r in transaction_results)
        total_successful = sum(r["successful_operations"] for r in transaction_results)
        
        # 检查数据一致性
        task_data_snapshots = defaultdict(list)
        for result in transaction_results:
            for op in result["operations"]:
                if op["operation"] == "get_task" and op["success"] and op["data"]:
                    task_id = op["task_id"]
                    # 收集关键字段的值
                    snapshot = {
                        "id": op["data"].get("id"),
                        "status": op["data"].get("status"),
                        "created_at": op["data"].get("created_at"),
                        "user_id": op["data"].get("user_id")
                    }
                    task_data_snapshots[task_id].append(snapshot)
        
        # 检查每个任务的数据是否一致
        consistency_issues = []
        for task_id, snapshots in task_data_snapshots.items():
            if len(snapshots) > 1:
                # 检查关键字段是否在所有快照中都一致
                first_snapshot = snapshots[0]
                for snapshot in snapshots[1:]:
                    for field in ["id", "status", "created_at", "user_id"]:
                        if first_snapshot[field] != snapshot[field]:
                            consistency_issues.append({
                                "task_id": task_id,
                                "field": field,
                                "values": [s[field] for s in snapshots]
                            })
                            break
        
        print(f"📊 数据库事务一致性测试结果:")
        print(f"   并发用户数: {len(self.resource_users[:10])}")
        print(f"   测试任务数: {len(base_task_ids)}")
        print(f"   总操作数: {total_operations}")
        print(f"   成功操作数: {total_successful}")
        print(f"   操作成功率: {total_successful/total_operations*100:.1f}%")
        print(f"   数据一致性问题: {len(consistency_issues)}")
        print(f"   总耗时: {total_time:.2f}秒")
        
        if consistency_issues:
            print(f"⚠️ 发现的一致性问题:")
            for issue in consistency_issues[:5]:  # 只显示前5个
                print(f"     任务{issue['task_id']} 字段'{issue['field']}' 值不一致: {issue['values']}")
        
        # 断言：不应该有数据一致性问题
        assert len(consistency_issues) == 0, \
            f"发现了{len(consistency_issues)}个数据一致性问题"
        
        # 断言：操作成功率应该大于90%
        success_rate = total_successful / total_operations if total_operations > 0 else 0
        assert success_rate >= 0.90, \
            f"并发事务操作成功率过低: {success_rate*100:.1f}%"
    
    @pytest.mark.stress
    def test_file_upload_resource_contention(self, client):
        """测试文件上传资源竞争"""
        print(f"\n📁 测试文件上传资源竞争")
        
        upload_results = []
        uploaded_file_sizes = []
        
        def create_test_file_content(size_kb: int, file_id: int) -> bytes:
            """创建指定大小的测试文件内容"""
            base_content = f"# 文件上传竞争测试 {file_id}\n\n这是用于测试文件上传资源竞争的内容。文件ID：{file_id}\n\n"
            # 每100个字符大约1KB
            repeat_count = (size_kb * 1024) // len(base_content)
            return (base_content * repeat_count).encode('utf-8')
        
        def upload_file_concurrently(user_info: Dict, file_index: int) -> Dict:
            """并发上传文件"""
            start_time = time.time()
            
            try:
                # 创建不同大小的文件（1-10KB）
                file_size_kb = random.randint(1, 10)
                file_content = create_test_file_content(file_size_kb, file_index)
                filename = f"concurrent_upload_{file_index}_{file_size_kb}kb.md"
                
                response = client.post(
                    "/api/tasks/",
                    files={"file": (filename, file_content, "text/markdown")},
                    data={"description": f"并发文件上传测试 {file_index} ({file_size_kb}KB)"},
                    headers=user_info["headers"]
                )
                
                end_time = time.time()
                
                return {
                    "success": response.status_code == 201,
                    "file_index": file_index,
                    "file_size_kb": file_size_kb,
                    "user_id": user_info["user_id"],
                    "upload_time": end_time - start_time,
                    "task_id": response.json().get("id") if response.status_code == 201 else None,
                    "status_code": response.status_code
                }
                
            except Exception as e:
                end_time = time.time()
                return {
                    "success": False,
                    "file_index": file_index,
                    "file_size_kb": 0,
                    "user_id": user_info["user_id"],
                    "upload_time": end_time - start_time,
                    "error": str(e)
                }
        
        # 并发文件上传
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=len(self.resource_users)) as executor:
            futures = []
            
            # 每个用户上传2个文件
            file_index = 0
            for user in self.resource_users:
                for i in range(2):
                    future = executor.submit(upload_file_concurrently, user, file_index)
                    futures.append(future)
                    file_index += 1
            
            # 收集结果
            for future in as_completed(futures):
                result = future.result()
                upload_results.append(result)
                if result["success"]:
                    uploaded_file_sizes.append(result["file_size_kb"])
        
        total_time = time.time() - start_time
        
        # 分析文件上传结果
        successful_uploads = [r for r in upload_results if r["success"]]
        failed_uploads = [r for r in upload_results if not r["success"]]
        
        avg_upload_time = sum(r["upload_time"] for r in upload_results) / len(upload_results)
        max_upload_time = max(r["upload_time"] for r in upload_results)
        
        # 按文件大小分析
        size_stats = Counter(uploaded_file_sizes)
        total_uploaded_size = sum(uploaded_file_sizes)
        
        print(f"📊 文件上传资源竞争测试结果:")
        print(f"   并发上传文件数: {len(upload_results)}")
        print(f"   成功上传: {len(successful_uploads)}")
        print(f"   失败上传: {len(failed_uploads)}")
        print(f"   上传成功率: {len(successful_uploads)/len(upload_results)*100:.1f}%")
        print(f"   总上传大小: {total_uploaded_size}KB")
        print(f"   平均上传时间: {avg_upload_time:.2f}秒")
        print(f"   最大上传时间: {max_upload_time:.2f}秒")
        print(f"   总耗时: {total_time:.2f}秒")
        
        print(f"   文件大小分布:")
        for size_kb, count in sorted(size_stats.items()):
            print(f"     {size_kb}KB: {count}个文件")
        
        # 断言：文件上传成功率应该大于85%
        upload_success_rate = len(successful_uploads) / len(upload_results) if upload_results else 0
        assert upload_success_rate >= 0.85, \
            f"并发文件上传成功率过低: {upload_success_rate*100:.1f}%"
        
        # 断言：平均上传时间不应该太长
        assert avg_upload_time <= 3.0, \
            f"平均文件上传时间过长: {avg_upload_time:.2f}秒"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "stress"])