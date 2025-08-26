#!/usr/bin/env python3
"""
外键约束问题修复脚本
清理孤儿记录，修复数据库一致性问题

使用方法：
1. 备份数据库：mysqldump -u root -p ai_doc_test > backup_foreign_key_fix.sql
2. 运行修复：python fix_foreign_key_constraints.py
3. 验证结果：python fix_foreign_key_constraints.py --verify
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
        charset = mysql_config.get('charset', 'utf8mb4')
        
        try:
            database_url = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}?charset={charset}"
            engine = create_engine(database_url)
            return engine, 'mysql'
        except Exception as e:
            print(f"⚠️ MySQL连接失败: {e}")
            print("ℹ️ 可能是缺少pymysql模块或MySQL服务未启动")
            print("   在生产环境请安装: pip install pymysql")
            raise e

@contextmanager
def get_db_transaction(engine):
    """数据库事务上下文管理器"""
    conn = engine.connect()
    trans = conn.begin()
    try:
        yield conn
        trans.commit()
        print("✅ 事务提交成功")
    except Exception as e:
        trans.rollback()
        print(f"❌ 事务回滚: {e}")
        raise e
    finally:
        conn.close()

def analyze_foreign_key_issues(engine, db_type):
    """分析外键约束问题"""
    from sqlalchemy import text
    
    print("🔍 分析外键约束问题...")
    
    issues = []
    
    with engine.connect() as conn:
        try:
            # 检查 ai_outputs 表的孤儿记录
            print("   检查 ai_outputs 表的孤儿记录...")
            orphan_ai_outputs = conn.execute(text("""
                SELECT COUNT(*) as count
                FROM ai_outputs ao
                LEFT JOIN tasks t ON ao.task_id = t.id
                WHERE t.id IS NULL
            """)).fetchone()
            
            if orphan_ai_outputs[0] > 0:
                issues.append({
                    'table': 'ai_outputs',
                    'count': orphan_ai_outputs[0],
                    'description': f"ai_outputs表中有 {orphan_ai_outputs[0]} 条记录引用了不存在的task_id"
                })
            
            # 检查 issues 表的孤儿记录
            print("   检查 issues 表的孤儿记录...")
            orphan_issues = conn.execute(text("""
                SELECT COUNT(*) as count
                FROM issues i
                LEFT JOIN tasks t ON i.task_id = t.id
                WHERE t.id IS NULL
            """)).fetchone()
            
            if orphan_issues[0] > 0:
                issues.append({
                    'table': 'issues',
                    'count': orphan_issues[0],
                    'description': f"issues表中有 {orphan_issues[0]} 条记录引用了不存在的task_id"
                })
            
            # 检查 task_logs 表的孤儿记录
            print("   检查 task_logs 表的孤儿记录...")
            orphan_logs = conn.execute(text("""
                SELECT COUNT(*) as count
                FROM task_logs tl
                LEFT JOIN tasks t ON tl.task_id = t.id
                WHERE t.id IS NULL
            """)).fetchone()
            
            if orphan_logs[0] > 0:
                issues.append({
                    'table': 'task_logs',
                    'count': orphan_logs[0],
                    'description': f"task_logs表中有 {orphan_logs[0]} 条记录引用了不存在的task_id"
                })
                
        except Exception as e:
            print(f"❌ 分析过程中发生错误: {e}")
            return issues
    
    if issues:
        print("⚠️ 发现外键约束问题:")
        for issue in issues:
            print(f"   - {issue['description']}")
    else:
        print("✅ 没有发现外键约束问题")
    
    return issues

def fix_foreign_key_issues(engine, db_type, issues):
    """修复外键约束问题"""
    from sqlalchemy import text
    
    if not issues:
        print("✅ 没有需要修复的外键约束问题")
        return True
    
    print("🚀 开始修复外键约束问题...")
    
    try:
        with get_db_transaction(engine) as conn:
            total_deleted = 0
            
            for issue in issues:
                table = issue['table']
                count = issue['count']
                
                print(f"   修复 {table} 表的 {count} 条孤儿记录...")
                
                if table == 'ai_outputs':
                    if db_type == 'mysql':
                        result = conn.execute(text("""
                            DELETE ao FROM ai_outputs ao
                            LEFT JOIN tasks t ON ao.task_id = t.id
                            WHERE t.id IS NULL
                        """))
                    else:  # SQLite
                        result = conn.execute(text("""
                            DELETE FROM ai_outputs 
                            WHERE task_id NOT IN (SELECT id FROM tasks)
                        """))
                    deleted_count = result.rowcount
                    
                elif table == 'issues':
                    if db_type == 'mysql':
                        result = conn.execute(text("""
                            DELETE i FROM issues i
                            LEFT JOIN tasks t ON i.task_id = t.id
                            WHERE t.id IS NULL
                        """))
                    else:  # SQLite
                        result = conn.execute(text("""
                            DELETE FROM issues 
                            WHERE task_id NOT IN (SELECT id FROM tasks)
                        """))
                    deleted_count = result.rowcount
                    
                elif table == 'task_logs':
                    if db_type == 'mysql':
                        result = conn.execute(text("""
                            DELETE tl FROM task_logs tl
                            LEFT JOIN tasks t ON tl.task_id = t.id
                            WHERE t.id IS NULL
                        """))
                    else:  # SQLite
                        result = conn.execute(text("""
                            DELETE FROM task_logs 
                            WHERE task_id NOT IN (SELECT id FROM tasks)
                        """))
                    deleted_count = result.rowcount
                    
                else:
                    print(f"   ⚠️ 不支持的表: {table}")
                    continue
                
                print(f"   ✅ {table} 表删除了 {deleted_count} 条孤儿记录")
                total_deleted += deleted_count
            
            print(f"🎉 外键约束问题修复完成！总共删除了 {total_deleted} 条孤儿记录")
            return True
            
    except Exception as e:
        print(f"❌ 修复过程中发生错误: {e}")
        return False

def verify_fix(engine, db_type):
    """验证修复结果"""
    print("🔍 验证修复结果...")
    
    issues = analyze_foreign_key_issues(engine, db_type)
    
    if not issues:
        print("✅ 验证通过！没有外键约束问题")
        return True
    else:
        print("❌ 验证失败！仍然存在外键约束问题")
        return False

def get_database_statistics(engine, db_type):
    """获取数据库统计信息"""
    from sqlalchemy import text
    
    print("📊 数据库统计信息:")
    
    with engine.connect() as conn:
        try:
            # 统计各表记录数
            tables = ['tasks', 'ai_outputs', 'issues', 'task_logs', 'users']
            
            for table in tables:
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()
                    print(f"   {table}: {result[0]} 条记录")
                except Exception as e:
                    print(f"   {table}: 查询失败 ({e})")
            
            # 检查外键约束状态
            print("\n🔗 外键约束检查:")
            for child_table, parent_table in [
                ('ai_outputs', 'tasks'),
                ('issues', 'tasks'),
                ('task_logs', 'tasks')
            ]:
                try:
                    result = conn.execute(text(f"""
                        SELECT 
                            COUNT(c.task_id) as child_count,
                            COUNT(p.id) as valid_references
                        FROM {child_table} c
                        LEFT JOIN {parent_table} p ON c.task_id = p.id
                    """)).fetchone()
                    
                    child_count, valid_refs = result
                    invalid_refs = child_count - valid_refs
                    
                    if invalid_refs == 0:
                        print(f"   ✅ {child_table} → {parent_table}: {child_count} 条记录，全部引用有效")
                    else:
                        print(f"   ❌ {child_table} → {parent_table}: {child_count} 条记录，{invalid_refs} 条引用无效")
                        
                except Exception as e:
                    print(f"   ⚠️ {child_table} → {parent_table}: 检查失败 ({e})")
                    
        except Exception as e:
            print(f"❌ 统计信息获取失败: {e}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='外键约束问题修复脚本')
    parser.add_argument('--verify', action='store_true', help='仅验证，不执行修复')
    parser.add_argument('--stats', action='store_true', help='显示数据库统计信息')
    parser.add_argument('--force', action='store_true', help='强制执行修复，跳过备份提示')
    args = parser.parse_args()
    
    try:
        # 获取数据库连接
        engine, db_type = get_database_connection()
        print(f"🔗 连接到 {db_type.upper()} 数据库")
        
        # 显示统计信息
        if args.stats:
            get_database_statistics(engine, db_type)
            return
        
        # 分析问题
        issues = analyze_foreign_key_issues(engine, db_type)
        
        if args.verify:
            # 仅验证模式
            verify_fix(engine, db_type)
            return
        
        if not issues:
            print("✅ 数据库状态良好，无需修复")
            return
        
        # 创建备份提醒
        if not args.force and db_type == 'mysql':
            print("📦 建议在修复前创建备份:")
            print("   mysqldump -u root -p ai_doc_test > backup_foreign_key_fix.sql")
            input("   请手动执行备份后按回车继续... ")
        
        # 执行修复
        if fix_foreign_key_issues(engine, db_type, issues):
            # 验证修复结果
            verify_fix(engine, db_type)
            
            # 显示最终统计
            print("\n" + "="*50)
            get_database_statistics(engine, db_type)
        else:
            print("❌ 修复失败")
            sys.exit(1)
            
    except Exception as e:
        print(f"💥 脚本执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()