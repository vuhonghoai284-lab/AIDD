"""
根路径API测试
测试 / 端点
"""
import pytest
from fastapi.testclient import TestClient


class TestRootAPI:
    """根路径API测试类"""
    
    def test_root_endpoint_success(self, client: TestClient):
        """测试根路径访问成功 - GET /"""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "mode" in data
        assert data["message"] == "AI文档测试系统后端API v2.0"
        assert isinstance(data["mode"], str)
    
    def test_root_endpoint_cache_headers(self, client: TestClient):
        """测试根路径缓存头设置"""
        response = client.get("/")
        assert response.status_code == 200
        
        # 可以添加缓存头检查
        # assert "cache-control" in response.headers.keys()
    
    def test_root_endpoint_performance(self, client: TestClient):
        """测试根路径响应性能"""
        import time
        
        start_time = time.time()
        response = client.get("/")
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = (end_time - start_time) * 1000  # 转换为毫秒
        assert response_time < 200, f"Root endpoint response too slow: {response_time}ms"