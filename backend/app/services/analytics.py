"""
运营数据统计服务
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

from app.models import User, Task, FileInfo, AIOutput, Issue, TaskLog
from app.dto.analytics import (
    UserStatsResponse, TaskStatsResponse, SystemStatsResponse, 
    IssueStatsResponse, ErrorStatsResponse, OverallAnalyticsResponse
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """运营数据统计服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_stats(self, days: int = 30) -> UserStatsResponse:
        """获取用户统计数据"""
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)
        month_start = today_start - timedelta(days=30)
        
        # 基础用户统计
        total_users = self.db.query(User).count()
        
        # 新用户统计
        new_users_today = self.db.query(User).filter(
            User.created_at >= today_start
        ).count()
        
        new_users_this_week = self.db.query(User).filter(
            User.created_at >= week_start
        ).count()
        
        new_users_this_month = self.db.query(User).filter(
            User.created_at >= month_start
        ).count()
        
        # 活跃用户统计（基于最后登录时间）
        active_users_today = self.db.query(User).filter(
            User.last_login_at >= today_start
        ).count()
        
        active_users_this_week = self.db.query(User).filter(
            User.last_login_at >= week_start
        ).count()
        
        active_users_this_month = self.db.query(User).filter(
            User.last_login_at >= month_start
        ).count()
        
        # 管理员用户统计
        admin_users_count = self.db.query(User).filter(User.is_admin == True).count()
        system_admin_users_count = self.db.query(User).filter(User.is_system_admin == True).count()
        
        # 用户注册趋势（最近30天）
        registration_trend = self._get_daily_user_registration_trend(days)
        
        # 用户活跃趋势（最近30天）
        activity_trend = self._get_daily_user_activity_trend(days)
        
        return UserStatsResponse(
            total_users=total_users,
            new_users_today=new_users_today,
            new_users_this_week=new_users_this_week,
            new_users_this_month=new_users_this_month,
            active_users_today=active_users_today,
            active_users_this_week=active_users_this_week,
            active_users_this_month=active_users_this_month,
            admin_users_count=admin_users_count,
            system_admin_users_count=system_admin_users_count,
            user_registration_trend=registration_trend,
            user_activity_trend=activity_trend
        )
    
    def get_task_stats(self, days: int = 30) -> TaskStatsResponse:
        """获取任务统计数据"""
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)
        month_start = today_start - timedelta(days=30)
        
        # 基础任务统计
        total_tasks = self.db.query(Task).count()
        pending_tasks = self.db.query(Task).filter(Task.status == 'pending').count()
        processing_tasks = self.db.query(Task).filter(Task.status == 'processing').count()
        completed_tasks = self.db.query(Task).filter(Task.status == 'completed').count()
        failed_tasks = self.db.query(Task).filter(Task.status == 'failed').count()
        
        # 时间范围内任务统计
        tasks_today = self.db.query(Task).filter(Task.created_at >= today_start).count()
        tasks_this_week = self.db.query(Task).filter(Task.created_at >= week_start).count()
        tasks_this_month = self.db.query(Task).filter(Task.created_at >= month_start).count()
        
        # 平均处理时间
        avg_processing_time_result = self.db.query(func.avg(Task.processing_time)).filter(
            Task.processing_time.isnot(None)
        ).scalar()
        avg_processing_time = float(avg_processing_time_result) if avg_processing_time_result else None
        
        # 成功率
        success_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # 任务创建趋势
        creation_trend = self._get_daily_task_creation_trend(days)
        
        # 任务完成趋势
        completion_trend = self._get_daily_task_completion_trend(days)
        
        # 任务状态分布
        status_distribution = self._get_task_status_distribution()
        
        return TaskStatsResponse(
            total_tasks=total_tasks,
            pending_tasks=pending_tasks,
            processing_tasks=processing_tasks,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            tasks_today=tasks_today,
            tasks_this_week=tasks_this_week,
            tasks_this_month=tasks_this_month,
            avg_processing_time=avg_processing_time,
            success_rate=success_rate,
            task_creation_trend=creation_trend,
            task_completion_trend=completion_trend,
            task_status_distribution=status_distribution
        )
    
    def get_system_stats(self, days: int = 30) -> SystemStatsResponse:
        """获取系统资源统计数据"""
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)
        month_start = today_start - timedelta(days=30)
        
        # 文件统计
        total_files = self.db.query(FileInfo).count()
        total_file_size = self.db.query(func.sum(FileInfo.file_size)).scalar() or 0
        
        files_today = self.db.query(FileInfo).filter(FileInfo.created_at >= today_start).count()
        files_this_week = self.db.query(FileInfo).filter(FileInfo.created_at >= week_start).count()
        files_this_month = self.db.query(FileInfo).filter(FileInfo.created_at >= month_start).count()
        
        # AI调用统计
        total_ai_calls = self.db.query(AIOutput).count()
        ai_calls_today = self.db.query(AIOutput).filter(
            func.date(AIOutput.created_at) == today_start.date()
        ).count()
        ai_calls_this_week = self.db.query(AIOutput).filter(
            AIOutput.created_at >= week_start
        ).count()
        ai_calls_this_month = self.db.query(AIOutput).filter(
            AIOutput.created_at >= month_start
        ).count()
        
        # AI平均处理时间
        avg_ai_time_result = self.db.query(func.avg(AIOutput.processing_time)).filter(
            AIOutput.processing_time.isnot(None)
        ).scalar()
        avg_ai_processing_time = float(avg_ai_time_result) if avg_ai_time_result else None
        
        # 文件类型分布
        file_type_distribution = self._get_file_type_distribution()
        
        # AI模型使用统计
        ai_model_usage = self._get_ai_model_usage()
        
        return SystemStatsResponse(
            total_files=total_files,
            total_file_size=int(total_file_size),
            files_today=files_today,
            files_this_week=files_this_week,
            files_this_month=files_this_month,
            total_ai_calls=total_ai_calls,
            ai_calls_today=ai_calls_today,
            ai_calls_this_week=ai_calls_this_week,
            ai_calls_this_month=ai_calls_this_month,
            avg_ai_processing_time=avg_ai_processing_time,
            file_type_distribution=file_type_distribution,
            ai_model_usage=ai_model_usage
        )
    
    def get_issue_stats(self, days: int = 30) -> IssueStatsResponse:
        """获取问题统计数据"""
        total_issues = self.db.query(Issue).count()
        
        # 按严重程度分组
        issues_by_severity = self.db.query(
            Issue.severity, func.count(Issue.id)
        ).group_by(Issue.severity).all()
        
        severity_stats = [
            {"severity": severity, "count": count}
            for severity, count in issues_by_severity
        ]
        
        # 按问题类型分组
        issues_by_type = self.db.query(
            Issue.issue_type, func.count(Issue.id)
        ).group_by(Issue.issue_type).all()
        
        type_stats = [
            {"type": issue_type, "count": count}
            for issue_type, count in issues_by_type
        ]
        
        # 用户反馈统计
        feedback_stats = {}
        feedback_data = self.db.query(
            Issue.feedback_type, func.count(Issue.id)
        ).filter(Issue.feedback_type.isnot(None)).group_by(Issue.feedback_type).all()
        
        for feedback_type, count in feedback_data:
            feedback_stats[feedback_type] = count
        
        # 添加未反馈的统计
        total_issues = self.db.query(Issue).count()
        feedback_provided = sum(feedback_stats.values())
        feedback_stats['no_feedback'] = total_issues - feedback_provided
        
        # 满意度评分统计
        satisfaction_stats = {}
        # 平均满意度评分
        avg_satisfaction = self.db.query(func.avg(Issue.satisfaction_rating)).filter(
            Issue.satisfaction_rating.isnot(None)
        ).scalar()
        satisfaction_stats['average_rating'] = float(avg_satisfaction) if avg_satisfaction else 0.0
        
        # 按评分分布统计
        rating_distribution = self.db.query(
            Issue.satisfaction_rating, func.count(Issue.id)
        ).filter(Issue.satisfaction_rating.isnot(None)).group_by(Issue.satisfaction_rating).all()
        
        satisfaction_stats['rating_distribution'] = [
            {"rating": rating, "count": count} for rating, count in rating_distribution
        ]
        
        # 评分总数
        total_ratings = sum(count for rating, count in rating_distribution)
        satisfaction_stats['total_ratings'] = total_ratings
        
        # 高满意度比例 (4星及以上)
        high_satisfaction_count = self.db.query(Issue).filter(
            Issue.satisfaction_rating >= 4.0
        ).count()
        satisfaction_stats['high_satisfaction_rate'] = (
            (high_satisfaction_count / total_ratings * 100) if total_ratings > 0 else 0.0
        )
        
        # 低满意度比例 (2星及以下)
        low_satisfaction_count = self.db.query(Issue).filter(
            Issue.satisfaction_rating <= 2.0
        ).count()
        satisfaction_stats['low_satisfaction_rate'] = (
            (low_satisfaction_count / total_ratings * 100) if total_ratings > 0 else 0.0
        )
        
        # 最近的问题
        recent_issues = self.db.query(Issue).order_by(desc(Issue.id)).limit(10).all()
        recent_issues_data = [
            {
                "id": issue.id,
                "task_id": issue.task_id,
                "issue_type": issue.issue_type,
                "severity": issue.severity,
                "description": issue.description[:100] + "..." if len(issue.description) > 100 else issue.description,
                "created_at": issue.created_at
            }
            for issue in recent_issues
        ]
        
        # 问题趋势（简化版，按天统计）
        issue_trend = self._get_daily_issue_trend(days)
        
        return IssueStatsResponse(
            total_issues=total_issues,
            issues_by_severity=severity_stats,
            issues_by_type=type_stats,
            feedback_stats=feedback_stats,
            recent_issues=recent_issues_data,
            issue_trend=issue_trend,
            satisfaction_stats=satisfaction_stats  # 添加满意度统计
        )
    
    def get_error_stats(self, days: int = 30) -> ErrorStatsResponse:
        """获取错误统计数据"""
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)
        
        # 从失败的任务中获取错误统计
        total_errors = self.db.query(Task).filter(
            Task.status == 'failed',
            Task.error_message.isnot(None)
        ).count()
        
        errors_today = self.db.query(Task).filter(
            Task.status == 'failed',
            Task.error_message.isnot(None),
            Task.created_at >= today_start
        ).count()
        
        errors_this_week = self.db.query(Task).filter(
            Task.status == 'failed',
            Task.error_message.isnot(None),
            Task.created_at >= week_start
        ).count()
        
        # 错误类型分布（简化，基于错误消息关键词）
        error_types = []
        
        # 最近错误
        recent_errors_query = self.db.query(Task).filter(
            Task.status == 'failed',
            Task.error_message.isnot(None)
        ).order_by(desc(Task.created_at)).limit(10).all()
        
        recent_errors = [
            {
                "task_id": task.id,
                "title": task.title,
                "error_message": task.error_message[:200] + "..." if len(task.error_message) > 200 else task.error_message,
                "created_at": task.created_at.isoformat() if task.created_at else None
            }
            for task in recent_errors_query
        ]
        
        return ErrorStatsResponse(
            total_errors=total_errors,
            errors_today=errors_today,
            errors_this_week=errors_this_week,
            error_types=error_types,
            recent_errors=recent_errors
        )
    
    def get_overall_analytics(self, days: int = 30) -> OverallAnalyticsResponse:
        """获取综合运营数据"""
        return OverallAnalyticsResponse(
            user_stats=self.get_user_stats(days),
            task_stats=self.get_task_stats(days),
            system_stats=self.get_system_stats(days),
            issue_stats=self.get_issue_stats(days),
            error_stats=self.get_error_stats(days),
            last_updated=datetime.utcnow()
        )
    
    # 私有辅助方法
    def _get_daily_user_registration_trend(self, days: int) -> List[Dict[str, Any]]:
        """获取每日用户注册趋势"""
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days-1)
        
        # 查询每日注册数量
        daily_registrations = self.db.query(
            func.date(User.created_at).label('date'),
            func.count(User.id).label('count')
        ).filter(
            func.date(User.created_at) >= start_date,
            func.date(User.created_at) <= end_date
        ).group_by(func.date(User.created_at)).all()
        
        # 创建完整的日期序列
        result = []
        current_date = start_date
        registration_dict = {str(date): count for date, count in daily_registrations}
        
        while current_date <= end_date:
            result.append({
                "date": current_date.isoformat(),
                "count": registration_dict.get(str(current_date), 0)
            })
            current_date += timedelta(days=1)
        
        return result
    
    def _get_daily_user_activity_trend(self, days: int) -> List[Dict[str, Any]]:
        """获取每日用户活跃趋势"""
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days-1)
        
        # 查询每日活跃用户数量
        daily_activity = self.db.query(
            func.date(User.last_login_at).label('date'),
            func.count(User.id).label('count')
        ).filter(
            func.date(User.last_login_at) >= start_date,
            func.date(User.last_login_at) <= end_date
        ).group_by(func.date(User.last_login_at)).all()
        
        # 创建完整的日期序列
        result = []
        current_date = start_date
        activity_dict = {str(date): count for date, count in daily_activity}
        
        while current_date <= end_date:
            result.append({
                "date": current_date.isoformat(),
                "count": activity_dict.get(str(current_date), 0)
            })
            current_date += timedelta(days=1)
        
        return result
    
    def _get_daily_task_creation_trend(self, days: int) -> List[Dict[str, Any]]:
        """获取每日任务创建趋势"""
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days-1)
        
        daily_tasks = self.db.query(
            func.date(Task.created_at).label('date'),
            func.count(Task.id).label('count')
        ).filter(
            func.date(Task.created_at) >= start_date,
            func.date(Task.created_at) <= end_date
        ).group_by(func.date(Task.created_at)).all()
        
        result = []
        current_date = start_date
        task_dict = {str(date): count for date, count in daily_tasks}
        
        while current_date <= end_date:
            result.append({
                "date": current_date.isoformat(),
                "count": task_dict.get(str(current_date), 0)
            })
            current_date += timedelta(days=1)
        
        return result
    
    def _get_daily_task_completion_trend(self, days: int) -> List[Dict[str, Any]]:
        """获取每日任务完成趋势"""
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days-1)
        
        daily_completions = self.db.query(
            func.date(Task.completed_at).label('date'),
            func.count(Task.id).label('count')
        ).filter(
            Task.status == 'completed',
            func.date(Task.completed_at) >= start_date,
            func.date(Task.completed_at) <= end_date
        ).group_by(func.date(Task.completed_at)).all()
        
        result = []
        current_date = start_date
        completion_dict = {str(date): count for date, count in daily_completions}
        
        while current_date <= end_date:
            result.append({
                "date": current_date.isoformat(),
                "count": completion_dict.get(str(current_date), 0)
            })
            current_date += timedelta(days=1)
        
        return result
    
    def _get_task_status_distribution(self) -> List[Dict[str, Any]]:
        """获取任务状态分布"""
        status_data = self.db.query(
            Task.status, func.count(Task.id)
        ).group_by(Task.status).all()
        
        return [
            {"status": status, "count": count}
            for status, count in status_data
        ]
    
    def _get_file_type_distribution(self) -> List[Dict[str, Any]]:
        """获取文件类型分布"""
        file_type_data = self.db.query(
            FileInfo.file_type, func.count(FileInfo.id)
        ).group_by(FileInfo.file_type).all()
        
        return [
            {"file_type": file_type, "count": count}
            for file_type, count in file_type_data
        ]
    
    def _get_ai_model_usage(self) -> List[Dict[str, Any]]:
        """获取AI模型使用统计"""
        # 通过任务关联获取AI模型使用情况
        model_usage = self.db.query(
            Task.model_id, func.count(Task.id)
        ).group_by(Task.model_id).all()
        
        result = []
        for model_id, count in model_usage:
            # 获取模型名称
            from app.models.ai_model import AIModel
            model = self.db.query(AIModel).filter(AIModel.id == model_id).first()
            model_name = model.label if model else f"Model {model_id}"
            
            result.append({
                "model_id": model_id,
                "model_name": model_name,
                "usage_count": count
            })
        
        return result
    
    def _get_daily_issue_trend(self, days: int) -> List[Dict[str, Any]]:
        """获取每日问题趋势"""
        # 简化实现，返回空数据
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days-1)
        
        result = []
        current_date = start_date
        
        while current_date <= end_date:
            result.append({
                "date": current_date.isoformat(),
                "count": 0  # 简化实现
            })
            current_date += timedelta(days=1)
        
        return result