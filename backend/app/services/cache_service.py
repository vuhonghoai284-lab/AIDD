"""
优化的缓存服务 - 基于fastapi-cache2
使用成熟开源库，避免重复造轮子
"""
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.backends.inmemory import InMemoryBackend
from app.core.config import get_settings


def init_cache():
    """初始化缓存后端"""
    settings = get_settings()
    cache_config = settings.cache_config
    strategy = cache_config.get('strategy', 'memory')
    
    if strategy == 'redis':
        # Redis缓存配置
        redis_config = cache_config.get('redis', {})
        redis_url = f"redis://{redis_config.get('host', 'localhost')}:{redis_config.get('port', 6379)}/{redis_config.get('database', 0)}"
        
        if redis_config.get('password'):
            redis_url = f"redis://:{redis_config['password']}@{redis_config.get('host', 'localhost')}:{redis_config.get('port', 6379)}/{redis_config.get('database', 0)}"
        
        print(f"🚀 初始化Redis缓存: {redis_url}")
        FastAPICache.init(RedisBackend, url=redis_url)
    else:
        # 内存缓存配置
        memory_config = cache_config.get('memory', {})
        print(f"🚀 初始化内存缓存: max_size={memory_config.get('max_entries', 1000)}")
        FastAPICache.init(InMemoryBackend)


def close_cache():
    """关闭缓存连接"""
    try:
        FastAPICache.reset()
        print("🔒 缓存连接已关闭")
    except Exception as e:
        print(f"⚠️ 关闭缓存时出错: {e}")