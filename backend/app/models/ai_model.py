"""
AI模型数据模型
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, Float, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class AIModel(Base):
    """AI模型信息表"""
    __tablename__ = "ai_models"
    
    id = Column(Integer, primary_key=True, index=True)
    # 模型标识符（唯一）
    model_key = Column(String(100), unique=True, index=True, nullable=False)
    # 前端显示标签
    label = Column(String(200), nullable=False)
    # 服务提供商
    provider = Column(String(50), nullable=False)  # openai, anthropic, etc.
    # 模型名称
    model_name = Column(String(100), nullable=False)
    # 模型描述
    description = Column(Text)
    
    # 模型配置参数
    temperature = Column(Float, default=0.3)
    max_tokens = Column(Integer, default=8000)
    context_window = Column(Integer, default=128000)
    reserved_tokens = Column(Integer, default=2000)
    timeout = Column(Integer, default=12000)
    max_retries = Column(Integer, default=3)
    
    # API配置（不存储敏感信息）
    base_url = Column(String(500))
    api_key_env = Column(String(100))  # 环境变量名
    
    # 模型状态
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    
    # 排序权重
    sort_order = Column(Integer, default=0)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系定义
    tasks = relationship("Task", back_populates="ai_model")
    
    def __repr__(self):
        return f"<AIModel(id={self.id}, key='{self.model_key}', label='{self.label}')>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'model_key': self.model_key,
            'label': self.label,
            'provider': self.provider,
            'model_name': self.model_name,
            'description': self.description,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'context_window': self.context_window,
            'reserved_tokens': self.reserved_tokens,
            'timeout': self.timeout,
            'max_retries': self.max_retries,
            'base_url': self.base_url,
            'is_active': self.is_active,
            'is_default': self.is_default,
            'sort_order': self.sort_order
        }