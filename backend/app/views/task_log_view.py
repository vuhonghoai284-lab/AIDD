"""
任务日志相关视图
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.repositories.task import TaskRepository
from app.models import TaskLog
from app.views.base import BaseView


class TaskLogView(BaseView):
    """任务日志视图类"""
    
    def __init__(self):
        super().__init__()
        self.router = APIRouter(tags=["task-logs"])
        self._setup_routes()
    
    def _setup_routes(self):
        """设置路由"""
        self.router.add_api_route("/{task_id}/logs/history", self.get_task_logs, methods=["GET"])
    
    def get_task_logs(
        self,
        task_id: int,
        current_user: User = Depends(BaseView.get_current_user),
        db: Session = Depends(get_db)
    ):
        """获取任务的历史日志"""
        task_repo = TaskRepository(db)
        task = task_repo.get_by_id(task_id)
        if not task:
            raise HTTPException(404, "任务不存在")
        
        # 检查用户权限
        self.check_task_access_permission(current_user, task.user_id)
        
        logs = db.query(TaskLog).filter(TaskLog.task_id == task_id).order_by(TaskLog.timestamp).all()
        return [
            {
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "level": log.level,
                "module": log.module,
                "stage": log.stage,
                "message": log.message,
                "progress": log.progress,
                "extra_data": log.extra_data
            }
            for log in logs
        ]


# 创建视图实例并导出router
task_log_view = TaskLogView()
router = task_log_view.router