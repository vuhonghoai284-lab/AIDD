"""
WebSocket真实场景集成测试
测试WebSocket在真实业务逻辑中的工作情况
"""
import pytest
import asyncio
import json
from typing import List, Dict, Any
from unittest.mock import AsyncMock, patch

from app.services.websocket import manager
from app.models.task import Task
from app.models.user import User
from app.services.new_task_processor import NewTaskProcessor as TaskProcessor
# 相对导入修复
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

# fixtures从conftest.py自动导入


class TestWebSocketRealScenario:
    """WebSocket真实场景测试"""
    
    @pytest.mark.asyncio
    async def test_websocket_task_processing_simulation(self):
        """测试WebSocket在任务处理中的完整流程"""
        
        # 模拟任务处理器发送日志消息
        task_id = 1  # 使用固定的task_id
        
        # 收集接收到的消息
        received_messages: List[Dict[str, Any]] = []
        
        # 模拟WebSocket连接
        class MockWebSocket:
            def __init__(self):
                self.messages = []
                
            async def accept(self):
                pass
                
            async def send_text(self, data: str):
                self.messages.append(json.loads(data))
                received_messages.append(json.loads(data))
                
            async def receive_text(self):
                # 模拟客户端发送ping
                await asyncio.sleep(0.1)
                return "ping"
        
        # 创建多个WebSocket连接模拟多个客户端
        connections = []
        for i in range(2):
            ws = MockWebSocket()
            connections.append(ws)
            await manager.connect(ws, task_id)
        
        # 模拟任务处理过程中的各种日志消息
        test_logs = [
            {"level": "INFO", "message": "开始处理文档", "stage": "初始化", "progress": 10},
            {"level": "INFO", "message": "正在分析文档结构", "stage": "预处理", "progress": 30},
            {"level": "WARNING", "message": "发现潜在问题", "stage": "分析", "progress": 60},
            {"level": "INFO", "message": "生成分析报告", "stage": "生成报告", "progress": 90},
            {"level": "INFO", "message": "任务完成", "stage": "完成", "progress": 100}
        ]
        
        # 发送测试日志
        for log_entry in test_logs:
            await manager.send_log(
                task_id=task_id,
                level=log_entry["level"],
                message=log_entry["message"],
                stage=log_entry["stage"],
                module="task_processor"
            )
            await manager.send_progress(task_id=task_id, progress=log_entry["progress"])
            await asyncio.sleep(0.1)  # 模拟处理时间
        
        # 验证所有连接都收到消息
        for ws in connections:
            assert len(ws.messages) > 0
        
        # 验证消息内容
        assert len(received_messages) >= len(test_logs) * 2  # 每条日志对应一条进度更新
        
        # 验证日志消息格式
        log_messages = [msg for msg in received_messages if msg.get("type") == "log"]
        progress_messages = [msg for msg in received_messages if msg.get("type") == "progress"]
        
        assert len(log_messages) >= len(test_logs)
        assert len(progress_messages) >= len(test_logs)
        
        # 验证特定日志内容
        start_msg = next((msg for msg in log_messages if "开始处理" in msg["message"]), None)
        assert start_msg is not None
        assert start_msg["level"] == "INFO"
        assert start_msg["stage"] == "初始化"
        
        # 清理连接
        for ws in connections:
            await manager.disconnect(ws, task_id)
    
    @pytest.mark.asyncio
    async def test_websocket_concurrent_connections(self):
        """测试WebSocket并发连接处理"""
        
        task_id = 2
        connection_count = 5
        connections = []
        
        # 创建多个并发连接
        for i in range(connection_count):
            class MockWebSocket:
                def __init__(self, conn_id):
                    self.conn_id = conn_id
                    self.messages = []
                    
                async def accept(self):
                    pass
                    
                async def send_text(self, data: str):
                    self.messages.append(json.loads(data))
            
            ws = MockWebSocket(i)
            connections.append(ws)
            await manager.connect(ws, task_id)
        
        # 验证所有连接都已注册
        assert task_id in manager.active_connections
        assert len(manager.active_connections[task_id]) == connection_count
        
        # 发送广播消息
        await manager.send_log(task_id, "INFO", "并发测试消息", module="test")
        
        await asyncio.sleep(0.1)
        
        # 验证所有连接都收到消息
        for ws in connections:
            assert len(ws.messages) > 0
            assert any(msg["message"] == "并发测试消息" for msg in ws.messages)
        
        # 清理连接
        for ws in connections:
            await manager.disconnect(ws, task_id)
        
        # 验证连接已清理
        assert task_id not in manager.active_connections or not manager.active_connections[task_id]
    
    @pytest.mark.asyncio
    async def test_websocket_connection_cleanup_on_error(self):
        """测试WebSocket连接在错误时的清理"""
        
        task_id = 3
        
        # 创建一个会抛出异常的WebSocket
        class FaultyWebSocket:
            def __init__(self):
                self.messages = []
                
            async def accept(self):
                pass
                
            async def send_text(self, data: str):
                raise ConnectionResetError("Connection lost")
        
        faulty_ws = FaultyWebSocket()
        await manager.connect(faulty_ws, task_id)
        
        # 验证连接已注册
        assert task_id in manager.active_connections
        assert len(manager.active_connections[task_id]) == 1
        
        # 尝试发送消息（应该触发清理）
        await manager.send_log(task_id, "INFO", "测试错误处理", module="test")
        
        await asyncio.sleep(0.1)
        
        # 验证故障连接已被清理
        assert task_id not in manager.active_connections or not manager.active_connections[task_id]
    
    @pytest.mark.asyncio
    async def test_websocket_message_formatting(self):
        """测试WebSocket消息格式化"""
        
        task_id = 4
        
        class MockWebSocket:
            def __init__(self):
                self.messages = []
                
            async def accept(self):
                pass
                
            async def send_text(self, data: str):
                self.messages.append(json.loads(data))
        
        ws = MockWebSocket()
        await manager.connect(ws, task_id)
        
        # 测试不同类型的消息
        await manager.send_log(task_id, "ERROR", "错误消息", stage="测试阶段", module="test")
        await manager.send_progress(task_id, 75, "进度测试")
        await manager.send_status(task_id, "processing")
        
        await asyncio.sleep(0.1)
        
        # 验证消息格式
        assert len(ws.messages) >= 3
        
        log_msg = next((msg for msg in ws.messages if msg["type"] == "log"), None)
        assert log_msg is not None
        assert log_msg["level"] == "ERROR"
        assert log_msg["message"] == "错误消息"
        assert log_msg["stage"] == "测试阶段"
        assert log_msg["module"] == "test"
        assert "timestamp" in log_msg
        
        progress_msg = next((msg for msg in ws.messages if msg["type"] == "progress"), None)
        assert progress_msg is not None
        assert progress_msg["progress"] == 75
        assert progress_msg["stage"] == "进度测试"
        
        status_msg = next((msg for msg in ws.messages if msg["type"] == "status"), None)
        assert status_msg is not None
        assert status_msg["status"] == "processing"
        
        await manager.disconnect(ws, task_id)
    
    @pytest.mark.asyncio
    async def test_websocket_large_message_handling(self):
        """测试WebSocket大消息处理"""
        
        task_id = 5
        
        class MockWebSocket:
            def __init__(self):
                self.messages = []
                
            async def accept(self):
                pass
                
            async def send_text(self, data: str):
                self.messages.append(json.loads(data))
        
        ws = MockWebSocket()
        await manager.connect(ws, task_id)
        
        # 发送大消息
        large_message = "大型数据处理结果: " + "X" * 1000  # 1KB消息
        await manager.send_log(task_id, "INFO", large_message, module="processor")
        
        await asyncio.sleep(0.1)
        
        # 验证大消息正确处理
        assert len(ws.messages) > 0
        received_msg = ws.messages[0]
        assert received_msg["message"] == large_message
        assert received_msg["type"] == "log"
        
        await manager.disconnect(ws, task_id)
    
    def test_websocket_manager_singleton(self):
        """测试WebSocket管理器单例模式"""
        from app.services.websocket import manager as manager1
        from app.services.websocket import manager as manager2
        
        # 验证是同一个实例
        assert manager1 is manager2
        assert id(manager1) == id(manager2)
    
    @pytest.mark.asyncio
    async def test_websocket_task_not_exists_handling(self):
        """测试WebSocket处理不存在的任务"""
        
        non_existent_task_id = 999999
        
        class MockWebSocket:
            def __init__(self):
                self.messages = []
                
            async def accept(self):
                pass
                
            async def send_text(self, data: str):
                self.messages.append(json.loads(data))
        
        ws = MockWebSocket()
        await manager.connect(ws, non_existent_task_id)
        
        # 即使任务不存在，WebSocket连接也应该正常工作
        await manager.send_log(non_existent_task_id, "INFO", "测试不存在任务", module="test")
        
        await asyncio.sleep(0.1)
        
        # 验证消息正常发送
        assert len(ws.messages) > 0
        assert ws.messages[0]["message"] == "测试不存在任务"
        
        await manager.disconnect(ws, non_existent_task_id)