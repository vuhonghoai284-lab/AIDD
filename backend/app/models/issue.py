"""
问题数据模型
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship

from app.core.database import Base


class Issue(Base):
    """问题模型"""
    __tablename__ = "issues"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)  # 添加索引优化JOIN查询
    issue_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    location = Column(String(500))
    severity = Column(String(50), nullable=False)
    confidence = Column(Float)
    suggestion = Column(Text)
    original_text = Column(Text)
    user_impact = Column(Text)
    reasoning = Column(Text)
    context = Column(Text)
    feedback_type = Column(String(50), index=True)  # 添加索引优化已处理问题统计
    feedback_comment = Column(Text)
    satisfaction_rating = Column(Float)  # 满意度评分 1-5星
    # 反馈操作人信息
    feedback_user_id = Column(Integer, ForeignKey("users.id"), index=True)  # 反馈操作用户ID
    feedback_user_name = Column(String(100))  # 反馈操作用户名称
    feedback_updated_at = Column(DateTime)  # 最后反馈时间
    created_at = Column(String(50))
    updated_at = Column(String(50))
    
    # 关系
    task = relationship("Task", backref="issues")