"""
任务缓存服务 - 优化分页查询性能
"""
import time
import hashlib
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from app.dto.pagination import PaginationParams, PaginatedResponse
from app.dto.task import TaskResponse

@dataclass
class CacheEntry:
    """缓存条目"""
    data: Any
    timestamp: float
    expires_at: float
    cache_key: str

class TaskCacheService:
    """任务缓存服务"""
    
    def __init__(self, default_ttl: int = 30):
        self.cache: Dict[str, CacheEntry] = {}
        self.default_ttl = default_ttl  # 默认缓存时间30秒
        self.max_cache_size = 100  # 最大缓存条目数
        
    def _generate_cache_key(self, params: PaginationParams, user_id: Optional[int] = None) -> str:
        """生成缓存键"""
        cache_data = {
            'page': params.page,
            'page_size': params.page_size,
            'search': params.search,
            'status': params.status,
            'sort_by': params.sort_by,
            'sort_order': params.sort_order,
            'user_id': user_id
        }
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def get_cached_tasks(self, params: PaginationParams, user_id: Optional[int] = None) -> Optional[PaginatedResponse[TaskResponse]]:
        """获取缓存的任务数据"""
        cache_key = self._generate_cache_key(params, user_id)
        
        # 清理过期缓存
        self._cleanup_expired_cache()
        
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if time.time() < entry.expires_at:
                print(f"🎯 使用缓存数据: {cache_key[:8]}...")
                return entry.data
            else:
                # 缓存已过期，删除
                del self.cache[cache_key]
                print(f"🗑️ 缓存已过期，删除: {cache_key[:8]}...")
        
        return None
    
    def cache_tasks(self, params: PaginationParams, user_id: Optional[int], data: PaginatedResponse[TaskResponse], ttl: Optional[int] = None):
        """缓存任务数据"""
        cache_key = self._generate_cache_key(params, user_id)
        ttl = ttl or self.default_ttl
        
        # 如果缓存已满，删除最旧的条目
        if len(self.cache) >= self.max_cache_size:
            self._cleanup_oldest_cache()
        
        entry = CacheEntry(
            data=data,
            timestamp=time.time(),
            expires_at=time.time() + ttl,
            cache_key=cache_key
        )
        
        self.cache[cache_key] = entry
        print(f"💾 缓存任务数据: {cache_key[:8]}..., TTL={ttl}s, 数据量={len(data.items)}")
    
    def _cleanup_expired_cache(self):
        """清理过期的缓存"""
        current_time = time.time()
        expired_keys = [key for key, entry in self.cache.items() if current_time >= entry.expires_at]
        
        for key in expired_keys:
            del self.cache[key]
            
        if expired_keys:
            print(f"🧹 清理了 {len(expired_keys)} 个过期缓存条目")
    
    def _cleanup_oldest_cache(self):
        """清理最旧的缓存条目"""
        if not self.cache:
            return
            
        # 找到最旧的缓存条目
        oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k].timestamp)
        del self.cache[oldest_key]
        print(f"🧹 清理最旧缓存条目: {oldest_key[:8]}...")
    
    def invalidate_cache(self, user_id: Optional[int] = None):
        """使缓存失效"""
        if user_id is None:
            # 清空所有缓存
            cleared_count = len(self.cache)
            self.cache.clear()
            print(f"🔄 清空所有任务缓存: {cleared_count} 个条目")
        else:
            # 清空特定用户的缓存
            keys_to_remove = []
            for key, entry in self.cache.items():
                # 简单的用户ID匹配（基于缓存键中的用户ID）
                if f'"user_id": {user_id}' in key or f'"user_id": null' in key:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.cache[key]
            
            print(f"🔄 清空用户 {user_id} 的任务缓存: {len(keys_to_remove)} 个条目")
    
    def get_cache_stats(self) -> dict:
        """获取缓存统计信息"""
        current_time = time.time()
        active_count = sum(1 for entry in self.cache.values() if current_time < entry.expires_at)
        expired_count = len(self.cache) - active_count
        
        return {
            'total_entries': len(self.cache),
            'active_entries': active_count,
            'expired_entries': expired_count,
            'max_cache_size': self.max_cache_size,
            'default_ttl': self.default_ttl,
            'memory_usage_estimate': len(self.cache) * 1024  # 粗略估算，每个条目约1KB
        }

# 全局缓存服务实例
_task_cache_service = None

def get_task_cache_service() -> TaskCacheService:
    """获取任务缓存服务实例"""
    global _task_cache_service
    if _task_cache_service is None:
        _task_cache_service = TaskCacheService()
    return _task_cache_service