"""
优化的pytest配置
提供更快的fixture和数据库操作
"""
import pytest
import pytest_asyncio
import tempfile
import shutil
import io
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.models.user import User
from app.models.ai_model import AIModel
from app.services.model_initializer import ModelInitializer


# 使用内存数据库提升测试速度
@pytest.fixture(scope="session")
def memory_engine():
    """会话级别的内存数据库引擎"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
        echo=False  # 关闭SQL日志提升性能
    )
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    # 初始化基础数据
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    with SessionLocal() as session:
        # 创建默认系统管理员
        admin_user = User(
            username="sys_admin",
            display_name="系统管理员",
            email="admin@system.local",
            avatar_url="https://api.dicebear.com/7.x/personas/svg?seed=admin",
            is_admin=True,
            provider="system",
            provider_user_id="admin_001"
        )
        session.add(admin_user)
        
        # 快速初始化AI模型（测试模式）
        initializer = ModelInitializer(session)
        initializer.initialize_test_models()
        
    return engine


@pytest.fixture(scope="function")
def db(memory_engine):
    """函数级别的数据库会话，测试间自动清理"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=memory_engine)
    session = SessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        
        # 快速清理测试数据（除了基础数据）
        with SessionLocal() as cleanup_session:
            # 清理任务相关数据，保留用户和模型
            cleanup_session.execute("DELETE FROM issues WHERE 1=1")
            cleanup_session.execute("DELETE FROM ai_outputs WHERE 1=1") 
            cleanup_session.execute("DELETE FROM tasks WHERE 1=1")
            cleanup_session.execute("DELETE FROM file_infos WHERE 1=1")
            # 清理除系统管理员外的用户
            cleanup_session.execute("DELETE FROM users WHERE username != 'sys_admin'")
            cleanup_session.commit()


@pytest.fixture(scope="function")
def client(memory_engine):
    """优化的测试客户端，使用内存数据库"""
    
    def override_get_db():
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=memory_engine)
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


# 缓存的认证token，避免重复登录
_cached_admin_token = None
_cached_normal_token = None

@pytest.fixture(scope="session")
def admin_user_token():
    """缓存的管理员token"""
    global _cached_admin_token
    if _cached_admin_token is None:
        # 使用简单的mock token
        _cached_admin_token = {
            "token": "mock_admin_token_fast",
            "user": {
                "id": 1,
                "username": "sys_admin",
                "is_admin": True
            }
        }
    return _cached_admin_token


@pytest.fixture(scope="session") 
def normal_user_token():
    """缓存的普通用户token"""
    global _cached_normal_token
    if _cached_normal_token is None:
        _cached_normal_token = {
            "token": "mock_normal_token_fast",
            "user": {
                "id": 2,
                "username": "test_user",
                "is_admin": False
            }
        }
    return _cached_normal_token


@pytest.fixture
def auth_headers(admin_user_token):
    """快速认证头"""
    return {"Authorization": f"Bearer {admin_user_token['token']}"}


@pytest.fixture
def normal_auth_headers(normal_user_token):
    """快速普通用户认证头"""
    return {"Authorization": f"Bearer {normal_user_token['token']}"}


# 预定义的测试文件，避免重复创建
@pytest.fixture(scope="session")
def sample_file():
    """缓存的示例文件"""
    content = "# 测试文档\n\n这是一个用于测试的示例文档。"
    return ("test.md", content.encode('utf-8'), "text/markdown")


@pytest.fixture(scope="session")
def invalid_file():
    """缓存的无效文件"""
    content = b"invalid file content"
    return ("test.exe", content, "application/octet-stream")


# Mock认证配置，加速认证流程
@pytest.fixture(autouse=True)
def mock_auth_optimized(monkeypatch):
    """优化的认证mock，减少外部调用"""
    
    def mock_verify_token(token: str):
        # 快速token验证
        if token == "mock_admin_token_fast":
            return {
                "user_id": 1,
                "username": "sys_admin", 
                "is_admin": True,
                "display_name": "系统管理员"
            }
        elif token == "mock_normal_token_fast":
            return {
                "user_id": 2,
                "username": "test_user",
                "is_admin": False, 
                "display_name": "测试用户"
            }
        elif token.startswith("mock_user_"):
            # 动态生成用户token
            user_id = hash(token) % 10000
            return {
                "user_id": user_id,
                "username": f"user_{user_id}",
                "is_admin": False,
                "display_name": f"用户{user_id}"
            }
        else:
            raise Exception("Invalid token")
    
    # 模拟第三方认证
    def mock_exchange_token(code: str):
        import hashlib
        token_hash = hashlib.md5(str(code).encode()).hexdigest()[:16]
        return {"access_token": f"mock_access_token_{token_hash}"}
    
    def mock_third_party_login(access_token: str):
        if access_token.startswith("mock_access_token_"):
            user_id = hash(access_token) % 10000
            return {
                "access_token": f"mock_user_{user_id}",
                "user": {
                    "id": user_id,
                    "username": f"user_{user_id}",
                    "display_name": f"用户{user_id}",
                    "is_admin": False
                }
            }
        raise Exception("Invalid access token")
    
    # 应用所有mock
    monkeypatch.setattr("app.core.auth.verify_token", mock_verify_token)
    monkeypatch.setattr("app.services.auth.ThirdPartyAuthService.exchange_code_for_token", mock_exchange_token)
    monkeypatch.setattr("app.services.auth.ThirdPartyAuthService.login_with_token", mock_third_party_login)


# 临时目录管理
@pytest.fixture(scope="session")
def temp_upload_dir():
    """会话级别的临时上传目录"""
    temp_dir = tempfile.mkdtemp(prefix="pytest_uploads_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(autouse=True)
def setup_test_config(monkeypatch, temp_upload_dir):
    """自动应用测试配置"""
    # 设置快速配置
    monkeypatch.setenv("CONFIG_FILE", "config.test.yaml")
    monkeypatch.setenv("UPLOAD_DIR", temp_upload_dir)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    
    # 禁用慢速功能
    monkeypatch.setattr("app.services.new_task_processor.NewTaskProcessor.process_task", 
                       lambda self, task_id: None)


# 性能监控装饰器
def pytest_runtest_call(item):
    """监控测试执行时间"""
    import time
    start = time.time()
    outcome = yield
    duration = time.time() - start
    
    # 标记慢速测试
    if duration > 2.0:
        print(f"\n⚠️  慢速测试: {item.name} ({duration:.2f}s)")
    
    return outcome


# 并行测试配置
def pytest_configure(config):
    """pytest配置优化"""
    # 设置worker数量
    if hasattr(config.option, 'numprocesses'):
        if config.option.numprocesses == 'auto':
            import multiprocessing
            config.option.numprocesses = min(multiprocessing.cpu_count(), 4)


# 跳过慢速测试的条件
@pytest.fixture
def skip_slow_tests():
    """用于跳过慢速测试的标记"""
    return pytest.mark.skipif(
        pytest.current_test_config.get("skip_slow", False),
        reason="Skipping slow tests for fast execution"
    )