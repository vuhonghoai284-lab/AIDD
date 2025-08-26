"""
压力测试配置
为高并发和性能测试提供专门的配置和fixtures
"""
import pytest
import time
from typing import List, Dict
import concurrent.futures


def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line("markers", "stress: 标记为压力测试的用例")
    config.addinivalue_line("markers", "performance: 标记为性能测试的用例") 
    config.addinivalue_line("markers", "concurrency: 标记为并发测试的用例")
    config.addinivalue_line("markers", "load: 标记为负载测试的用例")


@pytest.fixture(scope="session")
def stress_test_config():
    """压力测试配置"""
    return {
        "max_concurrent_users": 20,
        "test_duration_seconds": 30,
        "max_requests_per_test": 1000,
        "response_time_threshold": 5.0,
        "success_rate_threshold": 0.85,
        "memory_limit_mb": 512,
        "database_connection_limit": 50
    }


@pytest.fixture
def performance_monitor():
    """性能监控工具"""
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.metrics = {}
            self.checkpoints = []
        
        def start(self):
            """开始监控"""
            self.start_time = time.time()
            self.metrics = {
                "start_time": self.start_time,
                "checkpoints": [],
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0
            }
        
        def checkpoint(self, name: str, additional_data: Dict = None):
            """添加检查点"""
            if self.start_time is None:
                self.start()
            
            checkpoint_time = time.time()
            checkpoint_data = {
                "name": name,
                "timestamp": checkpoint_time,
                "elapsed_time": checkpoint_time - self.start_time
            }
            
            if additional_data:
                checkpoint_data.update(additional_data)
            
            self.checkpoints.append(checkpoint_data)
            self.metrics["checkpoints"].append(checkpoint_data)
        
        def record_request(self, success: bool):
            """记录请求结果"""
            self.metrics["total_requests"] += 1
            if success:
                self.metrics["successful_requests"] += 1
            else:
                self.metrics["failed_requests"] += 1
        
        def get_summary(self) -> Dict:
            """获取性能摘要"""
            if not self.start_time:
                return {"error": "监控未开始"}
            
            current_time = time.time()
            total_time = current_time - self.start_time
            
            success_rate = 0
            if self.metrics["total_requests"] > 0:
                success_rate = self.metrics["successful_requests"] / self.metrics["total_requests"]
            
            return {
                "total_time": total_time,
                "total_requests": self.metrics["total_requests"],
                "successful_requests": self.metrics["successful_requests"],
                "failed_requests": self.metrics["failed_requests"],
                "success_rate": success_rate,
                "requests_per_second": self.metrics["total_requests"] / total_time if total_time > 0 else 0,
                "checkpoints": len(self.checkpoints)
            }
    
    return PerformanceMonitor()


@pytest.fixture
def concurrent_executor():
    """并发执行器工具"""
    class ConcurrentExecutor:
        def __init__(self, max_workers: int = 20):
            self.max_workers = max_workers
            self.results = []
        
        def execute_concurrent(self, func, args_list: List, timeout: float = 30.0):
            """并发执行函数"""
            results = []
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交所有任务
                future_to_args = {
                    executor.submit(func, *args): args for args in args_list
                }
                
                # 收集结果
                for future in concurrent.futures.as_completed(future_to_args, timeout=timeout):
                    args = future_to_args[future]
                    try:
                        result = future.result()
                        results.append({
                            "success": True,
                            "result": result,
                            "args": args
                        })
                    except Exception as e:
                        results.append({
                            "success": False,
                            "error": str(e),
                            "args": args
                        })
            
            self.results = results
            return results
        
        def get_stats(self) -> Dict:
            """获取执行统计"""
            if not self.results:
                return {"total": 0, "successful": 0, "failed": 0, "success_rate": 0}
            
            successful = sum(1 for r in self.results if r["success"])
            failed = len(self.results) - successful
            
            return {
                "total": len(self.results),
                "successful": successful,
                "failed": failed,
                "success_rate": successful / len(self.results) if self.results else 0
            }
    
    return ConcurrentExecutor()


@pytest.fixture
def resource_tracker():
    """资源使用跟踪器"""
    class ResourceTracker:
        def __init__(self):
            self.snapshots = []
        
        def snapshot(self, label: str = None):
            """获取资源使用快照"""
            try:
                import psutil
                import os
                
                process = psutil.Process(os.getpid())
                memory_info = process.memory_info()
                
                snapshot = {
                    "timestamp": time.time(),
                    "label": label,
                    "memory_mb": memory_info.rss / 1024 / 1024,
                    "cpu_percent": process.cpu_percent(),
                    "thread_count": process.num_threads(),
                    "open_files": len(process.open_files())
                }
                
                self.snapshots.append(snapshot)
                return snapshot
                
            except ImportError:
                # 如果psutil不可用，返回基本信息
                snapshot = {
                    "timestamp": time.time(),
                    "label": label,
                    "note": "psutil not available, limited resource tracking"
                }
                self.snapshots.append(snapshot)
                return snapshot
        
        def get_peak_usage(self) -> Dict:
            """获取峰值资源使用"""
            if not self.snapshots:
                return {}
            
            snapshots_with_memory = [s for s in self.snapshots if "memory_mb" in s]
            if not snapshots_with_memory:
                return {"note": "No memory data available"}
            
            return {
                "peak_memory_mb": max(s["memory_mb"] for s in snapshots_with_memory),
                "max_threads": max(s.get("thread_count", 0) for s in snapshots_with_memory),
                "max_open_files": max(s.get("open_files", 0) for s in snapshots_with_memory),
                "snapshots_count": len(self.snapshots)
            }
    
    return ResourceTracker()


@pytest.fixture
def load_test_data_generator():
    """负载测试数据生成器"""
    class LoadTestDataGenerator:
        def generate_user_data(self, count: int) -> List[Dict]:
            """生成测试用户数据"""
            users = []
            for i in range(count):
                users.append({
                    "username": f"load_test_user_{i:03d}",
                    "email": f"load_test_{i:03d}@example.com",
                    "display_name": f"Load Test User {i:03d}",
                    "index": i
                })
            return users
        
        def generate_document_content(self, size_category: str = "medium") -> str:
            """生成测试文档内容"""
            base_content = """
# 负载测试文档

## 概述
这是一个用于负载测试的文档内容，包含了合适的结构和长度来测试系统的文档处理能力。

## 详细内容

### 技术规格
系统需要能够处理各种大小的文档，从小型的配置文件到大型的技术规范文档。

### 性能要求
- 响应时间：平均小于2秒
- 并发处理：支持至少20个并发用户
- 成功率：大于95%

### 测试场景
包括正常负载、峰值负载和异常情况的测试。

## 结论
通过系统化的负载测试，我们可以确保系统在各种条件下都能稳定运行。
            """
            
            size_multipliers = {
                "small": 1,
                "medium": 5,
                "large": 15,
                "xlarge": 30
            }
            
            multiplier = size_multipliers.get(size_category, 5)
            return base_content * multiplier
        
        def generate_file_data(self, filename: str, size_category: str = "medium") -> tuple:
            """生成文件数据"""
            content = self.generate_document_content(size_category)
            return (filename, content.encode('utf-8'), "text/markdown")
    
    return LoadTestDataGenerator()


# 在测试结束后收集并报告性能数据
@pytest.fixture(autouse=True)
def stress_test_reporter(request):
    """压力测试报告器"""
    # 测试开始
    start_time = time.time()
    
    yield
    
    # 测试结束
    end_time = time.time()
    test_duration = end_time - start_time
    
    # 如果是压力测试，输出额外的信息
    if hasattr(request.node, 'get_closest_marker'):
        stress_marker = request.node.get_closest_marker('stress')
        if stress_marker:
            print(f"\n⏱️ 压力测试 '{request.node.name}' 耗时: {test_duration:.2f}秒")
            
            # 如果测试时间过长，给出警告
            if test_duration > 60:
                print(f"⚠️ 警告: 测试耗时较长 ({test_duration:.1f}秒), 请检查性能")