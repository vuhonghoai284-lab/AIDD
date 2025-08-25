"""
用户数据仓库
"""
from sqlalchemy.orm import Session
from typing import Optional, List
from app.models.user import User
from app.dto.user import UserCreate, UserUpdate
from app.repositories.interfaces.user_repository import IUserRepository
from datetime import datetime


class UserRepository(IUserRepository):
    """用户仓库类"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_by_uid(self, uid: str) -> Optional[User]:
        """根据UID获取用户"""
        return self.db.query(User).filter(User.uid == uid).first()
    
    def get_all(self) -> List[User]:
        """获取所有用户"""
        return self.db.query(User).all()
    
    def create(self, user_data=None, **kwargs) -> User:
        """创建用户"""
        if user_data and hasattr(user_data, 'uid'):
            # 使用UserCreate对象
            db_user = User(
                uid=user_data.uid,
                display_name=user_data.display_name,
                email=user_data.email,
                avatar_url=user_data.avatar_url,
                is_admin=user_data.is_admin,
                is_system_admin=user_data.is_system_admin
            )
        else:
            # 使用kwargs
            db_user = User(**kwargs)
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user
    
    def get_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        return self.db.query(User).filter(User.email == email).first()
    
    def update(self, user_id: int, user_data=None, **kwargs) -> Optional[User]:
        """更新用户信息"""
        db_user = self.get_by_id(user_id)
        if not db_user:
            return None
        
        if user_data and hasattr(user_data, 'dict'):
            update_data = user_data.dict(exclude_unset=True)
        else:
            update_data = kwargs
        
        for key, value in update_data.items():
            setattr(db_user, key, value)
        
        self.db.commit()
        self.db.refresh(db_user)
        return db_user
    
    def update_last_login(self, user_id: int) -> Optional[User]:
        """更新用户最后登录时间"""
        db_user = self.get_by_id(user_id)
        if not db_user:
            return None
        
        db_user.last_login_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(db_user)
        return db_user
    
    def delete(self, user_id: int) -> bool:
        """删除用户"""
        db_user = self.get_by_id(user_id)
        if not db_user:
            return False
        
        self.db.delete(db_user)
        self.db.commit()
        return True