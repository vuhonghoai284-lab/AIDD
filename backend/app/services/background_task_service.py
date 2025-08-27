"""
后台任务服务
定期检查和恢复超时任务、僵尸任务等
"""
import asyncio
import logging
from typing import Optional
from app.services.task_recovery_service import task_recovery_service
from app.core.database import SessionLocal
from app.core.config import get_settings


logger = logging.getLogger(__name__)


class BackgroundTaskService:
    """后台任务服务"""
    
    def __init__(self):
        self.settings = get_settings()
        self.running = False
        self.task = None
        
        # 从配置获取检查间隔
        task_config = self.settings.task_processing_config
        self.check_interval = task_config.get('zombie_detection_interval', 300)  # 默认5分钟
        
    async def start(self):
        """启动后台服务"""
        if self.running:
            logger.warning("后台任务服务已经在运行中")
            return
            
        self.running = True
        self.task = asyncio.create_task(self._background_loop())
        logger.info(f"🚀 后台任务服务已启动，检查间隔: {self.check_interval}秒")
    
    async def stop(self):
        """停止后台服务"""
        if not self.running:
            return
            
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 后台任务服务已停止")
    
    async def _background_loop(self):
        """后台循环检查任务"""
        while self.running:
            try:
                await self._check_and_recover_tasks()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ 后台任务检查失败: {e}")
                await asyncio.sleep(60)  # 出错时等待1分钟再重试
    
    async def _check_and_recover_tasks(self):
        """检查和恢复任务"""
        db = SessionLocal()
        try:
            # 检查超时任务
            timeout_count = await task_recovery_service.check_and_recover_timeout_tasks(db)
            if timeout_count > 0:
                logger.info(f"🔧 检查到 {timeout_count} 个超时任务并已处理")
            
            # 调度待处理任务（如果有可用资源）
            scheduled_count = await task_recovery_service.schedule_pending_tasks_if_available(db)
            if scheduled_count > 0:
                logger.info(f"📋 调度了 {scheduled_count} 个待处理任务")
                
        except Exception as e:
            logger.error(f"❌ 定期任务检查失败: {e}")
        finally:
            db.close()


# 创建全局实例
background_task_service = BackgroundTaskService()