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
    
    if db_type == 'mysql':
        # MySQL配置
        db_config = settings.database_config
        mysql_config = db_config.get('mysql', {})
        pool_config = mysql_config.get('pool', {})
        
        return {
            'connect_args': {
                'charset': mysql_config.get('charset', 'utf8mb4'),
                'autocommit': False,
                'connect_timeout': 30,
                'read_timeout': 30,
                'write_timeout': 30,
            },
            'pool_size': pool_config.get('pool_size', 10),
            'max_overflow': pool_config.get('max_overflow', 20),
            'pool_timeout': pool_config.get('pool_timeout', 60),
            'pool_recycle': pool_config.get('pool_recycle', 1800),  # 30分钟回收连接
            'pool_pre_ping': pool_config.get('pool_pre_ping', True),
            'echo': False,  # 可根据需要开启SQL日志
            'isolation_level': 'READ_COMMITTED'  # 设置隔离级别
        }
    else:
        # SQLite配置（默认）
        return {
            'connect_args': {
                "check_same_thread": False,
                "timeout": 30,
                "isolation_level": None
            },
            'pool_pre_ping': True,
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
    async_database_url = settings.database_url.replace('mysql://', 'mysql+aiomysql://') if 'mysql://' in settings.database_url else settings.database_url.replace('sqlite:///', 'sqlite+aiosqlite:///')
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
    print("✅ 异步数据库引擎初始化成功")
except ImportError as e:
    print(f"⚠️ 异步数据库驱动未安装，仅使用同步模式: {e}")
    print("💡 要启用异步模式，请安装: pip install aiomysql aiosqlite")
except Exception as e:
    print(f"⚠️ 异步数据库引擎初始化失败: {e}")
    print("💡 将使用同步数据库模式")

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
        # 发生异常时回滚事务
        try:
            db.rollback()
        except Exception:
            pass  # 忽略回滚异常
        raise e
    finally:
        # 安全关闭会话
        try:
            if db.is_active:
                db.close()
        except Exception:
            # 忽略关闭异常，避免状态冲突
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