#!/usr/bin/env python3
"""
MySQL生产环境兼容性检查和修复脚本
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def check_task_queue_table():
    """检查task_queue表是否存在，不存在则创建"""
    print("\n=== 任务队列表检查 ===")
    
    try:
        from app.core.database import engine
        from app.models.task_queue import Base, TaskQueue
        from sqlalchemy import text
        
        # 检查表是否存在
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'task_queue'
            """))
            
            table_exists = result.scalar() > 0
            
        if table_exists:
            print("✅ task_queue表已存在")
            
            # 检查表结构
            with engine.connect() as conn:
                columns_result = conn.execute(text("""
                    SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
                    FROM information_schema.COLUMNS 
                    WHERE table_schema = DATABASE() 
                    AND table_name = 'task_queue'
                    ORDER BY ORDINAL_POSITION
                """))
                
                columns = columns_result.fetchall()
                print("📊 task_queue表结构:")
                for col in columns:
                    print(f"   {col[0]} ({col[1]}) {'NULL' if col[2] == 'YES' else 'NOT NULL'}")
                    
            return True
        else:
            print("❌ task_queue表不存在，正在创建...")
            
            # 创建表
            Base.metadata.create_all(bind=engine, tables=[TaskQueue.__table__])
            print("✅ task_queue表创建成功")
            return True
            
    except Exception as e:
        print(f"❌ task_queue表检查失败: {e}")
        return False

def check_queue_config_table():
    """检查queue_config表"""
    print("\n=== 队列配置表检查 ===")
    
    try:
        from app.core.database import engine
        from app.models.task_queue import QueueConfig
        from sqlalchemy import text
        
        # 检查表是否存在
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'queue_config'
            """))
            
            table_exists = result.scalar() > 0
            
        if table_exists:
            print("✅ queue_config表已存在")
        else:
            print("❌ queue_config表不存在，正在创建...")
            from app.models.task_queue import Base
            Base.metadata.create_all(bind=engine, tables=[QueueConfig.__table__])
            print("✅ queue_config表创建成功")
        
        return True
        
    except Exception as e:
        print(f"❌ queue_config表检查失败: {e}")
        return False

def init_queue_config():
    """初始化队列配置数据"""
    print("\n=== 队列配置初始化 ===")
    
    try:
        from app.core.database import SessionLocal
        from app.models.task_queue import QueueConfig
        
        db = SessionLocal()
        try:
            # 检查是否已有配置
            existing_configs = db.query(QueueConfig).all()
            
            # 定义默认配置
            default_configs = [
                ("system_max_concurrent_tasks", "60", "系统最大并发任务数（20用户×3并发）"),
                ("user_max_concurrent_tasks", "3", "用户默认最大并发任务数"),
                ("admin_max_concurrent_tasks", "10", "管理员最大并发任务数"),
                ("task_timeout_seconds", "1800", "任务超时时间（秒）"),
                ("enable_priority_scheduling", "true", "启用优先级调度"),
                ("enable_user_concurrency_limit", "true", "启用用户并发限制"),
                ("enable_system_concurrency_limit", "true", "启用系统并发限制")
            ]
            
            if existing_configs:
                print("✅ 队列配置已存在:")
                for config in existing_configs:
                    print(f"   {config.config_key}: {config.config_value}")
            else:
                print("🔧 创建默认队列配置...")
                
                for key, value, description in default_configs:
                    config = QueueConfig(
                        config_key=key,
                        config_value=value,
                        description=description
                    )
                    db.add(config)
                
                db.commit()
                print("✅ 默认队列配置创建成功")
                
                # 显示创建的配置
                for key, value, description in default_configs:
                    print(f"   {key}: {value}")
            
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ 队列配置初始化失败: {e}")
        return False

def check_foreign_key_constraints():
    """检查外键约束"""
    print("\n=== 外键约束检查 ===")
    
    try:
        from app.core.database import engine
        from sqlalchemy import text
        
        with engine.connect() as conn:
            # 检查task_queue表的外键
            fk_result = conn.execute(text("""
                SELECT 
                    CONSTRAINT_NAME, 
                    COLUMN_NAME,
                    REFERENCED_TABLE_NAME,
                    REFERENCED_COLUMN_NAME
                FROM information_schema.KEY_COLUMN_USAGE 
                WHERE table_schema = DATABASE() 
                AND table_name = 'task_queue'
                AND REFERENCED_TABLE_NAME IS NOT NULL
            """))
            
            foreign_keys = fk_result.fetchall()
            
            if foreign_keys:
                print("✅ 外键约束检查:")
                for fk in foreign_keys:
                    print(f"   {fk[1]} -> {fk[2]}.{fk[3]}")
            else:
                print("⚠️ 未找到外键约束（可能是表刚创建）")
                
            return True
            
    except Exception as e:
        print(f"❌ 外键约束检查失败: {e}")
        return False

def fix_mysql_timezone():
    """修复MySQL时区问题"""
    print("\n=== MySQL时区修复 ===")
    
    try:
        from app.core.database import engine
        from sqlalchemy import text
        
        with engine.connect() as conn:
            # 检查当前时区设置
            tz_result = conn.execute(text("SELECT @@time_zone, @@system_time_zone"))
            time_zone, system_tz = tz_result.fetchone()
            print(f"⏰ MySQL时区: {time_zone}, 系统时区: {system_tz}")
            
            # 设置会话时区为UTC（可选）
            conn.execute(text("SET time_zone = '+00:00'"))
            print("✅ 已设置MySQL时区为UTC")
            
            return True
            
    except Exception as e:
        print(f"❌ MySQL时区修复失败: {e}")
        return False

def main():
    """主修复流程"""
    print("🔧 开始MySQL生产环境兼容性检查和修复...")
    
    # 设置必要的环境变量（临时）
    if not os.environ.get('JWT_SECRET_KEY'):
        os.environ['JWT_SECRET_KEY'] = 'production_jwt_secret_key_change_me_123456789'
        print("⚠️ 临时设置JWT_SECRET_KEY，生产环境请使用安全密钥")
    
    if not os.environ.get('MYSQL_PASSWORD'):
        os.environ['MYSQL_PASSWORD'] = 'ai_docs_password'
        print("⚠️ 临时设置MYSQL_PASSWORD，生产环境请使用实际密码")
    
    fixes = [
        ("任务队列表", check_task_queue_table),
        ("队列配置表", check_queue_config_table),  
        ("队列配置初始化", init_queue_config),
        ("外键约束", check_foreign_key_constraints),
        ("MySQL时区", fix_mysql_timezone)
    ]
    
    results = {}
    for name, fix_func in fixes:
        try:
            results[name] = fix_func()
        except Exception as e:
            print(f"❌ {name}修复异常: {e}")
            results[name] = False
    
    print("\n" + "="*50)
    print("📋 修复结果总览:")
    print("="*50)
    
    all_fixed = True
    for name, fixed in results.items():
        status = "✅ 成功" if fixed else "❌ 失败"
        print(f"{status} {name}")
        if not fixed:
            all_fixed = False
    
    if all_fixed:
        print("\n🎉 MySQL兼容性修复完成！")
        print("💡 生产环境部署建议:")
        print("   1. 设置 JWT_SECRET_KEY 环境变量")
        print("   2. 设置正确的MySQL连接信息")
        print("   3. 确保MySQL用户有足够权限")
        print("   4. 考虑启用SSL连接")
    else:
        print("\n⚠️ 发现修复失败的项目，请手动检查")
        
    return 0 if all_fixed else 1

if __name__ == "__main__":
    exit(main())