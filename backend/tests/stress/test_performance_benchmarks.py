"""
性能基准测试
测试系统在各种负载条件下的性能表现
"""
import asyncio
import json
import pytest
import time
import threading
import queue
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta
import statistics

@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_time: float
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    success_rate: float
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "total_time": self.total_time,
            "avg_response_time": self.avg_response_time,
            "min_response_time": self.min_response_time,
            "max_response_time": self.max_response_time,
            "p95_response_time": self.p95_response_time,
            "p99_response_time": self.p99_response_time,
            "requests_per_second": self.requests_per_second,
            "success_rate": self.success_rate
        }


class LoadTestRunner:
    """负载测试执行器"""
    
    def __init__(self, client, users: List[Dict]):
        self.client = client
        self.users = users
        self.results_queue = queue.Queue()
    
    def execute_load_test(
        self,
        test_function,
        concurrent_users: int,
        total_requests: int,
        test_duration_seconds: Optional[int] = None
    ) -> PerformanceMetrics:
        """
        执行负载测试
        
        Args:
            test_function: 测试函数
            concurrent_users: 并发用户数
            total_requests: 总请求数（如果指定了duration则忽略）
            test_duration_seconds: 测试持续时间（秒）
        """
        print(f"🚀 开始负载测试:")
        print(f"   并发用户数: {concurrent_users}")
        print(f"   总请求数: {total_requests}")
        if test_duration_seconds:
            print(f"   测试持续时间: {test_duration_seconds}秒")
        
        start_time = time.time()
        stop_event = threading.Event()
        
        # 如果指定了持续时间，设置定时器
        if test_duration_seconds:
            timer = threading.Timer(test_duration_seconds, stop_event.set)
            timer.start()
        
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = []
            requests_submitted = 0
            
            # 提交请求
            while (not stop_event.is_set() and 
                   (test_duration_seconds or requests_submitted < total_requests)):
                
                if requests_submitted >= len(self.users) * 10:  # 避免提交过多请求
                    break
                    
                user = self.users[requests_submitted % len(self.users)]
                future = executor.submit(self._execute_single_request, test_function, user, requests_submitted)
                futures.append(future)
                requests_submitted += 1
                
                # 如果基于时间的测试，稍微延迟避免瞬间提交太多
                if test_duration_seconds and requests_submitted % 10 == 0:
                    time.sleep(0.1)
            
            # 停止定时器（如果还在运行）
            if test_duration_seconds:
                timer.cancel()
                stop_event.set()
            
            # 收集所有结果
            results = []
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=30)  # 30秒超时
                    results.append(result)
                except Exception as e:
                    # 超时或其他异常的请求记录为失败
                    results.append({
                        "success": False,
                        "response_time": 30.0,
                        "error": str(e)
                    })
        
        total_time = time.time() - start_time
        
        # 计算性能指标
        return self._calculate_metrics(results, total_time)
    
    def _execute_single_request(self, test_function, user: Dict, request_id: int) -> Dict:
        """执行单个请求"""
        start_time = time.time()
        
        try:
            result = test_function(self.client, user, request_id)
            end_time = time.time()
            
            return {
                "success": result.get("success", False),
                "response_time": end_time - start_time,
                "status_code": result.get("status_code"),
                "request_id": request_id
            }
            
        except Exception as e:
            end_time = time.time()
            return {
                "success": False,
                "response_time": end_time - start_time,
                "error": str(e),
                "request_id": request_id
            }
    
    def _calculate_metrics(self, results: List[Dict], total_time: float) -> PerformanceMetrics:
        """计算性能指标"""
        if not results:
            raise ValueError("没有测试结果数据")
        
        successful_results = [r for r in results if r["success"]]
        failed_results = [r for r in results if not r["success"]]
        
        response_times = [r["response_time"] for r in results]
        response_times.sort()
        
        # 计算百分位数
        def percentile(data: List[float], p: float) -> float:
            if not data:
                return 0.0
            index = int((len(data) - 1) * p / 100)
            return data[index]
        
        return PerformanceMetrics(
            total_requests=len(results),
            successful_requests=len(successful_results),
            failed_requests=len(failed_results),
            total_time=total_time,
            avg_response_time=statistics.mean(response_times) if response_times else 0,
            min_response_time=min(response_times) if response_times else 0,
            max_response_time=max(response_times) if response_times else 0,
            p95_response_time=percentile(response_times, 95),
            p99_response_time=percentile(response_times, 99),
            requests_per_second=len(results) / total_time if total_time > 0 else 0,
            success_rate=len(successful_results) / len(results) if results else 0
        )


class TestPerformanceBenchmarks:
    """性能基准测试类"""
    
    @pytest.fixture(autouse=True)
    def setup_load_test_users(self, client, create_stress_test_users):
        """设置负载测试用户"""
        self.load_test_users = []
        
        # 使用Mock系统创建50个用户用于负载测试
        mock_users = create_stress_test_users(50)
        
        for i, user in enumerate(mock_users):
            auth_data = {"code": f"load_test_user_{i}_auth_code_{user.uid}"}
            response = client.post("/api/auth/thirdparty/login-legacy", json=auth_data)
            
            if response.status_code == 200:
                result = response.json()
                self.load_test_users.append({
                    "user_id": result["user"]["id"],
                    "token": result["access_token"],
                    "headers": {"Authorization": f"Bearer {result['access_token']}"}
                })
        
        self.load_runner = LoadTestRunner(client, self.load_test_users)
        
        assert len(self.load_test_users) >= 10, "需要至少10个用户进行负载测试"
    
    def create_benchmark_document(self, size_category: str = "small") -> tuple:
        """创建不同大小的基准测试文档"""
        
        base_content = "这是一个用于性能基准测试的标准文档内容。它包含了完整的结构和足够的文字来进行有意义的测试。"
        
        size_configs = {
            "small": 1,      # ~1KB
            "medium": 10,    # ~10KB  
            "large": 50,     # ~50KB
            "xlarge": 100    # ~100KB
        }
        
        multiplier = size_configs.get(size_category, 1)
        content = base_content * multiplier * 20  # 每20次重复约1KB
        
        # 添加结构化内容
        structured_content = f"""
# 性能基准测试文档 ({size_category.upper()})

## 文档概述
{content}

## 主要内容

### 第一部分：基础信息
{content}

### 第二部分：详细分析  
{content}

### 第三部分：技术细节
{content}

## 结论和建议

### 主要发现
{content}

### 实施建议
{content}

### 后续步骤
{content}
        """
        
        return (f"benchmark_{size_category}.md", structured_content.encode('utf-8'), "text/markdown")
    
    @pytest.mark.stress
    def test_task_creation_benchmark(self, client):
        """任务创建性能基准测试"""
        print(f"\n📈 任务创建性能基准测试")
        
        def create_task_request(client, user: Dict, request_id: int) -> Dict:
            """单个任务创建请求"""
            try:
                filename, content, content_type = self.create_benchmark_document("small")
                
                response = client.post(
                    "/api/tasks/",
                    files={"file": (filename, content, content_type)},
                    data={"description": f"基准测试任务 {request_id}"},
                    headers=user["headers"]
                )
                
                return {
                    "success": response.status_code == 201,
                    "status_code": response.status_code,
                    "task_id": response.json().get("id") if response.status_code == 201 else None
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e)
                }
        
        # 执行基准测试：10个并发用户，100个请求
        metrics = self.load_runner.execute_load_test(
            test_function=create_task_request,
            concurrent_users=10,
            total_requests=100
        )
        
        # 打印基准结果
        self._print_benchmark_results("任务创建", metrics)
        
        # 基准断言
        assert metrics.success_rate >= 0.7, f"任务创建成功率低于基准: {metrics.success_rate*100:.1f}%"
        assert metrics.avg_response_time <= 2.0, f"任务创建平均响应时间超过基准: {metrics.avg_response_time:.2f}s"
        assert metrics.p95_response_time <= 5.0, f"任务创建P95响应时间超过基准: {metrics.p95_response_time:.2f}s"
        assert metrics.requests_per_second >= 20, f"任务创建RPS低于基准: {metrics.requests_per_second:.1f}/s"
    
    @pytest.mark.stress
    def test_task_query_benchmark(self, client):
        """任务查询性能基准测试"""
        print(f"\n🔍 任务查询性能基准测试")
        
        # 先创建一些任务供查询
        for user in self.load_test_users[:5]:
            filename, content, content_type = self.create_benchmark_document("small")
            client.post(
                "/api/tasks/",
                files={"file": (filename, content, content_type)},
                data={"description": "查询基准测试任务"},
                headers=user["headers"]
            )
        
        def query_tasks_request(client, user: Dict, request_id: int) -> Dict:
            """单个任务查询请求"""
            try:
                response = client.get(
                    "/api/tasks/",
                    headers=user["headers"]
                )
                
                return {
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "task_count": len(response.json()) if response.status_code == 200 else 0
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e)
                }
        
        # 执行基准测试：15个并发用户，200个请求
        metrics = self.load_runner.execute_load_test(
            test_function=query_tasks_request,
            concurrent_users=15,
            total_requests=200
        )
        
        # 打印基准结果
        self._print_benchmark_results("任务查询", metrics)
        
        # 基准断言
        assert metrics.success_rate >= 0.8, f"任务查询成功率低于基准: {metrics.success_rate*100:.1f}%"
        assert metrics.avg_response_time <= 1.0, f"任务查询平均响应时间超过基准: {metrics.avg_response_time:.2f}s"
        assert metrics.p95_response_time <= 2.0, f"任务查询P95响应时间超过基准: {metrics.p95_response_time:.2f}s"
        assert metrics.requests_per_second >= 50, f"任务查询RPS低于基准: {metrics.requests_per_second:.1f}/s"
    
    @pytest.mark.stress
    def test_mixed_operations_benchmark(self, client):
        """混合操作性能基准测试"""
        print(f"\n🔄 混合操作性能基准测试")
        
        def mixed_operation_request(client, user: Dict, request_id: int) -> Dict:
            """混合操作请求"""
            try:
                # 根据请求ID选择不同的操作类型
                operation_type = request_id % 4
                
                if operation_type == 0:
                    # 25% 创建任务
                    filename, content, content_type = self.create_benchmark_document("small")
                    response = client.post(
                        "/api/tasks/",
                        files={"file": (filename, content, content_type)},
                        data={"description": f"混合基准测试任务 {request_id}"},
                        headers=user["headers"]
                    )
                    return {
                        "success": response.status_code == 201,
                        "operation": "create",
                        "status_code": response.status_code
                    }
                
                elif operation_type == 1:
                    # 25% 查询任务列表
                    response = client.get("/api/tasks/", headers=user["headers"])
                    return {
                        "success": response.status_code == 200,
                        "operation": "list",
                        "status_code": response.status_code
                    }
                
                elif operation_type == 2:
                    # 25% 查询用户信息
                    response = client.get("/api/users/me", headers=user["headers"])
                    return {
                        "success": response.status_code == 200,
                        "operation": "user",
                        "status_code": response.status_code
                    }
                
                else:
                    # 25% 查询系统状态
                    response = client.get("/api/system/health", headers=user["headers"])
                    return {
                        "success": response.status_code == 200,
                        "operation": "health",
                        "status_code": response.status_code
                    }
                    
            except Exception as e:
                return {
                    "success": False,
                    "operation": "error",
                    "error": str(e)
                }
        
        # 执行基准测试：20个并发用户，持续30秒
        metrics = self.load_runner.execute_load_test(
            test_function=mixed_operation_request,
            concurrent_users=20,
            total_requests=1000,  # 这个在time-based测试中会被忽略
            test_duration_seconds=30
        )
        
        # 打印基准结果
        self._print_benchmark_results("混合操作", metrics)
        
        # 基准断言
        assert metrics.success_rate >= 0.6, f"混合操作成功率低于基准: {metrics.success_rate*100:.1f}%"
        assert metrics.avg_response_time <= 3.0, f"混合操作平均响应时间超过基准: {metrics.avg_response_time:.2f}s"
        assert metrics.requests_per_second >= 15, f"混合操作RPS低于基准: {metrics.requests_per_second:.1f}/s"
    
    @pytest.mark.stress 
    def test_large_file_processing_benchmark(self, client):
        """大文件处理性能基准测试"""
        print(f"\n📄 大文件处理性能基准测试")
        
        def large_file_task_request(client, user: Dict, request_id: int) -> Dict:
            """大文件任务创建请求"""
            try:
                # 根据请求ID使用不同大小的文件
                size_types = ["medium", "large", "xlarge"]
                size_type = size_types[request_id % len(size_types)]
                
                filename, content, content_type = self.create_benchmark_document(size_type)
                
                response = client.post(
                    "/api/tasks/",
                    files={"file": (filename, content, content_type)},
                    data={"description": f"大文件基准测试({size_type}) {request_id}"},
                    headers=user["headers"]
                )
                
                return {
                    "success": response.status_code == 201,
                    "status_code": response.status_code,
                    "file_size": size_type,
                    "task_id": response.json().get("id") if response.status_code == 201 else None
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e)
                }
        
        # 执行基准测试：5个并发用户，30个请求（大文件处理较慢）
        metrics = self.load_runner.execute_load_test(
            test_function=large_file_task_request,
            concurrent_users=5,
            total_requests=30
        )
        
        # 打印基准结果
        self._print_benchmark_results("大文件处理", metrics)
        
        # 大文件处理的基准要求相对宽松
        assert metrics.success_rate >= 0.80, f"大文件处理成功率低于基准: {metrics.success_rate*100:.1f}%"
        assert metrics.avg_response_time <= 10.0, f"大文件处理平均响应时间超过基准: {metrics.avg_response_time:.2f}s"
        assert metrics.p95_response_time <= 20.0, f"大文件处理P95响应时间超过基准: {metrics.p95_response_time:.2f}s"
    
    def _print_benchmark_results(self, test_name: str, metrics: PerformanceMetrics):
        """打印基准测试结果"""
        print(f"\n📊 {test_name}性能基准结果:")
        print(f"   总请求数: {metrics.total_requests}")
        print(f"   成功请求: {metrics.successful_requests}")
        print(f"   失败请求: {metrics.failed_requests}")
        print(f"   成功率: {metrics.success_rate*100:.1f}%")
        print(f"   总耗时: {metrics.total_time:.2f}s")
        print(f"   平均响应时间: {metrics.avg_response_time:.3f}s")
        print(f"   最小响应时间: {metrics.min_response_time:.3f}s")
        print(f"   最大响应时间: {metrics.max_response_time:.3f}s")
        print(f"   P95响应时间: {metrics.p95_response_time:.3f}s")
        print(f"   P99响应时间: {metrics.p99_response_time:.3f}s")
        print(f"   RPS (每秒请求数): {metrics.requests_per_second:.1f}")
        print(f"   {'='*50}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "stress"])