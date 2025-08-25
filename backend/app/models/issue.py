"""
问题数据模型
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float
from sqlalchemy.orm import relationship

from app.core.database import Base


class Issue(Base):
    """问题模型"""
    __tablename__ = "issues"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
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
    feedback_type = Column(String(50))  # accept, reject
    feedback_comment = Column(Text)
    satisfaction_rating = Column(Float)  # 满意度评分 1-5星
    created_at = Column(String(50))
    updated_at = Column(String(50))
    
    # 关系
    task = relationship("Task", backref="issues")