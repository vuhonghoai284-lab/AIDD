#!/usr/bin/env python3
"""
用户并发限制字段迁移脚本
为users表添加max_concurrent_tasks字段

使用方法：
1. 备份数据库：mysqldump -u root -p ai_doc_test > backup_$(date +%Y%m%d_%H%M%S).sql
2. 运行迁移：python migrate_user_concurrency.py
3. 验证迁移：python migrate_user_concurrency.py --verify
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
        host = database_config.get('host', 'localhost')
        port = database_config.get('port', 3306)
        username = database_config.get('username', 'root')
        password = database_config.get('password', '')
        database = database_config.get('database', 'ai_doc_test')
        
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
    
    print("🔍 检查users表当前结构...")
    
    with engine.connect() as conn:
        if db_type == 'mysql':
            # MySQL查询表结构
            result = conn.execute(text("DESCRIBE users"))
            columns = result.fetchall()
            
            print("📊 当前表结构:")
            has_concurrency_field = False
            for col in columns:
                field_name, field_type = col[0], col[1]
                print(f"   {field_name}: {field_type}")
                
                if field_name == 'max_concurrent_tasks':
                    has_concurrency_field = True
                    print(f"   ✅ 已存在并发限制字段: {field_name} ({field_type})")
            
            if not has_concurrency_field:
                print("   ⚠️ 缺少 max_concurrent_tasks 字段，需要添加")
                return False
        else:
            # SQLite查询表结构
            result = conn.execute(text("PRAGMA table_info(users)"))
            columns = result.fetchall()
            
            print("📊 当前表结构 (SQLite):")
            has_concurrency_field = False
            for col in columns:
                field_name = col[1]
                print(f"   {col[1]}: {col[2]}")
                
                if field_name == 'max_concurrent_tasks':
                    has_concurrency_field = True
                    print(f"   ✅ 已存在并发限制字段")
            
            if not has_concurrency_field:
                print("   ⚠️ 缺少 max_concurrent_tasks 字段，需要添加")
                return False
    
    return True

def migrate_add_concurrency_field(engine, db_type):
    """添加并发限制字段"""
    from sqlalchemy import text
    
    print("🚀 开始添加用户并发限制字段...")
    
    try:
        with engine.connect() as conn:
            # 开始事务
            trans = conn.begin()
            
            if db_type == 'mysql':
                # MySQL添加字段
                sql = "ALTER TABLE users ADD COLUMN max_concurrent_tasks INT DEFAULT 10;"
                print(f"   执行SQL: {sql}")
                conn.execute(text(sql))
            else:
                # SQLite添加字段
                sql = "ALTER TABLE users ADD COLUMN max_concurrent_tasks INTEGER DEFAULT 10;"
                print(f"   执行SQL: {sql}")
                conn.execute(text(sql))
            
            # 提交事务
            trans.commit()
            print("✅ 用户并发限制字段添加完成！")
            return True
            
    except Exception as e:
        print(f"❌ 字段添加失败: {e}")
        return False

def initialize_user_concurrency_limits(engine, db_type):
    """初始化现有用户的并发限制"""
    from sqlalchemy import text
    
    print("🔧 初始化现有用户的并发限制...")
    
    try:
        with engine.connect() as conn:
            trans = conn.begin()
            
            # 为管理员设置更高的限制
            admin_sql = """
                UPDATE users 
                SET max_concurrent_tasks = 50 
                WHERE (is_admin = true OR is_system_admin = true) 
                AND (max_concurrent_tasks IS NULL OR max_concurrent_tasks = 10)
            """
            
            # 为普通用户设置默认限制
            user_sql = """
                UPDATE users 
                SET max_concurrent_tasks = 10 
                WHERE (is_admin = false OR is_admin IS NULL) 
                AND (is_system_admin = false OR is_system_admin IS NULL)
                AND (max_concurrent_tasks IS NULL)
            """
            
            if db_type == 'mysql':
                # MySQL使用1/0表示boolean
                admin_sql = admin_sql.replace('= true', '= 1').replace('= false', '= 0')
                user_sql = user_sql.replace('= true', '= 1').replace('= false', '= 0')
            
            print(f"   为管理员设置并发限制: {admin_sql}")
            result = conn.execute(text(admin_sql))
            admin_updated = result.rowcount
            
            print(f"   为普通用户设置并发限制: {user_sql}")
            result = conn.execute(text(user_sql))
            user_updated = result.rowcount
            
            trans.commit()
            print(f"✅ 并发限制初始化完成！管理员更新: {admin_updated}个，普通用户更新: {user_updated}个")
            return True
            
    except Exception as e:
        print(f"❌ 并发限制初始化失败: {e}")
        return False

def verify_migration(engine, db_type):
    """验证迁移结果"""
    from sqlalchemy import text
    
    print("🔍 验证迁移结果...")
    
    with engine.connect() as conn:
        try:
            # 检查字段是否存在
            if db_type == 'mysql':
                result = conn.execute(text("DESCRIBE users"))
                columns = {row[0]: row[1] for row in result.fetchall()}
            else:
                result = conn.execute(text("PRAGMA table_info(users)"))
                columns = {row[1]: row[2] for row in result.fetchall()}
            
            if 'max_concurrent_tasks' not in columns:
                print("   ❌ max_concurrent_tasks 字段未找到")
                return False
            
            print(f"   ✅ max_concurrent_tasks 字段存在: {columns['max_concurrent_tasks']}")
            
            # 检查数据
            result = conn.execute(text("""
                SELECT 
                    COUNT(*) as total_users,
                    COUNT(CASE WHEN max_concurrent_tasks IS NOT NULL THEN 1 END) as users_with_limit,
                    AVG(max_concurrent_tasks) as avg_limit,
                    MIN(max_concurrent_tasks) as min_limit,
                    MAX(max_concurrent_tasks) as max_limit
                FROM users
            """))
            
            stats = result.fetchone()
            print("   📊 用户并发限制统计:")
            print(f"     总用户数: {stats[0]}")
            print(f"     已设置限制的用户: {stats[1]}")
            print(f"     平均限制: {stats[2]:.1f}" if stats[2] else "     平均限制: N/A")
            print(f"     最小限制: {stats[3]}" if stats[3] else "     最小限制: N/A")
            print(f"     最大限制: {stats[4]}" if stats[4] else "     最大限制: N/A")
            
            # 检查管理员和普通用户的设置
            result = conn.execute(text("""
                SELECT 
                    CASE 
                        WHEN is_admin = 1 OR is_system_admin = 1 THEN 'admin'
                        ELSE 'user' 
                    END as user_type,
                    AVG(max_concurrent_tasks) as avg_limit,
                    COUNT(*) as count
                FROM users 
                WHERE max_concurrent_tasks IS NOT NULL
                GROUP BY user_type
            """) if db_type == 'mysql' else text("""
                SELECT 
                    CASE 
                        WHEN is_admin = 1 OR is_system_admin = 1 THEN 'admin'
                        ELSE 'user' 
                    END as user_type,
                    AVG(max_concurrent_tasks) as avg_limit,
                    COUNT(*) as count
                FROM users 
                WHERE max_concurrent_tasks IS NOT NULL
                GROUP BY user_type
            """))
            
            type_stats = result.fetchall()
            print("   📊 按用户类型统计:")
            for row in type_stats:
                user_type, avg_limit, count = row
                print(f"     {user_type}: {count}个用户，平均限制 {avg_limit:.1f}")
            
            print("🎉 迁移验证成功！")
            return True
            
        except Exception as e:
            print(f"❌ 迁移验证失败: {e}")
            return False

def test_concurrency_service(engine, db_type):
    """测试并发控制服务"""
    print("🧪 测试并发控制服务...")
    
    try:
        # 导入并测试服务
        from app.services.concurrency_service import concurrency_service
        from app.models.user import User
        from sqlalchemy.orm import sessionmaker
        
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        try:
            # 获取一个测试用户
            user = db.query(User).first()
            if not user:
                print("   ⚠️ 数据库中没有用户，无法测试")
                return False
            
            print(f"   测试用户: {user.display_name or user.uid}")
            print(f"   用户并发限制: {concurrency_service.get_user_max_concurrent_tasks(user)}")
            
            # 获取并发状态
            status = concurrency_service.get_concurrency_status(db, user)
            print(f"   系统状态: {status['system']}")
            print(f"   用户状态: {status['user']}")
            
            # 测试并发限制检查
            allowed, info = concurrency_service.check_concurrency_limits(db, user, 1, False)
            print(f"   允许创建任务: {allowed}")
            if not allowed:
                print(f"   限制因素: {info['limiting_factor']}")
            
            print("✅ 并发控制服务测试通过！")
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ 并发控制服务测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='用户并发限制字段迁移脚本')
    parser.add_argument('--verify', action='store_true', help='仅验证迁移结果，不执行迁移')
    parser.add_argument('--test', action='store_true', help='测试并发控制服务')
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
            test_concurrency_service(engine, db_type)
            return
        
        if not needs_migration:
            print("✅ 表结构已经是最新版本，无需迁移")
            if args.test:
                test_concurrency_service(engine, db_type)
            return
        
        # 创建备份提醒
        if not args.force and db_type == 'mysql':
            print("📦 建议在迁移前创建备份:")
            print("   mysqldump -u root -p ai_doc_test > backup_user_concurrency_migration.sql")
            input("   请手动执行备份后按回车继续... ")
        
        # 执行迁移
        if migrate_add_concurrency_field(engine, db_type):
            # 初始化用户并发限制
            if initialize_user_concurrency_limits(engine, db_type):
                # 验证迁移结果
                if verify_migration(engine, db_type):
                    # 测试并发控制服务
                    test_concurrency_service(engine, db_type)
                else:
                    print("⚠️ 迁移验证失败，请检查数据库状态")
                    sys.exit(1)
            else:
                print("⚠️ 并发限制初始化失败")
                sys.exit(1)
        else:
            print("❌ 字段添加失败")
            sys.exit(1)
            
    except Exception as e:
        print(f"💥 迁移脚本执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()