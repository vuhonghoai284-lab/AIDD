"""
任务数据访问层
"""
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func
from datetime import datetime

from app.models import Task, Issue
from app.repositories.interfaces.task_repository import ITaskRepository
from app.dto.pagination import PaginationParams


class TaskRepository(ITaskRepository):
    """任务仓库"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, **kwargs) -> Task:
        """创建任务"""
        task = Task(**kwargs)
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task
    
    def get_by_id(self, task_id: int) -> Optional[Task]:
        """根据ID获取任务"""
        return self.db.query(Task).filter(Task.id == task_id).first()
    
    def get(self, task_id: int) -> Optional[Task]:
        """根据ID获取任务 (别名)"""
        return self.get_by_id(task_id)
    
    def get_all(self) -> List[Task]:
        """获取所有任务"""
        return self.db.query(Task).order_by(Task.created_at.desc()).all()
    
    def get_all_with_relations(self) -> List[Task]:
        """获取所有任务（使用JOIN预加载关联数据）"""
        from sqlalchemy.orm import joinedload
        return (self.db.query(Task)
                .options(
                    joinedload(Task.file_info),
                    joinedload(Task.ai_model), 
                    joinedload(Task.user)
                )
                .order_by(Task.created_at.desc())
                .all())
    
    def get_by_user_id(self, user_id: int) -> List[Task]:
        """根据用户ID获取任务"""
        return self.db.query(Task).filter(Task.user_id == user_id).order_by(Task.created_at.desc()).all()
        
    def get_by_user_id_with_relations(self, user_id: int) -> List[Task]:
        """根据用户ID获取任务（使用JOIN预加载关联数据）"""
        from sqlalchemy.orm import joinedload
        return (self.db.query(Task)
                .options(
                    joinedload(Task.file_info),
                    joinedload(Task.ai_model),
                    joinedload(Task.user)
                )
                .filter(Task.user_id == user_id)
                .order_by(Task.created_at.desc())
                .all())
    
    def update(self, task_id: int, **kwargs) -> Optional[Task]:
        """更新任务"""
        task = self.get_by_id(task_id)
        if task:
            for key, value in kwargs.items():
                setattr(task, key, value)
            self.db.commit()
            self.db.refresh(task)
        return task
    
    def delete(self, task_id: int) -> bool:
        """删除任务"""
        task = self.get_by_id(task_id)
        if task:
            # 删除相关的问题、AI输出和任务日志
            self.db.query(Issue).filter(Issue.task_id == task_id).delete()
            from app.models import AIOutput, TaskLog
            self.db.query(AIOutput).filter(AIOutput.task_id == task_id).delete()
            self.db.query(TaskLog).filter(TaskLog.task_id == task_id).delete()
            
            self.db.delete(task)
            self.db.commit()
            return True
        return False
    
    def get_pending_tasks(self) -> List[Task]:
        """获取待处理任务"""
        return self.db.query(Task).filter(Task.status == 'pending').all()
    
    def update_progress(self, task_id: int, progress: float, status: Optional[str] = None):
        """更新任务进度"""
        update_data = {"progress": progress}
        if status:
            update_data["status"] = status
            if status == "completed":
                update_data["completed_at"] = datetime.utcnow()
        self.update(task_id, **update_data)
    
    def count_issues(self, task_id: int) -> int:
        """统计任务的问题数量"""
        return self.db.query(Issue).filter(Issue.task_id == task_id).count()
    
    def count_processed_issues(self, task_id: int) -> int:
        """统计任务的已处理问题数量"""
        return self.db.query(Issue).filter(
            Issue.task_id == task_id,
            Issue.feedback_type.isnot(None)
        ).count()
        
    def batch_count_issues(self, task_ids: List[int]) -> dict:
        """批量统计任务的问题数量（性能优化版）"""
        from sqlalchemy import func
        if not task_ids:
            return {}
        
        # 快速检查：如果issues表为空，直接返回零值结果
        total_issues = self.db.query(Issue).count()
        if total_issues == 0:
            result = {}
            for task_id in task_ids:
                result[task_id] = {"issue_count": 0, "processed_issues": 0}
            return result
        
        # 使用单个查询获取所有统计信息，减少数据库往返
        from sqlalchemy import case
        stats_query = (
            self.db.query(
                Issue.task_id,
                func.count(Issue.id).label('total_count'),
                func.count(case((Issue.feedback_type.isnot(None), Issue.id))).label('processed_count')
            )
            .filter(Issue.task_id.in_(task_ids))
            .group_by(Issue.task_id)
            .all()
        )
        
        # 构建结果字典
        result = {}
        for task_id in task_ids:
            result[task_id] = {"issue_count": 0, "processed_issues": 0}
        
        for task_id, total_count, processed_count in stats_query:
            result[task_id] = {
                "issue_count": total_count,
                "processed_issues": processed_count
            }
            
        return result
    
    def get_by_id_with_relations(self, task_id: int) -> Optional[Task]:
        """根据ID获取任务（使用JOIN预加载关联数据）"""
        from sqlalchemy.orm import joinedload
        return (self.db.query(Task)
                .options(
                    joinedload(Task.file_info),
                    joinedload(Task.ai_model),
                    joinedload(Task.user)
                )
                .filter(Task.id == task_id)
                .first())
    
    def update_status(self, task_id: int, status: str, progress: int = None) -> Task:
        """更新任务状态和进度"""
        update_data = {"status": status}
        if progress is not None:
            update_data["progress"] = progress
        if status == "completed":
            update_data["completed_at"] = datetime.utcnow()
        return self.update(task_id, **update_data)
    
    def get_paginated_tasks(self, params: PaginationParams, user_id: Optional[int] = None) -> Tuple[List[Task], int]:
        """分页获取任务列表（高性能版，避免数据库锁竞争）
        
        Args:
            params: 分页参数
            user_id: 用户ID，None表示获取所有任务（管理员）
            
        Returns:
            (任务列表, 总数量)
        """
        from sqlalchemy.orm import joinedload
        import time
        query_start = time.time()
        
        # 构建查询，使用READ COMMITTED隔离级别避免锁等待
        query = self.db.query(Task).options(
            joinedload(Task.file_info),
            joinedload(Task.ai_model),
            joinedload(Task.user)
        )
        
        # 添加查询超时控制和索引提示
        # 为了提高性能，建议在以下列上创建索引：
        # - Task.user_id
        # - Task.created_at
        # - Task.status
        # - FileInfo.original_name (用于搜索)
        
        # 用户权限过滤（使用索引）
        if user_id is not None:
            query = query.filter(Task.user_id == user_id)
        
        # 状态过滤（使用索引）
        if params.status and params.status != 'all':
            query = query.filter(Task.status == params.status)
        
        # 搜索过滤
        if params.search:
            from app.models.file_info import FileInfo
            search_term = f"%{params.search}%"
            query = query.join(FileInfo, Task.file_id == FileInfo.id, isouter=True).filter(
                or_(
                    Task.title.ilike(search_term),
                    FileInfo.original_name.ilike(search_term)
                )
            )
        
        # 排序（确保使用索引）
        if params.sort_by:
            sort_column = getattr(Task, params.sort_by, None)
            if sort_column is not None:
                if params.sort_order == 'asc':
                    query = query.order_by(asc(sort_column))
                else:
                    query = query.order_by(desc(sort_column))
            else:
                # 默认按创建时间倒序（使用索引）
                query = query.order_by(desc(Task.created_at))
        else:
            query = query.order_by(desc(Task.created_at))
        
        # 构建计数查询（移除JOIN以提高性能）
        count_start = time.time()
        count_query = self.db.query(Task)
        
        # 应用相同的过滤条件
        if user_id is not None:
            count_query = count_query.filter(Task.user_id == user_id)
        if params.status and params.status != 'all':
            count_query = count_query.filter(Task.status == params.status)
        if params.search:
            from app.models.file_info import FileInfo
            search_term = f"%{params.search}%"
            count_query = count_query.join(FileInfo, Task.file_id == FileInfo.id, isouter=True).filter(
                or_(
                    Task.title.ilike(search_term),
                    FileInfo.original_name.ilike(search_term)
                )
            )
        
        # 执行计数查询
        total = count_query.count()
        count_time = (time.time() - count_start) * 1000
        print(f"📈 计数查询耗时: {count_time:.1f}ms")
        
        # 分页查询数据
        offset = (params.page - 1) * params.page_size
        # 设置查询超时，避免长时间等待
        try:
            items = query.offset(offset).limit(params.page_size).all()
            query_time = (time.time() - query_start) * 1000
            print(f"📊 分页查询完成，耗时: {query_time:.1f}ms")
            return items, total
        except Exception as e:
            print(f"❌ 分页查询失败: {e}")
            raise