"""
数据库连接管理
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

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
            },
            'pool_size': pool_config.get('pool_size', 5),
            'max_overflow': pool_config.get('max_overflow', 10),
            'pool_timeout': pool_config.get('pool_timeout', 30),
            'pool_recycle': pool_config.get('pool_recycle', 3600),
            'pool_pre_ping': pool_config.get('pool_pre_ping', True),
            'echo': False  # 可根据需要开启SQL日志
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

# 创建数据库引擎
engine_config = get_engine_config()
engine = create_engine(settings.database_url, **engine_config)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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
    finally:
        db.close()