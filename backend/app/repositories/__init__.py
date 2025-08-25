"""
数据仓库
"""
from app.repositories.task import TaskRepository
from app.repositories.issue import IssueRepository
from app.repositories.ai_output import AIOutputRepository
from app.repositories.user import UserRepository

__all__ = [
    "TaskRepository",
    "IssueRepository", 
    "AIOutputRepository",
    "UserRepository"
]