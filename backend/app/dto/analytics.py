"""
运营数据统计DTO
"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime


class UserStatsResponse(BaseModel):
    """用户统计响应"""
    total_users: int
    new_users_today: int
    new_users_this_week: int
    new_users_this_month: int
    active_users_today: int
    active_users_this_week: int
    active_users_this_month: int
    admin_users_count: int
    system_admin_users_count: int
    user_registration_trend: List[Dict[str, Any]]  # 每日注册趋势
    user_activity_trend: List[Dict[str, Any]]      # 每日活跃趋势


class TaskStatsResponse(BaseModel):
    """任务统计响应"""
    total_tasks: int
    pending_tasks: int
    processing_tasks: int
    completed_tasks: int
    failed_tasks: int
    tasks_today: int
    tasks_this_week: int
    tasks_this_month: int
    avg_processing_time: Optional[float]
    success_rate: float
    task_creation_trend: List[Dict[str, Any]]      # 每日任务创建趋势
    task_completion_trend: List[Dict[str, Any]]    # 每日任务完成趋势
    task_status_distribution: List[Dict[str, Any]] # 任务状态分布


class SystemStatsResponse(BaseModel):
    """系统资源统计响应"""
    total_files: int
    total_file_size: int  # 字节
    files_today: int
    files_this_week: int
    files_this_month: int
    total_ai_calls: int
    ai_calls_today: int
    ai_calls_this_week: int
    ai_calls_this_month: int
    avg_ai_processing_time: Optional[float]
    file_type_distribution: List[Dict[str, Any]]   # 文件类型分布
    ai_model_usage: List[Dict[str, Any]]           # AI模型使用统计


class IssueStatsResponse(BaseModel):
    """问题统计响应"""
    total_issues: int
    issues_by_severity: List[Dict[str, Any]]       # 按严重程度分组
    issues_by_type: List[Dict[str, Any]]           # 按问题类型分组
    feedback_stats: Dict[str, int]                 # 用户反馈统计
    recent_issues: List[Dict[str, Any]]            # 最近的问题
    issue_trend: List[Dict[str, Any]]              # 问题发现趋势
    satisfaction_stats: Dict[str, Any]             # 用户满意度统计


class ErrorStatsResponse(BaseModel):
    """错误统计响应"""
    total_errors: int
    errors_today: int
    errors_this_week: int
    error_types: List[Dict[str, Any]]              # 错误类型分布
    recent_errors: List[Dict[str, Any]]            # 最近的错误


class OverallAnalyticsResponse(BaseModel):
    """综合运营数据响应"""
    user_stats: UserStatsResponse
    task_stats: TaskStatsResponse
    system_stats: SystemStatsResponse
    issue_stats: IssueStatsResponse
    error_stats: ErrorStatsResponse
    last_updated: datetime


class DateRangeRequest(BaseModel):
    """日期范围请求"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    days: Optional[int] = 30  # 默认30天