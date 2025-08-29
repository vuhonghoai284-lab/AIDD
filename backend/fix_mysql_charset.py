"""
修复MySQL表字符集，确保支持中文字符
"""
import pymysql
from app.core.config import get_settings
import re

def fix_mysql_charset():
    """修复MySQL表和字段的字符集"""
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
            print("🔍 检查当前字符集状态...")
            
            # 检查数据库字符集
            cursor.execute('SELECT @@character_set_database, @@collation_database')
            db_charset = cursor.fetchone()
            print(f"数据库字符集: {db_charset}")
            
            # 检查ai_models表字符集
            cursor.execute("""
                SELECT TABLE_COLLATION 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'ai_models'
            """, (database,))
            table_collation = cursor.fetchone()
            print(f"ai_models表字符集: {table_collation}")
            
            # 检查label字段字符集
            cursor.execute("""
                SELECT CHARACTER_SET_NAME, COLLATION_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'ai_models' AND COLUMN_NAME = 'label'
            """, (database,))
            column_charset = cursor.fetchone()
            print(f"label字段字符集: {column_charset}")
            
            # 如果字符集不是utf8mb4，则修复
            if table_collation and not table_collation[0].startswith('utf8mb4'):
                print("🔧 修复ai_models表字符集...")
                
                # 修改表字符集
                cursor.execute("ALTER TABLE ai_models CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                print("✅ ai_models表字符集已修改为utf8mb4")
            
            # 确保label字段使用正确的字符集
            if column_charset and column_charset[0] != 'utf8mb4':
                print("🔧 修复label字段字符集...")
                cursor.execute("ALTER TABLE ai_models MODIFY COLUMN label VARCHAR(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL")
                print("✅ label字段字符集已修改为utf8mb4")
            
            # 同样修复description字段
            cursor.execute("""
                SELECT CHARACTER_SET_NAME, COLLATION_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'ai_models' AND COLUMN_NAME = 'description'
            """, (database,))
            desc_charset = cursor.fetchone()
            
            if desc_charset and desc_charset[0] != 'utf8mb4':
                print("🔧 修复description字段字符集...")
                cursor.execute("ALTER TABLE ai_models MODIFY COLUMN description TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                print("✅ description字段字符集已修改为utf8mb4")
            
            connection.commit()
            print("✅ 所有修复操作已提交")
            
            # 再次检查修复后的状态
            print("\n🔍 验证修复结果...")
            cursor.execute("""
                SELECT COLUMN_NAME, CHARACTER_SET_NAME, COLLATION_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'ai_models' 
                AND COLUMN_NAME IN ('label', 'description')
            """, (database,))
            
            results = cursor.fetchall()
            for row in results:
                print(f"{row[0]}字段: {row[1]} / {row[2]}")
        
        connection.close()
        print("✅ 字符集修复完成")
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")

if __name__ == "__main__":
    fix_mysql_charset()