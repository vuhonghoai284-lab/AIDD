"""
数据库连接监控模块
实时监控数据库会话使用情况，防止连接泄露
"""
import time
import threading
from collections import defaultdict
from typing import Dict, Any
from dataclasses import dataclass, field


@dataclass
class SessionStats:
    """数据库会话统计"""
    created_count: int = 0
    closed_count: int = 0
    active_count: int = 0
    max_concurrent: int = 0
    total_lifetime: float = 0.0
    error_count: int = 0
    long_sessions: int = 0  # 超过5秒的长会话数
    active_sessions: Dict[str, float] = field(default_factory=dict)
    

class DatabaseMonitor:
    """数据库连接监控器"""
    
    def __init__(self):
        self.stats = SessionStats()
        self._lock = threading.Lock()
        self.start_time = time.time()
        
    def log_session_create(self, session_id: str, operation: str = "unknown"):
        """记录会话创建"""
        with self._lock:
            current_time = time.time()
            self.stats.created_count += 1
            self.stats.active_count += 1
            self.stats.max_concurrent = max(self.stats.max_concurrent, self.stats.active_count)
            self.stats.active_sessions[session_id] = current_time
            
            # 高并发警告
            if self.stats.active_count > 15:
                print(f"⚠️ 数据库会话并发数较高: {self.stats.active_count} 个活跃会话")
            if self.stats.active_count > 25:
                print(f"🚨 数据库会话并发数过高: {self.stats.active_count} 个活跃会话，操作: {operation}")
    
    def log_session_close(self, session_id: str, operation: str = "unknown"):
        """记录会话关闭"""
        with self._lock:
            current_time = time.time()
            self.stats.closed_count += 1
            self.stats.active_count -= 1
            
            if session_id in self.stats.active_sessions:
                lifetime = current_time - self.stats.active_sessions[session_id]
                self.stats.total_lifetime += lifetime
                
                # 长会话警告
                if lifetime > 5.0:  # 超过5秒
                    self.stats.long_sessions += 1
                    print(f"⚠️ 检测到长时间数据库会话: {lifetime:.2f}s, 操作: {operation}")
                    
                del self.stats.active_sessions[session_id]
    
    def log_session_error(self, session_id: str, error: str):
        """记录会话错误"""
        with self._lock:
            self.stats.error_count += 1
            print(f"❌ 数据库会话错误 [{session_id}]: {error}")
            
            # 清理可能泄露的会话记录
            if session_id in self.stats.active_sessions:
                self.stats.active_count -= 1
                del self.stats.active_sessions[session_id]
    
    def get_current_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        with self._lock:
            runtime = time.time() - self.start_time
            avg_lifetime = (self.stats.total_lifetime / self.stats.closed_count 
                          if self.stats.closed_count > 0 else 0)
            
            return {
                'runtime_seconds': runtime,
                'sessions_created': self.stats.created_count,
                'sessions_closed': self.stats.closed_count,
                'sessions_active': self.stats.active_count,
                'max_concurrent_sessions': self.stats.max_concurrent,
                'avg_session_lifetime': avg_lifetime,
                'sessions_per_second': self.stats.created_count / runtime if runtime > 0 else 0,
                'error_count': self.stats.error_count,
                'long_sessions': self.stats.long_sessions,
                'potential_leaks': max(0, self.stats.created_count - self.stats.closed_count - self.stats.active_count)
            }
    
    def print_status(self, prefix: str = ""):
        """打印当前状态"""
        status = self.get_current_status()
        print(f"🔍 {prefix} 数据库监控状态:")
        print(f"   创建: {status['sessions_created']} | 关闭: {status['sessions_closed']} | 活跃: {status['sessions_active']}")
        print(f"   峰值: {status['max_concurrent_sessions']} | 平均时长: {status['avg_session_lifetime']:.3f}s")
        print(f"   错误: {status['error_count']} | 长会话: {status['long_sessions']} | 可能泄露: {status['potential_leaks']}")
        
        # 资源使用警告
        if status['sessions_active'] > 20:
            print(f"⚠️ 当前活跃会话数过多: {status['sessions_active']}")
        if status['potential_leaks'] > 0:
            print(f"🚨 检测到可能的连接泄露: {status['potential_leaks']} 个")


# 全局监控器实例
db_monitor = DatabaseMonitor()


def get_monitor() -> DatabaseMonitor:
    """获取数据库监控器实例"""
    return db_monitor