"""
系统配置API测试
测试 /api/config 端点
"""
import pytest
from fastapi.testclient import TestClient


class TestConfigAPI:
    """系统配置API测试类"""
    
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
    
    def test_config_endpoint_consistency(self, client: TestClient):
        """测试配置接口一致性"""
        # 多次调用应该返回相同配置
        response1 = client.get("/api/config")
        response2 = client.get("/api/config")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json() == response2.json()
    
    def test_config_data_types(self, client: TestClient):
        """测试配置数据类型验证"""
        response = client.get("/api/config")
        assert response.status_code == 200
        
        data = response.json()
        
        # 验证具体数据类型
        assert isinstance(data["api_base_url"], str)
        assert isinstance(data["ws_base_url"], str)
        assert isinstance(data["app_title"], str)
        assert isinstance(data["app_version"], str)
        assert isinstance(data["supported_file_types"], list)
        assert isinstance(data["max_file_size"], int)
        
        # 验证文件类型列表内容
        if data["supported_file_types"]:
            for file_type in data["supported_file_types"]:
                assert isinstance(file_type, str)
    
    def test_config_endpoint_invalid_methods(self, client: TestClient):
        """测试配置接口无效HTTP方法"""
        # POST方法不被支持
        response = client.post("/api/config")
        assert response.status_code == 405
        
        # PUT方法不被支持
        response = client.put("/api/config")
        assert response.status_code == 405
        
        # DELETE方法不被支持
        response = client.delete("/api/config")
        assert response.status_code == 405