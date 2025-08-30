"""
数据库连接管理
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import Generator, AsyncGenerator

from app.core.config import get_settings


# 获取配置
settings = get_settings()

# 根据数据库类型配置引擎参数
def get_engine_config():
    """根据数据库类型获取引擎配置"""
    db_type = settings.database_type
    
    if db_type == 'postgresql':
        return {
            'pool_size': 10,
            'max_overflow': 20,
            'pool_recycle': 3600,
            'pool_pre_ping': True,
            'echo': False
        }
    elif db_type == 'mysql':
        return {
            'connect_args': {
                'charset': 'utf8mb4',
                'autocommit': False,
                'use_unicode': True,
                'init_command': "SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci"
            },
            'pool_size': 10,
            'max_overflow': 20,
            'pool_recycle': 3600,
            'pool_pre_ping': True,
            'echo': False
        }
    else:
        # SQLite配置（默认） - 优化并发处理
        from sqlalchemy.pool import QueuePool
        return {
            'connect_args': {
                "check_same_thread": False,
                "timeout": 30,  # 增加超时时间
                "isolation_level": None,  # 自动提交模式
            },
            'poolclass': QueuePool,
            'pool_size': 10,  # 连接池大小
            'max_overflow': 20,  # 最大溢出连接数
            'pool_timeout': 30,  # 获取连接超时时间
            'pool_recycle': 3600,  # 连接回收时间(1小时)
            'pool_pre_ping': True,  # 连接前测试
            'echo': False
        }

# 创建同步数据库引擎
engine_config = get_engine_config()
engine = create_engine(settings.database_url, **engine_config)

# 创建会话工厂
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine,
    expire_on_commit=False  # 避免会话过期问题
)

# 尝试创建异步数据库引擎（可选）
async_engine = None
AsyncSessionLocal = None

try:
    # 仅在有异步驱动时创建异步引擎
    async_database_url = settings.database_url
    if 'postgresql://' in settings.database_url:
        async_database_url = settings.database_url.replace('postgresql://', 'postgresql+asyncpg://')
    elif 'mysql://' in settings.database_url:
        async_database_url = settings.database_url.replace('pymysql://', 'aiomysql://')
    elif 'sqlite:///' in settings.database_url:
        async_database_url = settings.database_url.replace('sqlite:///', 'sqlite+aiosqlite:///')
    
    async_engine_config = engine_config.copy()
    # 移除异步引擎不支持的参数
    async_engine_config.pop('isolation_level', None)
    async_engine = create_async_engine(async_database_url, **async_engine_config)
    
    # 创建异步会话工厂
    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        autoflush=False,
        expire_on_commit=False
    )
    pass
except ImportError:
    pass
except Exception:
    pass

# 声明基类
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话
    用作FastAPI的依赖注入
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        try:
            db.rollback()
        except:
            pass
        raise e
    finally:
        try:
            db.close()
        except:
            pass




def get_independent_db_session() -> Session:
    """
    获取独立的数据库会话，用于批量操作和后台任务
    调用者负责关闭会话
    """
    return SessionLocal()


def close_independent_db_session(db: Session, operation: str = "关闭独立会话"):
    """
    关闭独立数据库会话
    """
    if db:
        try:
            db.close()
        except:
            pass




async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取异步数据库会话
    用作FastAPI的异步依赖注入
    """
    if AsyncSessionLocal is None:
        raise RuntimeError("异步数据库未初始化，请安装异步驱动: pip install aiomysql aiosqlite")
        
    async with AsyncSessionLocal() as db:
        try:
            yield db
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise e