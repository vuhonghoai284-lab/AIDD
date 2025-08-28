"""
任务队列数据模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
import enum


class QueueStatus(enum.Enum):
    """队列状态枚举"""
    QUEUED = "queued"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskQueue(Base):
    """任务队列模型 - 支持20用户x3并发的队列调度"""
    __tablename__ = "task_queue"
    
    id = Column(Integer, primary_key=True, index=True, comment="队列项ID")
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, comment="关联任务ID")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="用户ID")
    priority = Column(Integer, default=5, comment="优先级1-10，越大越优先")
    status = Column(Enum(QueueStatus), default=QueueStatus.QUEUED, comment="队列状态")
    worker_id = Column(String(50), nullable=True, comment="处理工作者ID")
    
    # 时间字段
    queued_at = Column(DateTime, default=datetime.utcnow, comment="入队时间")
    started_at = Column(DateTime, nullable=True, comment="开始处理时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")
    
    # 重试机制
    attempts = Column(Integer, default=0, comment="已尝试次数")
    max_attempts = Column(Integer, default=3, comment="最大重试次数")
    error_message = Column(Text, nullable=True, comment="错误信息")
    
    # 任务数据和元信息
    task_data = Column(JSON, nullable=True, comment="任务数据快照")
    estimated_duration = Column(Integer, default=300, comment="预估处理时长(秒)")
    
    # 关联关系
    task = relationship("Task", back_populates="queue_items")
    user = relationship("User")

    def __repr__(self):
        return f"<TaskQueue(id={self.id}, task_id={self.task_id}, user_id={self.user_id}, status={self.status.value})>"
    
    @property
    def wait_time_seconds(self) -> int:
        """等待时间（秒）"""
        if self.started_at:
            return int((self.started_at - self.queued_at).total_seconds())
        return int((datetime.utcnow() - self.queued_at).total_seconds())
    
    @property
    def processing_time_seconds(self) -> int:
        """处理时间（秒）"""
        if self.status == QueueStatus.PROCESSING and self.started_at:
            return int((datetime.utcnow() - self.started_at).total_seconds())
        elif self.completed_at and self.started_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return 0
    
    @property
    def is_expired(self) -> bool:
        """是否已超时"""
        if self.status == QueueStatus.PROCESSING and self.started_at:
            timeout = getattr(self, 'timeout', 600)  # 默认10分钟超时
            return (datetime.utcnow() - self.started_at).total_seconds() > timeout
        return False


class QueueConfig(Base):
    """队列配置模型"""
    __tablename__ = "queue_config"
    
    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(100), nullable=False, unique=True, comment="配置键")
    config_value = Column(Text, nullable=False, comment="配置值")
    description = Column(Text, nullable=True, comment="配置描述")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    def __repr__(self):
        return f"<QueueConfig(key={self.config_key}, value={self.config_value})>"


# 在Task模型中添加反向关联 (需要在task.py中添加)
# task_queue_items = relationship("TaskQueue", back_populates="task", cascade="all, delete-orphan")