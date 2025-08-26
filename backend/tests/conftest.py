"""
超简化的pytest配置，专注于速度
"""
import pytest
import os
import sys
import tempfile
import io
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch

# 设置测试环境
os.environ['APP_MODE'] = 'test'
os.environ['CONFIG_FILE'] = 'config.test.yaml'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.core.database import Base, get_db

# 全局变量缓存
_test_engine = None

def get_test_engine():
    """获取测试引擎"""
    global _test_engine
    if _test_engine is None:
        _test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False
        )
        Base.metadata.create_all(bind=_test_engine)
    return _test_engine

@pytest.fixture(scope="session")
def test_engine():
    return get_test_engine()

@pytest.fixture(scope="function")
def db_session(test_engine):
    """数据库会话"""
    SessionLocal = sessionmaker(bind=test_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture(scope="function") 
def client(test_engine):
    """测试客户端"""
    def override_get_db():
        SessionLocal = sessionmaker(bind=test_engine)
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

# 快速认证fixtures
@pytest.fixture(scope="session")
def admin_user_token():
    return {"token": "admin_token", "user": {"id": 1, "username": "admin", "is_admin": True}}

@pytest.fixture(scope="session")
def normal_user_token():
    return {"token": "user_token", "user": {"id": 2, "username": "user", "is_admin": False}}

@pytest.fixture
def auth_headers(admin_user_token):
    return {"Authorization": f"Bearer {admin_user_token['token']}"}

@pytest.fixture
def normal_auth_headers(normal_user_token):
    return {"Authorization": f"Bearer {normal_user_token['token']}"}

# 测试文件fixtures
@pytest.fixture(scope="session")
def sample_file():
    content = "# 测试文档\n\n这是测试内容。"
    return ("test.md", content.encode('utf-8'), "text/markdown")

@pytest.fixture(scope="session")
def invalid_file():
    return ("test.exe", b"invalid", "application/octet-stream")

# 禁用慢速处理
@pytest.fixture(autouse=True)
def disable_slow_processing(monkeypatch):
    """禁用慢速的后台处理"""
    def mock_process(self, task_id):
        print(f"Mock处理任务: {task_id}")
        return None
    
    # 禁用任务处理器
    try:
        monkeypatch.setattr("app.services.new_task_processor.NewTaskProcessor.process_task", mock_process)
    except:
        pass