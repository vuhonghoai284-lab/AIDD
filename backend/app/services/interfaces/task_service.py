"""
任务服务接口
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from fastapi import UploadFile

from app.dto.task import TaskResponse, TaskDetail
from app.services.interfaces.base import BaseService


class ITaskService(BaseService[TaskResponse, int]):
    """任务服务接口"""
    
    @abstractmethod
    async def create_task(self, file: UploadFile, title: Optional[str] = None, 
                         ai_model_index: Optional[int] = None, user_id: Optional[int] = None) -> TaskResponse:
        """创建任务"""
        pass
    
    @abstractmethod
    def get_user_tasks(self, user_id: int) -> List[TaskResponse]:
        """获取指定用户的任务"""
        pass
    
    @abstractmethod
    def get_task_detail(self, task_id: int) -> TaskDetail:
        """获取任务详情"""
        pass
    
    @abstractmethod
    def delete_task(self, task_id: int) -> bool:
        """删除任务"""
        pass