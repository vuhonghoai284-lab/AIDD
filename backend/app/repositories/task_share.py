"""
任务分享数据访问层
"""
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from app.models.task_share import TaskShare
from app.models.task import Task


class TaskShareRepository:
    """任务分享仓库"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, **kwargs) -> TaskShare:
        """创建任务分享"""
        task_share = TaskShare(**kwargs)
        self.db.add(task_share)
        self.db.commit()
        self.db.refresh(task_share)
        return task_share
    
    def get_by_id(self, share_id: int) -> Optional[TaskShare]:
        """根据ID获取任务分享"""
        return self.db.query(TaskShare).filter(TaskShare.id == share_id).first()
    
    def get_by_task_and_user(self, task_id: int, user_id: int) -> Optional[TaskShare]:
        """获取特定任务对特定用户的分享记录"""
        return self.db.query(TaskShare).filter(
            and_(
                TaskShare.task_id == task_id,
                TaskShare.shared_user_id == user_id,
                TaskShare.is_active == True
            )
        ).first()
    
    def get_task_shares(self, task_id: int, include_inactive: bool = False) -> List[TaskShare]:
        """获取任务的所有分享记录"""
        query = self.db.query(TaskShare).options(
            joinedload(TaskShare.shared_user),
            joinedload(TaskShare.owner)
        ).filter(TaskShare.task_id == task_id)
        
        if not include_inactive:
            query = query.filter(TaskShare.is_active == True)
        
        return query.all()
    
    def get_user_shared_tasks(self, user_id: int, include_inactive: bool = False) -> List[TaskShare]:
        """获取分享给用户的任务列表"""
        query = self.db.query(TaskShare).options(
            joinedload(TaskShare.task).joinedload(Task.file_info),
            joinedload(TaskShare.task).joinedload(Task.ai_model),
            joinedload(TaskShare.owner)
        ).filter(TaskShare.shared_user_id == user_id)
        
        if not include_inactive:
            query = query.filter(TaskShare.is_active == True)
        
        return query.order_by(TaskShare.created_at.desc()).all()
    
    def check_user_task_permission(self, task_id: int, user_id: int) -> Optional[TaskShare]:
        """检查用户对任务的分享权限"""
        return self.db.query(TaskShare).filter(
            and_(
                TaskShare.task_id == task_id,
                TaskShare.shared_user_id == user_id,
                TaskShare.is_active == True
            )
        ).first()
    
    def batch_create_shares(self, task_id: int, owner_id: int, shared_user_ids: List[int], 
                           permission_level: str = 'read_only', share_comment: Optional[str] = None) -> List[TaskShare]:
        """批量创建任务分享"""
        created_shares = []
        
        for user_id in shared_user_ids:
            # 检查是否已经分享给该用户
            existing_share = self.get_by_task_and_user(task_id, user_id)
            
            if existing_share:
                # 更新现有分享记录
                existing_share.permission_level = permission_level
                existing_share.share_comment = share_comment
                existing_share.is_active = True
                created_shares.append(existing_share)
            else:
                # 创建新的分享记录
                new_share = TaskShare(
                    task_id=task_id,
                    owner_id=owner_id,
                    shared_user_id=user_id,
                    permission_level=permission_level,
                    share_comment=share_comment
                )
                self.db.add(new_share)
                created_shares.append(new_share)
        
        self.db.commit()
        
        # 刷新所有创建的记录
        for share in created_shares:
            self.db.refresh(share)
        
        return created_shares
    
    def revoke_share(self, share_id: int, owner_id: int) -> bool:
        """撤销任务分享（仅分享者可撤销）"""
        share = self.db.query(TaskShare).filter(
            and_(
                TaskShare.id == share_id,
                TaskShare.owner_id == owner_id,
                TaskShare.is_active == True
            )
        ).first()
        
        if share:
            share.is_active = False
            self.db.commit()
            return True
        return False
    
    def delete_share(self, share_id: int, owner_id: int) -> bool:
        """删除任务分享记录（仅分享者可删除）"""
        share = self.db.query(TaskShare).filter(
            and_(
                TaskShare.id == share_id,
                TaskShare.owner_id == owner_id
            )
        ).first()
        
        if share:
            self.db.delete(share)
            self.db.commit()
            return True
        return False
    
    def update_share_permission(self, share_id: int, owner_id: int, 
                               permission_level: str, share_comment: Optional[str] = None) -> Optional[TaskShare]:
        """更新分享权限（仅分享者可更新）"""
        share = self.db.query(TaskShare).filter(
            and_(
                TaskShare.id == share_id,
                TaskShare.owner_id == owner_id,
                TaskShare.is_active == True
            )
        ).first()
        
        if share:
            share.permission_level = permission_level
            if share_comment is not None:
                share.share_comment = share_comment
            self.db.commit()
            self.db.refresh(share)
            return share
        return None
    
    def get_task_share_count(self, task_id: int) -> int:
        """获取任务的分享数量"""
        return self.db.query(TaskShare).filter(
            and_(
                TaskShare.task_id == task_id,
                TaskShare.is_active == True
            )
        ).count()
    
    def get_user_received_share_count(self, user_id: int) -> int:
        """获取用户收到的分享数量"""
        return self.db.query(TaskShare).filter(
            and_(
                TaskShare.shared_user_id == user_id,
                TaskShare.is_active == True
            )
        ).count()