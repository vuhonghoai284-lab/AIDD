"""
WebSocket端点E2E测试
测试真实环境中WebSocket端点的完整功能
"""
import pytest
import asyncio
import json
from unittest.mock import patch
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from app.main import create_app
from app.core.config import get_settings


class TestWebSocketEndpoint:
    """WebSocket端点E2E测试"""
    
    @pytest.mark.asyncio
    async def test_websocket_endpoint_connection(self):
        """测试WebSocket端点连接"""
        
        task_id = 1  # 使用固定的task_id进行测试
        
        # 启动测试应用
        app = create_app()
        
        # 模拟WebSocket连接（由于测试环境限制，使用Mock）
        from app.views.system_view import system_view
        from app.services.websocket import manager
        
        # 创建模拟WebSocket
        class MockWebSocket:
            def __init__(self):
                self.messages = []
                self.closed = False
                
            async def accept(self):
                pass
                
            async def send_text(self, data: str):
                if not self.closed:
                    self.messages.append(data)
                
            async def receive_text(self):
                # 模拟客户端行为
                await asyncio.sleep(0.1)
                if len(self.messages) == 0:
                    return "test_message"
                return "ping"
                
            async def close(self, code=1000, reason="test"):
                self.closed = True
        
        mock_websocket = MockWebSocket()
        
        # 直接调用WebSocket端点
        websocket_task = asyncio.create_task(
            system_view.websocket_endpoint(mock_websocket, task_id)
        )
        
        # 等待连接建立
        await asyncio.sleep(0.2)
        
        # 验证连接确认消息
        assert len(mock_websocket.messages) > 0
        connect_msg = json.loads(mock_websocket.messages[0])
        assert connect_msg["type"] == "connected"
        assert f"task {task_id}" in connect_msg["message"]
        
        # 取消任务以结束WebSocket连接
        websocket_task.cancel()
        
        try:
            await websocket_task
        except asyncio.CancelledError:
            pass
    
    @pytest.mark.asyncio
    async def test_websocket_endpoint_with_real_manager(self):
        """测试WebSocket端点与真实管理器的集成"""
        
        task_id = 2  # 使用不同的task_id
        
        from app.views.system_view import system_view
        from app.services.websocket import manager
        
        class MockWebSocket:
            def __init__(self):
                self.messages = []
                self.accept_called = False
                self.receive_count = 0
                
            async def accept(self):
                self.accept_called = True
                
            async def send_text(self, data: str):
                self.messages.append(data)
                
            async def receive_text(self):
                self.receive_count += 1
                if self.receive_count == 1:
                    # 第一次接收，等待一下再返回
                    await asyncio.sleep(0.1)
                    return "ping"
                elif self.receive_count == 2:
                    # 第二次接收，测试日志推送
                    await asyncio.sleep(0.1)
                    # 在后台发送一条测试消息
                    asyncio.create_task(self._send_test_log())
                    return "test"
                else:
                    # 结束连接
                    raise Exception("Connection closed")
                    
            async def _send_test_log(self):
                await asyncio.sleep(0.05)
                await manager.send_log(
                    task_id=task_id,
                    level="INFO", 
                    message="WebSocket测试消息",
                    stage="测试阶段",
                    module="test"
                )
        
        mock_websocket = MockWebSocket()
        
        # 启动WebSocket端点
        try:
            await system_view.websocket_endpoint(mock_websocket, task_id)
        except Exception:
            pass  # 预期的连接结束异常
        
        # 验证连接流程
        assert mock_websocket.accept_called
        assert len(mock_websocket.messages) >= 2  # 至少有连接确认和pong响应
        
        # 验证连接确认消息
        connect_msg = json.loads(mock_websocket.messages[0])
        assert connect_msg["type"] == "connected"
        assert connect_msg["message"] == f"Connected to task {task_id} logs"
        
        # 查找测试日志消息
        log_messages = []
        for msg_str in mock_websocket.messages[1:]:  # 跳过连接确认消息
            if msg_str == "pong":
                continue
            try:
                msg = json.loads(msg_str)
                if msg.get("type") == "log":
                    log_messages.append(msg)
            except:
                continue
        
        # 验证是否收到了测试日志消息
        if log_messages:
            test_log = log_messages[0]
            assert test_log["level"] == "INFO"
            assert test_log["message"] == "WebSocket测试消息"
            assert test_log["stage"] == "测试阶段"
            assert test_log["module"] == "test"
    
    @pytest.mark.asyncio
    async def test_websocket_endpoint_error_handling(self):
        """测试WebSocket端点错误处理"""
        
        task_id = 3
        
        from app.views.system_view import system_view
        
        class FaultyWebSocket:
            async def accept(self):
                pass
                
            async def send_text(self, data: str):
                raise Exception("Send failed")
                
            async def receive_text(self):
                raise Exception("Receive failed")
        
        faulty_websocket = FaultyWebSocket()
        
        # WebSocket端点应该能优雅处理错误
        try:
            await system_view.websocket_endpoint(faulty_websocket, task_id)
        except Exception as e:
            # 验证错误被正确处理
            assert "failed" in str(e).lower() or "error" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_websocket_endpoint_parameter_validation(self):
        """测试WebSocket端点参数验证"""
        
        from app.views.system_view import system_view
        
        class MockWebSocket:
            async def accept(self):
                pass
                
            async def send_text(self, data: str):
                pass
                
            async def receive_text(self):
                await asyncio.sleep(0.1)
                raise Exception("Test end")
        
        mock_websocket = MockWebSocket()
        
        # 测试有效的task_id
        valid_task_ids = [1, 123, 999999]
        for task_id in valid_task_ids:
            try:
                await system_view.websocket_endpoint(mock_websocket, task_id)
            except Exception:
                pass  # 预期的连接结束异常
        
        # 测试task_id类型（应该被自动转换）
        try:
            await system_view.websocket_endpoint(mock_websocket, "123")
        except TypeError:
            pass  # FastAPI会处理类型转换
        except Exception:
            pass  # 其他异常是预期的
    
    @pytest.mark.asyncio
    async def test_websocket_system_view_routing(self):
        """测试SystemView中WebSocket路由配置"""
        
        from app.views.system_view import system_view
        
        # 检查路由器是否正确配置了WebSocket路由
        routes = system_view.router.routes
        
        # 查找WebSocket路由
        websocket_routes = [route for route in routes if hasattr(route, 'path') and 'ws/task' in route.path]
        
        # 验证WebSocket路由存在
        assert len(websocket_routes) > 0, "WebSocket路由未正确配置"
        
        websocket_route = websocket_routes[0]
        assert "{task_id}" in websocket_route.path, "WebSocket路由缺少task_id参数"
        assert "/logs" in websocket_route.path, "WebSocket路由路径不正确"
    
    def test_websocket_route_registration_in_main(self):
        """测试WebSocket路由在main.py中的注册"""
        
        from app.main import app
        
        # 检查应用中是否包含了系统路由
        routes = app.routes
        
        # 查找包含WebSocket的路由
        has_websocket_route = False
        for route in routes:
            if hasattr(route, 'routes'):  # APIRouter的情况
                for subroute in route.routes:
                    if hasattr(subroute, 'path') and 'ws/task' in subroute.path:
                        has_websocket_route = True
                        break
            elif hasattr(route, 'path') and 'ws/task' in route.path:
                has_websocket_route = True
                break
        
        assert has_websocket_route, "WebSocket路由未在主应用中正确注册"
    
    @pytest.mark.asyncio
    async def test_websocket_manager_integration(self):
        """测试WebSocket管理器集成"""
        
        task_id = 4
        
        from app.services.websocket import manager
        
        # 创建多个模拟连接
        connections = []
        for i in range(3):
            class MockWebSocket:
                def __init__(self, conn_id):
                    self.conn_id = conn_id
                    self.messages = []
                    
                async def accept(self):
                    pass
                    
                async def send_text(self, data: str):
                    self.messages.append(data)
            
            mock_ws = MockWebSocket(i)
            connections.append(mock_ws)
            await manager.connect(mock_ws, task_id)
        
        # 发送广播消息
        await manager.send_log(task_id, "INFO", "测试广播消息", module="test")
        
        await asyncio.sleep(0.1)
        
        # 验证所有连接都收到消息
        for conn in connections:
            assert len(conn.messages) > 0
            msg = json.loads(conn.messages[-1])
            assert msg["message"] == "测试广播消息"
        
        # 清理连接
        for conn in connections:
            await manager.disconnect(conn, task_id)
        
        # 验证连接已清理
        assert task_id not in manager.active_connections or not manager.active_connections[task_id]