#!/usr/bin/env python3
"""
生产环境检查脚本 - 诊断ai_models表问题
"""
import os
import sys
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

def check_env_vars():
    """检查环境变量"""
    print("=== 环境变量检查 ===")
    
    required_vars = {
        'MYSQL_HOST': os.getenv('MYSQL_HOST'),
        'MYSQL_USERNAME': os.getenv('MYSQL_USERNAME'), 
        'MYSQL_PASSWORD': os.getenv('MYSQL_PASSWORD'),
        'MYSQL_DATABASE': os.getenv('MYSQL_DATABASE'),
        'JWT_SECRET_KEY': os.getenv('JWT_SECRET_KEY')
    }
    
    for var, value in required_vars.items():
        if value:
            print(f"✅ {var}: {'*' * len(value[:5])}...")
        else:
            print(f"❌ {var}: 未设置")
    
    return all(required_vars.values())

def test_database_connection():
    """测试数据库连接"""
    print("\n=== 数据库连接测试 ===")
    
    try:
        from app.core.config import init_settings
        from sqlalchemy import create_engine, text
        
        settings = init_settings('config.prod.yaml')
        print(f"数据库URL: {settings.database_url}")
        
        engine = create_engine(settings.database_url)
        
        with engine.connect() as conn:
            # 测试基本连接
            result = conn.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1
            print("✅ 数据库连接成功")
            
            # 检查数据库和表
            result = conn.execute(text("SHOW DATABASES"))
            databases = [row[0] for row in result]
            print(f"可用数据库: {databases}")
            
            # 检查当前数据库的表
            result = conn.execute(text("SHOW TABLES"))
            tables = [row[0] for row in result]
            print(f"现有表: {tables}")
            
            if 'ai_models' in tables:
                print("✅ ai_models表存在")
                # 检查表结构
                result = conn.execute(text("DESCRIBE ai_models"))
                columns = [row[0] for row in result]
                print(f"ai_models字段: {columns}")
            else:
                print("❌ ai_models表不存在")
                
        return True, engine
        
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False, None

def test_alembic():
    """测试Alembic迁移"""
    print("\n=== Alembic迁移测试 ===")
    
    try:
        from app.core.alembic_manager import AlembicManager
        
        manager = AlembicManager('config.prod.yaml')
        
        # 检查迁移历史
        history = manager.get_migration_history()
        print(f"迁移文件数量: {len(history)}")
        
        for item in history:
            print(f"  - {item['revision']}: {item['message']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Alembic测试失败: {e}")
        return False

def main():
    """主检查函数"""
    print("🔍 生产环境问题诊断\n")
    
    # 1. 环境变量检查
    env_ok = check_env_vars()
    
    # 2. 数据库连接测试
    db_ok, engine = test_database_connection()
    
    # 3. Alembic测试
    alembic_ok = test_alembic()
    
    print(f"\n=== 诊断结果 ===")
    print(f"环境变量: {'✅' if env_ok else '❌'}")
    print(f"数据库连接: {'✅' if db_ok else '❌'}")
    print(f"Alembic迁移: {'✅' if alembic_ok else '❌'}")
    
    if not env_ok:
        print("\n💡 解决方案:")
        print("1. 创建.env文件并设置数据库连接信息")
        print("2. 参考.env.production.example模板")
    
    if not db_ok:
        print("\n💡 解决方案:")
        print("1. 检查MySQL服务是否运行")
        print("2. 验证数据库用户权限")
        print("3. 确认网络连接正常")
    
    if not alembic_ok:
        print("\n💡 解决方案:")
        print("1. 手动执行: CONFIG_FILE=config.prod.yaml alembic upgrade head")
        print("2. 或使用SQLAlchemy降级: python deploy_production.py")

if __name__ == "__main__":
    main()