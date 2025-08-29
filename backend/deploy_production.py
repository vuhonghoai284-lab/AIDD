#!/usr/bin/env python3
"""
生产环境部署脚本
确保数据库正确初始化和表创建
"""
import os
import sys
from pathlib import Path
import traceback

def check_environment():
    """检查生产环境变量"""
    required_vars = [
        'MYSQL_HOST',
        'MYSQL_USERNAME', 
        'MYSQL_PASSWORD',
        'JWT_SECRET_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ 缺少必需的环境变量: {', '.join(missing_vars)}")
        return False
    
    print("✅ 环境变量检查通过")
    return True

def test_database_connection():
    """测试数据库连接"""
    try:
        from app.core.config import init_settings
        from sqlalchemy import create_engine, text
        
        # 使用生产配置
        settings = init_settings('config.prod.yaml')
        engine = create_engine(settings.database_url)
        
        # 测试连接和基本操作
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1
        
        print("✅ 数据库连接测试成功")
        return True, engine
        
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False, None

def deploy_database():
    """部署数据库架构"""
    try:
        # 1. 尝试Alembic迁移
        print("\n🚀 开始数据库部署...")
        
        from app.core.alembic_manager import AlembicManager
        manager = AlembicManager('config.prod.yaml')
        
        print("📋 执行Alembic迁移...")
        manager.upgrade("head")
        print("✅ Alembic迁移成功")
        
        return True
        
    except Exception as alembic_error:
        print(f"❌ Alembic迁移失败: {alembic_error}")
        
        # 2. 降级到SQLAlchemy创建表
        print("\n🔄 使用SQLAlchemy降级方案...")
        try:
            from app.core.config import init_settings
            from app.core.database import Base
            from sqlalchemy import create_engine
            
            # 导入所有模型
            from app.models.user import User
            from app.models.ai_model import AIModel
            from app.models.file_info import FileInfo
            from app.models.task import Task
            from app.models.task_queue import TaskQueue, QueueConfig
            from app.models.task_share import TaskShare
            from app.models.issue import Issue
            from app.models.ai_output import AIOutput
            from app.models.task_log import TaskLog
            
            settings = init_settings('config.prod.yaml')
            engine = create_engine(settings.database_url)
            
            # 创建所有表
            Base.metadata.create_all(bind=engine)
            print("✅ SQLAlchemy表创建成功")
            
            return True
            
        except Exception as fallback_error:
            print(f"❌ SQLAlchemy表创建失败: {fallback_error}")
            return False

def verify_tables():
    """验证表创建结果"""
    try:
        from app.core.config import init_settings
        from sqlalchemy import create_engine, inspect
        
        settings = init_settings('config.prod.yaml')
        engine = create_engine(settings.database_url)
        inspector = inspect(engine)
        
        # 检查关键表
        required_tables = ['users', 'ai_models', 'tasks', 'file_infos']
        existing_tables = inspector.get_table_names()
        
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        if missing_tables:
            print(f"❌ 缺少表: {missing_tables}")
            return False
        
        # 检查ai_models表结构
        ai_models_columns = inspector.get_columns('ai_models')
        required_columns = ['model_key', 'label', 'provider', 'model_name']
        existing_columns = [col['name'] for col in ai_models_columns]
        
        missing_columns = [col for col in required_columns if col not in existing_columns]
        if missing_columns:
            print(f"❌ ai_models表缺少字段: {missing_columns}")
            return False
        
        print("✅ 数据库表结构验证通过")
        print(f"📊 现有表: {existing_tables}")
        
        return True
        
    except Exception as e:
        print(f"❌ 表验证失败: {e}")
        return False

def initialize_ai_models():
    """初始化AI模型配置"""
    try:
        from app.core.database import get_db
        from app.services.model_initializer import model_initializer
        
        print("\n🤖 初始化AI模型配置...")
        db = next(get_db())
        try:
            models = model_initializer.initialize_models(db)
            print(f"✅ AI模型初始化成功: {len(models)} 个模型")
            return True
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ AI模型初始化失败: {e}")
        return False

def main():
    """生产环境部署主函数"""
    print("🚀 生产环境部署开始...")
    
    # 1. 检查环境变量
    # if not check_environment():
    #     print("💡 请设置必需的环境变量后重试")
    #     sys.exit(1)
    
    # 2. 测试数据库连接
    conn_success, engine = test_database_connection()
    if not conn_success:
        print("💡 请检查数据库配置和网络连接")
        sys.exit(1)
    
    # 3. 部署数据库架构
    if not deploy_database():
        print("❌ 数据库部署失败")
        sys.exit(1)
    
    # 4. 验证表结构
    if not verify_tables():
        print("❌ 表结构验证失败")
        sys.exit(1)
    
    # 5. 初始化AI模型
    if not initialize_ai_models():
        print("❌ AI模型初始化失败")
        sys.exit(1)
    
    print("\n🎉 生产环境部署完成！")
    print("💡 现在可以启动应用: CONFIG_FILE=config.prod.yaml python app/main.py")

if __name__ == "__main__":
    main()