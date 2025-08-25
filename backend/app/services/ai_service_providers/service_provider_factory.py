"""
AI服务提供者工厂
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.services.interfaces.ai_service import IAIServiceProvider
from .real_ai_service_provider import RealAIServiceProvider


class AIServiceProviderFactory:
    """AI服务提供者工厂"""
    
    @staticmethod
    def create_provider(settings, model_index: int = 0, 
                       db_session: Optional[Session] = None) -> IAIServiceProvider:
        """
        创建AI服务提供者
        
        Args:
            settings: 设置对象
            model_index: 模型索引
            db_session: 数据库会话
            
        Returns:
            AI服务提供者实例
        """
        # 获取指定索引的模型配置
        model_config = settings.ai_models[model_index]
        # 创建真实AI服务提供者，传递配置中的config部分
        return RealAIServiceProvider(model_config['config'], db_session)

# 全局工厂实例
ai_service_provider_factory = AIServiceProviderFactory()