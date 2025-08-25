"""
任务日志数据模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from datetime import datetime, timezone

from app.core.database import Base


class TaskLog(Base):
    """任务日志模型"""
    __tablename__ = "task_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    level = Column(String, nullable=False)  # DEBUG, INFO, WARNING, ERROR, PROGRESS
    module = Column(String, default="system")
    stage = Column(String)  # 初始化, 文档解析, 内容分析, 报告生成, 完成, 错误
    message = Column(Text)
    progress = Column(Integer, default=0)
    extra_data = Column(JSON, default={})