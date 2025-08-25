"""
任务数据访问层
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.models import Task, Issue
from app.repositories.interfaces.task_repository import ITaskRepository


class TaskRepository(ITaskRepository):
    """任务仓库"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, **kwargs) -> Task:
        """创建任务"""
        task = Task(**kwargs)
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task
    
    def get_by_id(self, task_id: int) -> Optional[Task]:
        """根据ID获取任务"""
        return self.db.query(Task).filter(Task.id == task_id).first()
    
    def get(self, task_id: int) -> Optional[Task]:
        """根据ID获取任务 (别名)"""
        return self.get_by_id(task_id)
    
    def get_all(self) -> List[Task]:
        """获取所有任务"""
        return self.db.query(Task).order_by(Task.created_at.desc()).all()
    
    def get_by_user_id(self, user_id: int) -> List[Task]:
        """根据用户ID获取任务"""
        return self.db.query(Task).filter(Task.user_id == user_id).order_by(Task.created_at.desc()).all()
    
    def update(self, task_id: int, **kwargs) -> Optional[Task]:
        """更新任务"""
        task = self.get_by_id(task_id)
        if task:
            for key, value in kwargs.items():
                setattr(task, key, value)
            self.db.commit()
            self.db.refresh(task)
        return task
    
    def delete(self, task_id: int) -> bool:
        """删除任务"""
        task = self.get_by_id(task_id)
        if task:
            # 删除相关的问题和AI输出
            self.db.query(Issue).filter(Issue.task_id == task_id).delete()
            from app.models import AIOutput
            self.db.query(AIOutput).filter(AIOutput.task_id == task_id).delete()
            
            self.db.delete(task)
            self.db.commit()
            return True
        return False
    
    def get_pending_tasks(self) -> List[Task]:
        """获取待处理任务"""
        return self.db.query(Task).filter(Task.status == 'pending').all()
    
    def update_progress(self, task_id: int, progress: float, status: Optional[str] = None):
        """更新任务进度"""
        update_data = {"progress": progress}
        if status:
            update_data["status"] = status
            if status == "completed":
                update_data["completed_at"] = datetime.utcnow()
        self.update(task_id, **update_data)
    
    def count_issues(self, task_id: int) -> int:
        """统计任务的问题数量"""
        return self.db.query(Issue).filter(Issue.task_id == task_id).count()
    
    def count_processed_issues(self, task_id: int) -> int:
        """统计任务的已处理问题数量"""
        return self.db.query(Issue).filter(
            Issue.task_id == task_id,
            Issue.feedback_type.isnot(None)
        ).count()
    
    def update_status(self, task_id: int, status: str, progress: int = None) -> Task:
        """更新任务状态和进度"""
        update_data = {"status": status}
        if progress is not None:
            update_data["progress"] = progress
        if status == "completed":
            update_data["completed_at"] = datetime.utcnow()
        return self.update(task_id, **update_data)