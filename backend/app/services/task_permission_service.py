"""
任务权限管理服务
"""
from typing import Dict, List
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.task import Task
from app.repositories.task_share import TaskShareRepository
from app.repositories.task import TaskRepository


class TaskPermissionService:
    """任务权限管理服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.task_share_repo = TaskShareRepository(db)
        self.task_repo = TaskRepository(db)
    
    def get_user_task_permissions(self, task_id: int, user: User) -> Dict[str, bool]:
        """获取用户对任务的详细权限"""
        task = self.task_repo.get_by_id(task_id)
        if not task:
            return self._no_permission()
        
        # 1. 检查是否为任务创建者
        if task.user_id == user.id:
            return self._owner_permissions()
        
        # 2. 检查是否为管理员
        if user.is_admin or user.is_system_admin:
            return self._admin_permissions()
        
        # 3. 检查分享权限
        task_share = self.task_share_repo.check_user_task_permission(task_id, user.id)
        if task_share:
            return self._shared_permissions(task_share.permission_level)
        
        # 4. 无权限
        return self._no_permission()
    
    def check_task_access(self, task_id: int, user: User, required_permission: str = 'read') -> bool:
        """检查用户对任务的访问权限"""
        permissions = self.get_user_task_permissions(task_id, user)
        
        permission_map = {
            'read': permissions.get('can_view', False),
            'write': permissions.get('can_edit', False),
            'feedback': permissions.get('can_feedback', False),
            'share': permissions.get('can_share', False),
            'delete': permissions.get('can_delete', False),
            'download': permissions.get('can_download', False)
        }
        
        return permission_map.get(required_permission, False)
    
    def check_task_share_permission(self, task_id: int, user: User) -> bool:
        """检查用户是否可以分享任务"""
        task = self.task_repo.get_by_id(task_id)
        if not task:
            return False
        
        # 只有任务创建者和管理员可以分享任务
        return (task.user_id == user.id or 
                user.is_admin or 
                user.is_system_admin)
    
    def get_accessible_task_ids(self, user: User) -> List[int]:
        """获取用户可访问的所有任务ID列表"""
        accessible_ids = []
        
        # 1. 用户创建的任务
        user_tasks = self.db.query(Task.id).filter(Task.user_id == user.id).all()
        accessible_ids.extend([t.id for t in user_tasks])
        
        # 2. 分享给用户的任务
        shared_tasks = self.task_share_repo.get_user_shared_tasks(user.id)
        accessible_ids.extend([s.task_id for s in shared_tasks])
        
        # 3. 管理员可访问所有任务
        if user.is_admin or user.is_system_admin:
            all_tasks = self.db.query(Task.id).all()
            accessible_ids.extend([t.id for t in all_tasks])
        
        return list(set(accessible_ids))  # 去重
    
    def get_user_permission_summary(self, user: User) -> Dict[str, int]:
        """获取用户权限汇总信息"""
        # 统计用户可访问的任务数量
        owned_tasks = self.db.query(Task).filter(Task.user_id == user.id).count()
        shared_tasks = self.task_share_repo.get_user_received_share_count(user.id)
        
        return {
            'owned_tasks': owned_tasks,
            'shared_tasks': shared_tasks,
            'total_accessible': owned_tasks + shared_tasks,
            'is_admin': user.is_admin or user.is_system_admin
        }
    
    def _owner_permissions(self) -> Dict[str, bool]:
        """任务创建者权限"""
        return {
            'can_view': True,
            'can_edit': False,  # 任务完成后不能编辑任务本身
            'can_feedback': True,
            'can_comment': True,
            'can_rate': True,
            'can_download': True,
            'can_share': True,
            'can_delete': True,  # 只有创建者可以删除任务
            'is_owner': True
        }
    
    def _admin_permissions(self) -> Dict[str, bool]:
        """管理员权限"""
        return {
            'can_view': True,
            'can_edit': False,
            'can_feedback': True,
            'can_comment': True,
            'can_rate': True,
            'can_download': True,
            'can_share': False,  # 管理员不能分享别人的任务
            'can_delete': True,  # 管理员可以删除任务
            'is_admin': True
        }
    
    def _shared_permissions(self, permission_level: str) -> Dict[str, bool]:
        """分享权限"""
        base_permissions = {
            'can_view': True,
            'can_edit': False,
            'can_share': False,
            'can_delete': False,
            'is_shared': True,
            'permission_level': permission_level
        }
        
        if permission_level == 'full_access':
            base_permissions.update({
                'can_feedback': True,
                'can_comment': True,
                'can_rate': True,
                'can_download': True
            })
        elif permission_level == 'feedback_only':
            base_permissions.update({
                'can_feedback': True,
                'can_comment': True,
                'can_rate': True,
                'can_download': True
            })
        else:  # read_only
            base_permissions.update({
                'can_feedback': False,
                'can_comment': False,
                'can_rate': False,
                'can_download': False
            })
        
        return base_permissions
    
    def _no_permission(self) -> Dict[str, bool]:
        """无权限"""
        return {
            'can_view': False,
            'can_edit': False,
            'can_feedback': False,
            'can_comment': False,
            'can_rate': False,
            'can_download': False,
            'can_share': False,
            'can_delete': False,
            'no_access': True
        }