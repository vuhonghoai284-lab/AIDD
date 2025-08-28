#!/usr/bin/env python3
"""
任务分享功能MySQL生产环境数据库迁移脚本

此脚本会：
1. 创建 task_shares 表
2. 为 issues 表添加反馈操作人字段
3. 创建必要的索引
4. 验证迁移结果

使用方法：
python migration_task_sharing_mysql.py

环境要求：
- MySQL数据库连接配置正确
- 确保数据库用户有DDL权限
- 建议在维护窗口期间执行
- 执行前请备份数据库
"""

import pymysql
import sys
import os
from datetime import datetime
from contextlib import contextmanager


def get_database_config():
    """获取数据库配置"""
    # 从环境变量或配置文件获取数据库连接信息
    config = {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'port': int(os.getenv('MYSQL_PORT', '3306')),
        'user': os.getenv('MYSQL_USERNAME', 'root'),
        'password': os.getenv('MYSQL_PASSWORD', ''),
        'database': os.getenv('MYSQL_DATABASE', 'ai_doc_test'),
        'charset': 'utf8mb4'
    }
    
    # 检查必要的配置
    if not config['password']:
        password = input("请输入MySQL密码: ")
        config['password'] = password
    
    return config


@contextmanager
def get_db_connection(config):
    """获取数据库连接（上下文管理器）"""
    connection = None
    try:
        connection = pymysql.connect(**config)
        yield connection
    except Exception as e:
        if connection:
            connection.rollback()
        raise e
    finally:
        if connection:
            connection.close()


def backup_database(config):
    """创建数据库备份（使用mysqldump）"""
    try:
        import subprocess
        
        backup_file = f"backup_{config['database']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        
        # 构建mysqldump命令
        cmd = [
            'mysqldump',
            f'--host={config["host"]}',
            f'--port={config["port"]}',
            f'--user={config["user"]}',
            f'--password={config["password"]}',
            '--single-transaction',
            '--routines',
            '--triggers',
            config['database']
        ]
        
        print(f"🔄 正在备份数据库到: {backup_file}")
        
        with open(backup_file, 'w') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
        
        if result.returncode == 0:
            print(f"✅ 数据库备份成功: {backup_file}")
            return backup_file
        else:
            print(f"❌ 数据库备份失败: {result.stderr}")
            return None
            
    except subprocess.CalledProcessError as e:
        print(f"❌ 备份命令执行失败: {e}")
        return None
    except Exception as e:
        print(f"❌ 备份过程出错: {e}")
        return None


def create_task_shares_table(cursor):
    """创建 task_shares 表"""
    print("🔧 创建 task_shares 表...")
    
    try:
        # 检查表是否已存在
        cursor.execute("SHOW TABLES LIKE 'task_shares'")
        if cursor.fetchone():
            print("  ✅ task_shares 表已存在，跳过创建")
            return True
        
        # 创建 task_shares 表
        create_table_sql = """
        CREATE TABLE task_shares (
            id INT AUTO_INCREMENT PRIMARY KEY,
            task_id INT NOT NULL,
            owner_id INT NOT NULL,
            shared_user_id INT NOT NULL,
            permission_level VARCHAR(20) NOT NULL DEFAULT 'read_only',
            share_comment TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            INDEX idx_task_shares_task_id (task_id),
            INDEX idx_task_shares_owner_id (owner_id),
            INDEX idx_task_shares_shared_user_id (shared_user_id),
            INDEX idx_task_shares_is_active (is_active),
            UNIQUE INDEX idx_task_shares_unique (task_id, shared_user_id),
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
            FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (shared_user_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务分享表'
        """
        
        cursor.execute(create_table_sql)
        print("  ✅ task_shares 表创建成功")
        print("  ✅ 相关索引创建成功")
        print("  ✅ 外键约束创建成功")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 创建 task_shares 表失败: {e}")
        return False


def add_feedback_user_fields(cursor):
    """为 issues 表添加反馈操作人字段"""
    print("🔧 为 issues 表添加反馈操作人字段...")
    
    try:
        # 检查字段是否已存在
        cursor.execute("DESCRIBE issues")
        columns = [row[0] for row in cursor.fetchall()]
        
        fields_to_add = []
        if 'feedback_user_id' not in columns:
            fields_to_add.append(('feedback_user_id', 'INT', '反馈操作用户ID'))
        if 'feedback_user_name' not in columns:
            fields_to_add.append(('feedback_user_name', 'VARCHAR(100)', '反馈操作用户名称'))
        if 'feedback_updated_at' not in columns:
            fields_to_add.append(('feedback_updated_at', 'DATETIME', '最后反馈时间'))
        
        if not fields_to_add:
            print("  ✅ 反馈字段已存在，无需添加")
            return True
        
        # 添加字段
        for field_name, field_type, description in fields_to_add:
            alter_sql = f'ALTER TABLE issues ADD COLUMN {field_name} {field_type} COMMENT "{description}"'
            cursor.execute(alter_sql)
            print(f"  ✅ 添加字段: {field_name} {field_type} - {description}")
        
        # 添加索引
        try:
            cursor.execute('CREATE INDEX idx_issues_feedback_user ON issues(feedback_user_id)')
            print("  ✅ 添加反馈用户索引")
        except pymysql.Error as e:
            if "Duplicate key name" in str(e):
                print("  ✅ 反馈用户索引已存在")
            else:
                raise
        
        return True
        
    except Exception as e:
        print(f"  ❌ 添加反馈字段失败: {e}")
        return False


def verify_migration(cursor):
    """验证迁移结果"""
    print("📋 验证迁移结果...")
    
    try:
        # 验证 task_shares 表
        cursor.execute("SHOW TABLES LIKE 'task_shares'")
        if cursor.fetchone():
            print("  ✅ task_shares 表存在")
            
            # 检查表结构
            cursor.execute("DESCRIBE task_shares")
            columns = cursor.fetchall()
            expected_columns = ['id', 'task_id', 'owner_id', 'shared_user_id', 
                               'permission_level', 'share_comment', 'created_at', 'is_active']
            
            column_names = [col[0] for col in columns]
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
        cursor.execute("DESCRIBE issues")
        columns = [row[0] for row in cursor.fetchall()]
        
        feedback_fields = ['feedback_user_id', 'feedback_user_name', 'feedback_updated_at']
        missing_feedback_fields = [field for field in feedback_fields if field not in columns]
        
        if not missing_feedback_fields:
            print("  ✅ issues 表反馈字段完整")
        else:
            print(f"  ❌ issues 表缺少反馈字段: {missing_feedback_fields}")
            return False
        
        # 检查索引
        cursor.execute("SHOW INDEX FROM task_shares")
        indexes = cursor.fetchall()
        if len(indexes) >= 5:  # 至少应有5个索引（包括主键）
            print(f"  ✅ task_shares 相关索引已创建 ({len(indexes)} 个)")
        else:
            print(f"  ⚠️ task_shares 相关索引可能不完整 ({len(indexes)} 个)")
        
        # 检查外键约束
        cursor.execute("""
            SELECT CONSTRAINT_NAME 
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
            WHERE TABLE_NAME = 'task_shares' 
            AND TABLE_SCHEMA = DATABASE()
            AND REFERENCED_TABLE_NAME IS NOT NULL
        """)
        foreign_keys = cursor.fetchall()
        if len(foreign_keys) >= 3:
            print(f"  ✅ task_shares 外键约束已创建 ({len(foreign_keys)} 个)")
        else:
            print(f"  ⚠️ task_shares 外键约束可能不完整 ({len(foreign_keys)} 个)")
        
        print("🎉 迁移验证完成！")
        return True
        
    except Exception as e:
        print(f"❌ 迁移验证失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("🚀 任务分享功能MySQL数据库迁移脚本")
    print("=" * 60)
    
    # 获取数据库配置
    try:
        config = get_database_config()
        print(f"📡 连接数据库: {config['host']}:{config['port']}/{config['database']}")
    except Exception as e:
        print(f"❌ 数据库配置错误: {e}")
        return False
    
    # 测试数据库连接
    try:
        with get_db_connection(config) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            print(f"✅ 数据库连接成功，版本: {version}")
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False
    
    # 询问是否备份
    backup_choice = input("\n📦 是否需要备份数据库？(推荐) (y/N): ").strip().lower()
    if backup_choice in ['y', 'yes']:
        backup_file = backup_database(config)
        if not backup_file:
            print("❌ 备份失败，是否继续迁移？(y/N): ", end="")
            if input().strip().lower() not in ['y', 'yes']:
                return False
    
    # 执行迁移
    print("\n🔄 开始执行数据库迁移")
    
    try:
        with get_db_connection(config) as conn:
            cursor = conn.cursor()
            
            # 开启事务
            conn.begin()
            
            try:
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
                print("\n📋 验证迁移结果")
                if not verify_migration(cursor):
                    print("❌ 迁移验证失败，但数据已提交")
                    return False
                
                print("\n" + "=" * 60)
                print("🎉 MySQL任务分享功能数据库迁移完成！")
                print("=" * 60)
                print("\n📝 迁移摘要:")
                print("  1. ✅ 创建了 task_shares 表（包含索引和外键）")
                print("  2. ✅ 为 issues 表添加了反馈操作人字段")
                print("  3. ✅ 创建了必要的索引")
                if backup_choice in ['y', 'yes']:
                    print("  4. ✅ 数据库备份已保存")
                print("\n🚀 现在可以启用任务分享功能！")
                
                return True
                
            except Exception as e:
                print(f"\n❌ 迁移执行失败: {e}")
                conn.rollback()
                print("📦 事务已回滚，数据库状态恢复")
                return False
                
    except Exception as e:
        print(f"❌ 数据库操作失败: {e}")
        return False


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ 用户取消操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
        sys.exit(1)