"""
系统相关视图
"""
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
import json

from app.core.database import get_db
from app.core.config import get_settings
from app.services.model_initializer import model_initializer
from app.services.websocket import manager
from app.dto.model import ModelsResponse, ModelInfo


class SystemView:
    """系统视图类"""
    
    def __init__(self):
        self.router = APIRouter(tags=["system"])
        self.settings = get_settings()
        self._setup_routes()
    
    def _setup_routes(self):
        """设置路由"""
        self.router.add_api_route("/", self.root, methods=["GET"])
        self.router.add_api_route("/api/config", self.get_client_config, methods=["GET"])
        self.router.add_api_route("/api/models", self.get_models, methods=["GET"], response_model=ModelsResponse)
        
        # 使用装饰器方式注册WebSocket路由，避免参数传递问题
        @self.router.websocket("/ws/task/{task_id}/logs")
        async def websocket_handler(websocket: WebSocket, task_id: int):
            return await self.websocket_endpoint(websocket, task_id)
    
    def root(self):
        """根路径"""
        return {
            "message": "AI文档测试系统后端API v2.0",
            "mode": "生产模式"
        }
    
    def get_client_config(self):
        """获取客户端配置信息（用于前端动态配置）"""
        server_config = self.settings.server_config
        
        # 构建API和WebSocket基础URL
        host = server_config.get('host', '0.0.0.0')
        port = server_config.get('port', 8080)
        
        # 如果host是0.0.0.0，返回相对URL让客户端自适应
        if host in ['0.0.0.0', '127.0.0.1']:
            api_base_url = "/api"
            ws_base_url = ""  # 空字符串表示使用相对URL
        else:
            api_base_url = f"http://{host}:{port}/api"
            ws_base_url = f"ws://{host}:{port}"
        
        return {
            "api_base_url": api_base_url,
            "ws_base_url": ws_base_url,
            "app_title": "AI文档测试系统",
            "app_version": "2.0.0",
            "supported_file_types": self.settings.file_settings.get('allowed_extensions', ['pdf', 'docx', 'md', 'txt']),
            "max_file_size": self.settings.file_settings.get('max_file_size', 10485760)
        }
    
    def get_models(self, db: Session = Depends(get_db)) -> ModelsResponse:
        """获取可用模型列表"""
        # 从数据库获取活跃模型
        active_models = model_initializer.get_active_models(db)
        default_model = model_initializer.get_default_model(db)
        
        models = []
        default_index = 0
        
        for idx, model in enumerate(active_models):
            models.append(ModelInfo(
                index=idx,
                label=model.label,
                description=model.description or '',
                provider=model.provider,
                is_default=model.is_default
            ))
            
            if model.is_default or (default_model and model.id == default_model.id):
                default_index = idx
        
        return ModelsResponse(
            models=models,
            default_index=default_index
        )
    
    async def websocket_endpoint(self, websocket: WebSocket, task_id: int):
        """WebSocket端点 - 实时日志推送"""
        await manager.connect(websocket, task_id)
        try:
            # 发送连接成功消息
            await manager.send_personal_message(
                json.dumps({
                    "type": "connected",
                    "message": f"Connected to task {task_id} logs"
                }),
                websocket
            )
            
            # 保持连接
            while True:
                # 接收消息（主要是保持连接活跃）
                data = await websocket.receive_text()
                # 可以处理客户端发来的消息，比如心跳包
                if data == "ping":
                    await manager.send_personal_message("pong", websocket)
        except WebSocketDisconnect:
            await manager.disconnect(websocket, task_id)
        except Exception as e:
            print(f"WebSocket error: {e}")
            await manager.disconnect(websocket, task_id)


# 创建视图实例并导出router
system_view = SystemView()
router = system_view.router