"""
问题相关视图
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.views.base import BaseView
from app.models.user import User
from app.repositories.issue import IssueRepository
from app.repositories.task import TaskRepository
from app.services.task_permission_service import TaskPermissionService
from app.dto.issue import FeedbackRequest, SatisfactionRatingRequest, CommentOnlyRequest


router = APIRouter(tags=["issues"])


@router.put("/{issue_id}/feedback")
def submit_feedback(
    issue_id: int,
    feedback: FeedbackRequest,
    current_user: User = Depends(BaseView.get_current_user),
    db: Session = Depends(get_db)
):
    """提交问题反馈"""
    issue_repo = IssueRepository(db)
    
    # 获取问题信息
    issue = issue_repo.get_by_id(issue_id)
    if not issue:
        raise HTTPException(404, "问题不存在")
    
    # 检查用户权限
    permission_service = TaskPermissionService(db)
    if not permission_service.check_task_access(issue.task_id, current_user, 'feedback'):
        raise HTTPException(403, "您没有权限反馈此问题")
    
    updated_issue = issue_repo.update_feedback(issue_id, feedback.feedback_type, feedback.comment, current_user)
    if not updated_issue:
        raise HTTPException(500, "问题更新失败")
    return {"success": True}


@router.put("/{issue_id}/satisfaction")
def submit_satisfaction_rating(
    issue_id: int,
    rating_data: SatisfactionRatingRequest,
    current_user: User = Depends(BaseView.get_current_user),
    db: Session = Depends(get_db)
):
    """提交满意度评分"""
    issue_repo = IssueRepository(db)
    
    # 获取问题信息
    issue = issue_repo.get_by_id(issue_id)
    if not issue:
        raise HTTPException(404, "问题不存在")
    
    # 检查用户权限
    permission_service = TaskPermissionService(db)
    if not permission_service.check_task_access(issue.task_id, current_user, 'feedback'):
        raise HTTPException(403, "您没有权限评分此问题")
    
    updated_issue = issue_repo.update_satisfaction_rating(issue_id, rating_data.satisfaction_rating, current_user)
    if not updated_issue:
        raise HTTPException(500, "评分更新失败")
    return {"success": True}


@router.put("/{issue_id}/comment")
def update_comment_only(
    issue_id: int,
    comment_data: CommentOnlyRequest,
    current_user: User = Depends(BaseView.get_current_user),
    db: Session = Depends(get_db)
):
    """只更新评论，不改变反馈状态"""
    issue_repo = IssueRepository(db)
    
    # 获取问题信息
    issue = issue_repo.get_by_id(issue_id)
    if not issue:
        raise HTTPException(404, "问题不存在")
    
    # 检查用户权限
    permission_service = TaskPermissionService(db)
    if not permission_service.check_task_access(issue.task_id, current_user, 'feedback'):
        raise HTTPException(403, "您没有权限评论此问题")
    
    updated_issue = issue_repo.update_comment_only(issue_id, comment_data.comment, current_user)
    if not updated_issue:
        raise HTTPException(500, "评论更新失败")
    return {"success": True}