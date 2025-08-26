#!/usr/bin/env python3
"""
数据库迁移脚本：将ai_outputs表的TEXT字段升级为LONGTEXT
解决AI输出数据过大导致的DataError问题

使用方法：
1. 备份数据库：mysqldump -u root -p ai_doc_test > backup.sql
2. 运行迁移：python migrate_longtext.py
3. 验证迁移：python migrate_longtext.py --verify
"""
import sys
import os
import argparse
from contextlib import contextmanager

# 添加项目路径
sys.path.append('.')

def get_database_connection():
    """获取数据库连接"""
    from app.core.config import get_settings
    from sqlalchemy import create_engine, text
    
    settings = get_settings()
    database_config = settings.database_config
    
    # 构建数据库连接URL
    if database_config.get('type', 'sqlite').lower() == 'sqlite':
        # SQLite - 本地开发环境
        sqlite_config = database_config.get('sqlite', {})
        db_path = sqlite_config.get('path', './data/app.db')
        database_url = f"sqlite:///{db_path}"
        engine = create_engine(database_url)
        return engine, 'sqlite'
    else:
        # MySQL - 生产环境
        mysql_config = database_config.get('mysql', {})
        host = mysql_config.get('host', 'localhost')
        port = mysql_config.get('port', 3306)
        username = mysql_config.get('username', 'root')
        password = mysql_config.get('password', '')
        database = mysql_config.get('database', 'ai_doc_test')
        
        try:
            database_url = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}?charset=utf8mb4"
            engine = create_engine(database_url)
            return engine, 'mysql'
        except Exception as e:
            print(f"⚠️ MySQL连接失败: {e}")
            print("ℹ️ 可能是缺少pymysql模块或MySQL服务未启动")
            print("   在生产环境请安装: pip install pymysql")
            raise e

@contextmanager
def get_db_session(engine):
    """数据库会话上下文管理器"""
    from sqlalchemy.orm import sessionmaker
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def check_table_structure(engine, db_type):
    """检查当前表结构"""
    from sqlalchemy import text
    print("🔍 检查ai_outputs表当前结构...")
    
    with engine.connect() as conn:
        if db_type == 'mysql':
            # MySQL查询表结构
            result = conn.execute(text("DESCRIBE ai_outputs"))
            columns = result.fetchall()
            
            print("📊 当前表结构:")
            for col in columns:
                field_name, field_type = col[0], col[1]
                print(f"   {field_name}: {field_type}")
                
                # 检查关键字段类型
                if field_name in ['input_text', 'raw_output'] and 'text' in field_type.lower():
                    if 'longtext' in field_type.lower():
                        print(f"   ✅ {field_name} 已经是 LONGTEXT 类型")
                    else:
                        print(f"   ⚠️ {field_name} 是 {field_type}，需要升级为 LONGTEXT")
                        return False
        else:
            # SQLite查询表结构
            result = conn.execute(text("PRAGMA table_info(ai_outputs)"))
            columns = result.fetchall()
            
            print("📊 当前表结构 (SQLite):")
            for col in columns:
                print(f"   {col[1]}: {col[2]}")
            print("   ℹ️ SQLite 的 TEXT 类型支持大数据，无需迁移")
            return True
    
    return True

def migrate_to_longtext(engine, db_type):
    """执行迁移到LONGTEXT"""
    from sqlalchemy import text
    if db_type != 'mysql':
        print("ℹ️ 非MySQL数据库，跳过迁移")
        return True
    
    print("🚀 开始执行数据库迁移...")
    
    migration_sql = [
        "ALTER TABLE ai_outputs MODIFY COLUMN input_text LONGTEXT NOT NULL;",
        "ALTER TABLE ai_outputs MODIFY COLUMN raw_output LONGTEXT NOT NULL;"
    ]
    
    try:
        with engine.connect() as conn:
            # 开始事务
            trans = conn.begin()
            
            for i, sql in enumerate(migration_sql, 1):
                print(f"   执行迁移 {i}/{len(migration_sql)}: {sql}")
                conn.execute(text(sql))
            
            # 提交事务
            trans.commit()
            print("✅ 数据库迁移完成！")
            return True
            
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        return False

def verify_migration(engine, db_type):
    """验证迁移结果"""
    from sqlalchemy import text
    print("🔍 验证迁移结果...")
    
    with engine.connect() as conn:
        if db_type == 'mysql':
            result = conn.execute(text("DESCRIBE ai_outputs"))
            columns = result.fetchall()
            
            success = True
            for col in columns:
                field_name, field_type = col[0], col[1]
                if field_name in ['input_text', 'raw_output']:
                    if 'longtext' in field_type.lower():
                        print(f"   ✅ {field_name}: {field_type}")
                    else:
                        print(f"   ❌ {field_name}: {field_type} (应该是 LONGTEXT)")
                        success = False
            
            if success:
                print("🎉 迁移验证成功！所有字段都已升级为LONGTEXT")
            else:
                print("⚠️ 迁移验证失败，部分字段未正确升级")
                
            return success
        else:
            print("   ℹ️ SQLite环境，无需验证")
            return True

def test_large_data_insert(engine, db_type):
    """测试大数据插入"""
    from sqlalchemy import text
    print("🧪 测试大数据插入能力...")
    
    # 创建测试数据（模拟AI输出的大JSON）
    large_json = '{"test": "' + 'x' * 100000 + '"}'  # 100KB测试数据
    
    try:
        with get_db_session(engine) as session:
            # 插入测试数据
            if db_type == 'mysql':
                insert_sql = text("""
                    INSERT INTO ai_outputs 
                    (task_id, operation_type, input_text, raw_output, status, created_at)
                    VALUES 
                    (:task_id, :operation_type, :input_text, :raw_output, :status, NOW())
                """)
            else:
                insert_sql = text("""
                    INSERT INTO ai_outputs 
                    (task_id, operation_type, input_text, raw_output, status, created_at)
                    VALUES 
                    (:task_id, :operation_type, :input_text, :raw_output, :status, datetime('now'))
                """)
            
            session.execute(insert_sql, {
                'task_id': 999999,  # 测试任务ID
                'operation_type': 'test_migration',
                'input_text': large_json,
                'raw_output': large_json,
                'status': 'test'
            })
            
            # 查询并删除测试数据
            delete_sql = text("DELETE FROM ai_outputs WHERE task_id = 999999")
            session.execute(delete_sql)
            
        print("✅ 大数据插入测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ 大数据插入测试失败: {e}")
        return False

def create_migration_backup(engine, db_type):
    """创建迁移前备份（仅提示）"""
    if db_type == 'mysql':
        print("📦 建议在迁移前创建备份:")
        print("   mysqldump -u root -p ai_doc_test > backup_before_longtext_migration.sql")
        input("   请手动执行备份后按回车继续... ")
    else:
        print("📦 SQLite数据库，建议复制数据文件作为备份")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='AI输出表字段类型迁移脚本')
    parser.add_argument('--verify', action='store_true', help='仅验证迁移结果，不执行迁移')
    parser.add_argument('--test', action='store_true', help='测试大数据插入能力')
    parser.add_argument('--force', action='store_true', help='强制执行迁移，跳过备份提示')
    args = parser.parse_args()
    
    try:
        # 获取数据库连接
        engine, db_type = get_database_connection()
        print(f"🔗 连接到 {db_type.upper()} 数据库")
        
        # 检查当前表结构
        needs_migration = not check_table_structure(engine, db_type)
        
        if args.verify:
            # 仅验证模式
            verify_migration(engine, db_type)
            return
        
        if args.test:
            # 测试模式
            test_large_data_insert(engine, db_type)
            return
        
        if not needs_migration:
            print("✅ 表结构已经是最新版本，无需迁移")
            if not args.test:
                # 运行测试确认
                test_large_data_insert(engine, db_type)
            return
        
        # 创建备份提醒
        if not args.force:
            create_migration_backup(engine, db_type)
        
        # 执行迁移
        if migrate_to_longtext(engine, db_type):
            # 验证迁移结果
            if verify_migration(engine, db_type):
                # 测试大数据插入
                test_large_data_insert(engine, db_type)
            else:
                print("⚠️ 迁移验证失败，请检查表结构")
                sys.exit(1)
        else:
            print("❌ 迁移执行失败")
            sys.exit(1)
            
    except Exception as e:
        print(f"💥 迁移脚本执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()