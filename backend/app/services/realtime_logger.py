"""实时日志服务 - 将日志实时发送到前端"""
import json
import logging
import asyncio
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from enum import Enum


class LogLevel(str, Enum):
    """日志级别枚举"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogMessage:
    """日志消息模型"""
    
    def __init__(
        self, 
        level: LogLevel, 
        message: str, 
        timestamp: Optional[datetime] = None,
        context: Optional[Dict[str, Any]] = None,
        task_id: Optional[int] = None,
        operation: Optional[str] = None
    ):
        self.level = level
        self.message = message
        self.timestamp = timestamp or datetime.now()
        self.context = context or {}
        self.task_id = task_id
        self.operation = operation
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "level": self.level.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
            "task_id": self.task_id,
            "operation": self.operation
        }
    
    def to_json(self) -> str:
        """转换为JSON格式"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class RealtimeLogger:
    """实时日志服务"""
    
    def __init__(self):
        self.subscribers: List[Callable] = []
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        
        # 创建标准日志记录器
        self.logger = logging.getLogger("realtime_logger")
        self.logger.setLevel(logging.DEBUG)
        
        # 确保有控制台处理器
        if not self.logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
    
    async def start(self):
        """启动实时日志服务"""
        if not self.is_running:
            self.is_running = True
            self._task = asyncio.create_task(self._process_messages())
            self.logger.info("🚀 实时日志服务启动")
    
    async def stop(self):
        """停止实时日志服务"""
        if self.is_running:
            self.is_running = False
            if self._task:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            self.logger.info("🛑 实时日志服务停止")
    
    def subscribe(self, callback: Callable[[LogMessage], None]):
        """订阅日志消息"""
        self.subscribers.append(callback)
        self.logger.debug(f"📝 新增日志订阅者，当前订阅者数量: {len(self.subscribers)}")
    
    def unsubscribe(self, callback: Callable[[LogMessage], None]):
        """取消订阅日志消息"""
        if callback in self.subscribers:
            self.subscribers.remove(callback)
            self.logger.debug(f"📝 移除日志订阅者，当前订阅者数量: {len(self.subscribers)}")
    
    async def log(
        self, 
        level: LogLevel, 
        message: str, 
        context: Optional[Dict[str, Any]] = None,
        task_id: Optional[int] = None,
        operation: Optional[str] = None
    ):
        """发送日志消息"""
        log_message = LogMessage(
            level=level,
            message=message,
            context=context,
            task_id=task_id,
            operation=operation
        )
        
        # 同时输出到标准日志
        getattr(self.logger, level.value)(f"[Task {task_id}] {message}")
        
        # 放入队列等待处理
        await self.message_queue.put(log_message)
    
    async def debug(self, message: str, **kwargs):
        """发送DEBUG级别日志"""
        await self.log(LogLevel.DEBUG, message, **kwargs)
    
    async def info(self, message: str, **kwargs):
        """发送INFO级别日志"""
        await self.log(LogLevel.INFO, message, **kwargs)
    
    async def warning(self, message: str, **kwargs):
        """发送WARNING级别日志"""
        await self.log(LogLevel.WARNING, message, **kwargs)
    
    async def error(self, message: str, **kwargs):
        """发送ERROR级别日志"""
        await self.log(LogLevel.ERROR, message, **kwargs)
    
    async def critical(self, message: str, **kwargs):
        """发送CRITICAL级别日志"""
        await self.log(LogLevel.CRITICAL, message, **kwargs)
    
    async def _process_messages(self):
        """处理日志消息队列"""
        while self.is_running:
            try:
                # 等待新消息
                log_message = await asyncio.wait_for(
                    self.message_queue.get(), 
                    timeout=1.0
                )
                
                # 通知所有订阅者
                for callback in self.subscribers:
                    try:
                        # 如果回调是协程函数，使用await
                        if asyncio.iscoroutinefunction(callback):
                            await callback(log_message)
                        else:
                            callback(log_message)
                    except Exception as e:
                        self.logger.error(f"❌ 日志回调执行失败: {str(e)}")
                
                # 标记消息已处理
                self.message_queue.task_done()
                
            except asyncio.TimeoutError:
                # 超时是正常的，继续循环
                continue
            except Exception as e:
                self.logger.error(f"❌ 处理日志消息时出错: {str(e)}")


class TaskLoggerAdapter:
    """任务专用日志适配器"""
    
    def __init__(self, realtime_logger: RealtimeLogger, task_id: int, operation: str = ""):
        self.realtime_logger = realtime_logger
        self.task_id = task_id
        self.operation = operation
    
    async def debug(self, message: str, context: Optional[Dict[str, Any]] = None):
        """发送DEBUG日志"""
        await self.realtime_logger.debug(
            message, 
            context=context, 
            task_id=self.task_id, 
            operation=self.operation
        )
    
    async def info(self, message: str, context: Optional[Dict[str, Any]] = None):
        """发送INFO日志"""
        await self.realtime_logger.info(
            message, 
            context=context, 
            task_id=self.task_id, 
            operation=self.operation
        )
    
    async def warning(self, message: str, context: Optional[Dict[str, Any]] = None):
        """发送WARNING日志"""
        await self.realtime_logger.warning(
            message, 
            context=context, 
            task_id=self.task_id, 
            operation=self.operation
        )
    
    async def error(self, message: str, context: Optional[Dict[str, Any]] = None):
        """发送ERROR日志"""
        await self.realtime_logger.error(
            message, 
            context=context, 
            task_id=self.task_id, 
            operation=self.operation
        )
    
    async def critical(self, message: str, context: Optional[Dict[str, Any]] = None):
        """发送CRITICAL日志"""
        await self.realtime_logger.critical(
            message, 
            context=context, 
            task_id=self.task_id, 
            operation=self.operation
        )


# 创建全局实时日志服务实例
realtime_logger = RealtimeLogger()