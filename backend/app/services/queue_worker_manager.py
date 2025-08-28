"""
队列工作者管理器
管理20个工作者池，支持20用户×3并发任务调度
"""
import asyncio
import logging
from typing import List, Dict, Set, Optional
from contextlib import asynccontextmanager

from app.services.database_queue_service import DatabaseQueueService

logger = logging.getLogger(__name__)


class QueueWorkerManager:
    """队列工作者管理器 - 管理工作者池生命周期"""
    
    def __init__(self, worker_pool_size: int = 20):
        self.worker_pool_size = worker_pool_size
        self.workers: List[DatabaseQueueService] = []
        self.worker_tasks: List[asyncio.Task] = []
        self._shutdown_flag = False
        self._manager_task: Optional[asyncio.Task] = None
        
    async def start_worker_pool(self):
        """启动工作者池"""
        logger.info(f"启动队列工作者池，大小: {self.worker_pool_size}")
        
        # 创建工作者实例
        for i in range(self.worker_pool_size):
            worker = DatabaseQueueService()
            self.workers.append(worker)
            
            # 启动工作者任务
            worker_task = asyncio.create_task(
                worker.start_queue_worker(),
                name=f"queue_worker_{i}"
            )
            self.worker_tasks.append(worker_task)
        
        # 启动管理器任务
        self._manager_task = asyncio.create_task(
            self._manager_loop(),
            name="queue_worker_manager"
        )
        
        logger.info(f"队列工作者池已启动，{len(self.workers)} 个工作者运行中")
    
    async def _manager_loop(self):
        """管理器主循环 - 监控工作者状态"""
        while not self._shutdown_flag:
            try:
                # 检查工作者健康状态
                await self._health_check_workers()
                
                # 监控队列状态
                await self._monitor_queue_metrics()
                
                # 等待下一次检查
                await asyncio.sleep(30)  # 30秒检查一次
                
            except Exception as e:
                logger.error(f"工作者管理器循环错误: {e}")
                await asyncio.sleep(10)
    
    async def _health_check_workers(self):
        """健康检查工作者"""
        dead_workers = []
        
        for i, task in enumerate(self.worker_tasks):
            if task.done():
                try:
                    await task
                except Exception as e:
                    logger.error(f"工作者 {i} 异常退出: {e}")
                
                dead_workers.append(i)
        
        # 重启死亡的工作者
        for worker_idx in dead_workers:
            logger.warning(f"重启工作者 {worker_idx}")
            
            # 创建新的工作者
            new_worker = DatabaseQueueService()
            self.workers[worker_idx] = new_worker
            
            # 启动新的工作者任务
            new_task = asyncio.create_task(
                new_worker.start_queue_worker(),
                name=f"queue_worker_{worker_idx}_restarted"
            )
            self.worker_tasks[worker_idx] = new_task
    
    async def _monitor_queue_metrics(self):
        """监控队列指标"""
        try:
            # 使用第一个工作者获取队列状态
            if self.workers:
                status = await self.workers[0].get_queue_status()
                
                queued_count = status.get('queue_counts', {}).get('queued', 0)
                processing_count = status.get('queue_counts', {}).get('processing', 0)
                
                # 如果队列积压严重，记录警告
                if queued_count > 50:
                    logger.warning(f"队列积压严重: {queued_count} 个任务排队")
                
                # 如果处理中任务数异常，记录信息
                if processing_count == 0 and queued_count > 0:
                    logger.warning(f"异常: 有 {queued_count} 个排队任务但没有处理中的任务")
                elif processing_count > 60:
                    logger.warning(f"异常: 处理中任务数超过系统限制: {processing_count}")
                
                # 定期打印状态摘要
                logger.info(f"队列状态摘要: 排队 {queued_count}, 处理中 {processing_count}")
                
        except Exception as e:
            logger.error(f"监控队列指标失败: {e}")
    
    async def shutdown_worker_pool(self, timeout: int = 60):
        """优雅关闭工作者池"""
        logger.info("开始关闭队列工作者池...")
        
        self._shutdown_flag = True
        
        # 停止管理器任务
        if self._manager_task and not self._manager_task.done():
            self._manager_task.cancel()
            try:
                await asyncio.wait_for(self._manager_task, timeout=5)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        
        # 通知所有工作者停止
        for worker in self.workers:
            worker.shutdown()
        
        # 等待工作者任务完成
        if self.worker_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.worker_tasks, return_exceptions=True),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.warning(f"工作者关闭超时 {timeout}s，强制取消")
                
                # 强制取消未完成的任务
                for task in self.worker_tasks:
                    if not task.done():
                        task.cancel()
        
        logger.info("队列工作者池已关闭")
    
    async def get_worker_pool_status(self) -> Dict:
        """获取工作者池状态"""
        alive_workers = sum(1 for task in self.worker_tasks if not task.done())
        
        # 获取队列状态
        queue_status = {}
        if self.workers:
            try:
                queue_status = await self.workers[0].get_queue_status()
            except Exception as e:
                logger.error(f"获取队列状态失败: {e}")
                queue_status = {'error': str(e)}
        
        return {
            'worker_pool_size': self.worker_pool_size,
            'alive_workers': alive_workers,
            'dead_workers': self.worker_pool_size - alive_workers,
            'manager_running': self._manager_task is not None and not self._manager_task.done(),
            'queue_status': queue_status
        }


# 全局工作者管理器实例
_worker_manager_instance = None

def get_queue_worker_manager() -> QueueWorkerManager:
    """获取队列工作者管理器实例（单例）"""
    global _worker_manager_instance
    if _worker_manager_instance is None:
        _worker_manager_instance = QueueWorkerManager()
    return _worker_manager_instance


@asynccontextmanager
async def queue_worker_lifespan():
    """队列工作者生命周期管理器 - 用于FastAPI应用启动/关闭"""
    manager = get_queue_worker_manager()
    
    try:
        # 初始化队列表
        from app.services.database_queue_service import initialize_queue_tables
        await initialize_queue_tables()
        
        # 启动工作者池
        await manager.start_worker_pool()
        
        logger.info("队列系统启动完成")
        yield
        
    finally:
        # 关闭工作者池
        await manager.shutdown_worker_pool()
        logger.info("队列系统已关闭")