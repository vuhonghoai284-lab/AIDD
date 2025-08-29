"""
FastAPI + Alembic集成管理器
支持用户指定配置文件的数据库迁移
"""
import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any
from alembic.config import Config
from alembic import command
from alembic.script import ScriptDirectory
from alembic.runtime.environment import EnvironmentContext
from app.core.config import init_settings, get_settings
import logging

logger = logging.getLogger(__name__)


class AlembicManager:
    """FastAPI + Alembic集成管理器"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
        self.alembic_cfg = self._create_alembic_config(config_file)
        
    def _create_alembic_config(self, config_file: Optional[str] = None) -> Config:
        """创建Alembic配置"""
        # Alembic配置文件路径
        alembic_ini_path = Path(__file__).parent.parent.parent / "alembic.ini"
        
        # 创建Alembic配置对象
        alembic_cfg = Config(str(alembic_ini_path))
        
        # 如果指定了自定义配置文件，设置环境变量
        if config_file:
            os.environ['CONFIG_FILE'] = config_file
            settings = init_settings(config_file)
            logger.info(f"使用自定义配置文件: {config_file}")
        else:
            settings = get_settings()
            logger.info("使用默认配置文件")
        
        # 设置数据库URL
        alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
        
        return alembic_cfg
    
    def generate_migration(self, message: str, autogenerate: bool = True) -> str:
        """生成迁移脚本"""
        try:
            if autogenerate:
                # 自动生成迁移（推荐）
                command.revision(
                    self.alembic_cfg, 
                    message=message, 
                    autogenerate=True
                )
                logger.info(f"自动生成迁移: {message}")
            else:
                # 手动创建空迁移
                command.revision(
                    self.alembic_cfg, 
                    message=message
                )
                logger.info(f"创建空迁移: {message}")
            
            # 获取最新生成的迁移文件ID
            script_dir = ScriptDirectory.from_config(self.alembic_cfg)
            head_revision = script_dir.get_current_head()
            return head_revision
            
        except Exception as e:
            logger.error(f"生成迁移失败: {e}")
            raise
    
    def upgrade(self, revision: str = "head") -> None:
        """执行迁移升级"""
        try:
            command.upgrade(self.alembic_cfg, revision)
            logger.info(f"迁移升级成功: {revision}")
        except Exception as e:
            logger.error(f"迁移升级失败: {e}")
            raise
    
    def downgrade(self, revision: str) -> None:
        """执行迁移回滚"""
        try:
            command.downgrade(self.alembic_cfg, revision)
            logger.info(f"迁移回滚成功: {revision}")
        except Exception as e:
            logger.error(f"迁移回滚失败: {e}")
            raise
    
    def get_current_revision(self) -> str:
        """获取当前数据库版本"""
        try:
            script_dir = ScriptDirectory.from_config(self.alembic_cfg)
            
            def get_rev(rev, context):
                return script_dir.get_revision(rev)
            
            # 这里需要实际连接数据库获取当前版本
            # 简化版本，实际项目中需要更复杂的实现
            with EnvironmentContext(
                self.alembic_cfg,
                script_dir,
                fn=get_rev,
            ):
                script_dir.get_current_head()
                
        except Exception as e:
            logger.warning(f"获取当前版本失败: {e}")
            return "unknown"
    
    def get_migration_history(self) -> List[Dict[str, Any]]:
        """获取迁移历史"""
        try:
            script_dir = ScriptDirectory.from_config(self.alembic_cfg)
            revisions = []
            
            for script in script_dir.walk_revisions():
                revisions.append({
                    'revision': script.revision,
                    'down_revision': script.down_revision,
                    'message': script.doc,
                    'create_date': getattr(script, 'create_date', None)
                })
            
            return revisions
        except Exception as e:
            logger.error(f"获取迁移历史失败: {e}")
            return []
    
    def check_pending_migrations(self) -> bool:
        """检查是否有待执行的迁移"""
        try:
            # 这里需要实际的实现来比较数据库版本和脚本版本
            # 简化版本，实际项目中使用 alembic current 和 alembic heads 比较
            return True
        except Exception as e:
            logger.error(f"检查待执行迁移失败: {e}")
            return False


# FastAPI集成函数
async def run_migrations_on_startup(config_file: Optional[str] = None):
    """FastAPI启动时自动执行迁移（增强错误处理）"""
    try:
        manager = AlembicManager(config_file)
        
        # 首先测试数据库连接
        try:
            from sqlalchemy import create_engine
            settings = init_settings(config_file) if config_file else get_settings()
            engine = create_engine(settings.database_url)
            # 测试连接
            with engine.connect() as conn:
                pass
            print("✓ 数据库连接测试成功")
        except Exception as conn_error:
            print(f"❌ 数据库连接失败: {conn_error}")
            print("💡 请检查生产环境数据库配置和网络连接")
            raise conn_error
        
        # 执行迁移
        manager.upgrade("head")
        logger.info("✅ 数据库迁移完成")
        
    except Exception as e:
        logger.error(f"❌ 数据库迁移失败: {e}")
        print(f"🔧 迁移详细错误: {str(e)}")
        raise


# 命令行工具函数
def cli_generate_migration(message: str, config_file: Optional[str] = None):
    """命令行生成迁移"""
    manager = AlembicManager(config_file)
    revision = manager.generate_migration(message)
    print(f"✅ 迁移生成成功: {revision}")

def cli_upgrade(revision: str = "head", config_file: Optional[str] = None):
    """命令行升级迁移"""
    manager = AlembicManager(config_file)
    manager.upgrade(revision)
    print(f"✅ 迁移升级成功: {revision}")

def cli_downgrade(revision: str, config_file: Optional[str] = None):
    """命令行回滚迁移"""
    manager = AlembicManager(config_file)
    manager.downgrade(revision)
    print(f"✅ 迁移回滚成功: {revision}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Alembic迁移管理")
    parser.add_argument('--config-file', help='指定配置文件路径')
    parser.add_argument('command', choices=['generate', 'upgrade', 'downgrade', 'current', 'history'])
    parser.add_argument('--message', '-m', help='迁移描述（用于generate命令）')
    parser.add_argument('--revision', '-r', default='head', help='版本号（用于upgrade/downgrade命令）')
    
    args = parser.parse_args()
    
    try:
        if args.command == 'generate':
            if not args.message:
                print("❌ 生成迁移需要提供描述信息 (--message)")
                sys.exit(1)
            cli_generate_migration(args.message, args.config_file)
        
        elif args.command == 'upgrade':
            cli_upgrade(args.revision, args.config_file)
        
        elif args.command == 'downgrade':
            if args.revision == 'head':
                print("❌ 回滚需要指定具体版本号 (--revision)")
                sys.exit(1)
            cli_downgrade(args.revision, args.config_file)
        
        elif args.command == 'current':
            manager = AlembicManager(args.config_file)
            current = manager.get_current_revision()
            print(f"当前数据库版本: {current}")
        
        elif args.command == 'history':
            manager = AlembicManager(args.config_file)
            history = manager.get_migration_history()
            print("迁移历史:")
            for item in history:
                print(f"  {item['revision']}: {item['message']}")
                
    except Exception as e:
        logger.error(f"命令执行失败: {e}")
        sys.exit(1)