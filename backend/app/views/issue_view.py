"""
问题相关视图
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.user import User
from app.repositories.issue import IssueRepository
from app.repositories.task import TaskRepository
from app.dto.issue import FeedbackRequest, SatisfactionRatingRequest, CommentOnlyRequest
from app.views.base import BaseView


class IssueView(BaseView):
    """问题视图类"""
    
    def __init__(self):
        super().__init__()
        self.router = APIRouter(tags=["issues"])
        self._setup_routes()
    
    def _setup_routes(self):
        """设置路由"""
        self.router.add_api_route("/{issue_id}/feedback", self.submit_feedback, methods=["PUT"])
        self.router.add_api_route("/{issue_id}/comment", self.update_comment_only, methods=["PUT"])
        self.router.add_api_route("/{issue_id}/satisfaction", self.submit_satisfaction_rating, methods=["PUT"])
    
    def submit_feedback(
        self,
        issue_id: int,
        feedback: FeedbackRequest,
        current_user: User = Depends(BaseView.get_current_user),
        db: Session = Depends(get_db)
    ):
        """提交问题反馈"""
        issue_repo = IssueRepository(db)
        task_repo = TaskRepository(db)
        
        # 获取问题信息
        issue = issue_repo.get_by_id(issue_id)
        if not issue:
            raise HTTPException(404, "问题不存在")
        
        # 获取任务信息以检查权限
        task = task_repo.get_by_id(issue.task_id)
        if not task:
            raise HTTPException(404, "相关任务不存在")
        
        # 检查用户权限
        self.check_task_access_permission(current_user, task.user_id)
        
        updated_issue = issue_repo.update_feedback(issue_id, feedback.feedback_type, feedback.comment)
        if not updated_issue:
            raise HTTPException(404, "问题更新失败")
        return {"success": True}
    
    def submit_satisfaction_rating(
        self,
        issue_id: int,
        rating_data: SatisfactionRatingRequest,
        current_user: User = Depends(BaseView.get_current_user),
        db: Session = Depends(get_db)
    ):
        """提交满意度评分"""
        issue_repo = IssueRepository(db)
        task_repo = TaskRepository(db)
        
        # 获取问题信息
        issue = issue_repo.get_by_id(issue_id)
        if not issue:
            raise HTTPException(404, "问题不存在")
        
        # 获取任务信息以检查权限
        task = task_repo.get_by_id(issue.task_id)
        if not task:
            raise HTTPException(404, "相关任务不存在")
        
        # 检查用户权限
        self.check_task_access_permission(current_user, task.user_id)
        
        updated_issue = issue_repo.update_satisfaction_rating(issue_id, rating_data.satisfaction_rating)
        if not updated_issue:
            raise HTTPException(404, "评分更新失败")
        return {"success": True}
    
    def update_comment_only(
        self,
        issue_id: int,
        comment_data: CommentOnlyRequest,
        current_user: User = Depends(BaseView.get_current_user),
        db: Session = Depends(get_db)
    ):
        """只更新评论，不改变反馈状态"""
        issue_repo = IssueRepository(db)
        task_repo = TaskRepository(db)
        
        # 获取问题信息
        issue = issue_repo.get_by_id(issue_id)
        if not issue:
            raise HTTPException(404, "问题不存在")
        
        # 获取任务信息以检查权限
        task = task_repo.get_by_id(issue.task_id)
        if not task:
            raise HTTPException(404, "相关任务不存在")
        
        # 检查用户权限
        self.check_task_access_permission(current_user, task.user_id)
        
        updated_issue = issue_repo.update_comment_only(issue_id, comment_data.comment)
        if not updated_issue:
            raise HTTPException(404, "评论更新失败")
        return {"success": True}


# 创建视图实例并导出router
issue_view = IssueView()
router = issue_view.router