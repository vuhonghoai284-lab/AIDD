"""
任务数据模型
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class Task(Base):
    """任务模型"""
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    
    # 任务状态和进度
    status = Column(String(50), default='pending')  # pending, processing, completed, failed
    progress = Column(Float, default=0.0)
    processing_time = Column(Float)
    error_message = Column(Text)
    
    # 外键关联（添加索引以优化查询性能）
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    file_id = Column(Integer, ForeignKey("file_infos.id"), nullable=False, index=True)
    model_id = Column(Integer, ForeignKey("ai_models.id"), nullable=False, index=True)
    
    # 时间戳（添加索引以优化排序查询）
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime)
    
    # 关系定义
    user = relationship("User", back_populates="tasks")
    file_info = relationship("FileInfo", back_populates="tasks")
    ai_model = relationship("AIModel", back_populates="tasks")
    
    def __repr__(self):
        return f"<Task(id={self.id}, title='{self.title}', status='{self.status}')>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'title': self.title,
            'status': self.status,
            'progress': self.progress,
            'processing_time': self.processing_time,
            'error_message': self.error_message,
            'user_id': self.user_id,
            'file_id': self.file_id,
            'model_id': self.model_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }