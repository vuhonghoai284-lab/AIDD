"""
系统API测试
测试SystemView中的系统相关接口
"""
import pytest
from fastapi.testclient import TestClient


class TestSystemAPI:
    """系统API测试类"""
    
    def test_root_endpoint(self, client: TestClient):
        """测试根路径 - SYS-001"""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "mode" in data
        assert data["message"] == "AI文档测试系统后端API v2.0"
        assert isinstance(data["mode"], str)
    
    def test_get_client_config(self, client: TestClient):
        """测试获取客户端配置 - SYS-002"""
        response = client.get("/api/config")
        assert response.status_code == 200
        
        data = response.json()
        required_fields = [
            "api_base_url", "ws_base_url", "app_title", 
            "app_version", "supported_file_types", 
            "max_file_size"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        # 验证数据类型
        assert isinstance(data["supported_file_types"], list)
        assert isinstance(data["max_file_size"], int)
        assert data["app_title"] == "AI文档测试系统"
        assert data["app_version"] == "2.0.0"
    
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
        assert response_time < 500, f"Response time too slow: {response_time}ms"
    
    def test_root_endpoint_cache_headers(self, client: TestClient):
        """测试根路径缓存头设置"""
        response = client.get("/")
        assert response.status_code == 200
        
        # 可以添加缓存头检查
        # assert "cache-control" in response.headers.keys()
    
    def test_config_endpoint_consistency(self, client: TestClient):
        """测试配置接口一致性"""
        # 多次调用应该返回相同配置
        response1 = client.get("/api/config")
        response2 = client.get("/api/config")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json() == response2.json()
    
    def test_invalid_endpoint(self, client: TestClient):
        """测试无效端点"""
        response = client.get("/api/invalid")
        assert response.status_code == 404
    
    def test_models_endpoint_with_invalid_method(self, client: TestClient):
        """测试模型接口无效方法"""
        response = client.post("/api/models")
        assert response.status_code == 405  # Method Not Allowed
        
        response = client.delete("/api/models")  
        assert response.status_code == 405