"""
全面修复所有MySQL表的字符集，确保支持中文字符
"""
import pymysql
from app.core.config import get_settings
import re

def fix_all_tables_charset():
    """修复所有表的字符集"""
    settings = get_settings()
    
    # 从URL解析连接信息，去掉charset参数
    url_pattern = r'mysql\+pymysql://(.+):(.+)@(.+):(\d+)/(.+?)(?:\?.*)?$'
    match = re.match(url_pattern, settings.database_url)
    if not match:
        print("❌ 无法解析数据库URL")
        return
        
    username, password, host, port, database = match.groups()
    
    try:
        connection = pymysql.connect(
            host=host,
            port=int(port),
            user=username,
            password=password,
            database=database,
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            print("🔍 检查所有表的字符集状态...")
            
            # 获取所有表名
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
            print(f"找到 {len(tables)} 个表: {', '.join(tables)}")
            
            for table_name in tables:
                print(f"\n📋 处理表: {table_name}")
                
                # 检查表字符集
                cursor.execute(f"""
                    SELECT TABLE_COLLATION 
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                """, (database, table_name))
                table_collation = cursor.fetchone()
                
                if table_collation:
                    print(f"  当前表字符集: {table_collation[0]}")
                    
                    # 如果不是utf8mb4，修改表字符集
                    if not table_collation[0].startswith('utf8mb4'):
                        print(f"  🔧 修复表 {table_name} 字符集...")
                        cursor.execute(f"ALTER TABLE `{table_name}` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                        print(f"  ✅ 表 {table_name} 字符集已修改为utf8mb4")
                
                # 检查所有文本字段
                cursor.execute(f"""
                    SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_SET_NAME, COLLATION_NAME, IS_NULLABLE, COLUMN_DEFAULT
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s 
                    AND DATA_TYPE IN ('varchar', 'char', 'text', 'tinytext', 'mediumtext', 'longtext')
                """, (database, table_name))
                
                columns = cursor.fetchall()
                
                if columns:
                    print(f"  找到 {len(columns)} 个文本字段需要检查")
                    
                    for col in columns:
                        column_name, data_type, charset, collation, is_nullable, default = col
                        
                        if charset and charset != 'utf8mb4':
                            print(f"    🔧 修复字段 {column_name} ({data_type})")
                            
                            # 构建字段定义
                            nullable_clause = "NULL" if is_nullable == "YES" else "NOT NULL"
                            default_clause = f"DEFAULT '{default}'" if default and default != 'NULL' else ""
                            
                            # 根据字段类型构建ALTER语句
                            if data_type in ['varchar', 'char']:
                                # 获取字段长度
                                cursor.execute(f"""
                                    SELECT CHARACTER_MAXIMUM_LENGTH 
                                    FROM INFORMATION_SCHEMA.COLUMNS 
                                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
                                """, (database, table_name, column_name))
                                length = cursor.fetchone()[0]
                                
                                alter_sql = f"""
                                    ALTER TABLE `{table_name}` 
                                    MODIFY COLUMN `{column_name}` {data_type.upper()}({length}) 
                                    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci 
                                    {nullable_clause} {default_clause}
                                """.strip()
                                
                            else:  # text类型
                                alter_sql = f"""
                                    ALTER TABLE `{table_name}` 
                                    MODIFY COLUMN `{column_name}` {data_type.upper()} 
                                    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci 
                                    {nullable_clause}
                                """.strip()
                            
                            try:
                                cursor.execute(alter_sql)
                                print(f"    ✅ 字段 {column_name} 字符集已修改")
                            except Exception as e:
                                print(f"    ⚠️ 字段 {column_name} 修改失败: {e}")
                        else:
                            print(f"    ✅ 字段 {column_name} 字符集正确 ({charset})")
                
                # 提交当前表的修改
                connection.commit()
            
            print("\n🔍 最终验证所有表的字符集...")
            
            for table_name in tables:
                # 检查修复后的状态
                cursor.execute(f"""
                    SELECT COLUMN_NAME, CHARACTER_SET_NAME, COLLATION_NAME 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s 
                    AND DATA_TYPE IN ('varchar', 'char', 'text', 'tinytext', 'mediumtext', 'longtext')
                    AND CHARACTER_SET_NAME != 'utf8mb4'
                """, (database, table_name))
                
                remaining_issues = cursor.fetchall()
                if remaining_issues:
                    print(f"⚠️ 表 {table_name} 仍有字段未修复:")
                    for issue in remaining_issues:
                        print(f"  - {issue[0]}: {issue[1]} / {issue[2]}")
                else:
                    print(f"✅ 表 {table_name} 所有字段字符集正确")
        
        connection.close()
        print("\n✅ 全部表字符集修复完成")
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_all_tables_charset()