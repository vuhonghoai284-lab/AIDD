"""
用户认证缓存服务
解决 /api/user/me 接口性能问题，避免每次都查询数据库
"""
import time
from typing import Optional, Dict, Any
from app.models.user import User
from app.services.cache_service import init_cache
from fastapi_cache import FastAPICache


class UserCacheService:
    """用户缓存服务"""
    
    def __init__(self):
        self.cache_prefix = "user_auth:"
        self.default_ttl = 300  # 5分钟缓存
    
    def _get_cache_key(self, user_id: int) -> str:
        """生成用户缓存键"""
        return f"{self.cache_prefix}{user_id}"
    
    def get_user_from_cache(self, user_id: int) -> Optional[Dict[str, Any]]:
        """从缓存获取用户信息"""
        try:
            # 使用FastAPICache的后端直接访问
            if hasattr(FastAPICache, '_instance') and FastAPICache._instance:
                backend = FastAPICache._instance.backend
                cache_key = self._get_cache_key(user_id)
                cached_data = backend.get(cache_key)
                
                if cached_data:
                    print(f"📊 用户缓存命中: user_id={user_id}")
                    return cached_data
                    
            return None
        except Exception as e:
            print(f"⚠️ 获取用户缓存失败: {e}")
            return None
    
    def cache_user(self, user: User) -> None:
        """缓存用户信息"""
        try:
            if hasattr(FastAPICache, '_instance') and FastAPICache._instance:
                backend = FastAPICache._instance.backend
                cache_key = self._get_cache_key(user.id)
                
                # 只缓存必要的用户信息
                user_data = {
                    'id': user.id,
                    'uid': user.uid,
                    'display_name': user.display_name,
                    'email': user.email,
                    'avatar_url': user.avatar_url,
                    'is_admin': user.is_admin,
                    'is_system_admin': user.is_system_admin,
                    'last_login_at': user.last_login_at.isoformat() if user.last_login_at else None,
                    'created_at': user.created_at.isoformat() if user.created_at else None,
                    'updated_at': user.updated_at.isoformat() if user.updated_at else None,
                    'cached_at': time.time()
                }
                
                backend.set(cache_key, user_data, self.default_ttl)
                print(f"💾 用户信息已缓存: user_id={user.id}, TTL={self.default_ttl}s")
                
        except Exception as e:
            print(f"⚠️ 缓存用户信息失败: {e}")
    
    def invalidate_user_cache(self, user_id: int) -> None:
        """清除用户缓存"""
        try:
            if hasattr(FastAPICache, '_instance') and FastAPICache._instance:
                backend = FastAPICache._instance.backend
                cache_key = self._get_cache_key(user_id)
                backend.delete(cache_key)
                print(f"🗑️ 用户缓存已清除: user_id={user_id}")
                
        except Exception as e:
            print(f"⚠️ 清除用户缓存失败: {e}")
    
    def recreate_user_from_cache(self, cached_data: Dict[str, Any]) -> User:
        """从缓存数据重建User对象"""
        from datetime import datetime
        
        # 创建User对象（不通过SQLAlchemy，避免数据库查询）
        user = User()
        user.id = cached_data['id']
        user.uid = cached_data['uid']
        user.display_name = cached_data['display_name']
        user.email = cached_data['email']
        user.avatar_url = cached_data['avatar_url']
        user.is_admin = cached_data['is_admin']
        user.is_system_admin = cached_data['is_system_admin']
        
        # 处理时间字段
        if cached_data.get('last_login_at'):
            user.last_login_at = datetime.fromisoformat(cached_data['last_login_at'])
        if cached_data.get('created_at'):
            user.created_at = datetime.fromisoformat(cached_data['created_at'])
        if cached_data.get('updated_at'):
            user.updated_at = datetime.fromisoformat(cached_data['updated_at'])
        
        return user
    
    def is_cache_fresh(self, cached_data: Dict[str, Any]) -> bool:
        """检查缓存是否新鲜"""
        cached_at = cached_data.get('cached_at', 0)
        age = time.time() - cached_at
        return age < self.default_ttl


# 全局用户缓存服务实例
_user_cache_service: Optional[UserCacheService] = None


def get_user_cache_service() -> UserCacheService:
    """获取全局用户缓存服务实例"""
    global _user_cache_service
    if _user_cache_service is None:
        _user_cache_service = UserCacheService()
    return _user_cache_service