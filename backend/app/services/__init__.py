"""
服务模块
"""
from app.services.task import TaskService
from app.services.new_task_processor import NewTaskProcessor as TaskProcessor
from app.services.ai_service_factory import AIServiceFactory, ai_service_factory
from app.services.websocket import manager
from app.services.auth import AuthService
from app.services.ai_service import AIService
from app.services.document_processor import DocumentProcessor
from app.services.issue_detector import IssueDetector
from app.services.prompt_loader import prompt_loader
from app.services.realtime_logger import realtime_logger

__all__ = [
    "TaskService",
    "TaskProcessor", 
    "AIServiceFactory",
    "ai_service_factory",
    "manager",
    "AuthService",
    "AIService",
    "DocumentProcessor",
    "IssueDetector",
    "prompt_loader",
    "realtime_logger"
]