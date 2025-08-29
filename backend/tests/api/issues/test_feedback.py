"""
问题反馈API测试
测试 /api/issues/{id}/feedback 端点
"""
import pytest
import io
from fastapi.testclient import TestClient


class TestIssueFeedbackAPI:
    """问题反馈API测试类"""
    
    def test_submit_feedback_success(self, client: TestClient, sample_file, auth_headers):
        """测试提交问题反馈成功 - PUT /api/issues/{id}/feedback"""
        # 先创建任务以生成问题
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 等待任务处理并获取详情（其中包含issues）
        import time
        time.sleep(1)
        detail_response = client.get(f"/api/tasks/{task_id}", headers=auth_headers)
        task_detail = detail_response.json()
        
        if task_detail.get("issues") and len(task_detail["issues"]) > 0:
            issue_id = task_detail["issues"][0]["id"]
            
            feedback_data = {
                "feedback_type": "accept",
                "comment": "测试反馈评论"
            }
            
            response = client.put(f"/api/issues/{issue_id}/feedback", json=feedback_data, headers=auth_headers)
            assert response.status_code == 200
            
            result = response.json()
            assert "success" in result or "id" in result
    
    def test_submit_feedback_not_found(self, client: TestClient, auth_headers):
        """测试提交不存在问题的反馈"""
        feedback_data = {
            "feedback_type": "accept",
            "comment": "测试评论"
        }
        
        response = client.put("/api/issues/99999/feedback", json=feedback_data, headers=auth_headers)
        assert response.status_code == 404
        
        error = response.json()
        assert "detail" in error
        assert "问题不存在" in error["detail"]
    
    def test_submit_feedback_without_auth(self, client: TestClient):
        """测试未认证提交问题反馈"""
        feedback_data = {
            "feedback_type": "accept", 
            "comment": "测试评论"
        }
        
        response = client.put("/api/issues/1/feedback", json=feedback_data)
        assert response.status_code == 401
    
    def test_submit_feedback_empty_data(self, client: TestClient, sample_file, auth_headers):
        """测试提交空反馈数据"""
        # 先创建任务以生成问题
        filename, content, content_type = sample_file
        files = {"file": (filename, io.BytesIO(content), content_type)}
        create_response = client.post("/api/tasks/", files=files, data={"ai_model_index": "0"}, headers=auth_headers)
        task_id = create_response.json()["id"]
        
        # 等待任务处理
        import time
        time.sleep(1)
        detail_response = client.get(f"/api/tasks/{task_id}", headers=auth_headers)
        task_detail = detail_response.json()
        
        if task_detail.get("issues") and len(task_detail["issues"]) > 0:
            issue_id = task_detail["issues"][0]["id"]
            
            # 测试空数据（由于所有字段都是可选的，这应该返回200）
            response = client.put(f"/api/issues/{issue_id}/feedback", json={}, headers=auth_headers)
            assert response.status_code == 200
    
    def test_submit_feedback_invalid_type(self, client: TestClient, sample_file, auth_headers):
        """测试提交无效反馈类型"""
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
            
            # 测试无效的反馈类型
            invalid_feedback = {
                "feedback_type": "invalid_type",
                "comment": "测试评论"
            }
            response = client.put(f"/api/issues/{issue_id}/feedback", json=invalid_feedback, headers=auth_headers)
            assert response.status_code == 422  # Validation error
    
    def test_submit_feedback_valid_types(self, client: TestClient, sample_file, auth_headers):
        """测试提交有效反馈类型"""
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
            
            # 测试所有有效的反馈类型
            valid_types = ["accept", "reject", "modify"]
            
            for feedback_type in valid_types:
                feedback_data = {
                    "feedback_type": feedback_type,
                    "comment": f"测试{feedback_type}反馈"
                }
                response = client.put(f"/api/issues/{issue_id}/feedback", json=feedback_data, headers=auth_headers)
                assert response.status_code == 200, f"Valid feedback type {feedback_type} should be accepted"
    
    def test_submit_feedback_performance(self, client: TestClient, sample_file, auth_headers):
        """测试提交反馈性能"""
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
            
            feedback_data = {
                "feedback_type": "accept",
                "comment": "性能测试反馈"
            }
            
            start_time = time.time()
            response = client.put(f"/api/issues/{issue_id}/feedback", json=feedback_data, headers=auth_headers)
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000
            assert response_time < 500, f"Submit feedback too slow: {response_time}ms"


class TestIssueFeedbackValidation:
    """问题反馈验证测试"""
    
    def test_feedback_comment_validation(self, client: TestClient, sample_file, auth_headers):
        """测试反馈评论验证"""
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
            
            # 测试各种评论内容
            comment_cases = [
                "",  # 空评论
                "正常评论",  # 正常评论
                "很长的评论" * 100,  # 超长评论
                "包含特殊字符的评论!@#$%^&*()",  # 特殊字符
            ]
            
            for comment in comment_cases:
                feedback_data = {
                    "feedback_type": "accept",
                    "comment": comment
                }
                response = client.put(f"/api/issues/{issue_id}/feedback", json=feedback_data, headers=auth_headers)
                # 根据业务逻辑，大部分评论应该被接受
                assert response.status_code in [200, 422]
    
    def test_feedback_malformed_json(self, client: TestClient, auth_headers):
        """测试畸形JSON反馈"""
        # 发送无效JSON
        response = client.put("/api/issues/1/feedback", data="invalid_json", headers=auth_headers)
        assert response.status_code == 422
    
    def test_feedback_extra_fields(self, client: TestClient, sample_file, auth_headers):
        """测试反馈包含额外字段"""
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
            
            # 包含额外字段的反馈
            feedback_data = {
                "feedback_type": "accept",
                "comment": "测试反馈",
                "extra_field": "should_be_ignored",
                "user_agent": "test_agent"
            }
            
            response = client.put(f"/api/issues/{issue_id}/feedback", json=feedback_data, headers=auth_headers)
            # 额外字段应该被忽略，请求应该成功
            assert response.status_code == 200