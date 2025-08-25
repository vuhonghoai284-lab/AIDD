"""
重构后的主应用入口
"""
 
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import engine, get_db, Base
from app.views import system_view, auth_view, task_view, user_view, ai_output_view, issue_view, task_log_view, analytics_view

# 导入所有模型以确保它们被注册到Base.metadata
from app.models import *

# 获取配置
settings = get_settings()

# 创建数据库表
Base.metadata.create_all(bind=engine)

def create_app() -> FastAPI:
    """创建并配置FastAPI应用"""
    app = FastAPI(
        title="AI文档测试系统API",
        description="基于AI的文档质量检测系统后端API",
        version="2.0.0",
        debug=settings.server_config.get('debug', False),
        redirect_slashes=False  # 禁用自动斜杠重定向
    )
    
    # 配置CORS - 允许所有来源访问
    print("🌐 CORS配置: 允许所有来源访问 (已关闭CORS校验)")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 允许所有来源
        allow_credentials=False,  # 当allow_origins为["*"]时，必须设置为False
        allow_methods=["*"],  # 允许所有HTTP方法
        allow_headers=["*"],  # 允许所有请求头
    )
    
    return app

# 创建应用实例
app = create_app()

def setup_startup_event(app: FastAPI):
    """设置应用启动事件"""
    @app.on_event("startup")
    async def startup_event():
        """应用启动时的初始化操作"""        
        from app.services.model_initializer import model_initializer
        
        # 初始化AI模型配置到数据库
        db = next(get_db())
        try:
            models = model_initializer.initialize_models(db)
            print(f"✓ 已初始化 {len(models)} 个AI模型")
        except Exception as e:
            print(f"✗ AI模型初始化失败: {e}")
        finally:
            db.close()

# 设置启动事件
setup_startup_event(app)

def setup_routes(app: FastAPI):
    """设置所有路由"""
    # 注册系统相关路由
    app.include_router(system_view.router, tags=["系统"])
    
    # 注册认证相关路由
    app.include_router(auth_view.router, prefix="/api/auth", tags=["认证"])
    
    # 注册任务相关路由
    app.include_router(task_view.router, prefix="/api/tasks", tags=["任务"])
    
    # 注册用户相关路由
    app.include_router(user_view.router, prefix="/api/users", tags=["用户"])
    
    # 注册AI输出相关路由
    from app.views.ai_output_view import task_ai_output_view, single_ai_output_view
    app.include_router(task_ai_output_view.router, prefix="/api/tasks", tags=["AI输出"])
    app.include_router(single_ai_output_view.router, prefix="/api/ai-outputs", tags=["AI输出"])
    
    # 注册问题反馈相关路由
    app.include_router(issue_view.router, prefix="/api/issues", tags=["问题反馈"])
    
    # 注册任务日志相关路由
    app.include_router(task_log_view.router, prefix="/api/tasks", tags=["任务日志"])
    
    # 注册运营数据统计相关路由
    app.include_router(analytics_view.router, tags=["运营数据统计"])

# 设置路由
setup_routes(app)


if __name__ == "__main__":
    import uvicorn
    print("启动服务器...")
    # 从配置获取服务器端口
    server_config = settings.server_config
    host = server_config.get('host', '0.0.0.0')
    port = server_config.get('port', 8080)
    uvicorn.run(app, host=host, port=port)