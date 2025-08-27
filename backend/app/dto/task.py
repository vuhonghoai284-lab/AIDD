"""
任务相关的DTO（数据传输对象）
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


class TaskCreate(BaseModel):
    """创建任务请求"""
    title: Optional[str] = None
    ai_model_index: Optional[int] = None
    
    model_config = ConfigDict(protected_namespaces=())
    

class TaskResponse(BaseModel):
    """任务响应"""
    id: int
    title: str
    file_name: str
    file_size: int
    file_type: str
    status: str
    progress: float
    issue_count: Optional[int] = None
    processed_issues: Optional[int] = None
    ai_model_label: Optional[str] = None
    document_chars: Optional[int] = None
    processing_time: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    user_id: Optional[int] = None
    file_id: Optional[int] = None
    ai_model_id: Optional[int] = None
    created_by_name: Optional[str] = None
    created_by_type: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
    
    @classmethod
    def from_task_with_relations(cls, task, file_info=None, ai_model=None, user_info=None, issue_count: int = 0, processed_issues: int = 0):
        """从Task模型及其关联对象构建响应"""
        # 确定创建人名称和类型
        created_by_name = None
        created_by_type = None
        
        if user_info:
            created_by_name = user_info.display_name or user_info.uid
            if user_info.is_system_admin:
                created_by_type = 'system_admin'
            elif user_info.is_admin:
                created_by_type = 'admin'
            else:
                created_by_type = 'normal_user'
        
        return cls(
            id=task.id,
            title=task.title,
            file_name=file_info.original_name if file_info else 'Unknown',
            file_size=file_info.file_size if file_info else 0,
            file_type=file_info.file_type if file_info else 'unknown',
            status=task.status,
            progress=task.progress,
            issue_count=issue_count,
            processed_issues=processed_issues,
            ai_model_label=ai_model.label if ai_model else 'Unknown',
            document_chars=file_info.document_chars if file_info else None,
            processing_time=task.processing_time,
            created_at=task.created_at,
            completed_at=task.completed_at,
            error_message=task.error_message,
            user_id=task.user_id,
            file_id=task.file_id,
            ai_model_id=task.model_id,
            created_by_name=created_by_name,
            created_by_type=created_by_type
        )
        

class TaskDetail(BaseModel):
    """任务详情（懒加载模式）"""
    task: TaskResponse
    issue_summary: dict = {}  # 问题摘要统计信息，替代完整的问题列表
    ai_output_summary: dict = {}  # AI输出摘要统计信息
    
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


from app.dto.issue import IssueResponse
TaskDetail.model_rebuild()