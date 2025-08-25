"""
测试配置和fixtures
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import sys
import os
import tempfile
from unittest.mock import patch, AsyncMock

# 设置测试环境变量（必须在导入应用之前）
os.environ['APP_MODE'] = 'test'

# 设置第三方认证的mock配置
os.environ['FRONTEND_DOMAIN'] = 'http://localhost:3000'
os.environ['THIRD_PARTY_CLIENT_ID'] = 'test_client_id'
os.environ['THIRD_PARTY_CLIENT_SECRET'] = 'test_client_secret'
os.environ['THIRD_PARTY_AUTH_URL'] = 'https://test-auth.example.com/oauth2/authorize'
os.environ['THIRD_PARTY_TOKEN_URL'] = 'https://test-auth.example.com/oauth2/accesstoken'
os.environ['THIRD_PARTY_USERINFO_URL'] = 'https://test-auth.example.com/oauth2/userinfo'

# 添加父目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.core.database import Base, get_db

# 导入所有模型以确保它们被包含在Base.metadata中
from app.models.user import User
from app.models.task import Task
from app.models.ai_model import AIModel
from app.models.file_info import FileInfo

# 导入DTO类
from app.dto.user import UserCreate

# 创建内存测试数据库 - 使用StaticPool确保所有连接使用同一个内存数据库
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # 使用静态连接池，确保所有连接使用同一个内存数据库
    echo=False
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """覆盖数据库依赖"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")  # 改为function级别
def client():
    """创建测试客户端"""
    # 创建测试数据库表
    Base.metadata.create_all(bind=engine)
    
    # 覆盖依赖（必须在创建表之后，在初始化数据之前）
    app.dependency_overrides[get_db] = override_get_db
    
    # 初始化基础数据
    db = TestingSessionLocal()
    try:
        # 创建测试用AI模型
        from app.models.ai_model import AIModel
        
        test_model = AIModel(
            model_key="gpt-4o-mini",
            label="GPT-4o Mini (快速)",
            provider="openai",
            model_name="gpt-4o-mini",
            description="OpenAI GPT-4o Mini模型",
            is_active=True,
            is_default=True,
            sort_order=0
        )
        
        test_model2 = AIModel(
            model_key="claude-3-sonnet",
            label="Claude 3 Sonnet",
            provider="anthropic", 
            model_name="claude-3-sonnet-20240229",
            description="Anthropic Claude 3 Sonnet模型",
            is_active=True,
            is_default=False,
            sort_order=1
        )
        
        db.add(test_model)
        db.add(test_model2)
        db.commit()
        print(f"✓ 已初始化 2 个AI模型")
    except Exception as e:
        print(f"初始化测试数据失败: {e}")
        db.rollback()
    finally:
        db.close()
    
    # 创建测试客户端
    with TestClient(app) as c:
        yield c
    
    # 清理
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


@pytest.fixture
def sample_file():
    """创建测试文件"""
    content = b"# Test Document\nThis is a test content."
    return ("test.md", content, "text/markdown")


@pytest.fixture
def large_file():
    """创建大文件用于测试"""
    content = b"# Large Test Document\n" + b"This is test content.\n" * 10000
    return ("large_test.md", content, "text/markdown")


@pytest.fixture
def invalid_file():
    """创建无效文件类型"""
    content = b"\x00\x01\x02\x03"  # 二进制内容
    return ("test.exe", content, "application/octet-stream")


@pytest.fixture
def sample_pdf_file():
    """创建PDF测试文件"""
    # 简单的PDF文件头
    content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
    return ("test.pdf", content, "application/pdf")


@pytest.fixture
def test_db_session():
    """获取测试数据库会话"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def admin_user_token(client):
    """创建管理员用户并返回token - 通过API"""
    # 通过系统管理员登录API获取token
    login_data = {"username": "admin", "password": "admin123"}
    response = client.post("/api/auth/system/login", data=login_data)
    if response.status_code == 200:
        result = response.json()
        return {"token": result["access_token"], "user": result["user"]}
    else:
        # 如果系统登录失败，创建测试用户
        from app.repositories.user import UserRepository
        from app.services.auth import AuthService
        
        db = TestingSessionLocal()
        try:
            user_repo = UserRepository(db)
            auth_service = AuthService(db)
            
            admin_data = UserCreate(
                uid="test_admin",
                display_name="测试管理员", 
                email="admin@test.com",
                is_admin=True,
                is_system_admin=True
            )
            
            admin_user = user_repo.create(admin_data)
            token = auth_service.create_access_token(data={"sub": str(admin_user.id)})
            
            return {"token": token, "user": admin_user}
        finally:
            db.close()


@pytest.fixture
def normal_user_token(client):
    """创建普通用户并返回token - 通过API"""
    # 通过第三方认证API获取token
    auth_data = {"code": "test_user_auth_code"}
    response = client.post("/api/auth/thirdparty/login", json=auth_data)
    if response.status_code == 200:
        result = response.json()
        return {"token": result["access_token"], "user": result["user"]}
    else:
        # 如果第三方登录失败，创建测试用户
        from app.repositories.user import UserRepository
        from app.services.auth import AuthService
        
        db = TestingSessionLocal()
        try:
            user_repo = UserRepository(db)
            auth_service = AuthService(db)
            
            user_data = UserCreate(
                uid="test_user_001",
                display_name="测试用户001",
                email="user001@test.com",
                is_admin=False,
                is_system_admin=False
            )
            
            normal_user = user_repo.create(user_data)
            token = auth_service.create_access_token(data={"sub": str(normal_user.id)})
            
            return {"token": token, "user": normal_user}
        finally:
            db.close()


@pytest.fixture
def auth_headers(admin_user_token):
    """管理员认证头"""
    return {"Authorization": f"Bearer {admin_user_token['token']}"}


@pytest.fixture
def normal_auth_headers(normal_user_token):
    """普通用户认证头"""
    return {"Authorization": f"Bearer {normal_user_token['token']}"}


@pytest.fixture
def temp_upload_dir():
    """创建临时上传目录"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture(autouse=True)
def mock_third_party_auth():
    """Mock第三方认证HTTP请求"""
    
    async def mock_token_request(*args, **kwargs):
        """Mock token获取请求"""
        class MockResponse:
            def json(self):
                return {
                    "access_token": "mock_access_token_12345",
                    "refresh_token": "mock_refresh_token_67890", 
                    "scope": "base.profile",
                    "expires_in": 3600
                }
            
            def raise_for_status(self):
                pass
        
        return MockResponse()
    
    async def mock_userinfo_request(*args, **kwargs):
        """Mock用户信息获取请求"""
        # 从请求中获取auth code来生成不同的用户信息
        request_url = args[0] if args else kwargs.get('url', '')
        request_json = kwargs.get('json', {})
        request_data = kwargs.get('data', {})
        
        # 获取auth code
        auth_code = request_data.get('code') or request_json.get('code')
        
        class MockResponse:
            def json(self):
                # 根据auth code生成不同的用户信息
                if auth_code == "user_a_auth_code":
                    return {
                        "uid": "test_user_a",
                        "displayNameCn": "测试用户A",
                        "email": "user_a@test.com"
                    }
                elif auth_code == "user_c_auth_code":
                    return {
                        "uid": "test_user_c", 
                        "displayNameCn": "测试用户C",
                        "email": "user_c@test.com"
                    }
                else:
                    # 默认测试用户
                    return {
                        "uid": "test_third_party_user",
                        "displayNameCn": "第三方测试用户",
                        "email": "third_party@test.com"
                    }
            
            def raise_for_status(self):
                pass
        
        return MockResponse()
    
    # Mock httpx.AsyncClient的post和get方法
    with patch('httpx.AsyncClient') as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # 根据请求URL决定返回哪个mock响应
        async def mock_request_handler(method, url_or_first_arg, **kwargs):
            if method == 'POST':
                url = url_or_first_arg
                if 'accesstoken' in url or 'token' in url:
                    return await mock_token_request(url, **kwargs)
                else:
                    return await mock_userinfo_request(url, **kwargs)
            elif method == 'GET':
                url = url_or_first_arg
                return await mock_userinfo_request(url, **kwargs)
        
        async def post_handler(*args, **kwargs):
            return await mock_request_handler('POST', *args, **kwargs)
        
        async def get_handler(*args, **kwargs):  
            return await mock_request_handler('GET', *args, **kwargs)
        
        mock_instance.post = post_handler
        mock_instance.get = get_handler
        
        yield mock_client