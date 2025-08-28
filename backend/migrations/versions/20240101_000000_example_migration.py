"""
示例迁移：添加示例表

Migration ID: 20240101_000000_example_migration
Created: 2024-01-01T00:00:00
Checksum: example_checksum
"""

from datetime import datetime
from sqlalchemy import text

# 迁移信息
MIGRATION_ID = "20240101_000000_example_migration"
DESCRIPTION = "示例迁移：添加示例表"
CREATED_AT = datetime.fromisoformat("2024-01-01T00:00:00")
CHECKSUM = "example_checksum"

# 升级SQL
SQL_UP = """
CREATE TABLE example_table (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""

# 降级SQL（回滚）
SQL_DOWN = """
DROP TABLE example_table
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
