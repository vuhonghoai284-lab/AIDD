"""
性能监控和统计日志模块
"""
import time
import functools
import json
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict
from app.utils.logger import setup_logger

@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    operation: str
    duration: float
    success: bool
    error_message: Optional[str] = None
    input_size: Optional[int] = None
    output_size: Optional[int] = None
    additional_info: Optional[Dict[str, Any]] = None

class PerformanceLogger:
    """性能监控日志器"""
    
    def __init__(self):
        self.logger = setup_logger("performance", "performance.log")
        self.metrics: Dict[str, list] = {}
    
    def log_performance(self, metrics: PerformanceMetrics):
        """记录性能指标"""
        # 记录到日志文件
        log_data = {
            "timestamp": time.time(),
            "metrics": asdict(metrics)
        }
        
        if metrics.success:
            self.logger.info(f"✅ {metrics.operation} 完成 - 耗时: {metrics.duration:.2f}s")
        else:
            self.logger.error(f"❌ {metrics.operation} 失败 - 耗时: {metrics.duration:.2f}s, 错误: {metrics.error_message}")
        
        # 详细信息记录到DEBUG级别
        self.logger.debug(f"📊 性能详情: {json.dumps(log_data, ensure_ascii=False, indent=2)}")
        
        # 存储到内存中用于统计
        if metrics.operation not in self.metrics:
            self.metrics[metrics.operation] = []
        self.metrics[metrics.operation].append(metrics)
    
    def get_statistics(self, operation: str = None) -> Dict[str, Any]:
        """获取性能统计信息"""
        if operation:
            if operation not in self.metrics:
                return {}
            
            data = self.metrics[operation]
        else:
            data = []
            for op_data in self.metrics.values():
                data.extend(op_data)
        
        if not data:
            return {}
        
        successful = [m for m in data if m.success]
        failed = [m for m in data if not m.success]
        durations = [m.duration for m in successful]
        
        stats = {
            "total_operations": len(data),
            "successful_operations": len(successful),
            "failed_operations": len(failed),
            "success_rate": len(successful) / len(data) if data else 0,
        }
        
        if durations:
            stats.update({
                "avg_duration": sum(durations) / len(durations),
                "min_duration": min(durations),
                "max_duration": max(durations),
                "total_duration": sum(durations)
            })
        
        return stats

# 全局性能日志器实例
performance_logger = PerformanceLogger()

def monitor_performance(operation_name: str = None, track_input_size: bool = False, track_output_size: bool = False):
    """
    性能监控装饰器
    
    Args:
        operation_name: 操作名称，如果不提供则使用函数名
        track_input_size: 是否跟踪输入大小
        track_output_size: 是否跟踪输出大小
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            
            input_size = None
            if track_input_size and args:
                # 尝试计算输入大小
                first_arg = args[0] if args else None
                if isinstance(first_arg, str):
                    input_size = len(first_arg)
                elif isinstance(first_arg, (list, dict)):
                    input_size = len(first_arg)
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                output_size = None
                if track_output_size and result:
                    if isinstance(result, str):
                        output_size = len(result)
                    elif isinstance(result, (list, dict)):
                        output_size = len(result)
                
                metrics = PerformanceMetrics(
                    operation=op_name,
                    duration=duration,
                    success=True,
                    input_size=input_size,
                    output_size=output_size
                )
                performance_logger.log_performance(metrics)
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                metrics = PerformanceMetrics(
                    operation=op_name,
                    duration=duration,
                    success=False,
                    error_message=str(e),
                    input_size=input_size
                )
                performance_logger.log_performance(metrics)
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            
            input_size = None
            if track_input_size and args:
                first_arg = args[0] if args else None
                if isinstance(first_arg, str):
                    input_size = len(first_arg)
                elif isinstance(first_arg, (list, dict)):
                    input_size = len(first_arg)
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                output_size = None
                if track_output_size and result:
                    if isinstance(result, str):
                        output_size = len(result)
                    elif isinstance(result, (list, dict)):
                        output_size = len(result)
                
                metrics = PerformanceMetrics(
                    operation=op_name,
                    duration=duration,
                    success=True,
                    input_size=input_size,
                    output_size=output_size
                )
                performance_logger.log_performance(metrics)
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                metrics = PerformanceMetrics(
                    operation=op_name,
                    duration=duration,
                    success=False,
                    error_message=str(e),
                    input_size=input_size
                )
                performance_logger.log_performance(metrics)
                raise
        
        # 根据函数是否是协程来选择包装器
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator