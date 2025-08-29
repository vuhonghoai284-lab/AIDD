"""
运营数据传输对象 - 简化版本
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class TimeRangeType(str, Enum):
    """时间范围类型枚举"""
    DAYS_7 = "7days"
    DAYS_30 = "30days"
    MONTHS_6 = "6months" 
    THIS_YEAR = "this_year"
    YEAR_1 = "1year"
    CUSTOM = "custom"


class OperationsTimeRange(BaseModel):
    """运营数据时间范围"""
    type: TimeRangeType = TimeRangeType.DAYS_30
    start_date: Optional[str] = None  # 使用字符串避免序列化问题
    end_date: Optional[str] = None


class TaskStatistics(BaseModel):
    """任务统计数据"""
    total: int = Field(default=0, description="总任务数")
    running: int = Field(default=0, description="运行中任务数")
    completed: int = Field(default=0, description="完成任务数")
    failed: int = Field(default=0, description="失败任务数")
    success_rate: float = Field(default=0.0, description="成功率百分比")
    
    # 今日数据
    today_total: int = Field(default=0, description="今日新增任务")
    today_completed: int = Field(default=0, description="今日完成任务")
    today_failed: int = Field(default=0, description="今日失败任务")


class UserStatistics(BaseModel):
    """用户统计数据"""
    total_users: int = Field(default=0, description="总用户数")
    active_users: int = Field(default=0, description="活跃用户数")
    new_registrations: int = Field(default=0, description="新注册用户数")
    
    # 今日数据
    today_active: int = Field(default=0, description="今日活跃用户")
    today_new_registrations: int = Field(default=0, description="今日新注册")
    
    # 在线统计
    current_online: int = Field(default=0, description="当前在线用户")


class IssueStatistics(BaseModel):
    """问题统计数据"""
    total_issues: int = Field(default=0, description="总问题数")
    new_issues: int = Field(default=0, description="新增问题数") 
    accepted_issues: int = Field(default=0, description="接受的问题数")
    rejected_issues: int = Field(default=0, description="拒绝的问题数")
    pending_issues: int = Field(default=0, description="待处理问题数")
    
    # 按严重程度统计
    critical_issues: int = Field(default=0, description="致命问题数")
    high_issues: int = Field(default=0, description="严重问题数")
    medium_issues: int = Field(default=0, description="中等问题数")
    low_issues: int = Field(default=0, description="轻微问题数")
    
    # 今日数据
    today_new: int = Field(default=0, description="今日新增问题")
    today_accepted: int = Field(default=0, description="今日接受问题")


class FeedbackStatistics(BaseModel):
    """用户反馈统计"""
    total_feedback: int = Field(default=0, description="总反馈数")
    valid_feedback: int = Field(default=0, description="有效反馈数")
    average_score: float = Field(default=0.0, description="平均评分")
    
    # 评分分布
    score_distribution: Dict[str, int] = Field(default_factory=dict, description="评分分布")
    
    # 今日数据
    today_feedback: int = Field(default=0, description="今日新增反馈")
    today_average_score: float = Field(default=0.0, description="今日平均评分")


class TokenConsumption(BaseModel):
    """Token消耗统计"""
    total_tokens: int = Field(default=0, description="总Token消耗")
    input_tokens: int = Field(default=0, description="输入Token数")
    output_tokens: int = Field(default=0, description="输出Token数")
    estimated_cost: float = Field(default=0.0, description="预估成本(USD)")
    
    # 今日数据
    today_tokens: int = Field(default=0, description="今日Token消耗")
    today_cost: float = Field(default=0.0, description="今日预估成本")
    
    # 按模型统计
    by_model: Dict[str, int] = Field(default_factory=dict, description="按模型分组统计")


class CriticalIssueItem(BaseModel):
    """关键问题项目"""
    id: int = Field(description="问题ID")
    task_id: int = Field(description="关联任务ID")
    title: str = Field(description="问题标题")
    description: str = Field(description="问题描述")
    severity: str = Field(description="严重程度")
    issue_type: str = Field(description="问题类型")
    status: str = Field(description="处理状态")
    created_at: str = Field(description="创建时间")  # 使用字符串避免序列化问题
    task_title: str = Field(description="任务标题")


class TrendDataPoint(BaseModel):
    """趋势数据点"""
    date: str = Field(description="日期")  # 使用字符串避免序列化问题
    value: int = Field(description="数值")
    new_users: Optional[int] = Field(default=None, description="新增用户数")
    active_users: Optional[int] = Field(default=None, description="活跃用户数")


class OperationsTrends(BaseModel):
    """运营趋势数据"""
    task_trends: List[TrendDataPoint] = Field(default_factory=list, description="任务趋势")
    user_trends: List[TrendDataPoint] = Field(default_factory=list, description="用户趋势")
    issue_trends: List[TrendDataPoint] = Field(default_factory=list, description="问题趋势")
    token_trends: List[TrendDataPoint] = Field(default_factory=list, description="Token消耗趋势")


class OperationsOverview(BaseModel):
    """运营总览数据"""
    time_range: OperationsTimeRange = Field(description="时间范围")
    
    # 核心统计数据
    tasks: TaskStatistics = Field(default_factory=TaskStatistics, description="任务统计")
    users: UserStatistics = Field(default_factory=UserStatistics, description="用户统计")
    issues: IssueStatistics = Field(default_factory=IssueStatistics, description="问题统计")
    feedback: FeedbackStatistics = Field(default_factory=FeedbackStatistics, description="反馈统计")
    tokens: TokenConsumption = Field(default_factory=TokenConsumption, description="Token消耗")
    
    # 关键问题列表（最多20个）
    critical_issues: List[CriticalIssueItem] = Field(default_factory=list, description="关键问题列表")
    
    # 趋势数据
    trends: OperationsTrends = Field(default_factory=OperationsTrends, description="趋势数据")
    
    # 数据生成时间
    generated_at: Optional[str] = Field(default=None, description="数据生成时间")


class OperationsRequest(BaseModel):
    """运营数据请求参数"""
    time_range: OperationsTimeRange = Field(description="时间范围")
    include_trends: bool = Field(default=True, description="是否包含趋势数据")
    include_critical_issues: bool = Field(default=True, description="是否包含关键问题")
    max_critical_issues: int = Field(default=20, description="最大关键问题数量")