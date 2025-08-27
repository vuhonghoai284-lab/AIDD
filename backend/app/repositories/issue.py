"""
问题数据访问层
"""
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from app.models import Issue
from app.dto.pagination import PaginationParams


class IssueRepository:
    """问题仓库"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, **kwargs) -> Issue:
        """创建问题"""
        # 验证task_id是否有效（如果提供）
        task_id = kwargs.get('task_id')
        if task_id:
            from app.models.task import Task
            task_exists = self.db.query(Task.id).filter(Task.id == task_id).first()
            if not task_exists:
                raise ValueError(f"task_id {task_id} 不存在，无法创建问题记录")
        
        issue = Issue(**kwargs)
        self.db.add(issue)
        self.db.commit()
        self.db.refresh(issue)
        return issue
    
    def bulk_create(self, issues_data: List[dict]) -> List[Issue]:
        """批量创建问题"""
        # 验证所有task_id是否有效
        task_ids = {data.get('task_id') for data in issues_data if data.get('task_id')}
        if task_ids:
            from app.models.task import Task
            existing_task_ids = set(
                tid for tid, in self.db.query(Task.id).filter(Task.id.in_(task_ids)).all()
            )
            invalid_task_ids = task_ids - existing_task_ids
            if invalid_task_ids:
                raise ValueError(f"task_id {invalid_task_ids} 不存在，无法批量创建问题记录")
        
        issues = [Issue(**data) for data in issues_data]
        self.db.add_all(issues)
        self.db.commit()
        return issues
    
    def get_by_id(self, issue_id: int) -> Optional[Issue]:
        """根据ID获取问题"""
        return self.db.query(Issue).filter(Issue.id == issue_id).first()
    
    def get_by_task_id(self, task_id: int) -> List[Issue]:
        """获取任务的所有问题"""
        return self.db.query(Issue).filter(Issue.task_id == task_id).all()
    
    def update_feedback(self, issue_id: int, feedback_type: Optional[str], comment: Optional[str] = None) -> Optional[Issue]:
        """更新问题反馈"""
        issue = self.get_by_id(issue_id)
        if issue:
            # 如果feedback_type为空字符串或None，清除反馈
            if feedback_type == "" or feedback_type is None:
                issue.feedback_type = None
                issue.feedback_comment = None
            else:
                issue.feedback_type = feedback_type
                issue.feedback_comment = comment
            self.db.commit()
            self.db.refresh(issue)
        return issue
    
    def update_comment_only(self, issue_id: int, comment: Optional[str]) -> Optional[Issue]:
        """只更新评论，不改变反馈类型"""
        issue = self.get_by_id(issue_id)
        if issue:
            issue.feedback_comment = comment
            self.db.commit()
            self.db.refresh(issue)
        return issue
    
    def update_satisfaction_rating(self, issue_id: int, rating: float) -> Optional[Issue]:
        """更新满意度评分"""
        issue = self.get_by_id(issue_id)
        if issue:
            issue.satisfaction_rating = rating
            self.db.commit()
            self.db.refresh(issue)
        return issue
    
    def delete_by_task_id(self, task_id: int):
        """删除任务的所有问题"""
        self.db.query(Issue).filter(Issue.task_id == task_id).delete()
        self.db.commit()
    
    def get_paginated_issues_by_task_id(self, task_id: int, params: PaginationParams) -> Tuple[List[Issue], int]:
        """分页获取任务的问题列表
        
        Args:
            task_id: 任务ID
            params: 分页参数
            
        Returns:
            (问题列表, 总数量)
        """
        # 构建查询
        query = self.db.query(Issue).filter(Issue.task_id == task_id)
        
        # 严重程度过滤
        if hasattr(params, 'severity') and params.severity and params.severity != 'all':
            query = query.filter(Issue.severity == params.severity)
        
        # 问题类型过滤
        if hasattr(params, 'issue_type') and params.issue_type and params.issue_type != 'all':
            query = query.filter(Issue.issue_type == params.issue_type)
        
        # 反馈状态过滤
        if hasattr(params, 'feedback_status') and params.feedback_status:
            if params.feedback_status == 'processed':
                query = query.filter(Issue.feedback_type.isnot(None))
            elif params.feedback_status == 'unprocessed':
                query = query.filter(Issue.feedback_type.is_(None))
            elif params.feedback_status in ['accept', 'reject']:
                query = query.filter(Issue.feedback_type == params.feedback_status)
        
        # 搜索过滤
        if params.search:
            search_term = f"%{params.search}%"
            query = query.filter(
                Issue.description.ilike(search_term) | 
                Issue.location.ilike(search_term) |
                Issue.original_text.ilike(search_term)
            )
        
        # 排序
        if params.sort_by:
            sort_column = getattr(Issue, params.sort_by, None)
            if sort_column is not None:
                if params.sort_order == 'asc':
                    query = query.order_by(asc(sort_column))
                else:
                    query = query.order_by(desc(sort_column))
            else:
                # 默认按ID倒序
                query = query.order_by(desc(Issue.id))
        else:
            query = query.order_by(desc(Issue.id))
        
        # 获取总数
        total = query.count()
        
        # 分页
        offset = (params.page - 1) * params.page_size
        items = query.offset(offset).limit(params.page_size).all()
        
        return items, total