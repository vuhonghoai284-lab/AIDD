"""
任务分享API视图
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.views.base import BaseView
from app.models.user import User
from app.services.task_permission_service import TaskPermissionService
from app.repositories.task_share import TaskShareRepository
from app.repositories.user import UserRepository
from app.dto.task_share import (
    TaskShareCreateRequest,
    TaskShareUpdateRequest,
    TaskShareResponse,
    SharedTaskResponse,
    UserSearchResponse,
    TaskShareStatsResponse,
    BatchShareResult
)

router = APIRouter(prefix="/api/task-share", tags=["任务分享"])


@router.post("/{task_id}/share", response_model=BatchShareResult)
async def share_task(
    task_id: int,
    request: TaskShareCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(BaseView.get_current_user)
):
    """
    分享任务给其他用户
    """
    permission_service = TaskPermissionService(db)
    
    # 检查分享权限
    if not permission_service.check_task_share_permission(task_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您没有权限分享此任务"
        )
    
    # 检查被分享用户是否存在
    user_repo = UserRepository(db)
    valid_user_ids = []
    errors = []
    
    for user_id in request.shared_user_ids:
        if user_id == current_user.id:
            errors.append(f"不能分享给自己 (用户ID: {user_id})")
            continue
        
        user = user_repo.get_by_id(user_id)
        if not user:
            errors.append(f"用户不存在 (用户ID: {user_id})")
            continue
        
        valid_user_ids.append(user_id)
    
    if not valid_user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有有效的用户ID"
        )
    
    # 批量创建分享记录
    task_share_repo = TaskShareRepository(db)
    created_shares = task_share_repo.batch_create_shares(
        task_id=task_id,
        owner_id=current_user.id,
        shared_user_ids=valid_user_ids,
        permission_level=request.permission_level,
        share_comment=request.share_comment
    )
    
    # 构造响应对象
    share_responses = []
    for share in created_shares:
        # 加载关联用户信息
        share_user = user_repo.get_by_id(share.shared_user_id)
        share_responses.append(TaskShareResponse.from_task_share(
            share, shared_user=share_user, owner=current_user
        ))
    
    return BatchShareResult(
        success_count=len(created_shares),
        failed_count=len(errors),
        created_shares=share_responses,
        errors=errors
    )


@router.get("/{task_id}/shares", response_model=List[TaskShareResponse])
async def get_task_shares(
    task_id: int,
    include_inactive: bool = Query(False, description="是否包含已撤销的分享"),
    db: Session = Depends(get_db),
    current_user: User = Depends(BaseView.get_current_user)
):
    """
    获取任务的分享列表
    """
    permission_service = TaskPermissionService(db)
    
    # 检查查看权限
    if not permission_service.check_task_access(task_id, current_user, 'read'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您没有权限查看此任务"
        )
    
    task_share_repo = TaskShareRepository(db)
    shares = task_share_repo.get_task_shares(task_id, include_inactive)
    
    # 构造响应对象
    user_repo = UserRepository(db)
    response_shares = []
    
    for share in shares:
        shared_user = user_repo.get_by_id(share.shared_user_id)
        owner = user_repo.get_by_id(share.owner_id)
        response_shares.append(TaskShareResponse.from_task_share(
            share, shared_user=shared_user, owner=owner
        ))
    
    return response_shares


@router.put("/shares/{share_id}", response_model=TaskShareResponse)
async def update_share_permission(
    share_id: int,
    request: TaskShareUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(BaseView.get_current_user)
):
    """
    更新分享权限
    """
    task_share_repo = TaskShareRepository(db)
    
    # 更新分享权限（仅分享者可更新）
    updated_share = task_share_repo.update_share_permission(
        share_id=share_id,
        owner_id=current_user.id,
        permission_level=request.permission_level,
        share_comment=request.share_comment
    )
    
    if not updated_share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分享记录不存在或您没有权限更新"
        )
    
    # 构造响应对象
    user_repo = UserRepository(db)
    shared_user = user_repo.get_by_id(updated_share.shared_user_id)
    
    return TaskShareResponse.from_task_share(
        updated_share, shared_user=shared_user, owner=current_user
    )


@router.delete("/shares/{share_id}")
async def revoke_task_share(
    share_id: int,
    permanently: bool = Query(False, description="是否永久删除，默认为撤销"),
    db: Session = Depends(get_db),
    current_user: User = Depends(BaseView.get_current_user)
):
    """
    撤销或删除任务分享
    """
    task_share_repo = TaskShareRepository(db)
    
    if permanently:
        # 永久删除分享记录
        success = task_share_repo.delete_share(share_id, current_user.id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="分享记录不存在或您没有权限删除"
            )
        return {"message": "分享记录已永久删除"}
    else:
        # 撤销分享（软删除）
        success = task_share_repo.revoke_share(share_id, current_user.id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="分享记录不存在或您没有权限撤销"
            )
        return {"message": "分享已撤销"}


@router.get("/shared-with-me", response_model=List[SharedTaskResponse])
async def get_shared_tasks(
    include_inactive: bool = Query(False, description="是否包含已撤销的分享"),
    db: Session = Depends(get_db),
    current_user: User = Depends(BaseView.get_current_user)
):
    """
    获取分享给我的任务列表
    """
    task_share_repo = TaskShareRepository(db)
    shared_tasks = task_share_repo.get_user_shared_tasks(current_user.id, include_inactive)
    
    # 构造响应对象
    response_tasks = []
    for task_share in shared_tasks:
        response_tasks.append(SharedTaskResponse.from_task_share(task_share))
    
    return response_tasks


@router.get("/users/search", response_model=List[UserSearchResponse])
async def search_users(
    q: str = Query(..., min_length=2, max_length=50, description="搜索关键词，支持用户名或显示名称"),
    limit: int = Query(20, ge=1, le=50, description="返回结果限制，最多50个"),
    db: Session = Depends(get_db),
    current_user: User = Depends(BaseView.get_current_user)
):
    """
    搜索用户（用于分享任务时选择用户）
    """
    user_repo = UserRepository(db)
    
    # 搜索用户（排除当前用户）
    users = user_repo.search_users(query=q, exclude_user_id=current_user.id, limit=limit)
    
    # 构建响应对象
    response_users = []
    for user in users:
        response_users.append(UserSearchResponse(
            id=user.id,
            uid=user.uid,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            is_admin=user.is_admin,
            is_system_admin=user.is_system_admin
        ))
    
    return response_users


@router.get("/stats", response_model=TaskShareStatsResponse)
async def get_share_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(BaseView.get_current_user)
):
    """
    获取当前用户的分享统计信息
    """
    permission_service = TaskPermissionService(db)
    stats = permission_service.get_user_permission_summary(current_user)
    
    # 获取权限级别分布统计
    task_share_repo = TaskShareRepository(db)
    
    # 统计用户分享出去的任务权限分布
    from sqlalchemy import func
    from app.models.task_share import TaskShare
    
    permission_breakdown = db.query(
        TaskShare.permission_level,
        func.count(TaskShare.id)
    ).filter(
        TaskShare.owner_id == current_user.id,
        TaskShare.is_active == True
    ).group_by(TaskShare.permission_level).all()
    
    permission_dict = {level: count for level, count in permission_breakdown}
    
    return TaskShareStatsResponse(
        total_shares=stats.get('shared_tasks', 0),
        active_shares=stats.get('shared_tasks', 0),
        permission_breakdown=permission_dict
    )