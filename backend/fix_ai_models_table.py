#!/usr/bin/env python3
"""
快速修复ai_models表缺失问题
适用于生产环境紧急修复
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def fix_ai_models_table():
    """修复ai_models表问题"""
    try:
        # 设置生产环境配置
        os.environ['CONFIG_FILE'] = 'config.prod.yaml'
        
        from app.core.config import init_settings
        from sqlalchemy import create_engine, text
        
        print("🔧 连接生产数据库...")
        settings = init_settings('config.prod.yaml')
        engine = create_engine(settings.database_url)
        
        with engine.connect() as conn:
            # 检查ai_models表是否存在
            result = conn.execute(text("SHOW TABLES LIKE 'ai_models'"))
            table_exists = result.fetchone() is not None
            
            if table_exists:
                print("✅ ai_models表已存在")
                # 检查表结构
                result = conn.execute(text("DESCRIBE ai_models"))
                columns = [row[0] for row in result]
                print(f"现有字段: {columns}")
                
                # 检查关键字段
                required_fields = ['model_key', 'label', 'provider', 'model_name']
                missing_fields = [f for f in required_fields if f not in columns]
                
                if missing_fields:
                    print(f"❌ 缺少关键字段: {missing_fields}")
                    print("需要执行架构迁移修复")
                else:
                    print("✅ ai_models表结构正确")
                    return True
            else:
                print("❌ ai_models表不存在，开始创建...")
                
                # 直接创建ai_models表
                create_ai_models_sql = """
                CREATE TABLE ai_models (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    model_key VARCHAR(100) NOT NULL UNIQUE,
                    label VARCHAR(200) NOT NULL,
                    provider VARCHAR(50) NOT NULL,
                    model_name VARCHAR(100) NOT NULL,
                    description TEXT,
                    temperature FLOAT DEFAULT 0.3,
                    max_tokens INT DEFAULT 8000,
                    context_window INT DEFAULT 128000,
                    reserved_tokens INT DEFAULT 2000,
                    timeout INT DEFAULT 12000,
                    max_retries INT DEFAULT 3,
                    base_url VARCHAR(500),
                    api_key_env VARCHAR(100),
                    is_active BOOLEAN DEFAULT TRUE,
                    is_default BOOLEAN DEFAULT FALSE,
                    sort_order INT DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX ix_ai_models_model_key (model_key)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
                
                conn.execute(text(create_ai_models_sql))
                conn.commit()
                print("✅ ai_models表创建成功")
            
            # 初始化AI模型数据
            print("\n🤖 初始化AI模型配置...")
            from app.core.database import get_db
            from app.services.model_initializer import model_initializer
            
            db = next(get_db())
            try:
                models = model_initializer.initialize_models(db)
                print(f"✅ AI模型初始化成功: {len(models)} 个模型")
                return True
            finally:
                db.close()
                
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚨 ai_models表快速修复工具")
    print("适用于生产环境紧急修复\n")
    
    success = fix_ai_models_table()
    
    if success:
        print("\n🎉 修复完成！现在可以正常启动应用")
    else:
        print("\n💔 修复失败，请检查错误信息")
        print("💡 可能需要手动创建数据库或检查权限")