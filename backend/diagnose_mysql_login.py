#!/usr/bin/env python3
"""
MySQL登录问题诊断脚本
"""
import os
import sys
import pymysql
from sqlalchemy import create_engine, text


def test_mysql_connection():
    """测试MySQL连接的各种配置"""
    
    # 测试配置
    configs = [
        {
            'desc': '默认配置（可能的问题）',
            'host': 'localhost',
            'port': 3306,
            'user': 'root',
            'password': '123456',
            'database': 'ai_doc_test',
            'charset': 'utf8mb4'
        },
        {
            'desc': '使用127.0.0.1替代localhost',
            'host': '127.0.0.1', 
            'port': 3306,
            'user': 'root',
            'password': '123456',
            'database': 'ai_doc_test',
            'charset': 'utf8mb4'
        },
        {
            'desc': '不指定数据库',
            'host': 'localhost',
            'port': 3306, 
            'user': 'root',
            'password': '123456',
            'database': None,
            'charset': 'utf8mb4'
        }
    ]
    
    print("=== MySQL连接诊断 ===\n")
    
    for i, config in enumerate(configs, 1):
        print(f"{i}. 测试: {config['desc']}")
        print(f"   配置: {config['user']}@{config['host']}:{config['port']}")
        
        # 测试基础pymysql连接
        try:
            if config['database']:
                conn = pymysql.connect(
                    host=config['host'],
                    port=config['port'],
                    user=config['user'],
                    password=config['password'],
                    database=config['database'],
                    charset=config['charset']
                )
            else:
                conn = pymysql.connect(
                    host=config['host'],
                    port=config['port'],
                    user=config['user'],
                    password=config['password'],
                    charset=config['charset']
                )
            
            with conn.cursor() as cursor:
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()[0]
                print(f"   ✅ PyMySQL连接成功，MySQL版本: {version}")
                
                # 检查数据库是否存在
                if config['database']:
                    cursor.execute("SELECT DATABASE()")
                    current_db = cursor.fetchone()[0]
                    print(f"   ✅ 当前数据库: {current_db}")
                else:
                    cursor.execute("SHOW DATABASES")
                    databases = [row[0] for row in cursor.fetchall()]
                    print(f"   📋 可用数据库: {databases}")
                    
                    # 检查目标数据库是否存在
                    if 'ai_doc_test' in databases:
                        print("   ✅ ai_doc_test数据库存在")
                    else:
                        print("   ⚠️  ai_doc_test数据库不存在，需要创建")
            
            conn.close()
            
        except Exception as e:
            print(f"   ❌ PyMySQL连接失败: {e}")
        
        # 测试SQLAlchemy连接
        try:
            if config['database']:
                url = f"mysql+pymysql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}?charset={config['charset']}"
            else:
                url = f"mysql+pymysql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/?charset={config['charset']}"
                
            engine = create_engine(url)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                print(f"   ✅ SQLAlchemy连接成功")
            engine.dispose()
            
        except Exception as e:
            print(f"   ❌ SQLAlchemy连接失败: {e}")
        
        print()


def check_mysql_user_permissions():
    """检查MySQL用户权限"""
    print("=== MySQL用户权限检查 ===\n")
    
    try:
        conn = pymysql.connect(
            host='localhost',
            port=3306,
            user='root',
            password='123456',
            charset='utf8mb4'
        )
        
        with conn.cursor() as cursor:
            # 检查当前用户
            cursor.execute("SELECT USER(), CURRENT_USER()")
            user_info = cursor.fetchone()
            print(f"当前用户: {user_info[0]}")
            print(f"认证用户: {user_info[1]}")
            
            # 检查用户权限
            cursor.execute("SHOW GRANTS FOR CURRENT_USER()")
            grants = cursor.fetchall()
            print("\n用户权限:")
            for grant in grants:
                print(f"  - {grant[0]}")
                
            # 检查MySQL认证插件
            cursor.execute("""
                SELECT user, host, plugin, authentication_string 
                FROM mysql.user 
                WHERE user = 'root'
            """)
            auth_info = cursor.fetchall()
            print("\nroot用户认证信息:")
            for info in auth_info:
                print(f"  用户: {info[0]}@{info[1]}, 插件: {info[2]}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 权限检查失败: {e}")


def suggest_solutions():
    """提供解决方案建议"""
    print("=== 解决方案建议 ===\n")
    
    print("1. MySQL 8.0认证问题解决:")
    print("   -- 如果使用MySQL 8.0，可能需要修改认证方式")
    print("   -- 连接到MySQL并执行:")
    print("   ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '123456';")
    print("   FLUSH PRIVILEGES;")
    print()
    
    print("2. 创建专用数据库用户:")
    print("   CREATE USER 'aidd_user'@'localhost' IDENTIFIED BY 'aidd_password';")
    print("   GRANT ALL PRIVILEGES ON ai_doc_test.* TO 'aidd_user'@'localhost';")
    print("   FLUSH PRIVILEGES;")
    print()
    
    print("3. 创建数据库（如果不存在）:")
    print("   CREATE DATABASE IF NOT EXISTS ai_doc_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    print()
    
    print("4. 环境变量设置示例:")
    print("   export DATABASE_TYPE=mysql")
    print("   export MYSQL_HOST=localhost")
    print("   export MYSQL_USERNAME=aidd_user")  
    print("   export MYSQL_PASSWORD=aidd_password")
    print("   export MYSQL_DATABASE=ai_doc_test")
    print()
    
    print("5. 启动应用:")
    print("   DATABASE_TYPE=mysql MYSQL_HOST=localhost MYSQL_USERNAME=aidd_user MYSQL_PASSWORD=aidd_password MYSQL_DATABASE=ai_doc_test python app/main.py")


if __name__ == "__main__":
    test_mysql_connection()
    check_mysql_user_permissions() 
    suggest_solutions()