"""
用户数据模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    # 用户唯一标识符（第三方系统ID）
    uid = Column(String(100), unique=True, index=True, nullable=False)
    # 用户显示名称
    display_name = Column(String(200))
    # 用户邮箱
    email = Column(String(200))
    # 用户头像URL
    avatar_url = Column(String(500))
    # 是否为管理员
    is_admin = Column(Boolean, default=False)
    # 是否为系统管理员（用于本地登录）
    is_system_admin = Column(Boolean, default=False)
    # 创建时间
    created_at = Column(DateTime, default=datetime.utcnow)
    # 最后登录时间
    last_login_at = Column(DateTime)
    
    # 关系定义
    tasks = relationship("Task", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, uid='{self.uid}', display_name='{self.display_name}')>"