"""
数据库连接管理
"""
import time
import uuid
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import Generator, AsyncGenerator

from app.core.config import get_settings
from app.core.db_monitor import get_monitor

# 获取配置
settings = get_settings()

# 根据数据库类型配置引擎参数
def get_engine_config():
    """根据数据库类型获取引擎配置"""
    db_type = settings.database_type
    
    if db_type == 'mysql':
        # MySQL配置 - 生产环境优化
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
            'pool_size': pool_config.get('pool_size', 25),
            'max_overflow': pool_config.get('max_overflow', 30),
            'pool_timeout': pool_config.get('pool_timeout', 30),
            'pool_recycle': pool_config.get('pool_recycle', 1800),  # 30分钟回收连接
            'pool_pre_ping': pool_config.get('pool_pre_ping', True),
            'pool_reset_on_return': pool_config.get('pool_reset_on_return', 'rollback'),
            'echo': False,  # 可根据需要开启SQL日志
            'isolation_level': 'READ_COMMITTED'  # 设置隔离级别
        }
    else:
        # SQLite配置（默认） - 优化大量任务并发处理
        return {
            'connect_args': {
                "check_same_thread": False,
                "timeout": 10,  # 减少锁等待时间
                "isolation_level": None
            },
            'pool_pre_ping': True,
            'echo': False,
            # SQLite也配置连接池来管理会话资源
            'pool_size': 20,
            'max_overflow': 25,
            'pool_timeout': 5,
            'pool_recycle': 1800
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
    async_database_url = settings.database_url.replace('pymysql://', 'aiomysql://') if 'mysql://' in settings.database_url else settings.database_url.replace('sqlite:///', 'sqlite+aiosqlite:///')
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
    获取数据库会话（优化版，支持批量操作和锁竞争处理）
    用作FastAPI的依赖注入
    """
    session_id = f"fastapi_{uuid.uuid4().hex[:8]}"
    monitor = get_monitor()
    monitor.log_session_create(session_id, "FastAPI请求")
    
    session_start = time.time()
    connection_info = _log_connection_pool_status("获取FastAPI会话")
    
    db = SessionLocal()
    try:
        # 添加连接健康检查，确保会话可用
        try:
            db.execute("SELECT 1")
        except Exception as conn_error:
            print(f"⚠️ 数据库连接异常，重新创建会话: {conn_error}")
            monitor.log_session_error(session_id, f"连接异常: {conn_error}")
            db.close()
            db = SessionLocal()
        
        # 为SQLite设置WAL模式和优化参数，减少锁竞争
        if 'sqlite' in str(engine.url):
            try:
                from sqlalchemy import text
                # 启用WAL模式，提高并发性能
                db.execute(text("PRAGMA journal_mode=WAL"))
                # 设置合适的同步模式
                db.execute(text("PRAGMA synchronous=NORMAL"))
                # 增加缓存大小
                db.execute(text("PRAGMA cache_size=-2000"))  # 2MB缓存
                # 设置锁超时
                db.execute(text("PRAGMA busy_timeout=10000"))  # 10秒超时
                db.commit()
            except Exception as pragma_error:
                print(f"⚠️ SQLite PRAGMA设置失败: {pragma_error}")
                monitor.log_session_error(session_id, f"PRAGMA设置失败: {pragma_error}")
        
        yield db
    except Exception as e:
        # 发生异常时回滚事务
        try:
            db.rollback()
        except Exception:
            pass  # 忽略回滚异常
        monitor.log_session_error(session_id, str(e))
        raise e
    finally:
        # 记录会话使用时间
        session_time = (time.time() - session_start) * 1000
        if session_time > 5000:  # 超过5秒记录警告
            print(f"⚠️ FastAPI数据库会话使用时间过长: {session_time:.1f}ms")
        elif session_time > 1000:  # 超过1秒记录信息
            print(f"ℹ️ FastAPI数据库会话使用时间: {session_time:.1f}ms")
        
        # 安全关闭会话
        try:
            if db.is_active:
                db.close()
        except Exception:
            # 忽略关闭异常，避免状态冲突
            pass
        
        monitor.log_session_close(session_id, "FastAPI请求")
        _log_connection_pool_status("释放FastAPI会话", connection_info)


def _log_connection_pool_status(operation: str, previous_info: dict = None) -> dict:
    """记录数据库连接池状态"""
    try:
        pool = engine.pool
        current_info = {
            'checked_in': pool.checkedin(),
            'checked_out': pool.checkedout(), 
            'overflow': pool.overflow(),
            'size': pool.size(),
            'timestamp': time.time()
        }
        
        # 计算变化量
        if previous_info:
            delta_out = current_info['checked_out'] - previous_info['checked_out']
            delta_in = current_info['checked_in'] - previous_info['checked_in']
            time_diff = (current_info['timestamp'] - previous_info['timestamp']) * 1000
            
            if delta_out != 0 or delta_in != 0 or current_info['overflow'] > 0:
                print(f"🔗 [{operation}] 连接池变化 - "
                      f"活跃:{current_info['checked_out']}({delta_out:+d}) "
                      f"空闲:{current_info['checked_in']}({delta_in:+d}) "
                      f"溢出:{current_info['overflow']} "
                      f"耗时:{time_diff:.1f}ms")
        else:
            print(f"🔗 [{operation}] 连接池状态 - "
                  f"活跃:{current_info['checked_out']} "
                  f"空闲:{current_info['checked_in']} "
                  f"总数:{current_info['size']} "
                  f"溢出:{current_info['overflow']}")
        
        # 警告检查
        if current_info['checked_out'] > 15:
            print(f"⚠️ 数据库连接使用过多: {current_info['checked_out']} 个活跃连接")
        if current_info['overflow'] > 10:
            print(f"⚠️ 连接池溢出过多: {current_info['overflow']} 个溢出连接")
        if current_info['checked_out'] + current_info['checked_in'] > current_info['size'] + 20:
            print(f"🚨 连接池资源异常: 总使用数超出预期")
            
        return current_info
    except Exception as e:
        print(f"❌ 连接池状态监控失败: {e}")
        return {}


def get_independent_db_session() -> Session:
    """
    获取独立的数据库会话，用于批量操作和后台任务
    调用者负责关闭会话
    """
    session_id = f"independent_{uuid.uuid4().hex[:8]}"
    monitor = get_monitor()
    monitor.log_session_create(session_id, "独立会话")
    
    session_start = time.time() 
    connection_info = _log_connection_pool_status("获取独立会话")
    
    db = SessionLocal()
    
    # 为SQLite设置优化参数
    if 'sqlite' in str(engine.url):
        try:
            from sqlalchemy import text
            db.execute(text("PRAGMA journal_mode=WAL"))
            db.execute(text("PRAGMA synchronous=NORMAL")) 
            db.execute(text("PRAGMA cache_size=-2000"))
            db.execute(text("PRAGMA busy_timeout=10000"))
            db.commit()
        except Exception as e:
            print(f"⚠️ SQLite会话优化失败: {e}")
            monitor.log_session_error(session_id, f"SQLite优化失败: {e}")
    
    session_time = (time.time() - session_start) * 1000
    if session_time > 1000:
        print(f"⚠️ 独立会话创建耗时: {session_time:.1f}ms")
    
    # 在会话对象上附加监控ID，供关闭时使用
    db._monitor_session_id = session_id
    
    return db


def close_independent_db_session(db: Session, operation: str = "关闭独立会话"):
    """
    安全关闭独立数据库会话，并记录资源使用
    """
    if db:
        session_id = getattr(db, '_monitor_session_id', f"unknown_{uuid.uuid4().hex[:8]}")
        monitor = get_monitor()
        
        try:
            start = time.time()
            db.close()
            close_time = (time.time() - start) * 1000
            
            if close_time > 500:
                print(f"⚠️ 数据库会话关闭耗时: {close_time:.1f}ms")
            
            monitor.log_session_close(session_id, operation)
            _log_connection_pool_status(operation)
            
        except Exception as e:
            print(f"❌ 关闭数据库会话失败: {e}")
            monitor.log_session_error(session_id, f"关闭失败: {e}")


def get_db_monitor_status() -> dict:
    """获取数据库监控状态"""
    return get_monitor().get_current_status()


def print_db_monitor_status(prefix: str = ""):
    """打印数据库监控状态"""
    get_monitor().print_status(prefix)


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