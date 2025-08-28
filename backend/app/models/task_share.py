"""
任务分享数据模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class TaskShare(Base):
    """任务分享模型"""
    __tablename__ = "task_shares"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)  # 分享者ID
    shared_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)  # 被分享用户ID
    
    # 权限级别：full_access, read_only, feedback_only
    permission_level = Column(String(20), nullable=False, default='read_only')
    share_comment = Column(Text)  # 分享备注
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # 关系定义
    task = relationship("Task", backref="task_shares")
    owner = relationship("User", foreign_keys=[owner_id], backref="owned_shares")  # 分享者
    shared_user = relationship("User", foreign_keys=[shared_user_id], backref="received_shares")  # 被分享用户
    
    # 唯一约束：同一任务不能重复分享给同一用户
    __table_args__ = (
        Index('idx_task_shares_unique', 'task_id', 'shared_user_id', unique=True),
    )
    
    def __repr__(self):
        return f"<TaskShare(task_id={self.task_id}, shared_user_id={self.shared_user_id}, permission={self.permission_level})>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'owner_id': self.owner_id,
            'shared_user_id': self.shared_user_id,
            'permission_level': self.permission_level,
            'share_comment': self.share_comment,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active
        }
    
    @classmethod
    def get_permission_name(cls, permission_level: str) -> str:
        """获取权限级别的中文名称"""
        names = {
            'full_access': '完全权限',
            'read_only': '只读权限', 
            'feedback_only': '反馈权限'
        }
        return names.get(permission_level, permission_level)
    
    @classmethod
    def get_permission_description(cls, permission_level: str) -> str:
        """获取权限级别的详细描述"""
        descriptions = {
            'full_access': '可查看、反馈、评论、评分、下载报告',
            'read_only': '仅可查看任务和报告内容',
            'feedback_only': '可查看、反馈结果、评论、评分'
        }
        return descriptions.get(permission_level, permission_level)