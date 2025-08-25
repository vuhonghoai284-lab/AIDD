"""
WebSocket服务 - 实时日志推送
"""
import json
import asyncio
from typing import Dict, Set
from fastapi import WebSocket
from datetime import datetime


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 存储每个任务的WebSocket连接
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        self.lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, task_id: int):
        """接受新的WebSocket连接"""
        await websocket.accept()
        async with self.lock:
            if task_id not in self.active_connections:
                self.active_connections[task_id] = set()
            self.active_connections[task_id].add(websocket)
    
    async def disconnect(self, websocket: WebSocket, task_id: int):
        """断开WebSocket连接"""
        async with self.lock:
            if task_id in self.active_connections:
                self.active_connections[task_id].discard(websocket)
                if not self.active_connections[task_id]:
                    del self.active_connections[task_id]
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """发送个人消息"""
        try:
            await websocket.send_text(message)
        except:
            pass  # 忽略发送失败
    
    async def broadcast_to_task(self, task_id: int, message: dict):
        """向任务的所有连接广播消息"""
        if task_id in self.active_connections:
            message_json = json.dumps(message, ensure_ascii=False)
            # 复制连接集合以避免在迭代时修改
            connections = list(self.active_connections[task_id])
            for connection in connections:
                try:
                    await connection.send_text(message_json)
                except:
                    # 如果发送失败，从活动连接中移除
                    await self.disconnect(connection, task_id)
    
    async def send_log(self, task_id: int, level: str, message: str, 
                      stage: str = None, progress: int = None, module: str = "system"):
        """发送日志消息"""
        # 过滤空消息，避免产生空行
        if not message or not str(message).strip():
            return
            
        log_data = {
            "type": "log",
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "module": module,
            "stage": stage,
            "message": str(message).strip(),
            "progress": progress
        }
        await self.broadcast_to_task(task_id, log_data)
    
    async def send_progress(self, task_id: int, progress: int, stage: str = None):
        """发送进度更新"""
        progress_data = {
            "type": "progress",
            "timestamp": datetime.now().isoformat(),
            "progress": progress,
            "stage": stage
        }
        await self.broadcast_to_task(task_id, progress_data)
    
    async def send_status(self, task_id: int, status: str):
        """发送状态更新"""
        status_data = {
            "type": "status",
            "timestamp": datetime.now().isoformat(),
            "status": status
        }
        await self.broadcast_to_task(task_id, status_data)


# 全局连接管理器实例
manager = ConnectionManager()