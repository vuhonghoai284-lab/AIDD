#!/usr/bin/env python3
"""
数据库迁移管理器
负责管理数据库结构版本和迁移执行
"""

import os
import sys
import hashlib
import json
import shutil
import importlib.util
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from sqlalchemy import create_engine, text, MetaData, inspect, Table
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import logging

# 添加父目录到路径，以便导入app模块
sys.path.append(str(Path(__file__).parent.parent))

try:
    from app.core.config import get_settings
    from app.core.database import Base, get_engine_config
except ImportError:
    # 如果无法导入app模块，使用基础配置
    print("警告: 无法导入app模块，使用基础配置")
    Base = None

logger = logging.getLogger(__name__)


@dataclass
class MigrationRecord:
    """迁移记录数据类"""
    id: str
    name: str
    description: str
    created_at: datetime
    executed_at: Optional[datetime] = None
    checksum: Optional[str] = None
    backup_path: Optional[str] = None
    rollback_sql: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'checksum': self.checksum,
            'backup_path': self.backup_path,
            'rollback_sql': self.rollback_sql
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MigrationRecord':
        return cls(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            created_at=datetime.fromisoformat(data['created_at']),
            executed_at=datetime.fromisoformat(data['executed_at']) if data.get('executed_at') else None,
            checksum=data.get('checksum'),
            backup_path=data.get('backup_path'),
            rollback_sql=data.get('rollback_sql')
        )


class MigrationManager:
    """数据库迁移管理器"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.settings = None
        self.engine = None
        self.session = None
        self.config_file = config_file
        
        # 初始化配置
        try:
            if config_file:
                # 验证配置文件是否存在
                config_path = Path(config_file)
                if not config_path.exists():
                    raise FileNotFoundError(f"指定的配置文件不存在: {config_file}")
                
                # 设置环境变量以便app.core.config使用正确的配置文件
                os.environ['CONFIG_FILE'] = config_file
                logger.info(f"使用自定义配置文件: {config_file}")
                
                # 重新导入配置模块以确保使用新的CONFIG_FILE
                from app.core.config import init_settings
                self.settings = init_settings(config_file)
            else:
                from app.core.config import get_settings
                self.settings = get_settings()
                logger.info("使用默认配置文件")
                
        except ImportError:
            logger.warning("无法加载应用配置，使用默认设置")
            self.settings = self._create_default_settings()
        except FileNotFoundError as e:
            logger.error(str(e))
            raise
        
        # 迁移目录配置
        self.migrations_dir = Path(__file__).parent
        self.versions_dir = self.migrations_dir / "versions"
        self.backups_dir = self.migrations_dir / "backups"
        self.schema_snapshots_dir = self.migrations_dir / "schema_snapshots"
        
        # 确保目录存在
        for dir_path in [self.migrations_dir, self.versions_dir, self.backups_dir, self.schema_snapshots_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # 迁移记录文件
        self.migration_history_file = self.migrations_dir / "migration_history.json"
        
        # 初始化日志
        self._setup_logging()
        
        # 连接数据库
        self._connect_database()
        
        # 初始化迁移表
        self._init_migration_table()
    
    def _create_default_settings(self):
        """创建默认设置对象"""
        class DefaultSettings:
            database_url = "sqlite:///./data/app.db"
            database_type = "sqlite"
            database_config = {}
        
        return DefaultSettings()
    
    def _setup_logging(self):
        """设置日志"""
        log_file = self.migrations_dir / "migration.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    
    def _connect_database(self):
        """连接数据库"""
        try:
            # 获取引擎配置
            if hasattr(self.settings, 'database_url'):
                database_url = self.settings.database_url
                if hasattr(get_engine_config, '__call__'):
                    engine_config = get_engine_config()
                else:
                    engine_config = {"connect_args": {"check_same_thread": False}}
            else:
                database_url = "sqlite:///./data/app.db"
                engine_config = {"connect_args": {"check_same_thread": False}}
            
            self.engine = create_engine(database_url, **engine_config)
            self.session = sessionmaker(bind=self.engine)()
            
            # 测试连接
            self.session.execute(text("SELECT 1"))
            logger.info(f"数据库连接成功: {self._mask_database_url(database_url)}")
            
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    def _mask_database_url(self, url: str) -> str:
        """隐藏数据库URL中的敏感信息"""
        if '://' in url and '@' in url:
            protocol, rest = url.split('://', 1)
            if '@' in rest:
                auth, host_db = rest.split('@', 1)
                if ':' in auth:
                    user, password = auth.split(':', 1)
                    return f"{protocol}://{user}:***@{host_db}"
        return url
    
    def _init_migration_table(self):
        """初始化迁移记录表"""
        try:
            # 检查是否已存在迁移记录表
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            
            if 'schema_migrations' not in tables:
                logger.info("创建数据库迁移记录表")
                create_table_sql = """
                CREATE TABLE schema_migrations (
                    id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    checksum VARCHAR(64),
                    executed_at DATETIME,
                    backup_path VARCHAR(500),
                    rollback_sql TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
                
                # 根据数据库类型调整SQL
                if hasattr(self.settings, 'database_type') and self.settings.database_type == 'sqlite':
                    create_table_sql = create_table_sql.replace('TIMESTAMP', 'DATETIME')
                
                self.session.execute(text(create_table_sql))
                self.session.commit()
                logger.info("数据库迁移记录表创建成功")
            
        except Exception as e:
            logger.error(f"初始化迁移表失败: {e}")
            raise
    
    def generate_migration_id(self, description: str) -> str:
        """生成迁移ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 清理描述文本，只保留字母数字和下划线
        clean_desc = "".join(c if c.isalnum() or c == '_' else '_' for c in description.lower())
        clean_desc = clean_desc.strip('_')[:50]  # 限制长度
        return f"{timestamp}_{clean_desc}"
    
    def create_migration(self, description: str, sql_up: str, sql_down: str = "") -> str:
        """创建新的迁移文件"""
        migration_id = self.generate_migration_id(description)
        migration_file = self.versions_dir / f"{migration_id}.py"
        
        # 计算SQL的校验和
        checksum = hashlib.sha256((sql_up + sql_down).encode()).hexdigest()
        
        # 创建迁移文件内容
        migration_content = f'''"""
{description}

Migration ID: {migration_id}
Created: {datetime.now().isoformat()}
Checksum: {checksum}
"""

from datetime import datetime
from sqlalchemy import text

# 迁移信息
MIGRATION_ID = "{migration_id}"
DESCRIPTION = "{description}"
CREATED_AT = datetime.fromisoformat("{datetime.now().isoformat()}")
CHECKSUM = "{checksum}"

# 升级SQL
SQL_UP = """
{sql_up.strip()}
"""

# 降级SQL（回滚）
SQL_DOWN = """
{sql_down.strip()}
"""

def upgrade(session):
    """执行升级操作"""
    if SQL_UP.strip():
        for sql_statement in SQL_UP.strip().split(';'):
            sql_statement = sql_statement.strip()
            if sql_statement:
                session.execute(text(sql_statement))
    session.commit()

def downgrade(session):
    """执行降级操作"""
    if SQL_DOWN.strip():
        for sql_statement in SQL_DOWN.strip().split(';'):
            sql_statement = sql_statement.strip()
            if sql_statement:
                session.execute(text(sql_statement))
    session.commit()
'''
        
        # 写入迁移文件
        with open(migration_file, 'w', encoding='utf-8') as f:
            f.write(migration_content)
        
        logger.info(f"创建迁移文件: {migration_file}")
        return migration_id
    
    def detect_schema_changes(self) -> Dict[str, Any]:
        """检测数据库结构变更"""
        if not Base:
            logger.warning("无法导入SQLAlchemy模型，跳过自动检测")
            return {}
        
        try:
            # 获取当前数据库结构
            current_metadata = MetaData()
            current_metadata.reflect(bind=self.engine)
            
            # 获取应用模型定义的结构
            model_metadata = Base.metadata
            
            changes = {
                'new_tables': [],
                'dropped_tables': [],
                'modified_tables': [],
                'new_columns': [],
                'dropped_columns': [],
                'modified_columns': []
            }
            
            # 检查新增的表
            current_tables = set(current_metadata.tables.keys())
            model_tables = set(model_metadata.tables.keys())
            
            changes['new_tables'] = list(model_tables - current_tables)
            changes['dropped_tables'] = list(current_tables - model_tables)
            
            # 检查表结构变更
            for table_name in model_tables & current_tables:
                model_table = model_metadata.tables[table_name]
                current_table = current_metadata.tables[table_name]
                
                # 比较列
                model_columns = {col.name: col for col in model_table.columns}
                current_columns = {col.name: col for col in current_table.columns}
                
                new_cols = set(model_columns.keys()) - set(current_columns.keys())
                dropped_cols = set(current_columns.keys()) - set(model_columns.keys())
                
                if new_cols:
                    changes['new_columns'].extend([(table_name, col) for col in new_cols])
                if dropped_cols:
                    changes['dropped_columns'].extend([(table_name, col) for col in dropped_cols])
                
                # 检查列类型变更
                for col_name in set(model_columns.keys()) & set(current_columns.keys()):
                    model_col = model_columns[col_name]
                    current_col = current_columns[col_name]
                    
                    if str(model_col.type) != str(current_col.type):
                        changes['modified_columns'].append((table_name, col_name, str(current_col.type), str(model_col.type)))
            
            return changes
            
        except Exception as e:
            logger.error(f"检测结构变更失败: {e}")
            return {}
    
    def auto_generate_migration(self, description: str = None) -> Optional[str]:
        """自动生成迁移脚本"""
        changes = self.detect_schema_changes()
        
        if not any(changes.values()):
            logger.info("未检测到数据库结构变更")
            return None
        
        # 生成描述
        if not description:
            parts = []
            if changes['new_tables']:
                parts.append(f"新增表: {', '.join(changes['new_tables'])}")
            if changes['dropped_tables']:
                parts.append(f"删除表: {', '.join(changes['dropped_tables'])}")
            if changes['new_columns']:
                table_cols = {}
                for table_name, col_name in changes['new_columns']:
                    table_cols.setdefault(table_name, []).append(col_name)
                for table, cols in table_cols.items():
                    parts.append(f"{table}表新增列: {', '.join(cols)}")
            
            description = "; ".join(parts)
        
        # 生成SQL
        sql_up = self._generate_upgrade_sql(changes)
        sql_down = self._generate_downgrade_sql(changes)
        
        return self.create_migration(description, sql_up, sql_down)
    
    def _generate_upgrade_sql(self, changes: Dict[str, Any]) -> str:
        """生成升级SQL"""
        sql_statements = []
        
        # 新增表
        if changes['new_tables'] and Base:
            for table_name in changes['new_tables']:
                if table_name in Base.metadata.tables:
                    table = Base.metadata.tables[table_name]
                    sql_statements.append(self._generate_create_table_sql(table))
        
        # 新增列
        for table_name, col_name in changes['new_columns']:
            if Base and table_name in Base.metadata.tables:
                table = Base.metadata.tables[table_name]
                column = table.columns[col_name]
                sql_statements.append(f"ALTER TABLE {table_name} ADD COLUMN {self._generate_column_sql(column)}")
        
        return ";\n".join(sql_statements)
    
    def _generate_downgrade_sql(self, changes: Dict[str, Any]) -> str:
        """生成降级SQL"""
        sql_statements = []
        
        # 删除新增的表
        for table_name in changes['new_tables']:
            sql_statements.append(f"DROP TABLE IF EXISTS {table_name}")
        
        # 删除新增的列（注意：SQLite不支持删除列）
        db_type = getattr(self.settings, 'database_type', 'sqlite')
        if db_type == 'mysql':
            for table_name, col_name in changes['new_columns']:
                sql_statements.append(f"ALTER TABLE {table_name} DROP COLUMN {col_name}")
        else:
            if changes['new_columns']:
                sql_statements.append("-- SQLite不支持删除列，需要手动处理")
        
        return ";\n".join(sql_statements)
    
    def _generate_create_table_sql(self, table: Table) -> str:
        """生成创建表的SQL"""
        db_type = getattr(self.settings, 'database_type', 'sqlite')
        
        columns = []
        primary_keys = []
        
        for column in table.columns:
            col_sql = self._generate_column_sql(column)
            columns.append(col_sql)
            if column.primary_key:
                primary_keys.append(column.name)
        
        sql = f"CREATE TABLE {table.name} (\n    {',\n    '.join(columns)}"
        
        if primary_keys:
            sql += f",\n    PRIMARY KEY ({', '.join(primary_keys)})"
        
        sql += "\n)"
        
        return sql
    
    def _generate_column_sql(self, column) -> str:
        """生成列定义SQL"""
        db_type = getattr(self.settings, 'database_type', 'sqlite')
        
        col_sql = f"{column.name} {column.type}"
        
        if not column.nullable:
            col_sql += " NOT NULL"
        
        if column.default is not None:
            if hasattr(column.default, 'arg'):
                if callable(column.default.arg):
                    if db_type == 'mysql':
                        col_sql += " DEFAULT CURRENT_TIMESTAMP"
                    else:
                        col_sql += " DEFAULT CURRENT_TIMESTAMP"
                else:
                    if isinstance(column.default.arg, str):
                        col_sql += f" DEFAULT '{column.default.arg}'"
                    else:
                        col_sql += f" DEFAULT {column.default.arg}"
        
        if column.autoincrement and db_type == 'mysql':
            col_sql += " AUTO_INCREMENT"
        
        return col_sql
    
    def create_backup(self, backup_name: str = None) -> str:
        """创建数据库备份"""
        if not backup_name:
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        db_type = getattr(self.settings, 'database_type', 'sqlite')
        
        if db_type == 'sqlite':
            return self._create_sqlite_backup(backup_name)
        elif db_type == 'mysql':
            return self._create_mysql_backup(backup_name)
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")
    
    def _create_sqlite_backup(self, backup_name: str) -> str:
        """创建SQLite备份"""
        import sqlite3
        
        # 解析数据库路径
        db_url = getattr(self.settings, 'database_url', 'sqlite:///./data/app.db')
        db_path = db_url.replace('sqlite:///', '')
        
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"数据库文件不存在: {db_path}")
        
        backup_file = self.backups_dir / f"{backup_name}.db"
        
        # 使用sqlite3模块进行备份
        source = sqlite3.connect(db_path)
        backup = sqlite3.connect(str(backup_file))
        
        source.backup(backup)
        
        source.close()
        backup.close()
        
        logger.info(f"SQLite备份创建成功: {backup_file}")
        return str(backup_file)
    
    def _create_mysql_backup(self, backup_name: str) -> str:
        """创建MySQL备份"""
        import subprocess
        
        # 解析MySQL连接信息
        db_config = getattr(self.settings, 'database_config', {})
        mysql_config = db_config.get('mysql', {})
        
        host = mysql_config.get('host', 'localhost')
        port = mysql_config.get('port', 3306)
        username = mysql_config.get('username', 'root')
        password = mysql_config.get('password', '')
        database = mysql_config.get('database', 'ai_doc_test')
        
        backup_file = self.backups_dir / f"{backup_name}.sql"
        
        # 构建mysqldump命令
        cmd = [
            'mysqldump',
            f'--host={host}',
            f'--port={port}',
            f'--user={username}',
            f'--password={password}',
            '--single-transaction',
            '--routines',
            '--triggers',
            database
        ]
        
        try:
            with open(backup_file, 'w') as f:
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
            
            if result.returncode != 0:
                raise Exception(f"mysqldump执行失败: {result.stderr}")
            
            logger.info(f"MySQL备份创建成功: {backup_file}")
            return str(backup_file)
            
        except FileNotFoundError:
            raise Exception("mysqldump命令未找到，请确保MySQL客户端已安装")
    
    def restore_backup(self, backup_path: str):
        """恢复数据库备份"""
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"备份文件不存在: {backup_path}")
        
        db_type = getattr(self.settings, 'database_type', 'sqlite')
        
        if backup_path.endswith('.db') and db_type == 'sqlite':
            self._restore_sqlite_backup(backup_path)
        elif backup_path.endswith('.sql') and db_type == 'mysql':
            self._restore_mysql_backup(backup_path)
        else:
            raise ValueError("备份文件格式与数据库类型不匹配")
    
    def _restore_sqlite_backup(self, backup_path: str):
        """恢复SQLite备份"""
        db_url = getattr(self.settings, 'database_url', 'sqlite:///./data/app.db')
        db_path = db_url.replace('sqlite:///', '')
        
        # 关闭当前连接
        if self.session:
            self.session.close()
        if self.engine:
            self.engine.dispose()
        
        # 备份当前数据库
        if os.path.exists(db_path):
            backup_current = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(db_path, backup_current)
            logger.info(f"当前数据库已备份到: {backup_current}")
        
        # 恢复备份
        shutil.copy2(backup_path, db_path)
        logger.info(f"数据库恢复成功: {db_path}")
        
        # 重新连接
        self._connect_database()
    
    def _restore_mysql_backup(self, backup_path: str):
        """恢复MySQL备份"""
        import subprocess
        
        db_config = getattr(self.settings, 'database_config', {})
        mysql_config = db_config.get('mysql', {})
        
        host = mysql_config.get('host', 'localhost')
        port = mysql_config.get('port', 3306)
        username = mysql_config.get('username', 'root')
        password = mysql_config.get('password', '')
        database = mysql_config.get('database', 'ai_doc_test')
        
        cmd = [
            'mysql',
            f'--host={host}',
            f'--port={port}',
            f'--user={username}',
            f'--password={password}',
            database
        ]
        
        try:
            with open(backup_path, 'r') as f:
                result = subprocess.run(cmd, stdin=f, stderr=subprocess.PIPE, text=True)
            
            if result.returncode != 0:
                raise Exception(f"mysql恢复失败: {result.stderr}")
            
            logger.info(f"MySQL数据库恢复成功")
            
        except FileNotFoundError:
            raise Exception("mysql命令未找到，请确保MySQL客户端已安装")
    
    def get_pending_migrations(self) -> List[str]:
        """获取待执行的迁移"""
        # 获取所有迁移文件
        migration_files = []
        for file_path in self.versions_dir.glob("*.py"):
            if file_path.name != "__init__.py":
                migration_files.append(file_path.stem)
        
        migration_files.sort()
        
        # 获取已执行的迁移
        executed_migrations = set()
        try:
            result = self.session.execute(text("SELECT id FROM schema_migrations"))
            executed_migrations = {row[0] for row in result}
        except Exception:
            # 如果表不存在，则所有迁移都待执行
            pass
        
        # 返回待执行的迁移
        return [mid for mid in migration_files if mid not in executed_migrations]
    
    def get_migration_history(self) -> List[MigrationRecord]:
        """获取迁移历史"""
        try:
            result = self.session.execute(text("""
                SELECT id, name, description, checksum, executed_at, backup_path, rollback_sql, created_at
                FROM schema_migrations
                ORDER BY executed_at DESC
            """))
            
            records = []
            for row in result:
                # 处理日期时间字段
                executed_at = None
                if row[4]:
                    if isinstance(row[4], str):
                        # Handle common invalid datetime strings
                        if row[4] in ('CURRENT_DATETIME', 'CURRENT_TIMESTAMP'):
                            executed_at = datetime.now()
                        else:
                            try:
                                executed_at = datetime.fromisoformat(row[4])
                            except ValueError:
                                # If parsing fails, use current time
                                executed_at = datetime.now()
                    else:
                        executed_at = row[4]
                
                created_at = datetime.now()
                if row[7]:
                    if isinstance(row[7], str):
                        # Handle common invalid datetime strings
                        if row[7] in ('CURRENT_DATETIME', 'CURRENT_TIMESTAMP'):
                            created_at = datetime.now()
                        else:
                            try:
                                created_at = datetime.fromisoformat(row[7])
                            except ValueError:
                                # If parsing fails, use current time
                                created_at = datetime.now()
                    else:
                        created_at = row[7]
                
                record = MigrationRecord(
                    id=row[0],
                    name=row[1] or row[0],
                    description=row[2] or "",
                    checksum=row[3],
                    executed_at=executed_at,
                    backup_path=row[5],
                    rollback_sql=row[6],
                    created_at=created_at
                )
                records.append(record)
            
            return records
            
        except Exception as e:
            logger.error(f"获取迁移历史失败: {e}")
            return []
    
    def execute_migration(self, migration_id: str, create_backup: bool = True) -> bool:
        """执行指定的迁移"""
        migration_file = self.versions_dir / f"{migration_id}.py"
        
        if not migration_file.exists():
            raise FileNotFoundError(f"迁移文件不存在: {migration_file}")
        
        try:
            # 创建备份
            backup_path = None
            if create_backup:
                backup_path = self.create_backup(f"pre_migration_{migration_id}")
            
            # 动态导入迁移模块
            spec = importlib.util.spec_from_file_location(migration_id, migration_file)
            migration_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(migration_module)
            
            # 执行升级
            logger.info(f"执行迁移: {migration_id}")
            migration_module.upgrade(self.session)
            
            # 记录迁移执行
            self.session.execute(text("""
                INSERT INTO schema_migrations (id, name, description, checksum, executed_at, backup_path, rollback_sql, created_at)
                VALUES (:id, :name, :desc, :checksum, :executed_at, :backup_path, :rollback_sql, :created_at)
            """), {
                'id': migration_id,
                'name': getattr(migration_module, 'DESCRIPTION', migration_id),
                'desc': getattr(migration_module, 'DESCRIPTION', ''),
                'checksum': getattr(migration_module, 'CHECKSUM', ''),
                'executed_at': datetime.now(),
                'backup_path': backup_path,
                'rollback_sql': getattr(migration_module, 'SQL_DOWN', ''),
                'created_at': getattr(migration_module, 'CREATED_AT', datetime.now())
            })
            
            self.session.commit()
            logger.info(f"迁移执行成功: {migration_id}")
            return True
            
        except Exception as e:
            logger.error(f"迁移执行失败: {e}")
            self.session.rollback()
            
            # 如果有备份，询问是否恢复
            if backup_path and os.path.exists(backup_path):
                logger.info(f"可以使用备份恢复: {backup_path}")
            
            raise
    
    def rollback_migration(self, migration_id: str) -> bool:
        """回滚指定的迁移"""
        # 检查迁移是否已执行
        result = self.session.execute(text(
            "SELECT backup_path, rollback_sql FROM schema_migrations WHERE id = :id"
        ), {'id': migration_id})
        
        row = result.fetchone()
        if not row:
            raise ValueError(f"迁移未执行或不存在: {migration_id}")
        
        backup_path, rollback_sql = row
        
        try:
            # 创建回滚前的备份
            rollback_backup = self.create_backup(f"pre_rollback_{migration_id}")
            
            # 执行回滚SQL
            if rollback_sql:
                logger.info(f"执行回滚SQL: {migration_id}")
                for sql_statement in rollback_sql.split(';'):
                    sql_statement = sql_statement.strip()
                    if sql_statement:
                        self.session.execute(text(sql_statement))
            
            # 删除迁移记录
            self.session.execute(text("DELETE FROM schema_migrations WHERE id = :id"), {'id': migration_id})
            self.session.commit()
            
            logger.info(f"迁移回滚成功: {migration_id}")
            return True
            
        except Exception as e:
            logger.error(f"迁移回滚失败: {e}")
            self.session.rollback()
            raise
    
    def migrate_to_latest(self, create_backup: bool = True) -> int:
        """执行所有待执行的迁移"""
        pending_migrations = self.get_pending_migrations()
        
        if not pending_migrations:
            logger.info("没有待执行的迁移")
            return 0
        
        logger.info(f"发现 {len(pending_migrations)} 个待执行的迁移")
        
        executed_count = 0
        for migration_id in pending_migrations:
            try:
                self.execute_migration(migration_id, create_backup and executed_count == 0)
                executed_count += 1
            except Exception as e:
                logger.error(f"迁移执行中断: {e}")
                break
        
        logger.info(f"成功执行 {executed_count} 个迁移")
        return executed_count
    
    def close(self):
        """关闭数据库连接"""
        if self.session:
            self.session.close()
        if self.engine:
            self.engine.dispose()


# 导入模块
import importlib.util