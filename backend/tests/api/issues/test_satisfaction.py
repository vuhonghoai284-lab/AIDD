"""
问题满意度评分API测试
测试 /api/issues/{id}/satisfaction 端点
"""
import pytest
import io
from fastapi.testclient import TestClient


class TestIssueSatisfactionAPI:
    """问题满意度评分API测试类"""
    
    def test_submit_satisfaction_rating_success(self, client: TestClient, sample_file, auth_headers):
        """测试提交满意度评分成功 - PUT /api/issues/{id}/satisfaction"""
        # 先创建任务以生成问题
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 等待任务处理并获取详情
        import time
        time.sleep(1)
        detail_response = client.get(f"/api/tasks/{task_id}", headers=auth_headers)
        task_detail = detail_response.json()
        
        if task_detail.get("issues") and len(task_detail["issues"]) > 0:
            issue_id = task_detail["issues"][0]["id"]
            
            rating_data = {"satisfaction_rating": 4.5}
            response = client.put(f"/api/issues/{issue_id}/satisfaction", json=rating_data, headers=auth_headers)
            assert response.status_code == 200
            
            result = response.json()
            assert "success" in result or "id" in result
    
    def test_submit_satisfaction_rating_not_found(self, client: TestClient, auth_headers):
        """测试对不存在问题提交满意度评分"""
        rating_data = {"satisfaction_rating": 4.5}
        response = client.put("/api/issues/99999/satisfaction", json=rating_data, headers=auth_headers)
        assert response.status_code == 404
    
    def test_submit_satisfaction_rating_without_auth(self, client: TestClient):
        """测试未认证提交满意度评分"""
        rating_data = {"satisfaction_rating": 4.5}
        response = client.put("/api/issues/1/satisfaction", json=rating_data)
        assert response.status_code == 401
    
    def test_satisfaction_rating_validation(self, client: TestClient, auth_headers):
        """测试满意度评分数值验证"""
        # 测试有效评分范围 (1.0-5.0)
        valid_ratings = [1.0, 2.5, 3.0, 4.5, 5.0]
        
        for rating in valid_ratings:
            rating_data = {"satisfaction_rating": rating}
            response = client.put("/api/issues/999/satisfaction", json=rating_data, headers=auth_headers)
            # 虽然问题不存在会返回404，但评分验证应该先通过
            assert response.status_code == 404  # 而不是422，说明评分格式正确
        
        # 测试无效评分
        invalid_ratings = [0.5, 6.0, -1.0, 0.0, 10.0]
        
        for rating in invalid_ratings:
            rating_data = {"satisfaction_rating": rating}
            response = client.put("/api/issues/999/satisfaction", json=rating_data, headers=auth_headers)
            assert response.status_code == 422, f"Invalid rating {rating} should be rejected"
    
    def test_satisfaction_rating_data_types(self, client: TestClient, auth_headers):
        """测试满意度评分数据类型"""
        # 测试不同数据类型
        type_cases = [
            ("4.5", 4.5),  # 字符串数字
            (4, 4.0),      # 整数
            (4.0, 4.0),    # 浮点数
        ]
        
        for input_value, expected_value in type_cases:
            rating_data = {"satisfaction_rating": input_value}
            response = client.put("/api/issues/999/satisfaction", json=rating_data, headers=auth_headers)
            # 数值应该被正确解析，因为问题不存在会返回404而不是422
            assert response.status_code == 404
        
        # 测试无效数据类型
        invalid_types = ["abc", True, False, None, [], {}]
        
        for invalid_value in invalid_types:
            rating_data = {"satisfaction_rating": invalid_value}
            response = client.put("/api/issues/999/satisfaction", json=rating_data, headers=auth_headers)
            assert response.status_code == 422, f"Invalid type {type(invalid_value)} should be rejected"
    
    def test_satisfaction_rating_precision(self, client: TestClient, auth_headers):
        """测试满意度评分精度"""
        # 测试小数精度
        precision_cases = [
            1.1, 1.11, 1.111, 1.1111, 1.11111
        ]
        
        for rating in precision_cases:
            rating_data = {"satisfaction_rating": rating}
            response = client.put("/api/issues/999/satisfaction", json=rating_data, headers=auth_headers)
            # 精度测试，应该接受合理的小数位
            assert response.status_code == 404  # 问题不存在，但评分格式正确
    
    def test_satisfaction_rating_missing_field(self, client: TestClient, auth_headers):
        """测试缺少满意度评分字段"""
        # 空数据
        response = client.put("/api/issues/1/satisfaction", json={}, headers=auth_headers)
        assert response.status_code == 422  # 缺少必需字段
        
        # 包含其他字段但缺少评分
        data = {"comment": "评论", "other_field": "value"}
        response = client.put("/api/issues/1/satisfaction", json=data, headers=auth_headers)
        assert response.status_code == 422
    
    def test_satisfaction_rating_performance(self, client: TestClient, sample_file, auth_headers):
        """测试满意度评分提交性能"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 等待处理
        import time
        time.sleep(1)
        detail_response = client.get(f"/api/tasks/{task_id}", headers=auth_headers)
        task_detail = detail_response.json()
        
        if task_detail.get("issues") and len(task_detail["issues"]) > 0:
            issue_id = task_detail["issues"][0]["id"]
            
            rating_data = {"satisfaction_rating": 4.0}
            
            start_time = time.time()
            response = client.put(f"/api/issues/{issue_id}/satisfaction", json=rating_data, headers=auth_headers)
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000
            assert response_time < 300, f"Submit satisfaction rating too slow: {response_time}ms"


class TestIssueSatisfactionMethods:
    """问题满意度HTTP方法测试"""
    
    def test_satisfaction_invalid_methods(self, client: TestClient, auth_headers):
        """测试满意度端点无效HTTP方法"""
        issue_id = 1
        
        # GET方法不被支持
        response = client.get(f"/api/issues/{issue_id}/satisfaction", headers=auth_headers)
        assert response.status_code == 405
        
        # POST方法不被支持  
        response = client.post(f"/api/issues/{issue_id}/satisfaction", headers=auth_headers)
        assert response.status_code == 405
        
        # DELETE方法不被支持
        response = client.delete(f"/api/issues/{issue_id}/satisfaction", headers=auth_headers)
        assert response.status_code == 405


class TestIssueSatisfactionBusiness:
    """问题满意度业务逻辑测试"""
    
    def test_satisfaction_rating_update(self, client: TestClient, sample_file, auth_headers):
        """测试满意度评分更新"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 等待处理
        import time
        time.sleep(1)
        detail_response = client.get(f"/api/tasks/{task_id}", headers=auth_headers)
        task_detail = detail_response.json()
        
        if task_detail.get("issues") and len(task_detail["issues"]) > 0:
            issue_id = task_detail["issues"][0]["id"]
            
            # 提交初始评分
            initial_rating = {"satisfaction_rating": 3.0}
            response1 = client.put(f"/api/issues/{issue_id}/satisfaction", json=initial_rating, headers=auth_headers)
            assert response1.status_code == 200
            
            # 更新评分
            updated_rating = {"satisfaction_rating": 5.0}
            response2 = client.put(f"/api/issues/{issue_id}/satisfaction", json=updated_rating, headers=auth_headers)
            assert response2.status_code == 200
            
            # 验证最新评分生效
            # 这需要有获取问题详情的API来验证，暂时只验证请求成功
    
    def test_satisfaction_rating_statistics(self, client: TestClient, sample_file, auth_headers):
        """测试满意度评分统计"""
        # 创建任务
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 等待处理
        import time
        time.sleep(1)
        detail_response = client.get(f"/api/tasks/{task_id}", headers=auth_headers)
        task_detail = detail_response.json()
        
        if task_detail.get("issues") and len(task_detail["issues"]) > 0:
            issue_id = task_detail["issues"][0]["id"]
            
            # 提交评分
            rating_data = {"satisfaction_rating": 4.5}
            response = client.put(f"/api/issues/{issue_id}/satisfaction", json=rating_data, headers=auth_headers)
            assert response.status_code == 200
            
            # 如果有统计API，可以验证评分被正确记录
            # 这里只验证评分提交成功
    
    def test_satisfaction_rating_boundary_values(self, client: TestClient, auth_headers):
        """测试满意度评分边界值"""
        boundary_cases = [
            (1.0, 404),    # 最小值，问题不存在
            (5.0, 404),    # 最大值，问题不存在
            (0.9, 422),    # 小于最小值
            (5.1, 422),    # 大于最大值
        ]
        
        for rating, expected_status in boundary_cases:
            rating_data = {"satisfaction_rating": rating}
            response = client.put("/api/issues/999/satisfaction", json=rating_data, headers=auth_headers)
            assert response.status_code == expected_status, f"Rating {rating} should return {expected_status}"