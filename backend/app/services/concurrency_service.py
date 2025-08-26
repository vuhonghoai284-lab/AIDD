"""
并发任务控制服务
管理系统和用户级别的并发任务限制
"""
import logging
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.user import User
from app.models.task import Task
from app.core.config import get_settings


logger = logging.getLogger(__name__)


class ConcurrencyLimitExceeded(Exception):
    """并发限制超出异常"""
    def __init__(self, message: str, limit_type: str, current_count: int, max_count: int):
        self.limit_type = limit_type  # 'system' 或 'user'
        self.current_count = current_count
        self.max_count = max_count
        super().__init__(message)


class ConcurrencyService:
    """并发任务控制服务"""
    
    def __init__(self):
        self.settings = get_settings()
        self.concurrency_config = self.settings.task_processing_config.get('concurrency_limits', {})
        
    def get_system_max_concurrent_tasks(self) -> int:
        """获取系统最大并发任务数"""
        return self.concurrency_config.get('system_max_concurrent_tasks', 100)
    
    def get_user_max_concurrent_tasks(self, user: User) -> int:
        """
        获取用户最大并发任务数
        优先级：用户自定义 > 管理员配置 > 默认配置
        """
        # 1. 用户自定义限制
        if user.max_concurrent_tasks is not None and user.max_concurrent_tasks > 0:
            return user.max_concurrent_tasks
        
        # 2. 根据用户类型返回配置的默认值
        if user.is_admin or user.is_system_admin:
            return self.concurrency_config.get('admin_max_concurrent_tasks', 50)
        
        # 3. 普通用户默认限制
        return self.concurrency_config.get('default_user_max_concurrent_tasks', 10)
    
    def get_current_system_processing_count(self, db: Session) -> int:
        """获取系统当前正在处理的任务数"""
        return db.query(Task).filter(
            and_(
                Task.status.in_(['processing', 'pending']),
                # 可以添加更多条件，比如排除已停止的任务
            )
        ).count()
    
    def get_current_user_processing_count(self, db: Session, user_id: int) -> int:
        """获取用户当前正在处理的任务数"""
        return db.query(Task).filter(
            and_(
                Task.user_id == user_id,
                Task.status.in_(['processing', 'pending'])
            )
        ).count()
    
    def check_system_concurrency_limit(self, db: Session, requested_tasks: int = 1) -> Tuple[bool, Dict[str, Any]]:
        """
        检查系统并发限制
        
        Args:
            db: 数据库会话
            requested_tasks: 请求的任务数（批量创建时使用）
            
        Returns:
            (是否允许, 状态信息)
        """
        current_count = self.get_current_system_processing_count(db)
        max_count = self.get_system_max_concurrent_tasks()
        
        status_info = {
            'current_count': current_count,
            'max_count': max_count,
            'requested_tasks': requested_tasks,
            'available_slots': max(0, max_count - current_count),
            'can_create': (current_count + requested_tasks) <= max_count
        }
        
        logger.info(f"系统并发检查: 当前 {current_count}/{max_count}，请求 {requested_tasks} 个任务")
        
        return status_info['can_create'], status_info
    
    def check_user_concurrency_limit(self, db: Session, user: User, requested_tasks: int = 1) -> Tuple[bool, Dict[str, Any]]:
        """
        检查用户并发限制
        
        Args:
            db: 数据库会话
            user: 用户对象
            requested_tasks: 请求的任务数（批量创建时使用）
            
        Returns:
            (是否允许, 状态信息)
        """
        current_count = self.get_current_user_processing_count(db, user.id)
        max_count = self.get_user_max_concurrent_tasks(user)
        
        status_info = {
            'current_count': current_count,
            'max_count': max_count,
            'requested_tasks': requested_tasks,
            'available_slots': max(0, max_count - current_count),
            'can_create': (current_count + requested_tasks) <= max_count
        }
        
        logger.info(f"用户并发检查 [{user.display_name or user.uid}]: 当前 {current_count}/{max_count}，请求 {requested_tasks} 个任务")
        
        return status_info['can_create'], status_info
    
    def check_concurrency_limits(
        self, 
        db: Session, 
        user: User, 
        requested_tasks: int = 1,
        raise_exception: bool = True
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        综合检查系统和用户并发限制
        
        Args:
            db: 数据库会话
            user: 用户对象
            requested_tasks: 请求的任务数
            raise_exception: 是否在超限时抛出异常
            
        Returns:
            (是否允许, 详细状态信息)
            
        Raises:
            ConcurrencyLimitExceeded: 当超出限制且raise_exception=True时
        """
        # 检查系统限制
        system_allowed, system_info = self.check_system_concurrency_limit(db, requested_tasks)
        
        # 检查用户限制
        user_allowed, user_info = self.check_user_concurrency_limit(db, user, requested_tasks)
        
        # 综合状态信息
        status_info = {
            'system': system_info,
            'user': user_info,
            'overall_allowed': system_allowed and user_allowed,
            'limiting_factor': None  # 限制因素
        }
        
        # 确定限制因素
        if not system_allowed and not user_allowed:
            status_info['limiting_factor'] = 'both'
        elif not system_allowed:
            status_info['limiting_factor'] = 'system'
        elif not user_allowed:
            status_info['limiting_factor'] = 'user'
        
        # 如果超限且要求抛出异常
        if not status_info['overall_allowed'] and raise_exception:
            if status_info['limiting_factor'] == 'system':
                raise ConcurrencyLimitExceeded(
                    f"系统并发任务数已达上限 ({system_info['current_count']}/{system_info['max_count']})，"
                    f"无法创建 {requested_tasks} 个新任务",
                    'system',
                    system_info['current_count'],
                    system_info['max_count']
                )
            elif status_info['limiting_factor'] == 'user':
                raise ConcurrencyLimitExceeded(
                    f"用户并发任务数已达上限 ({user_info['current_count']}/{user_info['max_count']})，"
                    f"无法创建 {requested_tasks} 个新任务",
                    'user',
                    user_info['current_count'],
                    user_info['max_count']
                )
            else:  # both
                raise ConcurrencyLimitExceeded(
                    f"系统和用户并发任务数均已达上限，无法创建 {requested_tasks} 个新任务。"
                    f"系统: {system_info['current_count']}/{system_info['max_count']}，"
                    f"用户: {user_info['current_count']}/{user_info['max_count']}",
                    'both',
                    max(system_info['current_count'], user_info['current_count']),
                    min(system_info['max_count'], user_info['max_count'])
                )
        
        return status_info['overall_allowed'], status_info
    
    def get_concurrency_status(self, db: Session, user: Optional[User] = None) -> Dict[str, Any]:
        """
        获取并发状态信息（用于监控和前端显示）
        
        Args:
            db: 数据库会话
            user: 用户对象（可选，为空时只返回系统状态）
            
        Returns:
            并发状态信息
        """
        # 系统状态
        system_current = self.get_current_system_processing_count(db)
        system_max = self.get_system_max_concurrent_tasks()
        
        status = {
            'system': {
                'current_count': system_current,
                'max_count': system_max,
                'available_slots': max(0, system_max - system_current),
                'utilization_rate': round(system_current / system_max * 100, 1) if system_max > 0 else 0
            }
        }
        
        # 用户状态
        if user:
            user_current = self.get_current_user_processing_count(db, user.id)
            user_max = self.get_user_max_concurrent_tasks(user)
            
            status['user'] = {
                'current_count': user_current,
                'max_count': user_max,
                'available_slots': max(0, user_max - user_current),
                'utilization_rate': round(user_current / user_max * 100, 1) if user_max > 0 else 0
            }
        
        return status
    
    def update_user_concurrency_limit(
        self, 
        db: Session, 
        user_id: int, 
        new_limit: int, 
        operator_user: User
    ) -> bool:
        """
        更新用户并发限制（仅管理员可操作）
        
        Args:
            db: 数据库会话
            user_id: 目标用户ID
            new_limit: 新的限制数
            operator_user: 操作员用户
            
        Returns:
            是否更新成功
        """
        if not (operator_user.is_admin or operator_user.is_system_admin):
            logger.warning(f"非管理员用户 {operator_user.uid} 尝试修改并发限制")
            return False
        
        if new_limit < 0:
            logger.warning(f"无效的并发限制值: {new_limit}")
            return False
        
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"用户不存在: {user_id}")
                return False
            
            old_limit = self.get_user_max_concurrent_tasks(user)
            user.max_concurrent_tasks = new_limit
            db.commit()
            
            logger.info(f"管理员 {operator_user.uid} 将用户 {user.uid} 的并发限制从 {old_limit} 更新为 {new_limit}")
            return True
            
        except Exception as e:
            logger.error(f"更新用户并发限制失败: {e}")
            db.rollback()
            return False
    
    def get_user_task_statistics(self, db: Session, user_id: int) -> Dict[str, Any]:
        """
        获取用户任务统计信息
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            
        Returns:
            用户任务统计信息
        """
        # 各状态任务数统计
        task_counts = db.query(
            Task.status,
            func.count(Task.id).label('count')
        ).filter(
            Task.user_id == user_id
        ).group_by(Task.status).all()
        
        # 转换为字典
        status_counts = {status: count for status, count in task_counts}
        
        return {
            'total_tasks': sum(status_counts.values()),
            'pending_tasks': status_counts.get('pending', 0),
            'processing_tasks': status_counts.get('processing', 0),
            'completed_tasks': status_counts.get('completed', 0),
            'failed_tasks': status_counts.get('failed', 0),
            'active_tasks': status_counts.get('pending', 0) + status_counts.get('processing', 0)
        }


# 创建全局实例
concurrency_service = ConcurrencyService()