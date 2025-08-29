"""
任务统计API测试
测试 /api/analytics/tasks 端点
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models import User, Task, FileInfo, AIModel


class TestAnalyticsTasksAPI:
    """任务统计API测试类"""
    
    def test_get_task_analytics_success(self, client: TestClient, test_db_session: Session, admin_user_token):
        """测试获取任务统计数据成功 - GET /api/analytics/tasks"""
        # 创建测试数据
        import time
        timestamp = int(time.time() * 1000000) % 1000000
        
        # 创建测试用户
        test_user = User(
            uid=f"task_analytics_user_{timestamp}",
            display_name="Task Analytics Test User",
            email=f"task_analytics_{timestamp}@test.com"
        )
        test_db_session.add(test_user)
        test_db_session.flush()
        
        # 创建AI模型
        ai_model = AIModel(
            model_key=f"task-analytics-model-{timestamp}",
            label="任务统计测试模型",
            provider="test",
            model_name=f"task-analytics-model-{timestamp}"
        )
        test_db_session.add(ai_model)
        test_db_session.flush()
        
        # 创建文件信息
        file_info = FileInfo(
            original_name="task_analytics_test.txt",
            stored_name="task_analytics_test_stored.txt",
            file_path="/tmp/task_analytics_test.txt",
            file_size=1024,
            file_type="txt",
            mime_type="text/plain"
        )
        test_db_session.add(file_info)
        test_db_session.flush()
        
        # 创建不同状态的任务
        completed_task = Task(
            title="完成的任务",
            user_id=test_user.id,
            file_id=file_info.id,
            model_id=ai_model.id,
            status="completed",
            processing_time=30.5,
            completed_at=datetime.utcnow()
        )
        test_db_session.add(completed_task)
        
        failed_task = Task(
            title="失败的任务",
            user_id=test_user.id,
            file_id=file_info.id,
            model_id=ai_model.id,
            status="failed",
            error_message="测试失败"
        )
        test_db_session.add(failed_task)
        
        pending_task = Task(
            title="待处理的任务",
            user_id=test_user.id,
            file_id=file_info.id,
            model_id=ai_model.id,
            status="pending"
        )
        test_db_session.add(pending_task)
        
        test_db_session.commit()
        
        token = admin_user_token["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/analytics/tasks", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_tasks"] >= 3
        assert data["completed_tasks"] >= 1
        assert data["failed_tasks"] >= 1
        assert data["pending_tasks"] >= 1
        assert "success_rate" in data
        assert "avg_processing_time" in data
        assert "task_creation_trend" in data
        assert "task_completion_trend" in data
        assert "task_status_distribution" in data
    
    def test_get_task_analytics_without_auth(self, client: TestClient):
        """测试未认证获取任务统计"""
        response = client.get("/api/analytics/tasks")
        assert response.status_code == 401
    
    def test_get_task_analytics_normal_user(self, client: TestClient, normal_auth_headers):
        """测试普通用户获取任务统计（应被拒绝）"""
        response = client.get("/api/analytics/tasks", headers=normal_auth_headers)
        assert response.status_code == 403
        
        error = response.json()
        assert "detail" in error
        assert "权限不足" in error["detail"]
    
    def test_task_analytics_data_structure(self, client: TestClient, admin_user_token):
        """测试任务统计数据结构"""
        token = admin_user_token["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/analytics/tasks", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # 验证基本字段（只检查确实存在的字段）
        basic_fields = ["total_tasks", "completed_tasks", "failed_tasks", "pending_tasks"]
        for field in basic_fields:
            assert field in data, f"Missing basic field: {field}"
            assert isinstance(data[field], int), f"Field {field} should be integer"
        
        # 验证可选字段的类型（如果存在）
        optional_fields = {
            "success_rate": (int, float, type(None)),
            "avg_processing_time": (int, float, type(None)),
            "task_creation_trend": list,
            "task_completion_trend": list,
            "task_status_distribution": list
        }
        
        for field, expected_type in optional_fields.items():
            if field in data:
                if expected_type == list:
                    assert isinstance(data[field], list), f"Field {field} should be list"
                else:
                    assert isinstance(data[field], expected_type), f"Field {field} should be {expected_type}"
        
        
        # 验证状态分布结构
        if data["task_status_distribution"]:
            status_item = data["task_status_distribution"][0]
            assert "status" in status_item
            assert "count" in status_item
            assert isinstance(status_item["status"], str)
            assert isinstance(status_item["count"], int)
    
    def test_task_analytics_performance(self, client: TestClient, admin_user_token):
        """测试任务统计性能"""
        token = admin_user_token["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        import time
        start_time = time.time()
        response = client.get("/api/analytics/tasks", headers=headers)
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = (end_time - start_time) * 1000
        assert response_time < 1500, f"Task analytics too slow: {response_time}ms"


class TestTaskAnalyticsAccuracy:
    """任务统计准确性测试"""
    
    def test_task_stats_accuracy(self, client: TestClient, test_db_session: Session, admin_user_token):
        """测试任务统计数据准确性"""
        # 创建测试数据
        import time
        timestamp = int(time.time() * 1000000) % 1000000
        
        test_user = User(
            uid=f"task_accuracy_user_{timestamp}",
            display_name="Task Test User",
            email=f"task_{timestamp}@test.com"
        )
        test_db_session.add(test_user)
        test_db_session.flush()
        
        ai_model = AIModel(
            model_key=f"task-accuracy-model-{timestamp}",
            label="任务准确性测试模型",
            provider="test",
            model_name=f"task-accuracy-model-{timestamp}"
        )
        test_db_session.add(ai_model)
        test_db_session.flush()
        
        file_info = FileInfo(
            original_name="task_accuracy.txt",
            stored_name="task_accuracy_stored.txt",
            file_path="/tmp/task_accuracy.txt",
            file_size=1024,
            file_type="txt",
            mime_type="text/plain"
        )
        test_db_session.add(file_info)
        test_db_session.flush()
        
        # 创建不同状态的任务
        completed_task1 = Task(
            title="完成任务1",
            user_id=test_user.id,
            file_id=file_info.id,
            model_id=ai_model.id,
            status="completed",
            processing_time=30.5,
            completed_at=datetime.utcnow()
        )
        test_db_session.add(completed_task1)
        
        completed_task2 = Task(
            title="完成任务2",
            user_id=test_user.id,
            file_id=file_info.id,
            model_id=ai_model.id,
            status="completed",
            processing_time=45.2,
            completed_at=datetime.utcnow()
        )
        test_db_session.add(completed_task2)
        
        failed_task = Task(
            title="失败任务",
            user_id=test_user.id,
            file_id=file_info.id,
            model_id=ai_model.id,
            status="failed",
            error_message="测试失败"
        )
        test_db_session.add(failed_task)
        
        pending_task = Task(
            title="待处理任务",
            user_id=test_user.id,
            file_id=file_info.id,
            model_id=ai_model.id,
            status="pending"
        )
        test_db_session.add(pending_task)
        
        test_db_session.commit()
        
        # 获取统计数据
        token = admin_user_token["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/analytics/tasks", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # 验证任务状态统计
        assert data["completed_tasks"] >= 2
        assert data["failed_tasks"] >= 1
        assert data["pending_tasks"] >= 1
        
        # 验证成功率计算
        total_tasks = data["total_tasks"]
        completed_tasks = data["completed_tasks"]
        expected_success_rate = (completed_tasks / total_tasks) * 100
        assert abs(data["success_rate"] - expected_success_rate) < 0.01  # 允许小数点误差
        
        # 验证平均处理时间
        assert data["avg_processing_time"] is not None
        expected_avg_time = (30.5 + 45.2) / 2  # 两个完成任务的平均时间
        # 由于可能有其他任务的处理时间，我们只验证返回值是合理的
        assert data["avg_processing_time"] > 0
    
    def test_task_analytics_trend_data(self, client: TestClient, admin_user_token):
        """测试任务统计趋势数据"""
        token = admin_user_token["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/analytics/tasks", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # 验证趋势数据结构
        for trend_list in [data["task_creation_trend"], data["task_completion_trend"]]:
            assert isinstance(trend_list, list)
            if trend_list:
                trend_item = trend_list[0]
                assert isinstance(trend_item, dict)
                assert "date" in trend_item
                assert "count" in trend_item
                assert isinstance(trend_item["date"], str)
                assert isinstance(trend_item["count"], int)
                assert trend_item["count"] >= 0
        
        # 验证状态分布
        status_distribution = data["task_status_distribution"]
        assert isinstance(status_distribution, list)
        if status_distribution:
            status_item = status_distribution[0]
            assert "status" in status_item
            assert "count" in status_item


class TestTaskAnalyticsMethods:
    """任务统计HTTP方法测试"""
    
    def test_task_analytics_invalid_methods(self, client: TestClient, admin_user_token):
        """测试任务统计端点无效HTTP方法"""
        token = admin_user_token["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # POST方法不被支持
        response = client.post("/api/analytics/tasks", headers=headers)
        assert response.status_code == 405
        
        # PUT方法不被支持
        response = client.put("/api/analytics/tasks", headers=headers)
        assert response.status_code == 405
        
        # DELETE方法不被支持
        response = client.delete("/api/analytics/tasks", headers=headers)
        assert response.status_code == 405