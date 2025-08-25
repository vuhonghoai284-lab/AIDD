"""
模型初始化服务
负责从配置文件读取AI模型配置并初始化数据库
"""
import hashlib
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.database import get_db
from app.models.ai_model import AIModel


class ModelInitializer:
    """AI模型初始化器"""
    
    def __init__(self):
        self.settings = get_settings()
    
    def initialize_models(self, db: Session) -> List[AIModel]:
        """
        从配置文件初始化AI模型到数据库
        
        Args:
            db: 数据库会话
            
        Returns:
            初始化的模型列表
        """
        models_config = self.settings.ai_models
        default_index = self.settings.default_model_index
        
        initialized_models = []
        
        for index, model_config in enumerate(models_config):
            # 生成模型key（基于配置内容的哈希）
            model_key = self._generate_model_key(model_config)
            
            # 检查模型是否已存在
            existing_model = db.query(AIModel).filter(AIModel.model_key == model_key).first()
            
            if existing_model:
                # 更新现有模型
                self._update_model(existing_model, model_config, index, default_index)
                db.commit()
                initialized_models.append(existing_model)
            else:
                # 创建新模型
                new_model = self._create_model(model_config, model_key, index, default_index)
                db.add(new_model)
                db.commit()
                db.refresh(new_model)
                initialized_models.append(new_model)
        
        # 标记不在配置中的模型为非活跃状态
        self._deactivate_unused_models(db, [model.model_key for model in initialized_models])
        
        return initialized_models
    
    def _generate_model_key(self, model_config: Dict[str, Any]) -> str:
        """
        基于模型配置生成唯一key
        
        Args:
            model_config: 模型配置
            
        Returns:
            模型唯一key
        """
        # 使用label和provider生成key，确保唯一性
        label = model_config.get('label', '')
        provider = model_config.get('provider', '')
        config_data = model_config.get('config', {})
        model_name = config_data.get('model', '')
        
        # 创建唯一标识
        unique_string = f"{provider}_{model_name}_{label}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:16]
    
    def _create_model(self, model_config: Dict[str, Any], model_key: str, 
                     index: int, default_index: int) -> AIModel:
        """
        创建新的AI模型记录
        
        Args:
            model_config: 模型配置
            model_key: 模型key
            index: 模型索引
            default_index: 默认模型索引
            
        Returns:
            AI模型对象
        """
        config_data = model_config.get('config', {})
        
        return AIModel(
            model_key=model_key,
            label=model_config.get('label', ''),
            provider=model_config.get('provider', ''),
            model_name=config_data.get('model', ''),
            description=model_config.get('description', ''),
            temperature=config_data.get('temperature', 0.3),
            max_tokens=config_data.get('max_tokens', 8000),
            context_window=config_data.get('context_window', 128000),
            reserved_tokens=config_data.get('reserved_tokens', 2000),
            timeout=config_data.get('timeout', 12000),
            max_retries=config_data.get('max_retries', 3),
            base_url=config_data.get('base_url', ''),
            api_key_env=self._extract_env_var(config_data.get('api_key', '')),
            is_active=True,
            is_default=(index == default_index),
            sort_order=index
        )
    
    def _update_model(self, model: AIModel, model_config: Dict[str, Any], 
                     index: int, default_index: int):
        """
        更新现有模型配置
        
        Args:
            model: 现有模型对象
            model_config: 新配置
            index: 模型索引
            default_index: 默认模型索引
        """
        config_data = model_config.get('config', {})
        
        # 更新模型信息
        model.label = model_config.get('label', model.label)
        model.provider = model_config.get('provider', model.provider)
        model.model_name = config_data.get('model', model.model_name)
        model.description = model_config.get('description', model.description)
        model.temperature = config_data.get('temperature', model.temperature)
        model.max_tokens = config_data.get('max_tokens', model.max_tokens)
        model.context_window = config_data.get('context_window', model.context_window)
        model.reserved_tokens = config_data.get('reserved_tokens', model.reserved_tokens)
        model.timeout = config_data.get('timeout', model.timeout)
        model.max_retries = config_data.get('max_retries', model.max_retries)
        model.base_url = config_data.get('base_url', model.base_url)
        model.api_key_env = self._extract_env_var(config_data.get('api_key', ''))
        model.is_active = True
        model.is_default = (index == default_index)
        model.sort_order = index
    
    def _extract_env_var(self, api_key_string: str) -> str:
        """
        从API key配置中提取环境变量名
        
        Args:
            api_key_string: API key配置字符串，如 "${OPENAI_API_KEY}"
            
        Returns:
            环境变量名
        """
        if api_key_string.startswith('${') and api_key_string.endswith('}'):
            return api_key_string[2:-1]
        return api_key_string
    
    def _deactivate_unused_models(self, db: Session, active_keys: List[str]):
        """
        将不在配置中的模型标记为非活跃状态
        
        Args:
            db: 数据库会话
            active_keys: 活跃模型key列表
        """
        unused_models = db.query(AIModel).filter(
            ~AIModel.model_key.in_(active_keys),
            AIModel.is_active == True
        ).all()
        
        for model in unused_models:
            model.is_active = False
            model.is_default = False
        
        db.commit()
    
    def get_active_models(self, db: Session) -> List[AIModel]:
        """
        获取所有活跃的AI模型
        
        Args:
            db: 数据库会话
            
        Returns:
            活跃模型列表
        """
        return db.query(AIModel).filter(
            AIModel.is_active == True
        ).order_by(AIModel.sort_order).all()
    
    def get_default_model(self, db: Session) -> AIModel:
        """
        获取默认AI模型
        
        Args:
            db: 数据库会话
            
        Returns:
            默认模型
        """
        default_model = db.query(AIModel).filter(
            AIModel.is_active == True,
            AIModel.is_default == True
        ).first()
        
        if not default_model:
            # 如果没有默认模型，返回第一个活跃模型
            default_model = db.query(AIModel).filter(
                AIModel.is_active == True
            ).order_by(AIModel.sort_order).first()
        
        return default_model


# 全局实例
model_initializer = ModelInitializer()