"""
用户相关视图
"""
from fastapi import APIRouter, Depends
from fastapi_cache.decorator import cache
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.user import User
from app.repositories.user import UserRepository
from app.dto.user import UserResponse
from app.views.base import BaseView


def build_user_me_cache_key(func, *args, **kwargs):
    """构建/users/me缓存键"""
    current_user = kwargs.get('current_user')
    if current_user and hasattr(current_user, 'id'):
        return f"user_me:{current_user.id}"
    return "user_me:anonymous"


class UserView(BaseView):
    """用户视图类"""
    
    def __init__(self):
        super().__init__()
        self.router = APIRouter(tags=["users"])
        self._setup_routes()
    
    def _setup_routes(self):
        """设置路由"""
        self.router.add_api_route("/users/me", self.get_current_user_info, methods=["GET"], response_model=UserResponse)
        self.router.add_api_route("/users", self.get_users, methods=["GET"], response_model=List[UserResponse])
    
    @cache(expire=300, key_builder=build_user_me_cache_key)
    def get_current_user_info(
        self,
        current_user: User = Depends(BaseView.get_current_user)
    ) -> UserResponse:
        """获取当前用户信息（缓存5分钟）"""
        import time
        start_time = time.time()
        
        response = UserResponse.from_orm(current_user)
        
        elapsed_time = (time.time() - start_time) * 1000
        if elapsed_time > 10:  # 超过10ms记录
            print(f"📄 /users/me响应构建耗时: {elapsed_time:.1f}ms, user_id={current_user.id}")
        
        return response
    
    def get_users(
        self,
        current_user: User = Depends(BaseView.get_current_user),
        db: Session = Depends(get_db)
    ) -> List[UserResponse]:
        """获取所有用户（仅管理员可访问）"""
        self.check_admin_permission(current_user)
        
        user_repo = UserRepository(db)
        users = user_repo.get_all()
        return [UserResponse.from_orm(user) for user in users]


# 创建视图实例并导出router
user_view = UserView()
router = user_view.router