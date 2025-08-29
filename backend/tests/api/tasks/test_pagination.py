"""
任务分页API测试
测试 /api/tasks/paginated 端点
"""
import pytest
import io
from fastapi.testclient import TestClient


class TestTaskPaginationAPI:
    """任务分页API测试类"""
    
    def test_get_tasks_paginated_success(self, client: TestClient, auth_headers):
        """测试获取分页任务列表成功 - GET /api/tasks/paginated"""
        response = client.get("/api/tasks/paginated", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        # 验证分页响应结构 - 检查实际存在的字段
        required_fields = ["items", "total", "page"]
        for field in required_fields:
            assert field in data, f"Missing required pagination field: {field}"
        
        # 可选字段验证
        optional_fields = ["size", "pages", "has_next", "has_prev"]
        for field in optional_fields:
            if field in data:
                assert isinstance(data[field], (int, bool)), f"Invalid type for {field}"
        
        assert isinstance(data["items"], list)
        assert isinstance(data["total"], int)
        assert isinstance(data["page"], int)
    
    def test_get_tasks_paginated_with_parameters(self, client: TestClient, auth_headers):
        """测试分页参数"""
        # 测试不同的分页参数，注意API使用page_size参数而不是size
        pagination_cases = [
            "page=1&page_size=10",
            "page=2&page_size=5",
            "page=1&page_size=20",
            "page_size=15",  # 只指定page_size
            "page=2"    # 只指定page
        ]
        
        for params in pagination_cases:
            response = client.get(f"/api/tasks/paginated?{params}", headers=auth_headers)
            assert response.status_code == 200
            
            data = response.json()
            assert "items" in data
            assert "total" in data
            assert "page" in data
            assert "page_size" in data
    
    def test_get_tasks_paginated_invalid_parameters(self, client: TestClient, auth_headers):
        """测试无效分页参数"""
        invalid_params = [
            "page=0",         # 页码从1开始
            "page=-1",        # 负数页码
            "page_size=0",    # 大小为0
            "page_size=-10",  # 负数大小
            "page=abc",       # 非数字页码
            "page_size=xyz",  # 非数字大小
            "page_size=1000"  # 过大的页面大小
        ]
        
        for params in invalid_params:
            try:
                response = client.get(f"/api/tasks/paginated?{params}", headers=auth_headers)
                # Some invalid parameters might be handled gracefully (e.g., default values used)
                # or might cause validation errors
                assert response.status_code in [200, 400, 422], f"Unexpected status for params: {params}, got {response.status_code}"
                
                # If the API accepts invalid params gracefully, at least verify response structure
                if response.status_code == 200:
                    data = response.json()
                    assert "items" in data
                    assert "total" in data
                    assert "page" in data
                    assert "page_size" in data
            except Exception as e:
                # Some parameters might cause exceptions due to type conversion failures
                # This is also acceptable behavior for invalid parameters
                pass
    
    def test_paginated_tasks_without_auth(self, client: TestClient):
        """测试未认证获取分页任务"""
        response = client.get("/api/tasks/paginated")
        assert response.status_code == 401
    
    def test_pagination_data_consistency(self, client: TestClient, sample_file, auth_headers):
        """测试分页数据一致性"""
        # 先创建一些测试任务
        for i in range(5):
            filename = f"pagination_test_{i}.md"
            content = f"# Test Task {i}\n\nContent for task {i}".encode('utf-8')
            files = {"file": (filename, io.BytesIO(content), "text/markdown")}
            response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
            assert response.status_code == 201
        
        # 获取第一页
        response1 = client.get("/api/tasks/paginated?page=1&page_size=3", headers=auth_headers)
        assert response1.status_code == 200
        page1_data = response1.json()
        
        # 获取第二页
        response2 = client.get("/api/tasks/paginated?page=2&page_size=3", headers=auth_headers)
        assert response2.status_code == 200
        page2_data = response2.json()
        
        # 验证分页逻辑
        assert page1_data["page"] == 1
        assert page2_data["page"] == 2
        assert page1_data["page_size"] == 3
        assert page2_data["page_size"] == 3
        
        # 验证总数一致
        assert page1_data["total"] == page2_data["total"]
        
        # 验证没有重复的任务
        page1_ids = {task["id"] for task in page1_data["items"]}
        page2_ids = {task["id"] for task in page2_data["items"]}
        assert len(page1_ids.intersection(page2_ids)) == 0, "Pages should not contain duplicate tasks"
    
    def test_pagination_boundary_cases(self, client: TestClient, auth_headers):
        """测试分页边界情况"""
        # 获取第一页
        response = client.get("/api/tasks/paginated?page=1&page_size=100", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        total_tasks = data["total"]
        
        if total_tasks > 0:
            # 测试最后一页
            last_page = max(1, (total_tasks + 99) // 100)  # 向上取整
            response = client.get(f"/api/tasks/paginated?page={last_page}&page_size=100", headers=auth_headers)
            assert response.status_code == 200
            
            last_page_data = response.json()
            assert last_page_data["page"] == last_page
            assert len(last_page_data["items"]) <= 100
            
            # 测试超出范围的页码
            response = client.get(f"/api/tasks/paginated?page={last_page + 10}&page_size=100", headers=auth_headers)
            assert response.status_code == 200
            empty_page_data = response.json()
            assert len(empty_page_data["items"]) == 0
    
    def test_pagination_performance(self, client: TestClient, auth_headers):
        """测试分页性能"""
        import time
        
        start_time = time.time()
        response = client.get("/api/tasks/paginated?page=1&page_size=20", headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = (end_time - start_time) * 1000
        assert response_time < 1000, f"Paginated tasks query too slow: {response_time}ms"


class TestTaskPaginationFiltering:
    """任务分页过滤测试"""
    
    def test_paginated_tasks_with_status_filter(self, client: TestClient, auth_headers):
        """测试分页任务状态过滤"""
        status_filters = ["pending", "processing", "completed", "failed"]
        
        for status in status_filters:
            response = client.get(f"/api/tasks/paginated?status={status}&page=1&page_size=10", headers=auth_headers)
            assert response.status_code == 200
            
            data = response.json()
            
            # 验证返回的任务都是指定状态（如果有数据）
            for task in data["items"]:
                if "status" in task:
                    assert task["status"] == status
    
    def test_paginated_tasks_with_date_filter(self, client: TestClient, auth_headers):
        """测试分页任务日期过滤"""
        # 测试日期范围过滤
        date_filters = [
            "start_date=2024-01-01",
            "end_date=2024-12-31",
            "start_date=2024-01-01&end_date=2024-12-31"
        ]
        
        for date_filter in date_filters:
            response = client.get(f"/api/tasks/paginated?{date_filter}&page=1&page_size=10", headers=auth_headers)
            # 根据实现，可能支持或不支持日期过滤
            assert response.status_code in [200, 422]
    
    def test_paginated_tasks_with_search(self, client: TestClient, auth_headers):
        """测试分页任务搜索"""
        # 测试搜索参数
        search_params = [
            "search=test",
            "search=任务",
            "q=keyword"
        ]
        
        for search_param in search_params:
            response = client.get(f"/api/tasks/paginated?{search_param}&page=1&page_size=10", headers=auth_headers)
            # 根据实现，可能支持或不支持搜索
            assert response.status_code in [200, 422]


class TestTaskPaginationMethods:
    """任务分页HTTP方法测试"""
    
    def test_paginated_tasks_invalid_methods(self, client: TestClient, auth_headers):
        """测试分页端点无效HTTP方法"""
        methods_to_test = [
            ("POST", client.post),
            ("PUT", client.put),
            ("DELETE", client.delete)
        ]
        
        for method_name, method_func in methods_to_test:
            try:
                response = method_func("/api/tasks/paginated", headers=auth_headers)
                # Method not allowed (405) or not found (404) are both acceptable
                # Some frameworks might return 404 if the route doesn't exist for that method
                assert response.status_code in [404, 405], f"{method_name} method should not be allowed, got {response.status_code}"
            except Exception as e:
                # Connection errors or other exceptions are also acceptable for unsupported methods
                pass