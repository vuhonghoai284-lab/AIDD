"""
Fast Cache 服务
支持内存和Redis两种缓存策略，可通过配置文件动态切换
"""
import json
import time
import pickle
import threading
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, Union
from dataclasses import dataclass

from app.core.config import get_settings


@dataclass
class CacheEntry:
    """缓存条目"""
    data: Any
    timestamp: float
    ttl: int
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        return time.time() > (self.timestamp + self.ttl)


class CacheBackend(ABC):
    """缓存后端接口"""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: int):
        """设置缓存"""
        pass
    
    @abstractmethod
    def delete(self, key: str):
        """删除缓存"""
        pass
    
    @abstractmethod
    def clear(self):
        """清空缓存"""
        pass
    
    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        pass


class MemoryCacheBackend(CacheBackend):
    """内存缓存后端"""
    
    def __init__(self, max_entries: int = 1000, cleanup_interval: int = 60):
        self.max_entries = max_entries
        self.cleanup_interval = cleanup_interval
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._last_cleanup = time.time()
        
    def _cleanup_expired(self):
        """清理过期缓存"""
        now = time.time()
        if now - self._last_cleanup < self.cleanup_interval:
            return
            
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self._cache[key]
                
            if expired_keys:
                print(f"🧹 [MemoryCache] 清理了 {len(expired_keys)} 个过期缓存条目")
                
            self._last_cleanup = now
    
    def _evict_if_needed(self):
        """LRU淘汰策略"""
        if len(self._cache) >= self.max_entries:
            # 简单LRU：删除最旧的条目
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].timestamp)
            del self._cache[oldest_key]
            print(f"🗑️ [MemoryCache] LRU淘汰: {oldest_key}")
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        self._cleanup_expired()
        
        with self._lock:
            entry = self._cache.get(key)
            if entry is None or entry.is_expired():
                if entry:
                    del self._cache[key]
                return None
                
            print(f"📊 [MemoryCache] 缓存命中: {key}")
            return entry.data
    
    def set(self, key: str, value: Any, ttl: int):
        """设置缓存"""
        with self._lock:
            self._evict_if_needed()
            
            entry = CacheEntry(
                data=value,
                timestamp=time.time(),
                ttl=ttl
            )
            
            self._cache[key] = entry
            print(f"💾 [MemoryCache] 缓存设置: {key}, TTL={ttl}s")
    
    def delete(self, key: str):
        """删除缓存"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                print(f"🗑️ [MemoryCache] 缓存删除: {key}")
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            print(f"🗑️ [MemoryCache] 清空所有缓存: {count} 个条目")
    
    def get_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        with self._lock:
            now = time.time()
            valid_entries = sum(1 for entry in self._cache.values() if not entry.is_expired())
            expired_entries = len(self._cache) - valid_entries
            
            return {
                "backend": "memory",
                "total_entries": len(self._cache),
                "valid_entries": valid_entries,
                "expired_entries": expired_entries,
                "max_entries": self.max_entries,
                "cache_keys": list(self._cache.keys())
            }


class RedisCacheBackend(CacheBackend):
    """Redis缓存后端"""
    
    def __init__(self, host: str = "localhost", port: int = 6379, password: str = "", 
                 database: int = 0, max_connections: int = 20):
        try:
            import redis
            from redis.connection import ConnectionPool
        except ImportError:
            raise ImportError("Redis backend requires redis package: pip install redis")
        
        # 创建连接池
        pool_kwargs = {
            'host': host,
            'port': port,
            'db': database,
            'max_connections': max_connections,
            'retry_on_timeout': True,
            'health_check_interval': 30
        }
        
        if password:
            pool_kwargs['password'] = password
            
        self.pool = ConnectionPool(**pool_kwargs)
        self.client = redis.Redis(connection_pool=self.pool)
        
        # 测试连接
        try:
            self.client.ping()
            print(f"✅ [RedisCache] 连接成功: {host}:{port}/{database}")
        except Exception as e:
            print(f"❌ [RedisCache] 连接失败: {e}")
            raise
    
    def _serialize(self, value: Any) -> bytes:
        """序列化数据"""
        return pickle.dumps(value)
    
    def _deserialize(self, data: bytes) -> Any:
        """反序列化数据"""
        return pickle.loads(data)
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        try:
            data = self.client.get(key)
            if data is None:
                return None
                
            value = self._deserialize(data)
            print(f"📊 [RedisCache] 缓存命中: {key}")
            return value
            
        except Exception as e:
            print(f"❌ [RedisCache] 获取缓存失败 {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int):
        """设置缓存"""
        try:
            data = self._serialize(value)
            self.client.setex(key, ttl, data)
            print(f"💾 [RedisCache] 缓存设置: {key}, TTL={ttl}s")
            
        except Exception as e:
            print(f"❌ [RedisCache] 设置缓存失败 {key}: {e}")
    
    def delete(self, key: str):
        """删除缓存"""
        try:
            result = self.client.delete(key)
            if result:
                print(f"🗑️ [RedisCache] 缓存删除: {key}")
                
        except Exception as e:
            print(f"❌ [RedisCache] 删除缓存失败 {key}: {e}")
    
    def clear(self):
        """清空缓存（谨慎使用）"""
        try:
            self.client.flushdb()
            print("🗑️ [RedisCache] 清空数据库所有缓存")
            
        except Exception as e:
            print(f"❌ [RedisCache] 清空缓存失败: {e}")
    
    def get_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        try:
            info = self.client.info('memory')
            keyspace = self.client.info('keyspace')
            
            return {
                "backend": "redis",
                "used_memory": info.get('used_memory_human', 'unknown'),
                "connected_clients": info.get('connected_clients', 0),
                "total_keys": sum(db.get('keys', 0) for db in keyspace.values()),
                "redis_version": info.get('redis_version', 'unknown')
            }
            
        except Exception as e:
            return {"backend": "redis", "error": str(e)}


class FastCache:
    """快速缓存服务"""
    
    def __init__(self):
        self.settings = get_settings()
        self.backend = self._create_backend()
        self.default_ttl = self.settings.cache_config.get('default_ttl', 30)
        
    def _create_backend(self) -> CacheBackend:
        """创建缓存后端"""
        cache_config = self.settings.cache_config
        strategy = cache_config.get('strategy', 'memory')
        
        if strategy == 'redis':
            redis_config = cache_config.get('redis', {})
            pool_config = redis_config.get('pool', {})
            
            return RedisCacheBackend(
                host=redis_config.get('host', 'localhost'),
                port=redis_config.get('port', 6379),
                password=redis_config.get('password', ''),
                database=redis_config.get('database', 0),
                max_connections=pool_config.get('max_connections', 20)
            )
        else:
            # 默认使用内存缓存
            memory_config = cache_config.get('memory', {})
            return MemoryCacheBackend(
                max_entries=memory_config.get('max_entries', 1000),
                cleanup_interval=memory_config.get('cleanup_interval', 60)
            )
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        return self.backend.get(key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """设置缓存"""
        if ttl is None:
            ttl = self.default_ttl
        self.backend.set(key, value, ttl)
    
    def delete(self, key: str):
        """删除缓存"""
        self.backend.delete(key)
    
    def clear(self):
        """清空缓存"""
        self.backend.clear()
    
    def get_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        return self.backend.get_info()


# 全局缓存实例
_cache_instance: Optional[FastCache] = None


def get_cache() -> FastCache:
    """获取全局缓存实例"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = FastCache()
    return _cache_instance