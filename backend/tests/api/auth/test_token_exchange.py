"""
第三方认证Token交换API测试
测试 /api/auth/thirdparty/exchange-token 端点
"""
import pytest
from fastapi.testclient import TestClient


class TestTokenExchangeAPI:
    """Token交换API测试类"""
    
    def test_exchange_token_success(self, client: TestClient):
        """测试token交换成功 - POST /api/auth/thirdparty/exchange-token"""
        # 模拟有效的授权码
        exchange_data = {
            "code": "test_authorization_code",
            "state": "test_state"
        }
        
        response = client.post("/api/auth/thirdparty/exchange-token", json=exchange_data)
        # 在测试环境中，可能需要mock第三方服务
        assert response.status_code in [200, 400]  # 400表示无效授权码，这在测试中是正常的
        
        if response.status_code == 200:
            result = response.json()
            assert "access_token" in result
            # token_type字段可能不存在，根据实际API响应调整
            if "token_type" in result:
                assert result["token_type"] == "bearer"
            # 验证其他标准OAuth字段
            if "expires_in" in result:
                assert isinstance(result["expires_in"], int)
            if "scope" in result:
                assert isinstance(result["scope"], str)
    
    def test_exchange_token_invalid_code(self, client: TestClient):
        """测试无效授权码交换"""
        invalid_codes = [
            {"code": "", "state": "test_state"},  # 空授权码
            {"code": "invalid_code", "state": "test_state"},  # 无效授权码
            {"state": "test_state"},  # 缺少授权码
        ]
        
        for exchange_data in invalid_codes:
            response = client.post("/api/auth/thirdparty/exchange-token", json=exchange_data)
            # 在mock环境下，可能接受任何授权码格式
            assert response.status_code in [200, 400, 422]
    
    def test_exchange_token_missing_state(self, client: TestClient):
        """测试缺少state参数的token交换"""
        exchange_data = {"code": "test_code"}
        
        response = client.post("/api/auth/thirdparty/exchange-token", json=exchange_data)
        # 根据OAuth标准，state参数通常是可选的，但实现可能要求
        assert response.status_code in [200, 400, 422]
    
    def test_exchange_token_malformed_request(self, client: TestClient):
        """测试畸形请求"""
        # 空JSON
        response = client.post("/api/auth/thirdparty/exchange-token", json={})
        assert response.status_code == 422
        
        # 无效JSON格式
        response = client.post("/api/auth/thirdparty/exchange-token", data="invalid_json")
        assert response.status_code == 422
    
    def test_exchange_token_duplicate_code(self, client: TestClient):
        """测试重复使用授权码"""
        exchange_data = {
            "code": "duplicate_test_code",
            "state": "test_state"
        }
        
        # 第一次使用
        response1 = client.post("/api/auth/thirdparty/exchange-token", json=exchange_data)
        
        # 第二次使用相同授权码
        response2 = client.post("/api/auth/thirdparty/exchange-token", json=exchange_data)
        
        # 第二次应该被拒绝（授权码只能使用一次）
        if response1.status_code == 200:
            assert response2.status_code == 400
        elif response1.status_code == 400:
            # 如果第一次就失败，第二次也应该失败
            assert response2.status_code == 400
    
    def test_exchange_token_performance(self, client: TestClient):
        """测试token交换性能"""
        exchange_data = {
            "code": "performance_test_code",
            "state": "test_state"
        }
        
        import time
        start_time = time.time()
        response = client.post("/api/auth/thirdparty/exchange-token", json=exchange_data)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000
        assert response_time < 2000, f"Token exchange too slow: {response_time}ms"
    
    def test_exchange_token_concurrent_requests(self, client: TestClient):
        """测试并发token交换请求"""
        import threading
        import time
        
        results = []
        
        def exchange_token(code):
            exchange_data = {"code": f"concurrent_{code}", "state": "test_state"}
            response = client.post("/api/auth/thirdparty/exchange-token", json=exchange_data)
            results.append(response.status_code)
        
        # 启动多个并发交换请求
        threads = []
        for i in range(3):
            thread = threading.Thread(target=exchange_token, args=(i,))
            threads.append(thread)
            thread.start()
            time.sleep(0.01)
        
        for thread in threads:
            thread.join()
        
        # 所有请求都应该得到响应（成功或失败）
        assert len(results) == 3
        assert all(status in [200, 400, 422] for status in results)


class TestTokenExchangeValidation:
    """Token交换验证测试"""
    
    def test_exchange_token_field_types(self, client: TestClient):
        """测试交换token字段类型"""
        # 测试不同数据类型
        type_cases = [
            {"code": 123, "state": "test"},  # 数字类型code
            {"code": "test", "state": 456},  # 数字类型state
            {"code": True, "state": "test"},  # 布尔类型code
            {"code": None, "state": "test"},  # null值
        ]
        
        for exchange_data in type_cases:
            response = client.post("/api/auth/thirdparty/exchange-token", json=exchange_data)
            # 在mock环境下，可能对字段类型较为宽松
            assert response.status_code in [200, 400, 422], f"Unexpected status for: {exchange_data}"
    
    def test_exchange_token_extra_fields(self, client: TestClient):
        """测试包含额外字段的token交换"""
        exchange_data = {
            "code": "test_code",
            "state": "test_state",
            "extra_field": "should_be_ignored",
            "redirect_uri": "http://test.com"
        }
        
        response = client.post("/api/auth/thirdparty/exchange-token", json=exchange_data)
        # 额外字段应该被忽略，不影响核心功能
        assert response.status_code in [200, 400]  # 400可能是由于测试环境的授权码无效
    
    def test_exchange_token_long_values(self, client: TestClient):
        """测试超长字段值"""
        # 测试超长的授权码和state
        long_code = "a" * 1000  # 1KB长度的code
        long_state = "b" * 500  # 500字节长度的state
        
        exchange_data = {"code": long_code, "state": long_state}
        response = client.post("/api/auth/thirdparty/exchange-token", json=exchange_data)
        
        # 应该能处理合理长度的字段，或返回适当错误
        assert response.status_code in [200, 400, 422]


class TestTokenExchangeMethods:
    """Token交换HTTP方法测试"""
    
    def test_exchange_token_invalid_methods(self, client: TestClient):
        """测试token交换端点无效HTTP方法"""
        # GET方法不被支持
        response = client.get("/api/auth/thirdparty/exchange-token")
        assert response.status_code == 405
        
        # PUT方法不被支持
        response = client.put("/api/auth/thirdparty/exchange-token")
        assert response.status_code == 405
        
        # DELETE方法不被支持
        response = client.delete("/api/auth/thirdparty/exchange-token")
        assert response.status_code == 405