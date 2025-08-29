"""
Alembic环境配置 - 支持用户指定配置文件
"""
import sys
import os
from pathlib import Path
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# 添加项目路径 - 确保能找到app模块
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# 如果在项目根目录运行，也添加backend目录
project_root = backend_dir.parent
if (project_root / 'backend').exists():
    sys.path.insert(0, str(project_root / 'backend'))

# 导入应用配置和模型
try:
    from app.core.config import get_settings, init_settings
    from app.core.database import Base

    # 导入所有模型（确保Alembic能检测到所有表）
    from app.models.user import User
    from app.models.ai_model import AIModel
    from app.models.file_info import FileInfo
    from app.models.task import Task
    from app.models.task_queue import TaskQueue, QueueConfig
    from app.models.task_share import TaskShare
    from app.models.issue import Issue
    from app.models.ai_output import AIOutput
    from app.models.task_log import TaskLog
except ImportError as e:
    print(f"❌ Alembic导入错误: {e}")
    print(f"📁 当前工作目录: {os.getcwd()}")
    print(f"🐍 Python路径: {sys.path[:3]}...")
    print(f"📂 Backend目录: {backend_dir}")
    print("💡 请确保从backend目录运行Alembic或设置PYTHONPATH=.")
    raise

# Alembic配置对象
config = context.config

# 支持用户指定配置文件
# 使用方式1: 环境变量 CONFIG_FILE=config.test.yaml alembic upgrade head
# 使用方式2: 命令行参数 alembic -x config_file=config.test.yaml upgrade head

custom_config_file = None

# 方式1: 从环境变量获取
custom_config_file = os.getenv('CONFIG_FILE')

# 方式2: 从命令行参数获取 (-x config_file=xxx)
if context.get_x_argument(as_dictionary=True).get('config_file'):
    custom_config_file = context.get_x_argument(as_dictionary=True)['config_file']

# 根据指定的配置文件初始化设置
if custom_config_file:
    print(f"🔧 使用自定义配置文件: {custom_config_file}")
    settings = init_settings(custom_config_file)
else:
    settings = get_settings()
    print("🔧 使用默认配置文件")

# 设置数据库URL
config.set_main_option("sqlalchemy.url", settings.database_url)

# 如果有日志配置文件，则使用它
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 设置目标元数据
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """离线模式运行迁移"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """在线模式运行迁移"""
    # 根据数据库类型获取引擎配置
    from app.core.database import get_engine_config
    engine_config = get_engine_config()
    
    # 使用应用的数据库配置
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = settings.database_url
    
    # NullPool不支持连接池参数，所以只设置基本配置
    # 迁移时使用简单的连接方式，避免连接池复杂性

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # 迁移时使用NullPool避免连接池问题
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            # 比较类型时忽略varchar长度差异
            compare_type=True,
            compare_server_default=True,
            # 渲染模式配置
            render_as_batch=True if settings.database_type == 'sqlite' else False
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()