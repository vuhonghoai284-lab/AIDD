"""
最小化的pytest配置，专为快速测试优化
"""
import pytest
import pytest_asyncio
import tempfile
import shutil
import io
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db


# 全局变量缓存
_memory_engine = None
_test_client = None

def get_or_create_memory_engine():
    """获取或创建内存数据库引擎"""
    global _memory_engine
    if _memory_engine is None:
        _memory_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False
        )
        # 创建表
        Base.metadata.create_all(bind=_memory_engine)
        
        # 初始化基础数据
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_memory_engine)
        with SessionLocal() as session:
            # 创建用户表数据
            session.execute(text("""
                INSERT OR IGNORE INTO users (id, uid, display_name, email, is_admin, is_system_admin, created_at)
                VALUES (1, 'sys_admin', '系统管理员', 'admin@system.local', 1, 1, datetime('now'))
            """))
            
            # 创建AI模型数据
            session.execute(text("""
                INSERT OR IGNORE INTO ai_models (id, model_key, label, provider, model_name, description, temperature, max_tokens, is_active, is_default, sort_order, created_at)
                VALUES 
                (1, 'test_gpt4o_mini', 'GPT-4o Mini (测试)', 'openai', 'gpt-4o-mini', '测试模型', 0.1, 4096, 1, 1, 1, datetime('now')),
                (2, 'test_claude3', 'Claude-3 (测试)', 'anthropic', 'claude-3-sonnet', '测试模型', 0.1, 4096, 1, 0, 2, datetime('now'))
            """))
            
            session.commit()
    
    return _memory_engine


@pytest.fixture(scope="session")
def memory_engine():
    """会话级内存数据库引擎"""
    return get_or_create_memory_engine()


@pytest.fixture(scope="function") 
def db(memory_engine):
    """函数级数据库会话"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=memory_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(memory_engine):
    """优化的测试客户端"""
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


# 预定义快速认证
@pytest.fixture(scope="session")
def admin_user_token():
    """缓存管理员token"""
    return {
        "token": "mock_admin_token_fast",
        "user": {"id": 1, "username": "sys_admin", "is_admin": True}
    }


@pytest.fixture(scope="session") 
def normal_user_token():
    """缓存普通用户token"""
    return {
        "token": "mock_normal_token_fast", 
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


# 预定义测试文件
@pytest.fixture(scope="session")
def sample_file():
    """示例测试文件"""
    content = "# 测试文档\n\n这是测试内容。"
    return ("test.md", content.encode('utf-8'), "text/markdown")


@pytest.fixture(scope="session")
def invalid_file():
    """无效文件"""
    return ("test.exe", b"invalid", "application/octet-stream")


# 快速mock认证
@pytest.fixture(autouse=True)
def mock_auth_fast(monkeypatch):
    """超快速认证mock"""
    
    def mock_verify_token(token: str):
        if token == "mock_admin_token_fast":
            return {"user_id": 1, "username": "sys_admin", "is_admin": True, "display_name": "系统管理员"}
        elif token == "mock_normal_token_fast":
            return {"user_id": 2, "username": "test_user", "is_admin": False, "display_name": "测试用户"}
        else:
            raise Exception("Invalid token")
    
    def mock_exchange_token(code: str):
        return {"access_token": f"mock_access_token_{hash(code) % 10000}"}
    
    def mock_third_party_login(access_token: str):
        user_id = hash(access_token) % 10000
        return {
            "access_token": f"mock_user_{user_id}",
            "user": {"id": user_id, "username": f"user_{user_id}", "display_name": f"用户{user_id}", "is_admin": False}
        }
    
    monkeypatch.setattr("app.core.auth.verify_token", mock_verify_token)


# 测试环境配置  
@pytest.fixture(autouse=True)
def setup_fast_config(monkeypatch):
    """快速测试配置"""
    monkeypatch.setenv("CONFIG_FILE", "config.test.yaml")
    
    # 禁用慢速后台处理
    def mock_process_task(self, task_id):
        print(f"🔄 Mock处理任务: {task_id}")
        return None
    
    # monkeypatch.setattr("app.services.new_task_processor.NewTaskProcessor.process_task", mock_process_task)


# 性能监控
def pytest_runtest_call(item):
    """监控慢速测试"""
    import time
    start = time.time()
    outcome = yield
    duration = time.time() - start
    
    if duration > 1.0:
        print(f"\n⚠️  慢速测试: {item.name} ({duration:.2f}s)")
    
    return outcome