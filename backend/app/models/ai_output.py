"""
AI输出数据模型
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float, DateTime, JSON, TypeDecorator
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class LargeText(TypeDecorator):
    """跨数据库的大文本类型，MySQL使用LONGTEXT，SQLite使用TEXT"""
    impl = Text
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'mysql':
            return dialect.type_descriptor(LONGTEXT())
        else:
            return dialect.type_descriptor(Text())


class AIOutput(Base):
    """AI输出模型"""
    __tablename__ = "ai_outputs"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    operation_type = Column(String(100), nullable=False)
    section_title = Column(String(500))
    section_index = Column(Integer)
    input_text = Column(LargeText, nullable=False)  # 使用自定义大文本类型
    raw_output = Column(LargeText, nullable=False)  # 使用自定义大文本类型
    parsed_output = Column(JSON)
    status = Column(String(50), nullable=False)  # success, failed
    error_message = Column(Text)
    tokens_used = Column(Integer)
    processing_time = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    task = relationship("Task", backref="ai_outputs")