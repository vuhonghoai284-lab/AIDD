"""
超快速pytest配置 - 彻底解决速度和稳定性问题
"""
import pytest
import os
import sys
import sqlite3
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch, MagicMock
import logging

# 禁用过多的日志输出
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)

# 设置测试环境
os.environ.update({
    'APP_MODE': 'test',
    'CONFIG_FILE': 'config.test.yaml',
    'PYTHONPATH': os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'OPENAI_API_KEY': 'test-api-key',
    'DATABASE_URL': 'sqlite:///:memory:'
})

sys.path.insert(0, os.environ['PYTHONPATH'])

# 延迟导入，避免启动时的开销
def get_app():
    """延迟获取app"""
    from app.main import app
    return app

def get_db_components():
    """延迟获取数据库组件"""
    from app.core.database import Base, get_db
    return Base, get_db

# 全局测试数据库 - 使用更快的内存数据库
TEST_DB_URL = "sqlite:///:memory:"
_global_engine = None
_global_session_factory = None

def get_global_db():
    """获取全局数据库连接"""
    global _global_engine, _global_session_factory
    
    if _global_engine is None:
        _global_engine = create_engine(
            TEST_DB_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,  # 关闭SQL日志
            pool_pre_ping=False,  # 禁用连接检测
            pool_recycle=-1  # 禁用连接回收
        )
        
        Base, _ = get_db_components()
        Base.metadata.create_all(bind=_global_engine)
        
        _global_session_factory = sessionmaker(
            autocommit=False, 
            autoflush=False, 
            bind=_global_engine
        )
        
        # 预加载测试数据
        _preload_test_data()
    
    return _global_engine, _global_session_factory

def _preload_test_data():
    """预加载测试数据到内存数据库"""
    global _global_session_factory
    
    session = _global_session_factory()
    try:
        # 使用原生SQL快速插入数据
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

# Session级别的fixture
@pytest.fixture(scope="session")
def db_engine():
    """会话级数据库引擎"""
    engine, _ = get_global_db()
    return engine

@pytest.fixture(scope="session")
def session_factory(db_engine):
    """会话级session工厂"""
    _, factory = get_global_db()
    return factory

# Function级别的fixture - 快速清理
@pytest.fixture(scope="function")
def db_session(session_factory):
    """函数级数据库会话 - 快速清理版本"""
    session = session_factory()
    try:
        yield session
    finally:
        # 快速回滚，不提交
        session.rollback()
        session.close()

# 兼容性别名
@pytest.fixture(scope="function") 
def test_db_session(db_session):
    """向后兼容的数据库会话"""
    return db_session

# 超快速测试客户端
@pytest.fixture(scope="function")
def client(session_factory):
    """超快速测试客户端"""
    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()
    
    app = get_app()
    _, get_db = get_db_components()
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()

# 缓存的认证Token
_cached_tokens = {
    "admin": {"token": "ultra_fast_admin_token", "user": {"id": 1, "username": "sys_admin", "is_admin": True}},
    "user": {"token": "ultra_fast_user_token", "user": {"id": 2, "username": "test_user", "is_admin": False}}
}

@pytest.fixture(scope="session")
def admin_user_token():
    """缓存的管理员token"""
    return _cached_tokens["admin"]

@pytest.fixture(scope="session")
def normal_user_token():
    """缓存的普通用户token"""
    return _cached_tokens["user"]

@pytest.fixture
def auth_headers(admin_user_token):
    """管理员认证头"""
    return {"Authorization": f"Bearer {admin_user_token['token']}"}

@pytest.fixture
def normal_auth_headers(normal_user_token):
    """普通用户认证头"""
    return {"Authorization": f"Bearer {normal_user_token['token']}"}

# 预定义测试文件
_test_files = {
    "sample": ("test.md", b"# Test Document\n\nThis is a test.", "text/markdown"),
    "invalid": ("test.exe", b"invalid content", "application/octet-stream"),
    "large": ("large.md", b"# Large File\n" + b"Content " * 1000, "text/markdown")
}

@pytest.fixture(scope="session")
def sample_file():
    """示例测试文件"""
    return _test_files["sample"]

@pytest.fixture(scope="session")
def invalid_file():
    """无效文件"""
    return _test_files["invalid"]

@pytest.fixture(scope="session")
def large_file():
    """大文件"""
    return _test_files["large"]

# 超强Mock系统
@pytest.fixture(autouse=True)
def ultra_fast_mocks(monkeypatch):
    """超快速全面Mock系统"""
    
    # 1. 认证系统Mock
    def mock_verify_token(token: str):
        token_map = {
            "ultra_fast_admin_token": {"user_id": 1, "username": "sys_admin", "is_admin": True, "display_name": "系统管理员"},
            "ultra_fast_user_token": {"user_id": 2, "username": "test_user", "is_admin": False, "display_name": "测试用户"}
        }
        if token in token_map:
            return token_map[token]
        # 动态生成mock用户
        user_id = hash(token) % 10000 + 100
        return {
            "user_id": user_id,
            "username": f"mock_user_{user_id}",
            "is_admin": False,
            "display_name": f"Mock用户{user_id}"
        }
    
    # 2. 第三方认证Mock
    def mock_exchange_token(self, code: str):
        return {"access_token": f"mock_token_{abs(hash(code)) % 10000}"}
    
    def mock_third_party_login(self, access_token: str):
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
    
    # 3. HTTP请求Mock
    class UltraFastMockResponse:
        def __init__(self, status_code=200, json_data=None):
            self.status_code = status_code
            self._json_data = json_data or {"status": "ok"}
        
        def json(self):
            return self._json_data
        
        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception(f"HTTP {self.status_code}")
    
    async def mock_http_request(*args, **kwargs):
        # 根据请求类型返回不同的mock响应
        url = str(args[1]) if len(args) > 1 else kwargs.get('url', '')
        if 'token' in url:
            return UltraFastMockResponse(200, {"access_token": "mock_access_token", "token_type": "bearer"})
        elif 'userinfo' in url:
            return UltraFastMockResponse(200, {"id": "mock_user", "name": "Mock User", "email": "mock@test.com"})
        else:
            return UltraFastMockResponse(200, {"message": "success"})
    
    # 4. 任务处理Mock
    def mock_process_task(self, task_id):
        return None
    
    async def mock_async_process_task(self, task_id):
        return None
    
    # 5. AI服务Mock
    def mock_ai_service_call(*args, **kwargs):
        return {"response": "mock ai response", "confidence": 0.8}
    
    # 批量应用所有Mock
    mock_configs = [
        ("app.core.auth.verify_token", mock_verify_token),
        ("app.services.auth.ThirdPartyAuthService.exchange_code_for_token", mock_exchange_token),
        ("app.services.auth.ThirdPartyAuthService.login_with_token", mock_third_party_login),
        ("app.services.new_task_processor.NewTaskProcessor.process_task", mock_async_process_task),
    ]
    
    for attr_path, mock_func in mock_configs:
        try:
            monkeypatch.setattr(attr_path, mock_func)
        except (ImportError, AttributeError):
            # 静默忽略无法mock的模块
            pass
    
    # Mock HTTP客户端
    try:
        import httpx
        monkeypatch.setattr(httpx.AsyncClient, "post", mock_http_request)
        monkeypatch.setattr(httpx.AsyncClient, "get", mock_http_request)
        monkeypatch.setattr(httpx.AsyncClient, "request", mock_http_request)
    except ImportError:
        pass

# 测试数据快速清理
@pytest.fixture(autouse=True)
def ultra_fast_cleanup(db_session):
    """超快速数据清理"""
    yield  # 测试运行
    
    # 测试后快速清理动态数据，保留基础数据
    try:
        db_session.execute(text("DELETE FROM issues WHERE 1=1"))
        db_session.execute(text("DELETE FROM ai_outputs WHERE 1=1"))
        db_session.execute(text("DELETE FROM tasks WHERE 1=1"))
        db_session.execute(text("DELETE FROM file_infos WHERE 1=1"))
        db_session.execute(text("DELETE FROM users WHERE id > 10"))  # 保留前10个用户
        db_session.commit()
    except Exception:
        db_session.rollback()

# 性能监控
def pytest_runtest_call(item):
    """监控测试性能"""
    import time
    start = time.time()
    outcome = yield
    duration = time.time() - start
    
    if duration > 3.0:  # 超过3秒的测试
        print(f"\n🐌 慢速测试: {item.name} ({duration:.2f}s)")
        # 可以考虑标记为slow
        if hasattr(item, 'add_marker'):
            item.add_marker(pytest.mark.slow)
    
    return outcome

# 并发控制 - 避免数据库锁竞争
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """设置测试环境"""
    # 预热数据库连接
    get_global_db()
    yield
    # 清理（可选）
    global _global_engine
    if _global_engine:
        _global_engine.dispose()