"""
增强的并发控制服务
基于数据库队列的20用户×3并发控制系统
"""
from typing import Tuple, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime
import logging

from app.models.task_queue import TaskQueue, QueueStatus, QueueConfig
from app.models.user import User
from app.services.database_queue_service import DatabaseQueueService

logger = logging.getLogger(__name__)


class ConcurrencyLimitExceeded(Exception):
    """并发限制超出异常"""
    def __init__(self, message: str, limit_type: str, current_count: int, max_count: int):
        super().__init__(message)
        self.limit_type = limit_type  # 'user', 'system', 'both'
        self.current_count = current_count
        self.max_count = max_count


class EnhancedConcurrencyService:
    """增强的并发控制服务 - 基于数据库队列"""
    
    def __init__(self):
        self.queue_service = DatabaseQueueService()
    
    def _get_queue_config(self, db: Session) -> Dict[str, int]:
        """获取队列配置"""
        configs = db.query(QueueConfig).all()
        config_dict = {config.config_key: int(config.config_value) for config in configs}
        
        return {
            'max_concurrent_users': config_dict.get('max_concurrent_users', 20),
            'user_max_concurrent_tasks': config_dict.get('user_max_concurrent_tasks', 3),
            'system_max_concurrent_tasks': config_dict.get('system_max_concurrent_tasks', 60)
        }
    
    async def check_concurrency_limits(self, db: Session, user: User, 
                                     requested_tasks: int = 1, 
                                     raise_exception: bool = False) -> Tuple[bool, Dict]:
        """
        检查并发限制 - 基于队列系统
        
        Args:
            db: 数据库会话
            user: 用户对象
            requested_tasks: 请求的任务数量
            raise_exception: 是否在超限时抛出异常
            
        Returns:
            Tuple[bool, Dict]: (是否允许, 状态信息)
        """
        config = self._get_queue_config(db)
        
        # 获取当前活跃任务统计 (处理中 + 排队中)
        system_active = db.query(TaskQueue).filter(
            TaskQueue.status.in_([QueueStatus.PROCESSING, QueueStatus.QUEUED])
        ).count()
        
        user_active = db.query(TaskQueue).filter(
            and_(
                TaskQueue.user_id == user.id,
                TaskQueue.status.in_([QueueStatus.PROCESSING, QueueStatus.QUEUED])
            )
        ).count()
        
        # 计算可用槽位
        system_available = max(0, config['system_max_concurrent_tasks'] - system_active)
        user_available = max(0, config['user_max_concurrent_tasks'] - user_active)
        
        # 状态信息
        status_info = {
            'system': {
                'current_active': system_active,
                'max_concurrent': config['system_max_concurrent_tasks'],
                'available_slots': system_available
            },
            'user': {
                'user_id': user.id,
                'current_active': user_active,
                'max_concurrent': config['user_max_concurrent_tasks'],
                'available_slots': user_available
            },
            'requested_tasks': requested_tasks
        }
        
        # 检查限制
        system_allowed = system_available >= requested_tasks
        user_allowed = user_available >= requested_tasks
        
        if not system_allowed and not user_allowed:
            limit_type = 'both'
            message = f"系统和用户并发限制都已达上限"
            if raise_exception:
                raise ConcurrencyLimitExceeded(
                    message, limit_type, 
                    max(system_active, user_active),
                    min(config['system_max_concurrent_tasks'], config['user_max_concurrent_tasks'])
                )
        elif not system_allowed:
            limit_type = 'system'
            message = f"系统并发限制已达上限 ({system_active}/{config['system_max_concurrent_tasks']})"
            if raise_exception:
                raise ConcurrencyLimitExceeded(
                    message, limit_type, system_active, config['system_max_concurrent_tasks']
                )
        elif not user_allowed:
            limit_type = 'user'
            message = f"用户并发限制已达上限 ({user_active}/{config['user_max_concurrent_tasks']})"
            if raise_exception:
                raise ConcurrencyLimitExceeded(
                    message, limit_type, user_active, config['user_max_concurrent_tasks']
                )
        
        allowed = system_allowed and user_allowed
        
        return allowed, status_info
    
    def get_concurrency_status(self, db: Session, user: User) -> Dict:
        """
        获取并发状态信息
        
        Args:
            db: 数据库会话
            user: 用户对象
            
        Returns:
            Dict: 详细的并发状态信息
        """
        config = self._get_queue_config(db)
        
        # 系统级统计
        system_stats = db.query(
            TaskQueue.status,
            func.count(TaskQueue.id)
        ).group_by(TaskQueue.status).all()
        
        system_counts = {status.value: 0 for status in QueueStatus}
        for status, count in system_stats:
            system_counts[status.value] = count
        
        # 用户级统计
        user_stats = db.query(
            TaskQueue.status,
            func.count(TaskQueue.id)
        ).filter(TaskQueue.user_id == user.id).group_by(TaskQueue.status).all()
        
        user_counts = {status.value: 0 for status in QueueStatus}
        for status, count in user_stats:
            user_counts[status.value] = count
        
        # 活跃用户统计
        active_users = db.query(
            func.count(func.distinct(TaskQueue.user_id))
        ).filter(TaskQueue.status == QueueStatus.PROCESSING).scalar()
        
        return {
            'config': config,
            'system': {
                'queue_counts': system_counts,
                'active_users': active_users or 0,
                'available_slots': max(0, config['system_max_concurrent_tasks'] - system_counts.get('processing', 0))
            },
            'user': {
                'user_id': user.id,
                'queue_counts': user_counts,
                'available_slots': max(0, config['user_max_concurrent_tasks'] - user_counts.get('processing', 0))
            }
        }
    
    def update_user_concurrency_limit(self, db: Session, user_id: int, 
                                    new_limit: int, admin_user: User) -> bool:
        """
        更新用户并发限制 (管理员功能)
        
        Args:
            db: 数据库会话
            user_id: 目标用户ID
            new_limit: 新的并发限制
            admin_user: 管理员用户
            
        Returns:
            bool: 是否更新成功
        """
        if not (admin_user.is_admin or admin_user.is_system_admin):
            logger.warning(f"非管理员用户 {admin_user.id} 尝试更新并发限制")
            return False
        
        if new_limit < 1 or new_limit > 10:
            logger.warning(f"无效的并发限制值: {new_limit}")
            return False
        
        try:
            # 更新用户特定配置（这里简化为更新全局配置）
            # 在实际系统中，可能需要用户级配置表
            config = db.query(QueueConfig).filter(
                QueueConfig.config_key == 'user_max_concurrent_tasks'
            ).first()
            
            if config:
                old_value = config.config_value
                config.config_value = str(new_limit)
                config.updated_at = datetime.utcnow()
                db.commit()
                
                logger.info(f"管理员 {admin_user.id} 更新用户并发限制: {old_value} -> {new_limit}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"更新用户并发限制失败: {e}")
            db.rollback()
            return False


# 全局增强并发服务实例
_enhanced_concurrency_service_instance = None

def get_enhanced_concurrency_service() -> EnhancedConcurrencyService:
    """获取增强并发服务实例（单例）"""
    global _enhanced_concurrency_service_instance
    if _enhanced_concurrency_service_instance is None:
        _enhanced_concurrency_service_instance = EnhancedConcurrencyService()
    return _enhanced_concurrency_service_instance