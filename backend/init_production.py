#!/usr/bin/env python3
"""
生产环境初始化脚本
解决ai_models表缺失问题的完整方案
"""
import os
import sys
from dotenv import load_dotenv

# 确保加载.env文件
load_dotenv()

def init_production_database():
    """初始化生产环境数据库"""
    print("🚀 生产环境数据库初始化开始...")
    
    try:
        # 1. 设置配置文件环境变量
        os.environ['CONFIG_FILE'] = 'config.prod.yaml'
        
        # 2. 尝试Alembic迁移
        print("\n📋 执行Alembic数据库迁移...")
        try:
            from app.core.alembic_manager import AlembicManager
            
            manager = AlembicManager('config.prod.yaml')
            manager.upgrade("head")
            print("✅ Alembic迁移成功")
            
        except Exception as alembic_error:
            print(f"❌ Alembic迁移失败: {alembic_error}")
            
            # 3. 降级到SQLAlchemy创建表
            print("\n🔄 使用SQLAlchemy降级创建表...")
            from app.core.config import init_settings
            from app.core.database import Base
            from sqlalchemy import create_engine
            
            # 导入所有模型确保表定义完整
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
        
        # 4. 验证表创建结果
        print("\n🔍 验证数据库表...")
        from app.core.config import init_settings
        from sqlalchemy import create_engine, inspect
        
        settings = init_settings('config.prod.yaml')
        engine = create_engine(settings.database_url)
        inspector = inspect(engine)
        
        tables = inspector.get_table_names()
        print(f"现有表: {tables}")
        
        # 检查关键表
        required_tables = ['users', 'ai_models', 'tasks', 'file_infos']
        missing_tables = [t for t in required_tables if t not in tables]
        
        if missing_tables:
            print(f"❌ 缺少关键表: {missing_tables}")
            return False
        
        # 验证ai_models表结构
        if 'ai_models' in tables:
            columns = inspector.get_columns('ai_models')
            column_names = [col['name'] for col in columns]
            required_columns = ['model_key', 'label', 'provider', 'model_name']
            missing_columns = [c for c in required_columns if c not in column_names]
            
            if missing_columns:
                print(f"❌ ai_models表缺少字段: {missing_columns}")
                return False
            
            print("✅ ai_models表结构验证通过")
            print(f"字段: {column_names}")
        
        # 5. 初始化AI模型数据
        print("\n🤖 初始化AI模型配置...")
        from app.core.database import get_db
        from app.services.model_initializer import model_initializer
        
        db = next(get_db())
        try:
            models = model_initializer.initialize_models(db)
            print(f"✅ AI模型初始化成功: {len(models)} 个模型")
        finally:
            db.close()
        
        print("\n🎉 生产环境数据库初始化完成！")
        return True
        
    except Exception as e:
        print(f"❌ 生产环境初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_usage():
    """显示使用说明"""
    print("""
🔧 生产环境部署说明:

1. 设置环境变量:
   export MYSQL_HOST=your-db-host
   export MYSQL_USERNAME=your-db-user
   export MYSQL_PASSWORD=your-db-password
   export JWT_SECRET_KEY=your-secret-key

2. 或创建.env文件:
   cp .env.production.example .env
   # 编辑.env文件填入真实值

3. 运行初始化:
   python init_production.py

4. 启动应用:
   CONFIG_FILE=config.prod.yaml python app/main.py
""")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        show_usage()
        sys.exit(0)
    
    success = init_production_database()
    if not success:
        print("\n💡 如需帮助，运行: python init_production.py --help")
        sys.exit(1)