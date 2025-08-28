"""
重构后的主应用入口
"""
 
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import engine, get_db, Base
from app.services.cache_service import init_cache, close_cache
from app.views import system_view, auth_view, task_view, user_view, ai_output_view, issue_view, task_log_view, analytics_view, task_share_view

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
        redirect_slashes=True  # 启用自动斜杠重定向
    )
    
    # 配置CORS - 允许所有来源访问
    print("🌐 CORS配置: 允许所有来源访问 (已关闭CORS校验)")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 允许所有来源
        allow_credentials=False,  # 当allow_origins为["*"]时，必须设置为False
        allow_methods=["*"],  # 允许所有HTTP方法
        allow_headers=["*"],  # 允许所有请求头
        expose_headers=["Content-Disposition", "Content-Type", "Content-Length"],  # 暴露文件下载相关的响应头
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
        from app.services.task_recovery_service import task_recovery_service
        from app.services.background_task_service import background_task_service
        
        # 初始化缓存
        try:
            init_cache()
            print("✓ 缓存系统已初始化")
        except Exception as e:
            print(f"✗ 缓存初始化失败: {e}")
        
        # 初始化AI模型配置到数据库
        db = next(get_db())
        try:
            models = model_initializer.initialize_models(db)
            print(f"✓ 已初始化 {len(models)} 个AI模型")
        except Exception as e:
            print(f"✗ AI模型初始化失败: {e}")
        
        # 任务恢复机制
        try:
            recovered_count = await task_recovery_service.recover_tasks_on_startup(db)
            print(f"✓ 已恢复 {recovered_count} 个待处理任务")
        except Exception as e:
            print(f"✗ 任务恢复失败: {e}")
        finally:
            db.close()
        
        # 启动后台任务服务
        try:
            await background_task_service.start()
            print("✓ 后台任务服务已启动")
        except Exception as e:
            print(f"✗ 后台任务服务启动失败: {e}")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """应用关闭时的清理操作"""
        from app.services.background_task_service import background_task_service
        
        try:
            await background_task_service.stop()
            print("✓ 后台任务服务已停止")
        except Exception as e:
            print(f"✗ 后台任务服务停止失败: {e}")
        
        # 关闭缓存连接
        try:
            close_cache()
        except Exception as e:
            print(f"✗ 缓存关闭失败: {e}")

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
    app.include_router(user_view.router, prefix="/api", tags=["用户"])
    
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
    
    # 注册任务分享相关路由
    app.include_router(task_share_view.router, tags=["任务分享"])

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