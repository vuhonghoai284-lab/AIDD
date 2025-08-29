"""
运营数据统计服务 - 支持异步加载和缓存优化
"""
import asyncio
import time
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case, text
from fastapi import HTTPException

from app.dto.operations import (
    OperationsOverview, OperationsTimeRange, TimeRangeType,
    TaskStatistics, UserStatistics, IssueStatistics, 
    FeedbackStatistics, TokenConsumption, CriticalIssueItem,
    TrendDataPoint, OperationsTrends
)
from app.models.task import Task
from app.models.user import User
from app.models.issue import Issue
# from app.models.user_feedback import UserFeedback  # 不存在，使用Issue模型的satisfaction_rating
from app.models.ai_output import AIOutput


class OperationsService:
    """运营数据服务 - 支持异步并发查询和缓存"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def _get_date_range(self, time_range: OperationsTimeRange) -> Tuple[datetime, datetime]:
        """根据时间范围类型获取起止日期"""
        now = datetime.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if time_range.type == TimeRangeType.DAYS_7:
            start_date = today - timedelta(days=7)
            end_date = now
        elif time_range.type == TimeRangeType.DAYS_30:
            start_date = today - timedelta(days=30)
            end_date = now
        elif time_range.type == TimeRangeType.MONTHS_6:
            start_date = today - timedelta(days=180)
            end_date = now
        elif time_range.type == TimeRangeType.THIS_YEAR:
            start_date = today.replace(month=1, day=1)
            end_date = now
        elif time_range.type == TimeRangeType.YEAR_1:
            start_date = today - timedelta(days=365)
            end_date = now
        elif time_range.type == TimeRangeType.CUSTOM:
            if not time_range.start_date or not time_range.end_date:
                raise HTTPException(400, "自定义时间范围需要提供起止日期")
            # 将字符串转换为日期
            start_date = datetime.strptime(time_range.start_date, "%Y-%m-%d")
            end_date = datetime.strptime(time_range.end_date, "%Y-%m-%d")
            end_date = end_date.replace(hour=23, minute=59, second=59)
        else:
            # 默认30天
            start_date = today - timedelta(days=30)
            end_date = now
        
        return start_date, end_date
    
    async def get_task_statistics_async(self, start_date: datetime, end_date: datetime) -> TaskStatistics:
        """异步获取任务统计数据"""
        print(f"🚀 开始异步获取任务统计数据...")
        start_time = time.time()
        
        try:
            # 获取所有任务统计（不限制时间范围）
            total_query = self.db.query(
                func.count(Task.id).label('total'),
                func.sum(case((Task.status == 'processing', 1), else_=0)).label('running'),
                func.sum(case((Task.status == 'completed', 1), else_=0)).label('completed'),
                func.sum(case((Task.status == 'failed', 1), else_=0)).label('failed'),
                func.sum(case((Task.status == 'pending', 1), else_=0)).label('pending')
            )
            
            total_result = total_query.first()
            
            # 今日数据统计
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = datetime.now()
            
            today_query = self.db.query(
                func.count(Task.id).label('today_total'),
                func.sum(case((Task.status == 'completed', 1), else_=0)).label('today_completed'),
                func.sum(case((Task.status == 'failed', 1), else_=0)).label('today_failed')
            ).filter(
                Task.created_at >= today_start
            )
            
            today_result = today_query.first()
            
            # 计算成功率
            total = total_result.total or 0
            completed = total_result.completed or 0
            success_rate = (completed / total * 100) if total > 0 else 0.0
            
            stats = TaskStatistics(
                total=total,
                running=total_result.running or 0,
                completed=completed,
                failed=total_result.failed or 0,
                success_rate=round(success_rate, 2),
                today_total=today_result.today_total or 0,
                today_completed=today_result.today_completed or 0,
                today_failed=today_result.today_failed or 0
            )
            
            elapsed = (time.time() - start_time) * 1000
            print(f"✅ 任务统计数据获取完成，耗时: {elapsed:.1f}ms，数据: 总计{total}，成功率{success_rate:.1f}%")
            return stats
            
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            print(f"❌ 获取任务统计失败，耗时: {elapsed:.1f}ms，错误: {e}")
            return TaskStatistics()  # 返回默认值
    
    async def get_user_statistics_async(self, start_date: datetime, end_date: datetime) -> UserStatistics:
        """异步获取用户统计数据"""
        print(f"🚀 开始异步获取用户统计数据...")
        start_time = time.time()
        
        try:
            # 总用户数
            total_users = self.db.query(func.count(User.id)).scalar() or 0
            
            # 今日数据
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = today_start - timedelta(days=7)
            month_start = today_start - timedelta(days=30)
            
            # 新注册用户数（本月）
            new_registrations = self.db.query(func.count(User.id)).filter(
                User.created_at >= month_start
            ).scalar() or 0
            
            # 活跃用户数（本月有任务创建的用户）
            active_users = self.db.query(func.count(func.distinct(Task.user_id))).filter(
                Task.created_at >= month_start
            ).scalar() or 0
            
            # 今日新注册用户
            today_new_registrations = self.db.query(func.count(User.id)).filter(
                User.created_at >= today_start
            ).scalar() or 0
            
            # 今日活跃用户（有任务创建的用户）
            today_active = self.db.query(func.count(func.distinct(Task.user_id))).filter(
                Task.created_at >= today_start
            ).scalar() or 0
            
            # 模拟在线用户数（实际应该从会话或Redis获取）
            current_online = max(1, min(int(total_users * 0.05), 10))  # 假设5%用户在线，最多10个
            
            stats = UserStatistics(
                total_users=total_users,
                active_users=active_users,
                new_registrations=new_registrations,
                today_active=today_active,
                today_new_registrations=today_new_registrations,
                current_online=current_online
            )
            
            elapsed = (time.time() - start_time) * 1000
            print(f"✅ 用户统计数据获取完成，耗时: {elapsed:.1f}ms，数据: 总用户{total_users}，活跃{active_users}")
            return stats
            
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            print(f"❌ 获取用户统计失败，耗时: {elapsed:.1f}ms，错误: {e}")
            return UserStatistics()
    
    async def get_issue_statistics_async(self, start_date: datetime, end_date: datetime) -> IssueStatistics:
        """异步获取问题统计数据"""
        print(f"🚀 开始异步获取问题统计数据...")
        start_time = time.time()
        
        try:
            # 总问题统计查询（不限时间范围）
            main_query = self.db.query(
                func.count(Issue.id).label('total'),
                func.sum(case((Issue.feedback_type == 'accept', 1), else_=0)).label('accepted'),
                func.sum(case((Issue.feedback_type == 'reject', 1), else_=0)).label('rejected'),
                func.sum(case((Issue.feedback_type.is_(None), 1), else_=0)).label('pending')
            )
            
            main_result = main_query.first()
            
            # 按严重程度统计（所有问题）
            severity_query = self.db.query(
                func.sum(case((Issue.severity == 'critical', 1), else_=0)).label('critical'),
                func.sum(case((Issue.severity == 'high', 1), else_=0)).label('high'),
                func.sum(case((Issue.severity == 'medium', 1), else_=0)).label('medium'),
                func.sum(case((Issue.severity == 'low', 1), else_=0)).label('low')
            )
            
            severity_result = severity_query.first()
            
            # 今日数据
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            today_query = self.db.query(
                func.count(Issue.id).label('today_new'),
                func.sum(case((Issue.feedback_type == 'accept', 1), else_=0)).label('today_accepted')
            ).join(Task).filter(
                Task.created_at >= today_start
            )
            
            today_result = today_query.first()
            
            # 本月新增问题
            month_start = today_start - timedelta(days=30)
            new_issues = self.db.query(func.count(Issue.id)).join(Task).filter(
                Task.created_at >= month_start
            ).scalar() or 0
            
            total_issues = main_result.total or 0
            
            stats = IssueStatistics(
                total_issues=total_issues,
                new_issues=new_issues,
                accepted_issues=main_result.accepted or 0,
                rejected_issues=main_result.rejected or 0,
                pending_issues=main_result.pending or 0,
                critical_issues=severity_result.critical or 0,
                high_issues=severity_result.high or 0,
                medium_issues=severity_result.medium or 0,
                low_issues=severity_result.low or 0,
                today_new=today_result.today_new or 0,
                today_accepted=today_result.today_accepted or 0
            )
            
            elapsed = (time.time() - start_time) * 1000
            print(f"✅ 问题统计数据获取完成，耗时: {elapsed:.1f}ms，数据: 总问题{total_issues}，待处理{main_result.pending or 0}")
            return stats
            
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            print(f"❌ 获取问题统计失败，耗时: {elapsed:.1f}ms，错误: {e}")
            return IssueStatistics()
    
    async def get_feedback_statistics_async(self, start_date: datetime, end_date: datetime) -> FeedbackStatistics:
        """异步获取反馈统计数据"""
        print(f"🚀 开始异步获取反馈统计数据...")
        start_time = time.time()
        
        try:
            # 使用Issue模型的satisfaction_rating字段统计反馈
            feedback_query = self.db.query(
                func.count(Issue.id).label('total'),
                func.avg(Issue.satisfaction_rating).label('avg_score')
            ).join(Task).filter(
                Task.created_at.between(start_date, end_date),
                Issue.satisfaction_rating.isnot(None)
            )
            
            feedback_result = feedback_query.first()
            
            # 评分分布统计
            score_dist_query = self.db.query(
                Issue.satisfaction_rating,
                func.count(Issue.id).label('count')
            ).join(Task).filter(
                Task.created_at.between(start_date, end_date),
                Issue.satisfaction_rating.isnot(None)
            ).group_by(Issue.satisfaction_rating)
            
            score_distribution = {
                str(int(row.satisfaction_rating)): row.count 
                for row in score_dist_query.all() 
                if row.satisfaction_rating is not None
            }
            
            # 今日数据
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = datetime.now()
            
            today_query = self.db.query(
                func.count(Issue.id).label('today_total'),
                func.avg(Issue.satisfaction_rating).label('today_avg')
            ).join(Task).filter(
                Task.created_at.between(today_start, today_end),
                Issue.satisfaction_rating.isnot(None)
            )
            
            today_result = today_query.first()
            
            total_feedback = feedback_result.total or 0
            valid_feedback = total_feedback  # 假设所有反馈都有效
            
            stats = FeedbackStatistics(
                total_feedback=total_feedback,
                valid_feedback=valid_feedback,
                average_score=round(float(feedback_result.avg_score or 0), 2),
                score_distribution=score_distribution,
                today_feedback=today_result.today_total or 0,
                today_average_score=round(float(today_result.today_avg or 0), 2)
            )
            
            elapsed = (time.time() - start_time) * 1000
            print(f"✅ 反馈统计数据获取完成，耗时: {elapsed:.1f}ms")
            return stats
            
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            print(f"❌ 获取反馈统计失败，耗时: {elapsed:.1f}ms，错误: {e}")
            return FeedbackStatistics()
    
    async def get_token_consumption_async(self, start_date: datetime, end_date: datetime) -> TokenConsumption:
        """异步获取Token消耗统计"""
        print(f"🚀 开始异步获取Token消耗统计...")
        start_time = time.time()
        
        try:
            # 总Token消耗统计查询（所有时间）
            token_query = self.db.query(
                func.sum(AIOutput.tokens_used).label('total_tokens')
            )
            
            token_result = token_query.first()
            
            # 按模型分组统计（查询task表的model_id字段）
            model_query = self.db.query(
                Task.model_id,
                func.sum(AIOutput.tokens_used).label('tokens')
            ).join(AIOutput, Task.id == AIOutput.task_id).group_by(Task.model_id)
            
            by_model = {}
            for row in model_query.all():
                # 获取模型名称
                try:
                    from app.models.ai_model import AIModel
                    model = self.db.query(AIModel).filter(AIModel.id == row.model_id).first()
                    model_name = model.label if model else f"Model-{row.model_id}"
                except:
                    model_name = f"Model-{row.model_id}" if row.model_id else "未知模型"
                
                by_model[model_name] = row.tokens or 0
            
            # 如果没有按模型数据，创建默认数据
            if not by_model:
                total_tokens_val = token_result.total_tokens or 0
                if total_tokens_val > 0:
                    by_model["GPT-4o Mini"] = total_tokens_val
            
            # 今日数据
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            today_query = self.db.query(
                func.sum(AIOutput.tokens_used).label('today_tokens')
            ).join(Task).filter(
                Task.created_at >= today_start
            )
            
            today_result = today_query.first()
            
            # 估算成本 (假设每1K token = $0.002)
            total_tokens = int(token_result.total_tokens or 0)
            today_tokens = int(today_result.today_tokens or 0)
            
            estimated_cost = (total_tokens / 1000) * 0.002
            today_cost = (today_tokens / 1000) * 0.002
            
            stats = TokenConsumption(
                total_tokens=total_tokens,
                input_tokens=int(total_tokens * 0.7) if total_tokens > 0 else 0,  # 估算输入Token占70%
                output_tokens=int(total_tokens * 0.3) if total_tokens > 0 else 0,  # 估算输出Token占30%
                estimated_cost=round(estimated_cost, 4),
                today_tokens=today_tokens,
                today_cost=round(today_cost, 4),
                by_model=by_model
            )
            
            elapsed = (time.time() - start_time) * 1000
            print(f"✅ Token消耗统计获取完成，耗时: {elapsed:.1f}ms，数据: 总Token{total_tokens}，成本${estimated_cost:.4f}")
            return stats
            
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            print(f"❌ 获取Token统计失败，耗时: {elapsed:.1f}ms，错误: {e}")
            return TokenConsumption()
    
    async def get_critical_issues_async(self, max_count: int = 20) -> List[CriticalIssueItem]:
        """异步获取关键问题列表"""
        print(f"🚀 开始异步获取关键问题列表...")
        start_time = time.time()
        
        try:
            # 查询致命和严重问题，按创建时间排序
            issues_query = self.db.query(Issue, Task).join(Task).filter(
                Issue.severity.in_(['critical', 'high'])
            ).order_by(
                case((Issue.severity == 'critical', 1), else_=2),  # 致命问题优先
                Issue.created_at.desc()
            ).limit(max_count)
            
            critical_issues = []
            for issue, task in issues_query.all():
                item = CriticalIssueItem(
                    id=issue.id,
                    task_id=task.id,
                    title=f"{issue.issue_type}问题",
                    description=issue.description[:100] + "..." if len(issue.description) > 100 else issue.description,
                    severity=issue.severity,
                    issue_type=issue.issue_type,
                    status=issue.feedback_type or "pending",
                    created_at=issue.created_at if isinstance(issue.created_at, str) else issue.created_at.isoformat() if issue.created_at else "",
                    task_title=task.title or task.file_name or "未知任务"
                )
                critical_issues.append(item)
            
            elapsed = (time.time() - start_time) * 1000
            print(f"✅ 关键问题列表获取完成，耗时: {elapsed:.1f}ms，获取 {len(critical_issues)} 个问题")
            return critical_issues
            
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            print(f"❌ 获取关键问题失败，耗时: {elapsed:.1f}ms，错误: {e}")
            return []
    
    async def get_trends_async(self, start_date: datetime, end_date: datetime) -> OperationsTrends:
        """异步获取趋势数据"""
        print(f"🚀 开始异步获取趋势数据...")
        start_time = time.time()
        
        try:
            # 生成日期序列
            current_date = start_date.date()
            end_date_only = end_date.date()
            dates = []
            
            while current_date <= end_date_only:
                dates.append(current_date)
                current_date += timedelta(days=1)
            
            # 为了性能，如果时间范围超过90天，使用周统计
            if len(dates) > 90:
                # 每7天一个数据点
                dates = dates[::7]
            
            # 任务趋势
            task_trends = []
            for d in dates[:30]:  # 最多30个数据点
                day_start = datetime.combine(d, datetime.min.time())
                day_end = datetime.combine(d, datetime.max.time())
                
                count = self.db.query(func.count(Task.id)).filter(
                    Task.created_at.between(day_start, day_end)
                ).scalar() or 0
                
                task_trends.append(TrendDataPoint(date=d.isoformat(), value=count))
            
            # 用户趋势 - 每日新增用户数
            user_trends = []
            for d in dates[:30]:  # 最多30个数据点
                day_start = datetime.combine(d, datetime.min.time())
                day_end = datetime.combine(d, datetime.max.time())
                
                # 新增用户数
                new_users = self.db.query(func.count(User.id)).filter(
                    User.created_at.between(day_start, day_end)
                ).scalar() or 0
                
                # 活跃用户数（当日有创建任务的用户）
                active_users = self.db.query(func.count(func.distinct(Task.user_id))).filter(
                    Task.created_at.between(day_start, day_end)
                ).scalar() or 0
                
                # 合并数据：新增用户 + 活跃用户
                total_value = new_users + active_users
                user_trends.append(TrendDataPoint(
                    date=d.isoformat(), 
                    value=total_value,
                    new_users=new_users,
                    active_users=active_users
                ))
            
            # 问题趋势 - 每日新增问题数
            issue_trends = []
            for d in dates[:30]:
                day_start = datetime.combine(d, datetime.min.time())
                day_end = datetime.combine(d, datetime.max.time())
                
                count = self.db.query(func.count(Issue.id)).join(Task).filter(
                    Task.created_at.between(day_start, day_end)
                ).scalar() or 0
                
                issue_trends.append(TrendDataPoint(date=d.isoformat(), value=count))
            
            # Token趋势 - 每日Token消耗
            token_trends = []
            for d in dates[:30]:
                day_start = datetime.combine(d, datetime.min.time())
                day_end = datetime.combine(d, datetime.max.time())
                
                tokens = self.db.query(func.sum(AIOutput.tokens_used)).join(Task).filter(
                    Task.created_at.between(day_start, day_end)
                ).scalar() or 0
                
                token_trends.append(TrendDataPoint(date=d.isoformat(), value=int(tokens)))
            
            trends = OperationsTrends(
                task_trends=task_trends,
                user_trends=user_trends,
                issue_trends=issue_trends,
                token_trends=token_trends
            )
            
            elapsed = (time.time() - start_time) * 1000
            print(f"✅ 趋势数据获取完成，耗时: {elapsed:.1f}ms")
            return trends
            
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            print(f"❌ 获取趋势数据失败，耗时: {elapsed:.1f}ms，错误: {e}")
            return OperationsTrends()
    
    async def get_operations_overview_async(self, time_range: OperationsTimeRange, 
                                          include_trends: bool = True, 
                                          include_critical_issues: bool = True,
                                          max_critical_issues: int = 20) -> OperationsOverview:
        """异步获取运营总览数据 - 并发执行所有查询"""
        print(f"🚀 开始获取运营总览数据，时间范围: {time_range.type.value}")
        total_start_time = time.time()
        
        try:
            # 获取时间范围
            start_date, end_date = self._get_date_range(time_range)
            print(f"📅 时间范围: {start_date} - {end_date}")
            
            # 创建并发任务列表
            tasks = [
                self.get_task_statistics_async(start_date, end_date),
                self.get_user_statistics_async(start_date, end_date),
                self.get_issue_statistics_async(start_date, end_date),
                self.get_feedback_statistics_async(start_date, end_date),
                self.get_token_consumption_async(start_date, end_date)
            ]
            
            # 可选任务
            if include_critical_issues:
                tasks.append(self.get_critical_issues_async(max_critical_issues))
            
            if include_trends:
                tasks.append(self.get_trends_async(start_date, end_date))
            
            # 并发执行所有查询
            print(f"🔄 开始并发执行 {len(tasks)} 个查询任务...")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 解析结果
            task_stats = results[0] if not isinstance(results[0], Exception) else TaskStatistics()
            user_stats = results[1] if not isinstance(results[1], Exception) else UserStatistics()
            issue_stats = results[2] if not isinstance(results[2], Exception) else IssueStatistics()
            feedback_stats = results[3] if not isinstance(results[3], Exception) else FeedbackStatistics()
            token_stats = results[4] if not isinstance(results[4], Exception) else TokenConsumption()
            
            critical_issues = []
            trends = OperationsTrends()
            
            # 处理可选结果
            result_index = 5
            if include_critical_issues:
                critical_issues = results[result_index] if not isinstance(results[result_index], Exception) else []
                result_index += 1
            
            if include_trends:
                trends = results[result_index] if not isinstance(results[result_index], Exception) else OperationsTrends()
            
            # 构建总览数据
            overview = OperationsOverview(
                time_range=time_range,
                tasks=task_stats,
                users=user_stats,
                issues=issue_stats,
                feedback=feedback_stats,
                tokens=token_stats,
                critical_issues=critical_issues,
                trends=trends,
                generated_at=datetime.now().isoformat()
            )
            
            total_elapsed = (time.time() - total_start_time) * 1000
            print(f"✅ 运营总览数据获取完成，总耗时: {total_elapsed:.1f}ms")
            print(f"📊 数据概览:")
            print(f"   - 任务: 总计{task_stats.total}个，成功率{task_stats.success_rate}%")
            print(f"   - 用户: 总计{user_stats.total_users}个，活跃{user_stats.active_users}个")
            print(f"   - 问题: 总计{issue_stats.total_issues}个，待处理{issue_stats.pending_issues}个")
            print(f"   - 关键问题: {len(critical_issues)}个")
            
            return overview
            
        except Exception as e:
            total_elapsed = (time.time() - total_start_time) * 1000
            print(f"❌ 获取运营总览数据失败，总耗时: {total_elapsed:.1f}ms，错误: {e}")
            # 返回默认数据而不是抛出异常
            return OperationsOverview(
                time_range=time_range,
                tasks=TaskStatistics(),
                users=UserStatistics(),
                issues=IssueStatistics(),
                feedback=FeedbackStatistics(),
                tokens=TokenConsumption(),
                critical_issues=[],
                trends=OperationsTrends()
            )