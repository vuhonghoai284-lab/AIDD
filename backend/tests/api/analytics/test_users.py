"""
用户统计API测试
测试 /api/analytics/users 端点
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models import User


class TestAnalyticsUsersAPI:
    """用户统计API测试类"""
    
    def test_get_user_analytics_success(self, client: TestClient, test_db_session: Session, admin_user_token):
        """测试获取用户统计数据成功 - GET /api/analytics/users"""
        # 创建测试数据
        import time
        timestamp = int(time.time() * 1000000) % 1000000
        test_user = User(
            uid=f"analytics_test_user_{timestamp}",
            display_name="Analytics Test User",
            email=f"analytics_{timestamp}@test.com",
            created_at=datetime.utcnow() - timedelta(days=3)
        )
        test_db_session.add(test_user)
        test_db_session.commit()
        
        token = admin_user_token["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 测试默认30天统计
        response = client.get("/api/analytics/users", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_users"] >= 2
        assert "new_users_today" in data
        assert "active_users_today" in data
        assert "admin_users_count" in data
        assert "user_registration_trend" in data
        assert len(data["user_registration_trend"]) == 30  # 默认30天
    
    def test_get_user_analytics_custom_days(self, client: TestClient, admin_user_token):
        """测试自定义天数的用户统计"""
        token = admin_user_token["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 测试7天统计
        response = client.get("/api/analytics/users?days=7", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["user_registration_trend"]) == 7
        
        # 测试1天统计
        response = client.get("/api/analytics/users?days=1", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["user_registration_trend"]) == 1
    
    def test_get_user_analytics_without_auth(self, client: TestClient):
        """测试未认证获取用户统计"""
        response = client.get("/api/analytics/users")
        assert response.status_code == 401
    
    def test_get_user_analytics_normal_user(self, client: TestClient, normal_auth_headers):
        """测试普通用户获取用户统计（应被拒绝）"""
        response = client.get("/api/analytics/users", headers=normal_auth_headers)
        assert response.status_code == 403
        
        error = response.json()
        assert "detail" in error
        assert "权限不足" in error["detail"]
    
    def test_user_analytics_invalid_days_parameter(self, client: TestClient, admin_user_token):
        """测试无效天数参数"""
        token = admin_user_token["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 测试无效的天数参数
        invalid_params = [
            "days=0",      # 0天
            "days=-1",     # 负数
            "days=1000",   # 过大值
            "days=abc",    # 非数字
            "days=1.5",    # 小数
        ]
        
        for param in invalid_params:
            response = client.get(f"/api/analytics/users?{param}", headers=headers)
            assert response.status_code == 422, f"Should reject invalid days parameter: {param}"
    
    def test_user_analytics_data_structure(self, client: TestClient, admin_user_token):
        """测试用户统计数据结构"""
        token = admin_user_token["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/analytics/users", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # 验证必需字段
        required_fields = [
            "total_users", "new_users_today", "active_users_today", 
            "admin_users_count", "new_users_this_week", "user_registration_trend"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        # 验证数据类型
        assert isinstance(data["total_users"], int)
        assert isinstance(data["new_users_today"], int)
        assert isinstance(data["active_users_today"], int)
        assert isinstance(data["admin_users_count"], int)
        assert isinstance(data["new_users_this_week"], int)
        assert isinstance(data["user_registration_trend"], list)
        
        # 验证趋势数据结构
        for trend_item in data["user_registration_trend"]:
            assert isinstance(trend_item, dict)
            assert "date" in trend_item
            assert "count" in trend_item
            assert isinstance(trend_item["date"], str)
            assert isinstance(trend_item["count"], int)
    
    def test_user_analytics_performance(self, client: TestClient, admin_user_token):
        """测试用户统计性能"""
        token = admin_user_token["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        import time
        start_time = time.time()
        response = client.get("/api/analytics/users", headers=headers)
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = (end_time - start_time) * 1000
        assert response_time < 1000, f"User analytics too slow: {response_time}ms"


class TestUserAnalyticsAccuracy:
    """用户统计准确性测试"""
    
    def test_user_stats_accuracy(self, client: TestClient, test_db_session: Session, admin_user_token):
        """测试用户统计数据准确性"""
        # 清理现有数据（在测试会话中）
        test_db_session.query(User).filter(User.uid.like("accuracy_test_%")).delete()
        test_db_session.commit()
        
        # 创建特定的测试数据
        import time
        timestamp = int(time.time() * 1000000) % 1000000
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 今天注册的用户
        today_user = User(
            uid=f"accuracy_test_today_{timestamp}",
            display_name="Today User",
            email=f"today_{timestamp}@test.com",
            created_at=today_start + timedelta(hours=10),
            last_login_at=today_start + timedelta(hours=11)
        )
        test_db_session.add(today_user)
        
        # 昨天注册的用户
        yesterday_user = User(
            uid=f"accuracy_test_yesterday_{timestamp}",
            display_name="Yesterday User",
            email=f"yesterday_{timestamp}@test.com",
            created_at=today_start - timedelta(days=1),
            last_login_at=today_start + timedelta(hours=5)  # 今天活跃
        )
        test_db_session.add(yesterday_user)
        
        test_db_session.commit()
        
        # 获取统计数据
        token = admin_user_token["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/analytics/users?days=30", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # 验证今天注册用户数（应该包含today_user）
        assert data["new_users_today"] >= 1
        
        # 验证今天活跃用户数（应该包含today_user和yesterday_user）
        assert data["active_users_today"] >= 2
        
        # 验证本周注册用户数
        assert data["new_users_this_week"] >= 2
    
    def test_user_analytics_trend_data(self, client: TestClient, admin_user_token):
        """测试用户统计趋势数据"""
        token = admin_user_token["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/analytics/users?days=7", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        trend_data = data["user_registration_trend"]
        
        # 验证趋势数据完整性
        assert len(trend_data) == 7
        
        # 验证每日数据格式
        for day_data in trend_data:
            assert "date" in day_data
            assert "count" in day_data
            assert isinstance(day_data["date"], str)
            assert isinstance(day_data["count"], int)
            assert day_data["count"] >= 0  # 用户数不能为负


class TestUserAnalyticsMethods:
    """用户统计HTTP方法测试"""
    
    def test_user_analytics_invalid_methods(self, client: TestClient, admin_user_token):
        """测试用户统计端点无效HTTP方法"""
        token = admin_user_token["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # POST方法不被支持
        response = client.post("/api/analytics/users", headers=headers)
        assert response.status_code == 405
        
        # PUT方法不被支持
        response = client.put("/api/analytics/users", headers=headers)
        assert response.status_code == 405
        
        # DELETE方法不被支持
        response = client.delete("/api/analytics/users", headers=headers)
        assert response.status_code == 405