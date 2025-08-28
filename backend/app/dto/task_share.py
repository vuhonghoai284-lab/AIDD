"""
任务分享相关的DTO（数据传输对象）
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime

from app.dto.user import UserResponse
from app.dto.task import TaskResponse


class TaskShareCreateRequest(BaseModel):
    """创建任务分享请求"""
    shared_user_ids: List[int] = Field(..., min_items=1, max_items=20, description="被分享用户ID列表，最多20个")
    permission_level: str = Field(default="read_only", description="权限级别：full_access, read_only, feedback_only")
    share_comment: Optional[str] = Field(None, max_length=500, description="分享备注，最多500字符")
    
    @validator('permission_level')
    def validate_permission_level(cls, v):
        allowed_levels = ['full_access', 'read_only', 'feedback_only']
        if v not in allowed_levels:
            raise ValueError(f'权限级别必须是以下之一: {", ".join(allowed_levels)}')
        return v
    
    @validator('shared_user_ids')
    def validate_shared_user_ids(cls, v):
        # 检查是否有重复的用户ID
        if len(v) != len(set(v)):
            raise ValueError('被分享用户ID不能重复')
        return v


class TaskShareUpdateRequest(BaseModel):
    """更新任务分享请求"""
    permission_level: str = Field(..., description="权限级别：full_access, read_only, feedback_only")
    share_comment: Optional[str] = Field(None, max_length=500, description="分享备注，最多500字符")
    
    @validator('permission_level')
    def validate_permission_level(cls, v):
        allowed_levels = ['full_access', 'read_only', 'feedback_only']
        if v not in allowed_levels:
            raise ValueError(f'权限级别必须是以下之一: {", ".join(allowed_levels)}')
        return v


class TaskShareResponse(BaseModel):
    """任务分享响应"""
    id: int
    task_id: int
    shared_user: UserResponse
    owner: UserResponse
    permission_level: str
    permission_name: str
    permission_description: str
    share_comment: Optional[str] = None
    created_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_task_share(cls, task_share, shared_user=None, owner=None):
        """从TaskShare模型创建响应对象"""
        from app.models.task_share import TaskShare
        
        return cls(
            id=task_share.id,
            task_id=task_share.task_id,
            shared_user=UserResponse.from_orm(shared_user or task_share.shared_user),
            owner=UserResponse.from_orm(owner or task_share.owner),
            permission_level=task_share.permission_level,
            permission_name=TaskShare.get_permission_name(task_share.permission_level),
            permission_description=TaskShare.get_permission_description(task_share.permission_level),
            share_comment=task_share.share_comment,
            created_at=task_share.created_at,
            is_active=task_share.is_active
        )


class SharedTaskResponse(BaseModel):
    """分享给我的任务响应"""
    task: TaskResponse
    share_info: TaskShareResponse
    shared_by: UserResponse
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_task_share(cls, task_share):
        """从TaskShare模型创建分享任务响应"""
        # 构建任务响应对象
        task_response = TaskResponse.from_task_with_relations(
            task_share.task,
            task_share.task.file_info,
            task_share.task.ai_model,
            task_share.owner,  # 使用分享者作为创建人信息
            0,  # issue_count - 这里可以根据需要优化
            0   # processed_issues
        )
        
        # 构建分享信息响应
        share_response = TaskShareResponse.from_task_share(
            task_share,
            task_share.shared_user,
            task_share.owner
        )
        
        return cls(
            task=task_response,
            share_info=share_response,
            shared_by=UserResponse.from_orm(task_share.owner)
        )


class UserSearchResponse(BaseModel):
    """用户搜索响应"""
    id: int
    uid: str
    display_name: str
    avatar_url: Optional[str] = None
    is_admin: bool
    is_system_admin: bool
    
    class Config:
        from_attributes = True


class TaskShareStatsResponse(BaseModel):
    """任务分享统计响应"""
    total_shares: int = Field(description="总分享数")
    active_shares: int = Field(description="活跃分享数")
    permission_breakdown: dict = Field(description="权限级别分布")
    
    class Config:
        from_attributes = True


class BatchShareResult(BaseModel):
    """批量分享结果"""
    success_count: int = Field(description="成功分享数量")
    failed_count: int = Field(description="失败分享数量")
    created_shares: List[TaskShareResponse] = Field(description="创建的分享记录")
    errors: List[str] = Field(default_factory=list, description="错误信息列表")
    
    class Config:
        from_attributes = True