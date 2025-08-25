"""
AI输出数据模型
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class AIOutput(Base):
    """AI输出模型"""
    __tablename__ = "ai_outputs"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    operation_type = Column(String(100), nullable=False)
    section_title = Column(String(500))
    section_index = Column(Integer)
    input_text = Column(Text, nullable=False)
    raw_output = Column(Text, nullable=False)
    parsed_output = Column(JSON)
    status = Column(String(50), nullable=False)  # success, failed
    error_message = Column(Text)
    tokens_used = Column(Integer)
    processing_time = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    task = relationship("Task", backref="ai_outputs")