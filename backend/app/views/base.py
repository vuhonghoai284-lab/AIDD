"""
基础视图类
"""
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.models.user import User
from app.services.auth import AuthService


class BaseView:
    """基础视图类，提供通用的依赖和方法"""
    
    def __init__(self):
        pass
    
    @staticmethod
    def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)) -> User:
        """获取当前登录用户"""
        if not authorization:
            raise HTTPException(status_code=401, detail="缺少认证信息")
        
        # 解析Bearer token
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="无效的认证方案")
        
        # 验证token
        auth_service = AuthService(db)
        user = auth_service.verify_token(token)
        if not user:
            raise HTTPException(status_code=401, detail="无效的认证令牌")
        
        return user
    
    @staticmethod
    def get_current_user_optional(authorization: str = Header(None), db: Session = Depends(get_db)) -> Optional[User]:
        """获取当前登录用户（可选）"""
        if not authorization:
            return None
        
        # 解析Bearer token
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer":
            return None
        
        # 验证token
        auth_service = AuthService(db)
        user = auth_service.verify_token(token)
        return user
    
    @staticmethod
    def check_admin_permission(user: User):
        """检查管理员权限"""
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="权限不足")
    
    @staticmethod
    def check_task_access_permission(user: User, task_user_id: Optional[int]):
        """检查任务访问权限"""
        if not user.is_admin and task_user_id != user.id:
            raise HTTPException(status_code=403, detail="权限不足，无法访问此任务")