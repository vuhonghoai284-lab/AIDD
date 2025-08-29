"""
任务统计API测试
测试 /api/tasks/statistics 端点
"""
import pytest
from fastapi.testclient import TestClient


class TestTaskStatisticsAPI:
    """任务统计API测试类"""
    
    def test_get_task_statistics_success(self, client: TestClient, auth_headers):
        """测试获取任务统计成功 - GET /api/tasks/statistics"""
        response = client.get("/api/tasks/statistics", headers=auth_headers)
        assert response.status_code == 200
        
        stats = response.json()
        assert isinstance(stats, dict)
        
        # 验证基本统计字段
        expected_fields = ["total_tasks", "completed_tasks", "failed_tasks", "pending_tasks"]
        for field in expected_fields:
            if field in stats:
                assert isinstance(stats[field], int)
                assert stats[field] >= 0
    
    def test_get_task_statistics_without_auth(self, client: TestClient):
        """测试未认证获取任务统计"""
        response = client.get("/api/tasks/statistics")
        assert response.status_code == 401
    
    def test_task_statistics_data_structure(self, client: TestClient, auth_headers):
        """测试任务统计数据结构"""
        response = client.get("/api/tasks/statistics", headers=auth_headers)
        assert response.status_code == 200
        
        stats = response.json()
        
        # 验证数据类型
        numeric_fields = ["total_tasks", "completed_tasks", "failed_tasks", "pending_tasks", "processing_tasks"]
        for field in numeric_fields:
            if field in stats:
                assert isinstance(stats[field], int), f"Field {field} should be integer"
        
        # 验证逻辑一致性
        if all(field in stats for field in ["total_tasks", "completed_tasks", "failed_tasks", "pending_tasks"]):
            calculated_total = stats["completed_tasks"] + stats["failed_tasks"] + stats["pending_tasks"]
            # 总数应该大于等于已知状态的任务数（可能还有其他状态）
            assert stats["total_tasks"] >= calculated_total
    
    def test_task_statistics_performance(self, client: TestClient, auth_headers):
        """测试任务统计性能"""
        import time
        
        start_time = time.time()
        response = client.get("/api/tasks/statistics", headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = (end_time - start_time) * 1000
        assert response_time < 1000, f"Task statistics too slow: {response_time}ms"
    
    def test_task_statistics_caching(self, client: TestClient, auth_headers):
        """测试任务统计缓存"""
        # 多次请求应该快速响应（通过缓存）
        response1 = client.get("/api/tasks/statistics", headers=auth_headers)
        assert response1.status_code == 200
        
        import time
        start_time = time.time()
        response2 = client.get("/api/tasks/statistics", headers=auth_headers)
        end_time = time.time()
        
        assert response2.status_code == 200
        response_time = (end_time - start_time) * 1000
        assert response_time < 200, f"Cached statistics too slow: {response_time}ms"
    
    def test_task_statistics_admin_vs_user(self, client: TestClient, auth_headers, normal_auth_headers):
        """测试管理员与普通用户的统计权限"""
        # 管理员应该能看到全局统计
        admin_response = client.get("/api/tasks/statistics", headers=auth_headers)
        assert admin_response.status_code == 200
        
        # 普通用户可能只能看到自己的统计或被拒绝
        user_response = client.get("/api/tasks/statistics", headers=normal_auth_headers)
        assert user_response.status_code in [200, 403]
        
        if user_response.status_code == 200:
            admin_stats = admin_response.json()
            user_stats = user_response.json()
            
            # 普通用户的统计数据应该小于等于管理员看到的全局数据
            if "total_tasks" in both [admin_stats, user_stats]:
                assert user_stats["total_tasks"] <= admin_stats["total_tasks"]


class TestTaskStatisticsValidation:
    """任务统计验证测试"""
    
    def test_statistics_invalid_parameters(self, client: TestClient, auth_headers):
        """测试统计API无效参数"""
        # 测试可能的查询参数
        invalid_params = [
            "days=abc",
            "limit=-1", 
            "offset=-5",
            "invalid_param=value"
        ]
        
        for param in invalid_params:
            response = client.get(f"/api/tasks/statistics?{param}", headers=auth_headers)
            # 根据实现，可能忽略无效参数或返回验证错误
            assert response.status_code in [200, 422]
    
    def test_statistics_filtering_parameters(self, client: TestClient, auth_headers):
        """测试统计过滤参数"""
        # 测试可能的过滤参数
        filter_params = [
            "status=completed",
            "status=failed", 
            "status=pending",
            "days=7",
            "days=30"
        ]
        
        for param in filter_params:
            response = client.get(f"/api/tasks/statistics?{param}", headers=auth_headers)
            # 应该接受有效的过滤参数
            assert response.status_code == 200
    
    def test_statistics_date_range_validation(self, client: TestClient, auth_headers):
        """测试统计日期范围验证"""
        # 测试日期范围参数
        date_params = [
            "start_date=2024-01-01&end_date=2024-12-31",
            "start_date=invalid_date",
            "end_date=2024-13-40"  # 无效日期
        ]
        
        for param in date_params:
            response = client.get(f"/api/tasks/statistics?{param}", headers=auth_headers)
            if "invalid" in param or "13-40" in param:
                assert response.status_code == 422
            else:
                assert response.status_code == 200


class TestTaskStatisticsMethods:
    """任务统计HTTP方法测试"""
    
    def test_statistics_invalid_methods(self, client: TestClient, auth_headers):
        """测试统计端点无效HTTP方法"""
        # POST方法不被支持
        response = client.post("/api/tasks/statistics", headers=auth_headers)
        assert response.status_code == 405
        
        # PUT方法不被支持
        response = client.put("/api/tasks/statistics", headers=auth_headers)
        assert response.status_code == 405
        
        # DELETE方法不被支持
        response = client.delete("/api/tasks/statistics", headers=auth_headers)
        assert response.status_code == 405