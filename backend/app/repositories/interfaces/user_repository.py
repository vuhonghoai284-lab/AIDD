"""
用户Repository接口
"""
from abc import ABC, abstractmethod
from typing import Optional
from app.models.user import User
from app.dto.user import UserCreate
from app.repositories.interfaces.base import BaseRepository


class IUserRepository(BaseRepository[User, int]):
    """用户Repository接口"""
    
    @abstractmethod
    def get_by_uid(self, uid: str) -> Optional[User]:
        """根据UID获取用户"""
        pass
    
    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        pass
    
    @abstractmethod
    def update_last_login(self, user_id: int) -> Optional[User]:
        """更新用户最后登录时间"""
        pass