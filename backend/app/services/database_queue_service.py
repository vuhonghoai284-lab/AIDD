"""
数据库任务队列服务
支持20用户×3并发任务的队列管理系统
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
import logging

from app.core.database import get_independent_db_session, close_independent_db_session
from app.models.task_queue import TaskQueue, QueueStatus, QueueConfig
from app.models.task import Task
from app.models.user import User

logger = logging.getLogger(__name__)


class DatabaseQueueService:
    """数据库队列管理服务 - 支持20用户×3并发的任务调度"""
    
    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self._worker_id = str(uuid.uuid4())
        self._shutdown_flag = False
        
    def _get_queue_config(self, db: Session) -> Dict[str, int]:
        """获取队列配置"""
        configs = db.query(QueueConfig).all()
        config_dict = {config.config_key: int(config.config_value) for config in configs}
        
        # 默认配置值
        return {
            'max_concurrent_users': config_dict.get('max_concurrent_users', 20),
            'user_max_concurrent_tasks': config_dict.get('user_max_concurrent_tasks', 3),
            'system_max_concurrent_tasks': config_dict.get('system_max_concurrent_tasks', 60),
            'worker_pool_size': config_dict.get('worker_pool_size', 20),
            'queue_check_interval': config_dict.get('queue_check_interval', 2),
            'task_timeout': config_dict.get('task_timeout', 600),
            'max_queue_length': config_dict.get('max_queue_length', 200),
            'priority_boost_threshold': config_dict.get('priority_boost_threshold', 300)
        }
    
    async def enqueue_task(self, task_id: int, user_id: int, priority: int = 5, 
                          estimated_duration: int = 300) -> bool:
        """
        将任务加入队列
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            priority: 优先级(1-10，默认5)
            estimated_duration: 预估处理时长(秒)
            
        Returns:
            bool: 是否成功加入队列
        """
        db = get_independent_db_session()
        try:
            config = self._get_queue_config(db)
            
            # 检查队列长度限制
            current_queue_length = db.query(TaskQueue).filter(
                TaskQueue.status.in_([QueueStatus.QUEUED, QueueStatus.PROCESSING])
            ).count()
            
            if current_queue_length >= config['max_queue_length']:
                logger.warning(f"队列已满，当前长度: {current_queue_length}")
                return False
            
            # 检查任务是否已在队列中
            existing = db.query(TaskQueue).filter(TaskQueue.task_id == task_id).first()
            if existing:
                logger.warning(f"任务 {task_id} 已在队列中，状态: {existing.status}")
                return False
            
            # 创建队列项
            queue_item = TaskQueue(
                task_id=task_id,
                user_id=user_id,
                priority=priority,
                status=QueueStatus.QUEUED,
                estimated_duration=estimated_duration,
                queued_at=datetime.utcnow()
            )
            
            db.add(queue_item)
            db.commit()
            
            logger.info(f"任务 {task_id} 已加入队列，用户 {user_id}，优先级 {priority}")
            return True
            
        except Exception as e:
            logger.error(f"任务 {task_id} 加入队列失败: {e}")
            db.rollback()
            return False
        finally:
            close_independent_db_session(db, f"enqueue_task_{task_id}")
    
    async def dequeue_task_for_processing(self) -> Optional[TaskQueue]:
        """
        为当前工作者出队一个任务开始处理
        
        Returns:
            TaskQueue: 分配的队列项，如果没有可用任务则返回None
        """
        db = get_independent_db_session()
        try:
            config = self._get_queue_config(db)
            
            # 检查系统并发限制
            current_processing = db.query(TaskQueue).filter(
                TaskQueue.status == QueueStatus.PROCESSING
            ).count()
            
            if current_processing >= config['system_max_concurrent_tasks']:
                return None
            
            # 获取可处理的任务，按优先级和队列时间排序
            # 优先级高的先处理，同优先级的按入队时间先进先出
            candidates = db.query(TaskQueue).filter(
                TaskQueue.status == QueueStatus.QUEUED
            ).order_by(
                desc(TaskQueue.priority),  # 优先级降序
                TaskQueue.queued_at.asc()  # 时间升序(FIFO)
            ).all()
            
            if not candidates:
                return None
            
            # 遍历候选任务，找到第一个用户未达并发限制的任务
            for candidate in candidates:
                # 检查用户并发限制
                user_processing_count = db.query(TaskQueue).filter(
                    and_(
                        TaskQueue.user_id == candidate.user_id,
                        TaskQueue.status == QueueStatus.PROCESSING
                    )
                ).count()
                
                if user_processing_count < config['user_max_concurrent_tasks']:
                    # 找到可处理的任务，跳出循环
                    break
                else:
                    logger.debug(f"跳过用户 {candidate.user_id} 的任务(并发限制已达上限: {user_processing_count})")
                    candidate = None  # 标记需要继续寻找
                    
            if not candidate:
                logger.debug("所有排队任务的用户都已达并发限制")
                return None
            
            # 分配任务给当前工作者
            candidate.status = QueueStatus.PROCESSING
            candidate.worker_id = self._worker_id
            candidate.started_at = datetime.utcnow()
            candidate.attempts += 1
            
            db.commit()
            
            logger.info(f"任务 {candidate.task_id} 已分配给工作者 {self._worker_id}")
            return candidate
            
        except Exception as e:
            logger.error(f"出队任务失败: {e}")
            db.rollback()
            return None
        finally:
            close_independent_db_session(db, f"dequeue_task_{self._worker_id}")
    
    async def complete_task(self, queue_item_id: int, success: bool = True, 
                          error_message: Optional[str] = None) -> bool:
        """
        标记任务完成
        
        Args:
            queue_item_id: 队列项ID
            success: 是否成功完成
            error_message: 错误信息(如果失败)
            
        Returns:
            bool: 是否成功更新状态
        """
        db = get_independent_db_session()
        try:
            queue_item = db.query(TaskQueue).filter(TaskQueue.id == queue_item_id).first()
            if not queue_item:
                logger.warning(f"队列项 {queue_item_id} 不存在")
                return False
            
            if queue_item.worker_id != self._worker_id:
                logger.warning(f"队列项 {queue_item_id} 不属于工作者 {self._worker_id}")
                return False
            
            # 更新状态
            queue_item.status = QueueStatus.COMPLETED if success else QueueStatus.FAILED
            queue_item.completed_at = datetime.utcnow()
            if error_message:
                queue_item.error_message = error_message
            
            db.commit()
            
            logger.info(f"任务 {queue_item.task_id} 已标记为 {'完成' if success else '失败'}")
            return True
            
        except Exception as e:
            logger.error(f"完成任务状态更新失败: {e}")
            db.rollback()
            return False
        finally:
            close_independent_db_session(db, f"complete_task_{queue_item_id}")
    
    async def check_user_concurrency_limit(self, user_id: int, requested_tasks: int = 1) -> Tuple[bool, Dict]:
        """
        检查用户并发限制
        
        Args:
            user_id: 用户ID
            requested_tasks: 请求的任务数量
            
        Returns:
            Tuple[bool, Dict]: (是否允许, 状态信息)
        """
        db = get_independent_db_session()
        try:
            config = self._get_queue_config(db)
            
            # 获取用户当前处理中的任务数
            user_processing = db.query(TaskQueue).filter(
                and_(
                    TaskQueue.user_id == user_id,
                    TaskQueue.status == QueueStatus.PROCESSING
                )
            ).count()
            
            user_limit = config['user_max_concurrent_tasks']
            available_slots = max(0, user_limit - user_processing)
            
            status_info = {
                'user_id': user_id,
                'current_processing': user_processing,
                'max_concurrent': user_limit,
                'available_slots': available_slots,
                'requested_tasks': requested_tasks
            }
            
            allowed = available_slots >= requested_tasks
            
            return allowed, status_info
            
        except Exception as e:
            logger.error(f"检查用户并发限制失败: {e}")
            return False, {'error': str(e)}
        finally:
            close_independent_db_session(db, f"check_user_limit_{user_id}")
    
    async def check_system_concurrency_limit(self, requested_tasks: int = 1) -> Tuple[bool, Dict]:
        """
        检查系统并发限制
        
        Args:
            requested_tasks: 请求的任务数量
            
        Returns:
            Tuple[bool, Dict]: (是否允许, 状态信息)
        """
        db = get_independent_db_session()
        try:
            config = self._get_queue_config(db)
            
            # 获取系统当前处理中的任务数
            system_processing = db.query(TaskQueue).filter(
                TaskQueue.status == QueueStatus.PROCESSING
            ).count()
            
            system_limit = config['system_max_concurrent_tasks']
            available_slots = max(0, system_limit - system_processing)
            
            status_info = {
                'current_processing': system_processing,
                'max_concurrent': system_limit,
                'available_slots': available_slots,
                'requested_tasks': requested_tasks
            }
            
            allowed = available_slots >= requested_tasks
            
            return allowed, status_info
            
        except Exception as e:
            logger.error(f"检查系统并发限制失败: {e}")
            return False, {'error': str(e)}
        finally:
            close_independent_db_session(db, f"check_system_limit")
    
    async def get_queue_status(self) -> Dict:
        """获取队列状态信息"""
        db = get_independent_db_session()
        try:
            # 统计各状态的任务数量
            status_counts = db.query(
                TaskQueue.status,
                func.count(TaskQueue.id)
            ).group_by(TaskQueue.status).all()
            
            status_dict = {status.value: 0 for status in QueueStatus}
            for status, count in status_counts:
                status_dict[status.value] = count
            
            # 获取用户并发统计
            user_concurrency = db.query(
                TaskQueue.user_id,
                func.count(TaskQueue.id)
            ).filter(
                TaskQueue.status == QueueStatus.PROCESSING
            ).group_by(TaskQueue.user_id).all()
            
            # 获取平均等待时间 - 数据库兼容版本
            try:
                # 使用SQLAlchemy ORM计算，避免数据库特定函数
                from sqlalchemy import case
                
                # 使用Python时间差计算而非数据库函数
                wait_times = db.query(
                    case(
                        (TaskQueue.started_at.isnot(None), TaskQueue.started_at),
                        else_=func.current_timestamp()
                    ).label('end_time'),
                    TaskQueue.queued_at
                ).filter(TaskQueue.status != QueueStatus.QUEUED).all()
                
                if wait_times:
                    total_wait_seconds = 0
                    count = 0
                    for end_time, queued_at in wait_times:
                        if end_time and queued_at:
                            wait_seconds = (end_time - queued_at).total_seconds()
                            total_wait_seconds += wait_seconds
                            count += 1
                    avg_wait_time = total_wait_seconds / count if count > 0 else 0
                else:
                    avg_wait_time = 0
                    
            except Exception as e:
                logger.warning(f"计算平均等待时间失败: {e}")
                avg_wait_time = 0
            
            return {
                'queue_counts': status_dict,
                'user_concurrency': dict(user_concurrency),
                'avg_wait_time_seconds': avg_wait_time or 0,
                'worker_id': self._worker_id
            }
            
        except Exception as e:
            logger.error(f"获取队列状态失败: {e}")
            return {'error': str(e)}
        finally:
            close_independent_db_session(db, "get_queue_status")
    
    async def cleanup_expired_tasks(self) -> int:
        """清理超时任务"""
        db = get_independent_db_session()
        try:
            config = self._get_queue_config(db)
            timeout_seconds = config['task_timeout']
            
            # 查找超时的处理中任务
            timeout_threshold = datetime.utcnow() - timedelta(seconds=timeout_seconds)
            
            expired_tasks = db.query(TaskQueue).filter(
                and_(
                    TaskQueue.status == QueueStatus.PROCESSING,
                    TaskQueue.started_at < timeout_threshold
                )
            ).all()
            
            cleanup_count = 0
            for task in expired_tasks:
                # 检查是否超过最大重试次数
                if task.attempts >= task.max_attempts:
                    task.status = QueueStatus.FAILED
                    task.error_message = f"任务超时，已达最大重试次数 {task.max_attempts}"
                else:
                    task.status = QueueStatus.QUEUED
                    task.worker_id = None
                    task.started_at = None
                    task.error_message = f"任务超时，重新排队 (尝试 {task.attempts}/{task.max_attempts})"
                
                cleanup_count += 1
            
            db.commit()
            
            if cleanup_count > 0:
                logger.info(f"清理了 {cleanup_count} 个超时任务")
            
            return cleanup_count
            
        except Exception as e:
            logger.error(f"清理超时任务失败: {e}")
            db.rollback()
            return 0
        finally:
            close_independent_db_session(db, "cleanup_expired_tasks")
    
    async def boost_priority_for_waiting_tasks(self) -> int:
        """为长时间等待的任务提升优先级"""
        db = get_independent_db_session()
        try:
            config = self._get_queue_config(db)
            threshold_seconds = config['priority_boost_threshold']
            
            # 查找等待时间超过阈值的任务
            threshold_time = datetime.utcnow() - timedelta(seconds=threshold_seconds)
            
            waiting_tasks = db.query(TaskQueue).filter(
                and_(
                    TaskQueue.status == QueueStatus.QUEUED,
                    TaskQueue.queued_at < threshold_time,
                    TaskQueue.priority < 10  # 最高优先级是10
                )
            ).all()
            
            boost_count = 0
            for task in waiting_tasks:
                old_priority = task.priority
                task.priority = min(10, task.priority + 1)  # 最多提升到10
                if task.priority != old_priority:
                    boost_count += 1
                    logger.debug(f"任务 {task.task_id} 优先级从 {old_priority} 提升到 {task.priority}")
            
            db.commit()
            
            if boost_count > 0:
                logger.info(f"为 {boost_count} 个长等待任务提升了优先级")
            
            return boost_count
            
        except Exception as e:
            logger.error(f"提升任务优先级失败: {e}")
            db.rollback()
            return 0
        finally:
            close_independent_db_session(db, "boost_priority")
    
    async def get_user_queue_status(self, user_id: int) -> Dict:
        """获取指定用户的队列状态"""
        db = get_independent_db_session()
        try:
            # 用户的队列统计
            user_tasks = db.query(TaskQueue).filter(TaskQueue.user_id == user_id).all()
            
            status_counts = {}
            for status in QueueStatus:
                status_counts[status.value] = sum(1 for task in user_tasks if task.status == status)
            
            # 计算预估等待时间
            queued_tasks = [task for task in user_tasks if task.status == QueueStatus.QUEUED]
            estimated_wait_time = 0
            
            if queued_tasks:
                # 简单估算：前面排队任务的预估处理时间总和
                for task in queued_tasks:
                    # 计算前面有多少个优先级更高或时间更早的任务
                    ahead_count = db.query(TaskQueue).filter(
                        and_(
                            TaskQueue.status == QueueStatus.QUEUED,
                            TaskQueue.user_id != user_id,  # 其他用户的任务
                            func.or_(
                                TaskQueue.priority > task.priority,
                                and_(
                                    TaskQueue.priority == task.priority,
                                    TaskQueue.queued_at < task.queued_at
                                )
                            )
                        )
                    ).count()
                    
                    estimated_wait_time += ahead_count * 300  # 假设每个任务平均5分钟
            
            return {
                'user_id': user_id,
                'queue_counts': status_counts,
                'estimated_wait_time_seconds': estimated_wait_time,
                'queued_tasks': len(queued_tasks)
            }
            
        except Exception as e:
            logger.error(f"获取用户 {user_id} 队列状态失败: {e}")
            return {'error': str(e)}
        finally:
            close_independent_db_session(db, f"user_queue_status_{user_id}")
    
    async def cancel_queued_task(self, task_id: int, user_id: int) -> bool:
        """
        取消排队中的任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID (用于权限检查)
            
        Returns:
            bool: 是否成功取消
        """
        db = get_independent_db_session()
        try:
            queue_item = db.query(TaskQueue).filter(
                and_(
                    TaskQueue.task_id == task_id,
                    TaskQueue.user_id == user_id,
                    TaskQueue.status == QueueStatus.QUEUED
                )
            ).first()
            
            if not queue_item:
                return False
            
            queue_item.status = QueueStatus.CANCELLED
            queue_item.completed_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(f"用户 {user_id} 取消了任务 {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"取消任务 {task_id} 失败: {e}")
            db.rollback()
            return False
        finally:
            close_independent_db_session(db, f"cancel_task_{task_id}")
    
    async def start_queue_worker(self):
        """启动队列工作者"""
        logger.info(f"队列工作者 {self._worker_id} 启动")
        
        while not self._shutdown_flag:
            try:
                # 清理超时任务
                await self.cleanup_expired_tasks()
                
                # 提升长等待任务的优先级
                await self.boost_priority_for_waiting_tasks()
                
                # 尝试获取并处理任务
                queue_item = await self.dequeue_task_for_processing()
                
                if queue_item:
                    await self._process_queue_task(queue_item)
                else:
                    # 没有任务时短暂等待
                    await asyncio.sleep(2)
                    
            except Exception as e:
                logger.error(f"队列工作者错误: {e}")
                await asyncio.sleep(5)  # 出错时等待更长时间
        
        logger.info(f"队列工作者 {self._worker_id} 已停止")
    
    async def _process_queue_task(self, queue_item: TaskQueue):
        """处理队列中的任务"""
        try:
            logger.info(f"开始处理队列任务 {queue_item.task_id}")
            
            # 这里调用实际的任务处理逻辑
            from app.services.new_task_processor import NewTaskProcessor
            processor = NewTaskProcessor()
            
            # 处理任务
            await processor.process_task(queue_item.task_id)
            
            # 标记任务完成
            await self.complete_task(queue_item.id, success=True)
            
        except Exception as e:
            logger.error(f"处理队列任务 {queue_item.task_id} 失败: {e}")
            
            # 标记任务失败
            await self.complete_task(queue_item.id, success=False, error_message=str(e))
    
    def shutdown(self):
        """停止队列工作者"""
        self._shutdown_flag = True
        logger.info(f"队列工作者 {self._worker_id} 收到停止信号")


# 全局队列服务实例
_queue_service_instance = None

def get_database_queue_service() -> DatabaseQueueService:
    """获取数据库队列服务实例（单例）"""
    global _queue_service_instance
    if _queue_service_instance is None:
        _queue_service_instance = DatabaseQueueService()
    return _queue_service_instance

async def initialize_queue_tables():
    """初始化队列表结构"""
    db = get_independent_db_session()
    try:
        # 确保表已创建
        from app.core.database import engine, Base
        Base.metadata.create_all(bind=engine)
        
        # 检查并插入默认配置
        existing_configs = db.query(QueueConfig.config_key).all()
        existing_keys = {config[0] for config in existing_configs}
        
        default_configs = [
            ('max_concurrent_users', '20', '系统最大支持并发用户数'),
            ('user_max_concurrent_tasks', '3', '单用户最大并发任务数'),
            ('system_max_concurrent_tasks', '60', '系统总最大并发任务数(20用户x3)'),
            ('worker_pool_size', '20', '工作者池大小'),
            ('queue_check_interval', '2', '队列检查间隔(秒)'),
            ('task_timeout', '600', '任务超时时间(秒)'),
            ('max_queue_length', '200', '最大队列长度'),
            ('priority_boost_threshold', '300', '等待超过此秒数的任务优先级自动提升')
        ]
        
        new_configs = []
        for key, value, desc in default_configs:
            if key not in existing_keys:
                new_configs.append(QueueConfig(
                    config_key=key,
                    config_value=value,
                    description=desc
                ))
        
        if new_configs:
            db.add_all(new_configs)
            db.commit()
            logger.info(f"插入了 {len(new_configs)} 个默认队列配置")
        
        return True
        
    except Exception as e:
        logger.error(f"初始化队列表失败: {e}")
        db.rollback()
        return False
    finally:
        close_independent_db_session(db, "initialize_queue_tables")