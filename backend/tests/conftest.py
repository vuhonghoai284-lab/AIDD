"""
修复后的pytest配置，专注于稳定性和速度
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
from unittest.mock import patch, MagicMock

# 设置测试环境
os.environ['APP_MODE'] = 'test'
os.environ['CONFIG_FILE'] = 'config.test.yaml'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.core.database import Base, get_db

# 创建全局测试引擎和数据
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False
)

# 创建表和初始数据
Base.metadata.create_all(bind=engine)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 初始化测试数据
def init_test_data():
    """初始化测试数据"""
    session = TestingSessionLocal()
    try:
        from sqlalchemy import text
        # 清理现有数据
        session.execute(text("DELETE FROM users"))
        session.execute(text("DELETE FROM ai_models")) 
        
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
        from datetime import datetime
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
                sort_order=1,
                created_at=datetime.now()
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
                sort_order=2,
                created_at=datetime.now()
            )
        ]
        session.add_all(test_models)
        session.commit()
    finally:
        session.close()

# 初始化数据
init_test_data()

@pytest.fixture(scope="function")
def db_session():
    """数据库会话"""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()  # 回滚而不是提交
        session.close()

# 兼容性别名
@pytest.fixture(scope="function")
def test_db_session():
    """数据库会话别名 (向后兼容)"""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

@pytest.fixture(scope="function")
def client():
    """测试客户端"""
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()

# 认证fixtures
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

# 全面Mock系统
@pytest.fixture(autouse=True)
def comprehensive_mocks(monkeypatch):
    """全面的mock系统"""
    
    # 1. Mock认证系统
    def mock_verify_token(token: str):
        if token == "admin_token":
            return {"user_id": 1, "username": "sys_admin", "is_admin": True, "display_name": "系统管理员"}
        elif token == "user_token":
            return {"user_id": 2, "username": "test_user", "is_admin": False, "display_name": "测试用户"}
        else:
            raise Exception("Invalid token")
    
    # 2. Mock第三方认证
    def mock_exchange_token(self, code: str):
        return {"access_token": f"mock_token_{hash(code) % 10000}"}
    
    def mock_third_party_login(self, access_token: str):
        user_hash = abs(hash(access_token)) % 10000
        return {
            "access_token": f"test_user_token_{user_hash}",
            "user": {
                "id": user_hash,
                "uid": f"test_user_{user_hash}",
                "display_name": f"测试用户{user_hash}",
                "email": f"user{user_hash}@test.com",
                "is_admin": False
            }
        }
    
    # 3. Mock HTTP请求
    class MockHTTPResponse:
        def __init__(self, status_code=200, json_data=None):
            self.status_code = status_code
            self._json_data = json_data or {}
        
        def json(self):
            return self._json_data
        
        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception(f"HTTP {self.status_code}")
    
    async def mock_http_post(*args, **kwargs):
        return MockHTTPResponse(200, {"access_token": "mock_access_token"})
    
    async def mock_http_get(*args, **kwargs):
        return MockHTTPResponse(200, {"id": "test_user", "name": "测试用户"})
    
    # 4. Mock任务处理
    def mock_process_task(self, task_id):
        return None
    
    # 应用所有mock
    try:
        # 认证相关
        monkeypatch.setattr("app.core.auth.verify_token", mock_verify_token)
        monkeypatch.setattr("app.services.auth.ThirdPartyAuthService.exchange_code_for_token", mock_exchange_token)
        monkeypatch.setattr("app.services.auth.ThirdPartyAuthService.login_with_token", mock_third_party_login)
        
        # HTTP请求
        import httpx
        monkeypatch.setattr(httpx.AsyncClient, "post", mock_http_post)
        monkeypatch.setattr(httpx.AsyncClient, "get", mock_http_get)
        
        # 任务处理
        monkeypatch.setattr("app.services.new_task_processor.NewTaskProcessor.process_task", mock_process_task)
        
    except Exception as e:
        # 静默处理mock失败，不影响测试
        pass

# 测试数据重置
@pytest.fixture(autouse=True)
def reset_test_data():
    """每个测试后重置数据（除了基础数据）"""
    yield  # 测试运行
    
    # 测试后清理
    session = TestingSessionLocal()
    try:
        from sqlalchemy import text
        # 只清理测试产生的数据，保留基础数据
        session.execute(text("DELETE FROM issues WHERE 1=1"))
        session.execute(text("DELETE FROM ai_outputs WHERE 1=1"))
        session.execute(text("DELETE FROM tasks WHERE 1=1"))  
        session.execute(text("DELETE FROM file_infos WHERE 1=1"))
        session.execute(text("DELETE FROM users WHERE id > 2"))  # 保留前两个用户
        session.commit()
    except:
        session.rollback()
    finally:
        session.close()