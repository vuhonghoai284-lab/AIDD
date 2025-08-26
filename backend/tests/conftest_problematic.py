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
        
        # 初始化测试数据
        SessionLocal = sessionmaker(bind=_test_engine)
        with SessionLocal() as session:
            # 初始化用户数据
            from app.models.user import User
            admin_user = User(
                id=1,
                uid='sys_admin',
                display_name='系统管理员',
                email='admin@system.local',
                is_admin=True,
                is_system_admin=True
            )
            session.add(admin_user)
            
            # 初始化AI模型数据
            from app.models.ai_model import AIModel
            test_models = [
                AIModel(
                    id=1,
                    model_key='test_gpt4o_mini',
                    label='GPT-4o Mini (测试)',
                    provider='openai',
                    model_name='gpt-4o-mini',
                    description='测试模型',
                    temperature=0.1,
                    max_tokens=4096,
                    is_active=True,
                    is_default=True,
                    sort_order=1
                ),
                AIModel(
                    id=2,
                    model_key='test_claude3',
                    label='Claude-3 (测试)',
                    provider='anthropic',
                    model_name='claude-3-sonnet',
                    description='测试模型',
                    temperature=0.1,
                    max_tokens=4096,
                    is_active=True,
                    is_default=False,
                    sort_order=2
                )
            ]
            session.add_all(test_models)
            session.commit()
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

# 为兼容性提供别名
@pytest.fixture(scope="function")
def test_db_session(test_engine):
    """数据库会话别名 (向后兼容)"""
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

# 全面的mock系统
@pytest.fixture(autouse=True)
def comprehensive_mock_system(monkeypatch):
    """全面的mock系统，禁用慢速功能和外部依赖"""
    
    # 1. 禁用任务处理器
    def mock_process(self, task_id):
        print(f"Mock处理任务: {task_id}")
        return None
    
    try:
        monkeypatch.setattr("app.services.new_task_processor.NewTaskProcessor.process_task", mock_process)
    except:
        pass
    
    # 2. Mock第三方认证
    def mock_third_party_exchange_token(self, code: str):
        """Mock第三方token交换"""
        return {"access_token": f"mock_token_{hash(code) % 10000}"}
    
    def mock_third_party_login(self, access_token: str):
        """Mock第三方登录"""
        user_hash = hash(access_token) % 10000
        return {
            "access_token": f"test_user_token_{user_hash}",
            "user": {
                "id": user_hash,
                "uid": f"test_user_{user_hash}",
                "display_name": f"测试用户{user_hash}",
                "email": f"user{user_hash}@test.com",
                "avatar_url": f"https://avatar.test/{user_hash}",
                "is_admin": False
            }
        }
    
    try:
        monkeypatch.setattr("app.services.auth.ThirdPartyAuthService.exchange_code_for_token", mock_third_party_exchange_token)
        monkeypatch.setattr("app.services.auth.ThirdPartyAuthService.login_with_token", mock_third_party_login)
    except:
        pass
    
    # 3. Mock外部HTTP请求
    async def mock_http_post(*args, **kwargs):
        """Mock HTTP POST请求"""
        class MockResponse:
            def __init__(self):
                self.status_code = 200
            def json(self):
                return {"access_token": "mock_access_token", "token_type": "bearer"}
        return MockResponse()
    
    async def mock_http_get(*args, **kwargs):
        """Mock HTTP GET请求"""
        class MockResponse:
            def __init__(self):
                self.status_code = 200
            def json(self):
                return {"id": "test_user", "name": "测试用户", "email": "test@example.com"}
        return MockResponse()
    
    try:
        import httpx
        monkeypatch.setattr(httpx.AsyncClient, "post", mock_http_post)
        monkeypatch.setattr(httpx.AsyncClient, "get", mock_http_get)
    except:
        pass