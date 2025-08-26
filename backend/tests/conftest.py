"""
兼容版pytest配置 - 同时支持直接pytest和优化执行器
"""
import pytest
import os
import sys
import tempfile
import logging
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch, MagicMock

# 导入依赖Mock（必须在其他导入之前）
try:
    from . import mock_dependencies
except ImportError:
    import mock_dependencies

# 设置测试环境
os.environ.update({
    'APP_MODE': 'test',
    'CONFIG_FILE': 'config.test.yaml',
    'OPENAI_API_KEY': 'test-api-key',
    'DATABASE_URL': 'sqlite:///:memory:'
})

# 确保路径正确
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# 禁用过多的日志输出
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)

# 导入应用组件
from app.main import app
from app.core.database import Base, get_db

# 全局数据库配置
TEST_DB_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def db_engine():
    """会话级数据库引擎"""
    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # 清理
    engine.dispose()

@pytest.fixture(scope="session")
def session_factory(db_engine):
    """会话级session工厂"""
    SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    
    # 预加载测试数据
    session = SessionFactory()
    try:
        # 使用原生SQL快速插入基础数据
        session.execute(text("""
            INSERT OR IGNORE INTO users (id, uid, display_name, email, is_admin, is_system_admin, created_at)
            VALUES 
                (1, 'sys_admin', '系统管理员', 'admin@test.com', 1, 1, datetime('now')),
                (2, 'test_user', '测试用户', 'user@test.com', 0, 0, datetime('now'))
        """))
        
        session.execute(text("""
            INSERT OR IGNORE INTO ai_models (id, model_key, label, provider, model_name, description, 
                                           temperature, max_tokens, is_active, is_default, sort_order, created_at)
            VALUES 
                (1, 'test_gpt4o_mini', 'GPT-4o Mini (测试)', 'openai', 'gpt-4o-mini', '测试模型',
                 0.1, 4096, 1, 1, 1, datetime('now')),
                (2, 'test_claude3', 'Claude-3 (测试)', 'anthropic', 'claude-3-sonnet', '测试模型',
                 0.1, 4096, 1, 0, 2, datetime('now'))
        """))
        
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"预加载数据失败: {e}")
    finally:
        session.close()
    
    return SessionFactory

@pytest.fixture(scope="function")
def db_session(session_factory):
    """函数级数据库会话"""
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

@pytest.fixture(scope="function") 
def test_db_session(db_session):
    """向后兼容的数据库会话别名"""
    return db_session

@pytest.fixture(scope="function")
def client(session_factory):
    """测试客户端"""
    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()

# 认证相关fixtures
@pytest.fixture(scope="session")
def admin_user_token():
    """管理员token"""
    return {
        "token": "test_admin_token", 
        "user": {"id": 1, "username": "sys_admin", "is_admin": True}
    }

@pytest.fixture(scope="session")
def normal_user_token():
    """普通用户token"""
    return {
        "token": "test_user_token", 
        "user": {"id": 2, "username": "test_user", "is_admin": False}
    }

@pytest.fixture
def auth_headers(admin_user_token):
    """管理员认证头"""
    return {"Authorization": f"Bearer {admin_user_token['token']}"}

@pytest.fixture
def normal_auth_headers(normal_user_token):
    """普通用户认证头"""
    return {"Authorization": f"Bearer {normal_user_token['token']}"}

# 测试文件fixtures
@pytest.fixture(scope="session")
def sample_file():
    """示例测试文件"""
    return ("test.md", b"# Test Document\n\nThis is a test.", "text/markdown")

@pytest.fixture(scope="session")
def invalid_file():
    """无效文件"""
    return ("test.exe", b"invalid content", "application/octet-stream")

@pytest.fixture(scope="session")
def large_file():
    """大文件"""
    return ("large.md", b"# Large File\n" + b"Content " * 1000, "text/markdown")

# 全面Mock系统
@pytest.fixture(autouse=True)
def comprehensive_mocks(monkeypatch):
    """全面的mock系统"""
    
    # 1. 认证系统Mock
    def mock_verify_token(token: str):
        token_map = {
            "test_admin_token": {
                "user_id": 1, "username": "sys_admin", "is_admin": True, 
                "display_name": "系统管理员"
            },
            "test_user_token": {
                "user_id": 2, "username": "test_user", "is_admin": False,
                "display_name": "测试用户"
            }
        }
        if token in token_map:
            return token_map[token]
        
        # 动态生成mock用户
        user_id = abs(hash(token)) % 10000 + 100
        return {
            "user_id": user_id,
            "username": f"mock_user_{user_id}",
            "is_admin": False,
            "display_name": f"Mock用户{user_id}"
        }
    
    # 2. 第三方认证Mock
    def mock_exchange_code_for_token(self, code: str):
        """Mock第三方认证令牌交换"""
        print(f"🔧 Mock exchange_code_for_token被调用，code: {code[:10]}...")
        return {
            "access_token": f"mock_token_{abs(hash(code)) % 10000}",
            "token_type": "bearer",
            "scope": "read write",
            "refresh_token": f"refresh_token_{abs(hash(code)) % 10000}",
            "expires_in": 3600
        }
    
    def mock_get_user_info(self, access_token: str):
        """Mock获取用户信息"""
        print(f"🔧 Mock get_user_info被调用，token: {access_token[:10]}...")
        user_id = abs(hash(access_token)) % 10000 + 1000
        return {
            "id": user_id,
            "login": f"mock_user_{user_id}",
            "name": f"Mock用户{user_id}",
            "avatar_url": "https://gitee.com/assets/no_portrait.png",
            "email": f"mock{user_id}@gitee.com"
        }
    
    def mock_login_with_token(self, access_token: str):
        user_id = abs(hash(access_token)) % 10000 + 1000
        return {
            "access_token": f"mock_user_token_{user_id}",
            "user": {
                "id": user_id,
                "uid": f"third_party_user_{user_id}",
                "display_name": f"第三方用户{user_id}",
                "email": f"user{user_id}@thirdparty.com",
                "is_admin": False
            }
        }
    
    # UltraFastMockResponse class for enhanced HTTP mocks
    class UltraFastMockResponse:
        def __init__(self, status_code=200, json_data=None):
            self.status_code = status_code
            self._json_data = json_data or {}
        
        def json(self):
            return self._json_data
        
        async def json(self):
            return self._json_data
        
        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception(f"HTTP {self.status_code}")
    
    # 3. HTTP请求Mock
    class MockHTTPResponse:
        def __init__(self, status_code=200, json_data=None):
            self.status_code = status_code
            self._json_data = json_data or {"status": "ok"}
        
        def json(self):
            return self._json_data
        
        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception(f"HTTP {self.status_code}")
    
    async def mock_http_request(*args, **kwargs):
        url = str(args[1]) if len(args) > 1 else kwargs.get('url', '')
        if 'token' in url:
            return MockHTTPResponse(200, {
                "access_token": "mock_access_token", 
                "token_type": "bearer"
            })
        elif 'userinfo' in url:
            return MockHTTPResponse(200, {
                "id": "mock_user", 
                "name": "Mock User", 
                "email": "mock@test.com"
            })
        else:
            return MockHTTPResponse(200, {"message": "success"})
    
    # 4. 任务处理Mock
    async def mock_async_process_task(self, task_id):
        return {"task_id": task_id, "status": "completed"}
    
    def mock_sync_process_task(self, task_id):
        return {"task_id": task_id, "status": "completed"}
    
    
# 报告生成Mock
def mock_generate_report(self, task_id, user):
    """Mock报告生成，避免xlsxwriter依赖问题"""
    try:
        # 尝试生成真实报告
        from app.services.report_generator import ReportGenerator
        generator = ReportGenerator()
        return generator.generate_excel_report(task_id, user)
    except (ImportError, Exception) as e:
        # 如果失败，返回Mock数据
        import io
        mock_content = b"Mock Excel Report Content for Task " + str(task_id).encode()
        return io.BytesIO(mock_content), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    # 批量应用Mock
    mock_configs = [
        ("app.services.auth.ThirdPartyAuthService.get_user_info", mock_get_user_info),
        ("app.services.report_generator.ReportGenerator.generate_excel_report", mock_generate_report),
        ("app.core.auth.verify_token", mock_verify_token),
        ("app.services.auth.ThirdPartyAuthService.exchange_code_for_token", mock_exchange_code_for_token),
        ("app.services.auth.ThirdPartyAuthService.login_with_token", mock_login_with_token),
        ("app.services.new_task_processor.NewTaskProcessor.process_task", mock_async_process_task),
        ("app.services.task_processor.TaskProcessor.process_task", mock_sync_process_task),
    ]
    
    for attr_path, mock_func in mock_configs:
        try:
            monkeypatch.setattr(attr_path, mock_func)
        except (ImportError, AttributeError) as e:
            # 静默忽略无法mock的模块
            pass
    
    
    # 增强的HTTP Mock系统
    async def mock_http_request_enhanced(*args, **kwargs):
        """更强的HTTP Mock，完全拦截外部请求"""
        import time
        method = args[0] if args else kwargs.get('method', 'GET')
        url = str(args[1]) if len(args) > 1 else kwargs.get('url', '')
        
        # Gitee OAuth相关请求
        if 'gitee.com' in url or 'oauth' in url:
            if 'token' in url or '/oauth/token' in url:
                return UltraFastMockResponse(200, {
                    "access_token": "mock_gitee_token",
                    "token_type": "bearer",
                    "expires_in": 7200,
                    "refresh_token": "mock_refresh_token",
                    "scope": "user_info",
                    "created_at": int(time.time())
                })
            elif 'user' in url or '/user' in url:
                return UltraFastMockResponse(200, {
                    "id": 12345,
                    "login": "test_user",
                    "name": "测试用户",
                    "avatar_url": "https://gitee.com/assets/no_portrait.png",
                    "email": "test@gitee.com"
                })
        
        # 其他外部请求的通用Mock
        return UltraFastMockResponse(200, {"status": "mocked", "message": "success"})
    
    # Mock aiohttp.ClientSession (如果存在)
    try:
        import aiohttp
        
        class MockClientSession:
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
            
            async def post(self, url, **kwargs):
                return await mock_http_request_enhanced('POST', url, **kwargs)
            
            async def get(self, url, **kwargs):
                return await mock_http_request_enhanced('GET', url, **kwargs)
        
        # 替换aiohttp.ClientSession
        monkeypatch.setattr(aiohttp, "ClientSession", MockClientSession)
        
    except ImportError:
        pass
    # Mock HTTP客户端
    try:
        import httpx
        monkeypatch.setattr(httpx.AsyncClient, "post", mock_http_request)
        monkeypatch.setattr(httpx.AsyncClient, "get", mock_http_request)
        monkeypatch.setattr(httpx.AsyncClient, "request", mock_http_request)
    except ImportError:
        pass

# 数据清理
@pytest.fixture(autouse=True)
def cleanup_test_data(db_session):
    """测试后清理数据"""
    yield  # 测试运行
    
    # 清理动态数据，保留基础数据
    try:
        db_session.execute(text("DELETE FROM issues WHERE 1=1"))
        db_session.execute(text("DELETE FROM ai_outputs WHERE 1=1"))  
        db_session.execute(text("DELETE FROM tasks WHERE 1=1"))
        db_session.execute(text("DELETE FROM file_infos WHERE 1=1"))
        db_session.execute(text("DELETE FROM users WHERE id > 10"))  # 保留基础用户
        db_session.commit()
    except Exception:
        db_session.rollback()

# 性能监控
def pytest_runtest_call(item):
    """监控慢速测试"""
    import time
    start = time.time()
    outcome = yield
    duration = time.time() - start
    
    if duration > 5.0:  # 超过5秒的测试
        print(f"\n🐌 慢速测试: {item.name} ({duration:.2f}s)")
    
    return outcome

# 测试环境预热
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """设置测试环境"""
    print("\n🧪 初始化测试环境...")
    yield
    print("\n✅ 测试环境清理完成")