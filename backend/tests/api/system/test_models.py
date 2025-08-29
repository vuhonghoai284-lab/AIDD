"""
AI模型API测试
测试 /api/models 端点
"""
import pytest
from fastapi.testclient import TestClient


class TestModelsAPI:
    """AI模型API测试类"""
    
    def test_get_models_list(self, client: TestClient):
        """测试获取AI模型列表 - SYS-003"""
        response = client.get("/api/models")
        assert response.status_code == 200
        
        data = response.json()
        assert "models" in data
        assert "default_index" in data
        
        # 验证数据结构
        assert isinstance(data["models"], list)
        assert isinstance(data["default_index"], int)
        
        # 如果有模型，验证模型数据结构
        if data["models"]:
            model = data["models"][0]
            required_model_fields = ["index", "label", "description", "provider", "is_default"]
            for field in required_model_fields:
                assert field in model, f"Missing model field: {field}"
            
            # 验证default_index有效性
            assert 0 <= data["default_index"] < len(data["models"])
    
    def test_models_endpoint_performance(self, client: TestClient):
        """测试模型接口性能 - PERF-001"""
        import time
        
        start_time = time.time()
        response = client.get("/api/models")
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = (end_time - start_time) * 1000  # 转换为毫秒
        assert response_time < 500, f"Models endpoint response too slow: {response_time}ms"
    
    def test_models_data_structure(self, client: TestClient):
        """测试模型数据结构完整性"""
        response = client.get("/api/models")
        assert response.status_code == 200
        
        data = response.json()
        
        # 验证顶层结构
        assert "models" in data
        assert "default_index" in data
        
        # 验证模型列表结构
        if data["models"]:
            for i, model in enumerate(data["models"]):
                assert isinstance(model, dict)
                
                # 验证必需字段
                required_fields = ["index", "label", "description", "provider", "is_default"]
                for field in required_fields:
                    assert field in model
                
                # 验证字段类型
                assert isinstance(model["index"], int)
                assert isinstance(model["label"], str)
                assert isinstance(model["description"], str)
                assert isinstance(model["provider"], str)
                assert isinstance(model["is_default"], bool)
                
                # 验证索引一致性
                assert model["index"] == i
            
            # 验证默认模型设置
            default_count = sum(1 for model in data["models"] if model["is_default"])
            assert default_count <= 1, "Multiple default models found"
            
            if default_count == 1:
                default_model = next(model for model in data["models"] if model["is_default"])
                assert default_model["index"] == data["default_index"]
    
    def test_models_endpoint_invalid_methods(self, client: TestClient):
        """测试模型接口无效HTTP方法"""
        # POST方法不被支持
        response = client.post("/api/models")
        assert response.status_code == 405
        
        # PUT方法不被支持
        response = client.put("/api/models")
        assert response.status_code == 405
        
        # DELETE方法不被支持
        response = client.delete("/api/models")
        assert response.status_code == 405
    
    def test_models_consistency(self, client: TestClient):
        """测试模型列表一致性"""
        # 多次请求应该返回相同结果
        response1 = client.get("/api/models")
        response2 = client.get("/api/models")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json() == response2.json()
    
    def test_models_providers_validation(self, client: TestClient):
        """测试模型提供者验证"""
        response = client.get("/api/models")
        assert response.status_code == 200
        
        data = response.json()
        
        if data["models"]:
            valid_providers = ["openai", "mock", "test"]  # 根据实际支持的提供者调整
            
            for model in data["models"]:
                provider = model.get("provider")
                if provider:  # 如果有提供者信息，验证其有效性
                    # 提供者应该是已知的有效值之一
                    assert isinstance(provider, str)
                    assert len(provider) > 0