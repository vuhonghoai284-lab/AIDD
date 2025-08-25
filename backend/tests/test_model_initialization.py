"""
模型初始化相关测试
测试AI模型在不同模式下的初始化功能
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import init_settings
from app.core.database import SessionLocal, Base, engine
from app.services.model_initializer import model_initializer
# 确保导入所有模型
from app.models import *


class TestModelInitialization:
    """模型初始化测试"""
    
    def test_production_mode_models_config(self):
        """测试生产模式模型配置"""
        settings = init_settings("config.yaml")
        assert len(settings.ai_models) > 0, "生产模式应该有配置模型"
        
        # 检查模型配置结构
        for model in settings.ai_models:
            assert 'label' in model, "模型应该有label"
            assert 'provider' in model, "模型应该有provider"
            assert 'config' in model, "模型应该有config"
    
    def test_test_mode_models_config(self):
        """测试测试模式模型配置"""
        settings = init_settings("config.test.yaml")
        assert len(settings.ai_models) > 0, "测试配置应该有配置模型"
        
        # 检查测试模型配置结构
        for model in settings.ai_models:
            assert 'label' in model, "模型应该有label"
            assert 'provider' in model, "模型应该有provider"
            assert 'config' in model, "模型应该有config"
    
    def test_model_database_initialization(self):
        """测试模型数据库初始化"""
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        
        settings = init_settings("config.test.yaml")
        db = SessionLocal()
        
        try:
            # 初始化模型到数据库
            initializer = model_initializer
            initializer.settings = settings  # 使用测试配置
            
            models = initializer.initialize_models(db)
            
            # 验证初始化结果
            assert len(models) > 0, "应该初始化了至少一个模型"
            assert len(models) == len(settings.ai_models), "初始化的模型数量应该与配置一致"
            
            # 验证模型属性
            for model in models:
                assert model.id is not None, "模型应该有ID"
                assert model.label is not None, "模型应该有标签"
                assert model.provider is not None, "模型应该有提供商"
                assert model.is_active, "初始化的模型应该是活跃的"
            
            # 验证默认模型
            default_models = [m for m in models if m.is_default]
            assert len(default_models) == 1, "应该有且只有一个默认模型"
            
        finally:
            db.close()
    
    def test_get_active_models(self):
        """测试获取活跃模型"""
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        
        settings = init_settings("config.test.yaml")
        db = SessionLocal()
        
        try:
            # 先初始化模型
            initializer = model_initializer
            initializer.settings = settings
            initializer.initialize_models(db)
            
            # 获取活跃模型
            active_models = initializer.get_active_models(db)
            
            assert len(active_models) > 0, "应该有活跃模型"
            for model in active_models:
                assert model.is_active, "返回的模型应该都是活跃的"
            
        finally:
            db.close()
    
    def test_get_default_model(self):
        """测试获取默认模型"""
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        
        settings = init_settings("config.test.yaml")
        db = SessionLocal()
        
        try:
            # 先初始化模型
            initializer = model_initializer
            initializer.settings = settings
            initializer.initialize_models(db)
            
            # 获取默认模型
            default_model = initializer.get_default_model(db)
            
            assert default_model is not None, "应该有默认模型"
            assert default_model.is_default, "返回的模型应该是默认的"
            assert default_model.is_active, "默认模型应该是活跃的"
            
        finally:
            db.close()


class TestModelsAPI:
    """模型API测试"""
    
    def test_models_api_returns_models(self, client: TestClient):
        """测试模型API返回模型列表"""
        response = client.get("/api/models")
        assert response.status_code == 200
        
        data = response.json()
        assert "models" in data, "响应应该包含models字段"
        assert "default_index" in data, "响应应该包含default_index字段"
        
        models = data["models"]
        assert len(models) > 0, "应该返回至少一个模型"
        
        # 验证模型结构
        for model in models:
            assert "index" in model, "模型应该有index"
            assert "label" in model, "模型应该有label"
            assert "description" in model, "模型应该有description"
            assert "provider" in model, "模型应该有provider"
            assert "is_default" in model, "模型应该有is_default"
        
        # 验证默认模型索引
        default_index = data["default_index"]
        assert 0 <= default_index < len(models), "默认模型索引应该在有效范围内"
        assert models[default_index]["is_default"], "默认索引对应的模型应该标记为默认"
    
    def test_root_api_structure(self, client: TestClient):
        """测试根API响应结构"""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "mode" in data, "响应应该包含mode字段"
        assert "message" in data, "响应应该包含message字段"
        
        # 验证基本信息结构
        assert isinstance(data["mode"], str), "mode应该是字符串"
        assert isinstance(data["message"], str), "message应该是字符串"
    
    def test_config_api_structure(self, client: TestClient):
        """测试配置API响应结构"""
        response = client.get("/api/config")
        assert response.status_code == 200
        
        data = response.json()
        assert "supported_file_types" in data, "配置应该包含支持的文件类型"
        assert "max_file_size" in data, "配置应该包含最大文件大小"
        assert "app_title" in data, "配置应该包含应用标题"
        assert "app_version" in data, "配置应该包含应用版本"
        assert "api_base_url" in data, "配置应该包含API基础URL"
        
        # 验证数据类型
        assert isinstance(data["supported_file_types"], list), "支持的文件类型应该是列表"
        assert isinstance(data["max_file_size"], int), "最大文件大小应该是整数"


class TestModelInitializationIntegration:
    """模型初始化集成测试"""
    
    def test_startup_initializes_models_in_test_mode(self):
        """测试启动时在测试模式下也会初始化模型"""
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        
        # 这个测试验证startup事件会在测试模式下初始化模型
        # 我们可以通过检查数据库中是否有模型来验证
        
        db = SessionLocal()
        try:
            active_models = model_initializer.get_active_models(db)
            # 由于测试框架会触发startup事件，所以应该有模型
            assert len(active_models) > 0, "启动后应该有活跃模型"
            
            # 检查是否有测试模式的模型
            mock_models = [m for m in active_models if m.provider == 'mock']
            # 在测试环境中，应该有mock模型
            # 注意：这取决于测试环境使用的配置
            
        finally:
            db.close()
    
    def test_model_api_integration_with_database(self, client: TestClient):
        """测试模型API与数据库的集成"""
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        
        # 这个测试验证API能够从数据库正确读取模型信息
        
        # 1. 先通过API获取模型列表
        response = client.get("/api/models")
        assert response.status_code == 200
        api_models = response.json()["models"]
        
        # 2. 直接从数据库获取模型
        db = SessionLocal()
        try:
            db_models = model_initializer.get_active_models(db)
            
            # 3. 验证数量一致
            assert len(api_models) == len(db_models), "API返回的模型数量应该与数据库一致"
            
            # 4. 验证基本结构一致（不要求内容完全一致，因为测试环境可能使用不同配置）
            assert len(api_models) > 0, "应该有模型返回"
            
            # 验证API模型结构
            for api_model in api_models:
                assert "label" in api_model, "API模型应该有label"
                assert "provider" in api_model, "API模型应该有provider"
                assert "is_default" in api_model, "API模型应该有is_default"
            
            # 验证数据库模型结构
            for db_model in db_models:
                assert db_model.label is not None, "数据库模型应该有label"
                assert db_model.provider is not None, "数据库模型应该有provider"
                assert db_model.is_default is not None, "数据库模型应该有is_default"
                
        finally:
            db.close()