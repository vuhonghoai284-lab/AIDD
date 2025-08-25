"""
AI输出相关视图
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.models.user import User
from app.repositories.ai_output import AIOutputRepository
from app.repositories.task import TaskRepository
from app.dto.ai_output import AIOutputResponse
from app.views.base import BaseView


class AIOutputView(BaseView):
    """AI输出视图类"""
    
    def __init__(self, route_type="single"):
        super().__init__()
        self.route_type = route_type
        if route_type == "task":
            self.router = APIRouter(tags=["AI输出"])
        else:
            self.router = APIRouter(tags=["AI输出"])
        self._setup_routes()
    
    def _setup_routes(self):
        """设置路由"""
        if self.route_type == "task":
            # 任务相关的AI输出路由
            self.router.add_api_route("/{task_id}/ai-outputs", self.get_task_ai_outputs, methods=["GET"])
        else:
            # 单独的AI输出详情路由  
            self.router.add_api_route("/{output_id}", self.get_ai_output_detail, methods=["GET"])
    
    def get_task_ai_outputs(
        self,
        task_id: int,
        operation_type: Optional[str] = None,
        current_user: User = Depends(BaseView.get_current_user),
        db: Session = Depends(get_db)
    ) -> List[AIOutputResponse]:
        """获取任务的AI输出记录"""
        task_repo = TaskRepository(db)
        task = task_repo.get_by_id(task_id)
        if not task:
            raise HTTPException(404, "任务不存在")
        
        # 检查用户权限
        self.check_task_access_permission(current_user, task.user_id)
        
        ai_output_repo = AIOutputRepository(db)
        outputs = ai_output_repo.get_by_task_id(task_id, operation_type)
        return [AIOutputResponse.from_orm(output) for output in outputs]
    
    def get_ai_output_detail(
        self,
        output_id: int,
        current_user: User = Depends(BaseView.get_current_user),
        db: Session = Depends(get_db)
    ) -> AIOutputResponse:
        """获取AI输出详情"""
        ai_output_repo = AIOutputRepository(db)
        output = ai_output_repo.get_by_id(output_id)
        if not output:
            raise HTTPException(404, "AI输出不存在")
        
        # 获取相关任务以检查权限
        task_repo = TaskRepository(db)
        task = task_repo.get_by_id(output.task_id)
        if not task:
            raise HTTPException(404, "相关任务不存在")
        
        # 检查用户权限
        self.check_task_access_permission(current_user, task.user_id)
        
        return AIOutputResponse.from_orm(output)


# 创建两个不同的视图实例
task_ai_output_view = AIOutputView(route_type="task")
single_ai_output_view = AIOutputView(route_type="single")

# 为了保持兼容性，保留原有的ai_output_view实例
ai_output_view = AIOutputView()
router = ai_output_view.router