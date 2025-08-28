#!/usr/bin/env python3
"""
任务分享功能生产环境数据库迁移脚本

此脚本会：
1. 创建 task_shares 表
2. 为 issues 表添加反馈操作人字段
3. 创建必要的索引
4. 验证迁移结果

使用方法：
python migration_task_sharing.py

环境要求：
- 确保数据库连接正常
- 建议在维护窗口期间执行
- 执行前请备份数据库
"""

import sqlite3
import sys
import os
from datetime import datetime


def backup_database(db_path):
    """备份数据库"""
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return False
    
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        # 使用SQLite的备份API
        source_conn = sqlite3.connect(db_path)
        backup_conn = sqlite3.connect(backup_path)
        
        source_conn.backup(backup_conn)
        
        source_conn.close()
        backup_conn.close()
        
        print(f"✅ 数据库备份成功: {backup_path}")
        return True
    except Exception as e:
        print(f"❌ 数据库备份失败: {e}")
        return False


def create_task_shares_table(cursor):
    """创建 task_shares 表"""
    print("🔧 创建 task_shares 表...")
    
    # 检查表是否已存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='task_shares'")
    if cursor.fetchone():
        print("  ✅ task_shares 表已存在，跳过创建")
        return True
    
    try:
        # 创建 task_shares 表
        create_table_sql = """
        CREATE TABLE task_shares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            owner_id INTEGER NOT NULL,
            shared_user_id INTEGER NOT NULL,
            permission_level VARCHAR(20) NOT NULL DEFAULT 'read_only',
            share_comment TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN NOT NULL DEFAULT 1,
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
            FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (shared_user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
        cursor.execute(create_table_sql)
        print("  ✅ task_shares 表创建成功")
        
        # 创建索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_task_shares_task_id ON task_shares(task_id)",
            "CREATE INDEX IF NOT EXISTS idx_task_shares_owner_id ON task_shares(owner_id)", 
            "CREATE INDEX IF NOT EXISTS idx_task_shares_shared_user_id ON task_shares(shared_user_id)",
            "CREATE INDEX IF NOT EXISTS idx_task_shares_is_active ON task_shares(is_active)",
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_task_shares_unique ON task_shares(task_id, shared_user_id)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
            print(f"  ✅ 索引创建成功: {index_sql.split()[5]}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 创建 task_shares 表失败: {e}")
        return False


def add_feedback_user_fields(cursor):
    """为 issues 表添加反馈操作人字段"""
    print("🔧 为 issues 表添加反馈操作人字段...")
    
    try:
        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(issues)")
        columns = [col[1] for col in cursor.fetchall()]
        
        fields_to_add = []
        if 'feedback_user_id' not in columns:
            fields_to_add.append(('feedback_user_id', 'INTEGER', '反馈操作用户ID'))
        if 'feedback_user_name' not in columns:
            fields_to_add.append(('feedback_user_name', 'VARCHAR(100)', '反馈操作用户名称'))
        if 'feedback_updated_at' not in columns:
            fields_to_add.append(('feedback_updated_at', 'DATETIME', '最后反馈时间'))
        
        if not fields_to_add:
            print("  ✅ 反馈字段已存在，无需添加")
            return True
        
        # 添加字段
        for field_name, field_type, description in fields_to_add:
            alter_sql = f'ALTER TABLE issues ADD COLUMN {field_name} {field_type}'
            cursor.execute(alter_sql)
            print(f"  ✅ 添加字段: {field_name} {field_type} - {description}")
        
        # 添加索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_issues_feedback_user ON issues(feedback_user_id)')
        print("  ✅ 添加反馈用户索引")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 添加反馈字段失败: {e}")
        return False


def verify_migration(cursor):
    """验证迁移结果"""
    print("📋 验证迁移结果...")
    
    # 验证 task_shares 表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='task_shares'")
    if cursor.fetchone():
        print("  ✅ task_shares 表存在")
        
        # 检查表结构
        cursor.execute("PRAGMA table_info(task_shares)")
        columns = cursor.fetchall()
        expected_columns = ['id', 'task_id', 'owner_id', 'shared_user_id', 
                           'permission_level', 'share_comment', 'created_at', 'is_active']
        
        column_names = [col[1] for col in columns]
        missing_columns = [col for col in expected_columns if col not in column_names]
        
        if not missing_columns:
            print("  ✅ task_shares 表结构完整")
        else:
            print(f"  ❌ task_shares 表缺少字段: {missing_columns}")
            return False
    else:
        print("  ❌ task_shares 表不存在")
        return False
    
    # 验证 issues 表的新字段
    cursor.execute("PRAGMA table_info(issues)")
    columns = [col[1] for col in cursor.fetchall()]
    
    feedback_fields = ['feedback_user_id', 'feedback_user_name', 'feedback_updated_at']
    missing_feedback_fields = [field for field in feedback_fields if field not in columns]
    
    if not missing_feedback_fields:
        print("  ✅ issues 表反馈字段完整")
    else:
        print(f"  ❌ issues 表缺少反馈字段: {missing_feedback_fields}")
        return False
    
    # 检查索引
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE '%task_shares%'")
    indexes = cursor.fetchall()
    if len(indexes) >= 4:  # 至少应有4个索引
        print(f"  ✅ task_shares 相关索引已创建 ({len(indexes)} 个)")
    else:
        print(f"  ⚠️ task_shares 相关索引可能不完整 ({len(indexes)} 个)")
    
    print("🎉 迁移验证完成！")
    return True


def main():
    """主函数"""
    print("=" * 60)
    print("🚀 任务分享功能数据库迁移脚本")
    print("=" * 60)
    
    # 数据库路径
    db_path = './data/app.db'
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        print("请确保在正确的目录下运行此脚本")
        return False
    
    # 备份数据库
    print("📦 步骤 1: 备份数据库")
    if not backup_database(db_path):
        print("❌ 备份失败，停止迁移")
        return False
    
    # 执行迁移
    print("\n🔄 步骤 2: 执行数据库迁移")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 开启事务
        conn.execute("BEGIN TRANSACTION")
        
        # 创建 task_shares 表
        if not create_task_shares_table(cursor):
            raise Exception("创建 task_shares 表失败")
        
        # 添加反馈字段
        if not add_feedback_user_fields(cursor):
            raise Exception("添加反馈字段失败")
        
        # 提交事务
        conn.commit()
        print("✅ 数据库迁移执行成功")
        
        # 验证迁移
        print("\n📋 步骤 3: 验证迁移结果")
        if not verify_migration(cursor):
            print("❌ 迁移验证失败")
            return False
        
        print("\n" + "=" * 60)
        print("🎉 任务分享功能数据库迁移完成！")
        print("=" * 60)
        print("\n📝 迁移摘要:")
        print("  1. ✅ 创建了 task_shares 表")
        print("  2. ✅ 为 issues 表添加了反馈操作人字段")
        print("  3. ✅ 创建了必要的索引")
        print("  4. ✅ 数据库备份已保存")
        print("\n🚀 现在可以启用任务分享功能！")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 迁移执行失败: {e}")
        conn.rollback()
        print("📦 事务已回滚，数据库状态恢复")
        return False
        
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)