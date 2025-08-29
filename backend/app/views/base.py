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
        """获取当前登录用户（生产环境增强版本）"""
        import time
        start_time = time.time()
        
        try:
            if not authorization:
                print("❌ 认证失败: 缺少Authorization头")
                raise HTTPException(status_code=401, detail="缺少认证信息")
            
            # 解析Bearer token
            scheme, _, token = authorization.partition(" ")
            if scheme.lower() != "bearer":
                print(f"❌ 认证失败: 无效的认证方案 '{scheme}'")
                raise HTTPException(status_code=401, detail="无效的认证方案")
            
            if not token or len(token) < 10:
                print("❌ 认证失败: Token为空或过短")
                raise HTTPException(status_code=401, detail="无效的认证令牌")
            
            # 验证数据库会话
            if not db:
                print("❌ 数据库会话获取失败")
                raise HTTPException(status_code=500, detail="服务器内部错误")
            
            # 验证token
            auth_service = AuthService(db)
            user = auth_service.verify_token(token)
            
            if not user:
                print("❌ Token验证失败: verify_token返回None")
                raise HTTPException(status_code=401, detail="无效的认证令牌")
            
            # 验证用户对象完整性
            if not hasattr(user, 'id') or not hasattr(user, 'uid'):
                print(f"❌ 用户对象不完整: {type(user)}, 属性: {dir(user) if user else 'None'}")
                raise HTTPException(status_code=401, detail="用户数据异常")
            
            # 记录性能日志
            elapsed_time = (time.time() - start_time) * 1000
            if elapsed_time > 1000:  # 超过1秒记录警告
                print(f"⚠️ 用户认证耗时过长: {elapsed_time:.1f}ms, 用户: {user.uid}")
            elif elapsed_time > 100:  # 超过100ms记录信息
                print(f"ℹ️ 用户认证耗时: {elapsed_time:.1f}ms, 用户: {user.uid}")
            
            return user
            
        except HTTPException:
            raise
        except Exception as e:
            elapsed_time = (time.time() - start_time) * 1000
            print(f"❌ 用户认证异常: {e}, 耗时: {elapsed_time:.1f}ms, 异常类型: {type(e)}")
            raise HTTPException(status_code=500, detail="认证服务异常")
    
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
        """检查任务访问权限（已废弃，建议使用 check_task_access_with_permission_service）"""
        if not user.is_admin and task_user_id != user.id:
            raise HTTPException(status_code=403, detail="权限不足，无法访问此任务")
    
    @staticmethod
    def check_task_access_with_permission_service(task_id: int, user: User, db: Session, required_permission: str = 'read'):
        """使用权限服务检查任务访问权限"""
        from app.services.task_permission_service import TaskPermissionService
        
        permission_service = TaskPermissionService(db)
        if not permission_service.check_task_access(task_id, user, required_permission):
            raise HTTPException(
                status_code=403, 
                detail=f"权限不足，无法{required_permission}此任务"
            )