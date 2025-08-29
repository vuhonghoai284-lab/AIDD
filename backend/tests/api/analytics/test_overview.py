"""
运营数据概览API测试
测试 /api/analytics/overview 端点
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models import User, Task, FileInfo, AIOutput, Issue, AIModel


class TestAnalyticsOverviewAPI:
    """运营数据概览API测试类"""
    
    def setup_test_data(self, db_session: Session, admin_user_token):
        """设置测试数据"""
        import time
        # 创建唯一的测试用户
        timestamp = int(time.time() * 1000000) % 1000000
        test_user = User(
            uid=f"test_analytics_user_{timestamp}",
            display_name="Analytics Test User",
            email=f"analytics_{timestamp}@test.com",
            is_admin=False,
            created_at=datetime.utcnow() - timedelta(days=5),
            last_login_at=datetime.utcnow() - timedelta(hours=2)
        )
        db_session.add(test_user)
        db_session.flush()
        
        # 创建AI模型
        ai_model = AIModel(
            model_key=f"test-analytics-model-{timestamp}",
            label="测试分析模型",
            provider="test",
            model_name=f"test-analytics-model-{timestamp}"
        )
        db_session.add(ai_model)
        db_session.flush()
        
        # 创建文件信息
        file_info = FileInfo(
            original_name="analytics_test.txt",
            stored_name="analytics_test_stored.txt",
            file_path="/tmp/analytics_test.txt",
            file_size=2048,
            file_type="txt",
            mime_type="text/plain",
            created_at=datetime.utcnow() - timedelta(days=3)
        )
        db_session.add(file_info)
        db_session.flush()
        
        # 创建任务
        completed_task = Task(
            title="已完成的分析任务",
            user_id=admin_user_token["user"].get("id", admin_user_token["user"].id if hasattr(admin_user_token["user"], "id") else 1),
            file_id=file_info.id,
            model_id=ai_model.id,
            status="completed",
            progress=100.0,
            processing_time=45.5,
            created_at=datetime.utcnow() - timedelta(days=2),
            completed_at=datetime.utcnow() - timedelta(days=1)
        )
        db_session.add(completed_task)
        db_session.commit()
        
        return {
            "test_user": test_user,
            "ai_model": ai_model,
            "file_info": file_info,
            "completed_task": completed_task,
        }
    
    def test_get_analytics_overview_success(self, client: TestClient, test_db_session: Session, admin_user_token):
        """测试获取综合运营数据概览成功 - GET /api/analytics/overview"""
        # 设置测试数据
        test_data = self.setup_test_data(test_db_session, admin_user_token)
        
        # 使用管理员token
        token = admin_user_token["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 测试获取概览数据
        response = client.get("/api/analytics/overview", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # 验证响应结构
        required_sections = ["user_stats", "task_stats", "system_stats", "issue_stats", "error_stats", "last_updated"]
        for section in required_sections:
            assert section in data, f"Missing section: {section}"
        
        # 验证用户统计
        user_stats = data["user_stats"]
        assert user_stats["total_users"] >= 2  # 至少包含管理员和测试用户
        assert "new_users_today" in user_stats
        assert "active_users_today" in user_stats
        assert "user_registration_trend" in user_stats
        assert isinstance(user_stats["user_registration_trend"], list)
        
        # 验证任务统计
        task_stats = data["task_stats"]
        assert task_stats["total_tasks"] >= 1
        assert "completed_tasks" in task_stats
        assert "failed_tasks" in task_stats
        assert "pending_tasks" in task_stats
        assert "success_rate" in task_stats
        assert "task_creation_trend" in task_stats
        assert isinstance(task_stats["task_creation_trend"], list)
    
    def test_get_analytics_overview_without_auth(self, client: TestClient):
        """测试未认证获取运营数据概览"""
        response = client.get("/api/analytics/overview")
        assert response.status_code == 401
    
    def test_get_analytics_overview_normal_user(self, client: TestClient, normal_auth_headers):
        """测试普通用户获取运营数据概览（应被拒绝）"""
        response = client.get("/api/analytics/overview", headers=normal_auth_headers)
        assert response.status_code == 403
        
        error = response.json()
        assert "detail" in error
        assert "权限不足" in error["detail"]
    
    def test_analytics_overview_performance(self, client: TestClient, admin_user_token):
        """测试运营数据概览性能"""
        token = admin_user_token["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        import time
        start_time = time.time()
        response = client.get("/api/analytics/overview", headers=headers)
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = (end_time - start_time) * 1000
        assert response_time < 2000, f"Analytics overview too slow: {response_time}ms"
    
    def test_analytics_overview_data_consistency(self, client: TestClient, admin_user_token):
        """测试运营数据概览数据一致性"""
        token = admin_user_token["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 多次请求验证数据一致性
        response1 = client.get("/api/analytics/overview", headers=headers)
        response2 = client.get("/api/analytics/overview", headers=headers)
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        data1 = response1.json()
        data2 = response2.json()
        
        # 在短时间内，大部分统计数据应该相同
        # 验证结构一致性
        assert data1.keys() == data2.keys()
        
        # 验证数据类型一致性
        for key in data1.keys():
            if key != "last_updated":  # 更新时间可能不同
                assert type(data1[key]) == type(data2[key])


class TestAnalyticsOverviewDataTypes:
    """运营数据概览数据类型测试"""
    
    def test_overview_data_types(self, client: TestClient, admin_user_token):
        """测试概览数据类型"""
        token = admin_user_token["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/analytics/overview", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # 验证各统计部分的数据类型
        assert isinstance(data["user_stats"], dict)
        assert isinstance(data["task_stats"], dict)
        assert isinstance(data["system_stats"], dict)
        assert isinstance(data["issue_stats"], dict)
        assert isinstance(data["error_stats"], dict)
        assert isinstance(data["last_updated"], str)
        
        # 验证用户统计数据类型
        user_stats = data["user_stats"]
        assert isinstance(user_stats["total_users"], int)
        assert isinstance(user_stats["new_users_today"], int)
        assert isinstance(user_stats["active_users_today"], int)
        assert isinstance(user_stats["user_registration_trend"], list)
        
        # 验证任务统计数据类型
        task_stats = data["task_stats"]
        assert isinstance(task_stats["total_tasks"], int)
        assert isinstance(task_stats["completed_tasks"], int)
        assert isinstance(task_stats["failed_tasks"], int)
        assert isinstance(task_stats["pending_tasks"], int)
        assert isinstance(task_stats["success_rate"], (int, float))
        assert isinstance(task_stats["task_creation_trend"], list)


class TestAnalyticsOverviewMethods:
    """运营数据概览HTTP方法测试"""
    
    def test_analytics_overview_invalid_methods(self, client: TestClient, admin_user_token):
        """测试运营数据概览端点无效HTTP方法"""
        token = admin_user_token["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # POST方法不被支持
        response = client.post("/api/analytics/overview", headers=headers)
        assert response.status_code == 405
        
        # PUT方法不被支持
        response = client.put("/api/analytics/overview", headers=headers)
        assert response.status_code == 405
        
        # DELETE方法不被支持
        response = client.delete("/api/analytics/overview", headers=headers)
        assert response.status_code == 405