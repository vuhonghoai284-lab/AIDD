"""
任务Repository接口
"""
from abc import ABC, abstractmethod
from typing import List
from app.models.task import Task
from app.repositories.interfaces.base import BaseRepository


class ITaskRepository(BaseRepository[Task, int]):
    """任务Repository接口"""
    
    @abstractmethod
    def get_by_user_id(self, user_id: int) -> List[Task]:
        """根据用户ID获取任务列表"""
        pass
    
    @abstractmethod
    def update_status(self, task_id: int, status: str, progress: int = None) -> Task:
        """更新任务状态和进度"""
        pass
    
    @abstractmethod
    def count_issues(self, task_id: int) -> int:
        """统计任务的问题数量"""
        pass