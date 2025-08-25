"""
用户相关视图
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.user import User
from app.repositories.user import UserRepository
from app.dto.user import UserResponse
from app.views.base import BaseView


class UserView(BaseView):
    """用户视图类"""
    
    def __init__(self):
        super().__init__()
        self.router = APIRouter(tags=["users"])
        self._setup_routes()
    
    def _setup_routes(self):
        """设置路由"""
        self.router.add_api_route("/me", self.get_current_user_info, methods=["GET"], response_model=UserResponse)
        self.router.add_api_route("/", self.get_users, methods=["GET"], response_model=List[UserResponse])
    
    def get_current_user_info(
        self,
        current_user: User = Depends(BaseView.get_current_user)
    ) -> UserResponse:
        """获取当前用户信息"""
        return UserResponse.from_orm(current_user)
    
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