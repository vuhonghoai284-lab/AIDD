"""
任务恢复服务
处理系统重启后的任务恢复、任务调度和健康检查
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.core.database import SessionLocal, get_db
from app.models.task import Task
from app.repositories.task import TaskRepository
from app.repositories.ai_model import AIModelRepository
from app.services.concurrency_service import concurrency_service
from app.services.new_task_processor import NewTaskProcessor
from app.core.config import get_settings


logger = logging.getLogger(__name__)


class TaskRecoveryService:
    """任务恢复服务"""
    
    def __init__(self):
        self.settings = get_settings()
        self.processing_timeout = self.settings.task_processing_config.get('processing_timeout', 3600)  # 默认1小时
        self.recovery_enabled = self.settings.task_processing_config.get('recovery_enabled', True)
        
    async def recover_tasks_on_startup(self, db: Session = None) -> int:
        """
        系统启动时恢复任务
        
        Returns:
            恢复的任务数量
        """
        if not self.recovery_enabled:
            logger.info("任务恢复功能已禁用")
            return 0
            
        # 如果没有提供数据库会话，创建新的
        if db is None:
            db = SessionLocal()
            should_close_db = True
        else:
            should_close_db = False
            
        try:
            logger.info("🔄 开始系统启动任务恢复...")
            
            task_repo = TaskRepository(db)
            
            # 1. 重置僵尸处理任务
            zombie_count = await self._reset_zombie_processing_tasks(task_repo)
            
            # 2. 调度待处理任务
            scheduled_count = await self._schedule_pending_tasks(db, task_repo)
            
            total_recovered = zombie_count + scheduled_count
            
            logger.info(f"✅ 任务恢复完成: 重置僵尸任务 {zombie_count} 个，调度待处理任务 {scheduled_count} 个")
            
            return total_recovered
            
        except Exception as e:
            logger.error(f"❌ 任务恢复失败: {e}")
            raise
        finally:
            if should_close_db:
                db.close()
    
    async def _reset_zombie_processing_tasks(self, task_repo: TaskRepository) -> int:
        """
        重置僵尸处理任务（处理中但可能已停止的任务）
        
        Returns:
            重置的任务数量
        """
        try:
            # 查找可能的僵尸任务：状态为processing的所有任务（服务重启后，所有processing任务都是僵尸任务）
            # 这里不用时间判断，因为服务重启意味着所有processing任务都应该被重置
            zombie_tasks = task_repo.db.query(Task).filter(Task.status == 'processing').all()
            
            reset_count = 0
            for task in zombie_tasks:
                logger.warning(f"🧟 发现僵尸任务: {task.id} ({task.title})，标记为失败状态（服务重启导致中断）")
                task_repo.update(
                    task.id, 
                    status='failed', 
                    progress=0, 
                    error_message="服务重启导致任务中断，请手动重试"
                )
                reset_count += 1
            
            if reset_count > 0:
                logger.info(f"✅ 发现并重置了 {reset_count} 个僵尸任务（因服务重启中断）")
            
            return reset_count
            
        except Exception as e:
            logger.error(f"❌ 重置僵尸任务失败: {e}")
            return 0
    
    async def _schedule_pending_tasks(self, db: Session, task_repo: TaskRepository) -> int:
        """
        调度待处理任务
        
        Returns:
            调度的任务数量
        """
        try:
            # 获取所有待处理任务
            pending_tasks = task_repo.get_pending_tasks()
            
            if not pending_tasks:
                logger.info("没有待处理的任务")
                return 0
                
            logger.info(f"📋 发现 {len(pending_tasks)} 个待处理任务")
            
            scheduled_count = 0
            
            for task in pending_tasks:
                try:
                    # 检查系统并发限制
                    system_allowed, _ = concurrency_service.check_system_concurrency_limit(db, 1)
                    
                    if not system_allowed:
                        logger.info(f"🚦 系统并发限制已达上限，暂停调度剩余任务")
                        break
                    
                    # 检查用户并发限制（如果任务有用户ID）
                    if task.user_id:
                        from app.repositories.user import UserRepository
                        user_repo = UserRepository(db)
                        user = user_repo.get_by_id(task.user_id)
                        
                        if user:
                            user_allowed, _ = concurrency_service.check_user_concurrency_limit(db, user, 1)
                            if not user_allowed:
                                logger.info(f"🚦 用户 {user.uid} 并发限制已达上限，跳过任务 {task.id}")
                                continue
                    
                    # 启动任务处理
                    await self._start_task_processing(task.id)
                    scheduled_count += 1
                    logger.info(f"🚀 已调度任务: {task.id} ({task.title})")
                    
                    # 添加短暂延迟，避免过快启动任务
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"❌ 调度任务 {task.id} 失败: {e}")
                    continue
            
            logger.info(f"✅ 调度了 {scheduled_count} 个待处理任务")
            return scheduled_count
            
        except Exception as e:
            logger.error(f"❌ 调度待处理任务失败: {e}")
            return 0
    
    async def _start_task_processing(self, task_id: int):
        """启动任务处理"""
        try:
            processor = NewTaskProcessor()
            # 使用create_task在后台执行，不等待完成
            asyncio.create_task(processor.process_task(task_id))
        except Exception as e:
            logger.error(f"❌ 启动任务处理器失败 (task_id={task_id}): {e}")
            raise
    
    async def retry_task(self, task_id: int, db: Session = None) -> bool:
        """
        重试指定的任务
        
        Args:
            task_id: 任务ID
            db: 数据库会话（可选）
            
        Returns:
            是否成功启动重试
        """
        if db is None:
            db = SessionLocal()
            should_close_db = True
        else:
            should_close_db = False
            
        try:
            task_repo = TaskRepository(db)
            task = task_repo.get_by_id(task_id)
            
            if not task:
                logger.warning(f"❌ 重试失败: 任务 {task_id} 不存在")
                return False
            
            # 检查任务状态是否可重试
            if task.status not in ['failed', 'completed']:
                logger.warning(f"❌ 重试失败: 任务 {task_id} 状态为 {task.status}，不支持重试")
                return False
            
            logger.info(f"🔄 开始重试任务: {task_id} ({task.title})")
            
            # 重置任务状态
            task_repo.update(
                task_id, 
                status='pending', 
                progress=0, 
                error_message=None,
                completed_at=None,
                processing_time=None
            )
            
            # 清理相关数据（保留文件信息）
            await self._cleanup_task_results(task_id, db)
            
            # 检查并发限制
            system_allowed, _ = concurrency_service.check_system_concurrency_limit(db, 1)
            if not system_allowed:
                logger.info(f"🚦 系统并发限制已达上限，任务 {task_id} 已重置为pending状态，等待调度")
                return True
            
            # 检查用户并发限制
            if task.user_id:
                from app.repositories.user import UserRepository
                user_repo = UserRepository(db)
                user = user_repo.get_by_id(task.user_id)
                
                if user:
                    user_allowed, _ = concurrency_service.check_user_concurrency_limit(db, user, 1)
                    if not user_allowed:
                        logger.info(f"🚦 用户并发限制已达上限，任务 {task_id} 已重置为pending状态，等待调度")
                        return True
            
            # 立即启动处理
            await self._start_task_processing(task_id)
            logger.info(f"✅ 任务 {task_id} 重试启动成功")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 重试任务 {task_id} 失败: {e}")
            return False
        finally:
            if should_close_db:
                db.close()
    
    async def _cleanup_task_results(self, task_id: int, db: Session):
        """清理任务的结果数据（保留文件）"""
        try:
            # 删除任务相关的问题、AI输出和日志
            from app.models import Issue, AIOutput, TaskLog
            
            db.query(Issue).filter(Issue.task_id == task_id).delete()
            db.query(AIOutput).filter(AIOutput.task_id == task_id).delete()
            db.query(TaskLog).filter(TaskLog.task_id == task_id).delete()
            
            db.commit()
            logger.info(f"✅ 已清理任务 {task_id} 的历史结果数据")
            
        except Exception as e:
            logger.error(f"❌ 清理任务 {task_id} 结果数据失败: {e}")
            db.rollback()
    
    async def check_and_recover_timeout_tasks(self, db: Session = None) -> int:
        """
        检查并恢复超时任务
        
        Returns:
            恢复的任务数量
        """
        if db is None:
            db = SessionLocal()
            should_close_db = True
        else:
            should_close_db = False
            
        try:
            task_repo = TaskRepository(db)
            timeout_threshold = datetime.utcnow() - timedelta(seconds=self.processing_timeout)
            
            # 查找超时的处理中任务（基于created_at字段）
            timeout_tasks = task_repo.db.query(Task).filter(
                and_(
                    Task.status == 'processing',
                    Task.created_at < timeout_threshold
                )
            ).all()
            
            recovered_count = 0
            for task in timeout_tasks:
                logger.warning(f"⏰ 发现超时任务: {task.id} ({task.title})，标记为失败")
                task_repo.update(
                    task.id, 
                    status='failed', 
                    error_message=f"任务处理超时 (>{self.processing_timeout}秒)"
                )
                recovered_count += 1
            
            if recovered_count > 0:
                logger.info(f"✅ 恢复了 {recovered_count} 个超时任务")
            
            return recovered_count
            
        except Exception as e:
            logger.error(f"❌ 检查超时任务失败: {e}")
            return 0
        finally:
            if should_close_db:
                db.close()
    
    async def schedule_pending_tasks_if_available(self, db: Session = None) -> int:
        """
        在资源可用时调度待处理任务
        
        Returns:
            调度的任务数量
        """
        if db is None:
            db = SessionLocal()
            should_close_db = True
        else:
            should_close_db = False
            
        try:
            # 检查系统是否有可用资源
            system_allowed, system_info = concurrency_service.check_system_concurrency_limit(db, 1)
            
            if not system_allowed:
                return 0
                
            # 获取可用的并发槽位数
            available_slots = system_info['available_slots']
            
            # 调度待处理任务
            task_repo = TaskRepository(db)
            return await self._schedule_pending_tasks_with_limit(db, task_repo, available_slots)
            
        except Exception as e:
            logger.error(f"❌ 资源可用时调度任务失败: {e}")
            return 0
        finally:
            if should_close_db:
                db.close()
    
    async def _schedule_pending_tasks_with_limit(self, db: Session, task_repo: TaskRepository, max_tasks: int) -> int:
        """按限制调度待处理任务"""
        pending_tasks = task_repo.get_pending_tasks()
        
        if not pending_tasks:
            return 0
            
        scheduled_count = 0
        
        for task in pending_tasks[:max_tasks]:  # 限制调度数量
            try:
                # 检查用户并发限制
                if task.user_id:
                    from app.repositories.user import UserRepository
                    user_repo = UserRepository(db)
                    user = user_repo.get_by_id(task.user_id)
                    
                    if user:
                        user_allowed, _ = concurrency_service.check_user_concurrency_limit(db, user, 1)
                        if not user_allowed:
                            continue
                
                # 启动任务处理
                await self._start_task_processing(task.id)
                scheduled_count += 1
                
                # 短暂延迟
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"❌ 调度任务 {task.id} 失败: {e}")
                continue
        
        return scheduled_count
    
    def get_recovery_status(self, db: Session = None) -> Dict[str, Any]:
        """
        获取任务恢复状态信息
        
        Returns:
            恢复状态信息
        """
        if db is None:
            db = SessionLocal()
            should_close_db = True
        else:
            should_close_db = False
            
        try:
            task_repo = TaskRepository(db)
            
            # 统计各状态任务数量
            from sqlalchemy import func
            status_counts = task_repo.db.query(
                Task.status,
                func.count(Task.id).label('count')
            ).group_by(Task.status).all()
            
            status_dict = {status: count for status, count in status_counts}
            
            # 检查可能的僵尸任务
            timeout_threshold = datetime.utcnow() - timedelta(seconds=self.processing_timeout)
            potential_zombie_count = task_repo.db.query(Task).filter(
                and_(
                    Task.status == 'processing',
                    Task.created_at < timeout_threshold
                )
            ).count()
            
            return {
                'recovery_enabled': self.recovery_enabled,
                'processing_timeout': self.processing_timeout,
                'task_counts': status_dict,
                'potential_zombie_tasks': potential_zombie_count,
                'system_concurrency': concurrency_service.get_concurrency_status(db)
            }
            
        except Exception as e:
            logger.error(f"❌ 获取恢复状态失败: {e}")
            return {'error': str(e)}
        finally:
            if should_close_db:
                db.close()


# 创建全局实例
task_recovery_service = TaskRecoveryService()