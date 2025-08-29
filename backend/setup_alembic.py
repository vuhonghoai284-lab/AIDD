#!/usr/bin/env python3
"""
Alembic迁移系统设置脚本
替代自写的迁移管理器
"""
import os
import sys
from pathlib import Path
import subprocess

def setup_alembic():
    """设置Alembic迁移环境"""
    print("🔄 开始设置Alembic迁移系统...")
    
    # 1. 安装Alembic（如果未安装）
    try:
        import alembic
        print("✅ Alembic已安装")
    except ImportError:
        print("📦 安装Alembic...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "alembic==1.13.1"])
        print("✅ Alembic安装完成")
    
    # 2. 初始化Alembic环境
    if not Path("alembic").exists():
        print("🏗️ 初始化Alembic环境...")
        subprocess.run([sys.executable, "-m", "alembic", "init", "alembic"])
        print("✅ Alembic环境初始化完成")
    else:
        print("✅ Alembic环境已存在")
    
    # 3. 配置alembic.ini
    configure_alembic_ini()
    
    # 4. 配置env.py
    configure_env_py()
    
    print("✅ Alembic设置完成！")
    print("\n📖 使用说明：")
    print("  生成迁移: python -m alembic revision --autogenerate -m '描述'")
    print("  执行迁移: python -m alembic upgrade head")
    print("  查看状态: python -m alembic current")
    print("  查看历史: python -m alembic history")

def configure_alembic_ini():
    """配置alembic.ini文件"""
    alembic_ini_content = """[alembic]
# 脚本位置
script_location = alembic

# 数据库URL - 将从应用配置中动态获取
# sqlalchemy.url = 

# 解释器输出编码
output_encoding = utf-8

# 日志配置
[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
"""
    
    with open("alembic.ini", "w", encoding='utf-8') as f:
        f.write(alembic_ini_content)
    print("📝 alembic.ini配置完成")

def configure_env_py():
    """配置env.py文件"""
    env_py_content = '''"""
Alembic环境配置 - 支持用户指定配置文件
"""
import sys
from pathlib import Path
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent))

# 导入应用配置和模型
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

# Alembic配置对象
config = context.config

# 从命令行参数获取自定义配置文件
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--config-file', help='指定配置文件路径')
args, unknown = parser.parse_known_args()

# 根据指定的配置文件初始化设置
if args.config_file:
    print(f"🔧 使用自定义配置文件: {args.config_file}")
    settings = init_settings(args.config_file)
else:
    settings = get_settings()

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
    
    # 合并引擎配置
    for key, value in engine_config.items():
        if key == 'connect_args':
            # 处理connect_args特殊配置
            for connect_key, connect_value in value.items():
                configuration[f"sqlalchemy.connect_args.{connect_key}"] = connect_value
        else:
            configuration[f"sqlalchemy.{key}"] = value

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''
    
    alembic_dir = Path("alembic")
    alembic_dir.mkdir(exist_ok=True)
    
    with open(alembic_dir / "env.py", "w", encoding='utf-8') as f:
        f.write(env_py_content)
    print("📝 env.py配置完成")

if __name__ == "__main__":
    setup_alembic()