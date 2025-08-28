#!/usr/bin/env python3
"""
为issues表添加反馈操作人字段的数据库迁移脚本
"""
import sqlite3
import sys
import os

def add_feedback_user_fields():
    """为issues表添加反馈操作人相关字段"""
    db_path = './data/app.db'
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return False
    
    print("🔧 开始为issues表添加反馈操作人字段...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
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
            print("✅ 字段已存在，无需添加")
            return True
        
        # 添加字段
        for field_name, field_type, description in fields_to_add:
            alter_sql = f'ALTER TABLE issues ADD COLUMN {field_name} {field_type}'
            cursor.execute(alter_sql)
            print(f"  ✅ 添加字段: {field_name} {field_type} - {description}")
        
        # 添加索引
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_issues_feedback_user ON issues(feedback_user_id)')
            print("  ✅ 添加反馈用户索引")
        except:
            print("  ⚠️ 反馈用户索引可能已存在")
        
        conn.commit()
        
        # 验证字段添加结果
        print("\n📋 验证字段添加结果...")
        cursor.execute("PRAGMA table_info(issues)")
        columns = cursor.fetchall()
        
        print("Issues表当前结构:")
        for col in columns:
            field_desc = ""
            if col[1] in ['feedback_user_id', 'feedback_user_name', 'feedback_updated_at']:
                field_desc = " [新增]"
            print(f"  - {col[1]} {col[2]}{field_desc}")
        
        print(f"\n🎉 字段添加完成！")
        return True
        
    except Exception as e:
        print(f"❌ 添加字段失败: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    success = add_feedback_user_fields()
    sys.exit(0 if success else 1)