"""
数据库字符集自动修复服务
在应用启动时自动检查和修复MySQL表字符集问题
"""
import re
from typing import List, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.database import get_independent_db_session, close_independent_db_session


class DatabaseCharsetFixer:
    """数据库字符集修复器"""
    
    def __init__(self):
        self.settings = get_settings()
        self.is_mysql = self.settings.database_type == 'mysql'
    
    def fix_all_tables_charset(self) -> bool:
        """
        修复所有表的字符集问题
        
        Returns:
            bool: 是否成功修复
        """
        if not self.is_mysql:
            print("ℹ️ 非MySQL数据库，跳过字符集修复")
            return True
            
        print("🔍 开始检查和修复数据库表字符集...")
        
        db = get_independent_db_session()
        try:
            # 获取数据库名
            database_name = self._get_database_name()
            if not database_name:
                print("❌ 无法获取数据库名")
                return False
            
            # 获取所有表
            tables = self._get_all_tables(db, database_name)
            if not tables:
                print("ℹ️ 数据库中没有找到表")
                return True
            
            print(f"📋 找到 {len(tables)} 个表: {', '.join(tables)}")
            
            total_fixed = 0
            for table_name in tables:
                fixed_count = self._fix_table_charset(db, database_name, table_name)
                total_fixed += fixed_count
            
            if total_fixed > 0:
                print(f"✅ 完成字符集修复，共修复 {total_fixed} 个字段")
            else:
                print("✅ 所有表字符集正确，无需修复")
            
            return True
            
        except Exception as e:
            print(f"❌ 字符集修复失败: {e}")
            return False
        finally:
            close_independent_db_session(db, "字符集修复")
    
    def _get_database_name(self) -> str:
        """从数据库URL中提取数据库名"""
        url_pattern = r'mysql\+pymysql://[^/]+/([^?]+)'
        match = re.search(url_pattern, self.settings.database_url)
        return match.group(1) if match else ""
    
    def _get_all_tables(self, db: Session, database_name: str) -> List[str]:
        """获取所有表名"""
        try:
            result = db.execute(text("SHOW TABLES"))
            return [row[0] for row in result.fetchall()]
        except Exception as e:
            print(f"⚠️ 获取表名失败: {e}")
            return []
    
    def _fix_table_charset(self, db: Session, database_name: str, table_name: str) -> int:
        """
        修复单个表的字符集
        
        Returns:
            int: 修复的字段数量
        """
        fixed_count = 0
        
        try:
            # 检查表字符集
            table_collation = self._get_table_collation(db, database_name, table_name)
            if table_collation and not table_collation.startswith('utf8mb4'):
                print(f"🔧 修复表 {table_name} 字符集...")
                db.execute(text(f"ALTER TABLE `{table_name}` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                print(f"✅ 表 {table_name} 字符集已修改")
                db.commit()
            
            # 获取所有文本字段
            text_columns = self._get_text_columns(db, database_name, table_name)
            
            for column_info in text_columns:
                column_name, data_type, charset, collation, is_nullable, max_length = column_info
                
                if charset and charset != 'utf8mb4':
                    print(f"  🔧 修复字段 {table_name}.{column_name} ({data_type})")
                    
                    # 构建ALTER语句
                    alter_sql = self._build_alter_column_sql(
                        table_name, column_name, data_type, is_nullable, max_length
                    )
                    
                    try:
                        db.execute(text(alter_sql))
                        db.commit()
                        print(f"  ✅ 字段 {column_name} 字符集已修改")
                        fixed_count += 1
                    except Exception as e:
                        print(f"  ⚠️ 字段 {column_name} 修改失败: {e}")
                        db.rollback()
        
        except Exception as e:
            print(f"⚠️ 处理表 {table_name} 时出错: {e}")
            db.rollback()
        
        return fixed_count
    
    def _get_table_collation(self, db: Session, database_name: str, table_name: str) -> str:
        """获取表的字符集"""
        try:
            result = db.execute(text("""
                SELECT TABLE_COLLATION 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = :database AND TABLE_NAME = :table
            """), {"database": database_name, "table": table_name})
            
            row = result.fetchone()
            return row[0] if row else ""
        except:
            return ""
    
    def _get_text_columns(self, db: Session, database_name: str, table_name: str) -> List[Tuple]:
        """获取所有文本类型的字段信息"""
        try:
            result = db.execute(text("""
                SELECT 
                    COLUMN_NAME, 
                    DATA_TYPE, 
                    CHARACTER_SET_NAME, 
                    COLLATION_NAME, 
                    IS_NULLABLE,
                    CHARACTER_MAXIMUM_LENGTH
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = :database 
                AND TABLE_NAME = :table 
                AND DATA_TYPE IN ('varchar', 'char', 'text', 'tinytext', 'mediumtext', 'longtext')
            """), {"database": database_name, "table": table_name})
            
            return result.fetchall()
        except:
            return []
    
    def _build_alter_column_sql(self, table_name: str, column_name: str, 
                               data_type: str, is_nullable: str, max_length: int) -> str:
        """构建修改字段的SQL语句"""
        nullable_clause = "NULL" if is_nullable == "YES" else "NOT NULL"
        
        if data_type in ['varchar', 'char'] and max_length:
            type_def = f"{data_type.upper()}({max_length})"
        else:
            type_def = data_type.upper()
        
        return f"""
            ALTER TABLE `{table_name}` 
            MODIFY COLUMN `{column_name}` {type_def}
            CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci 
            {nullable_clause}
        """.strip()


# 全局修复器实例
charset_fixer = DatabaseCharsetFixer()


def fix_database_charset() -> bool:
    """修复数据库字符集的全局函数"""
    return charset_fixer.fix_all_tables_charset()