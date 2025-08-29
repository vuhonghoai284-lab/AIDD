#!/usr/bin/env python3
"""
生产环境配置检查脚本
用于诊断生产环境认证和数据库配置问题
"""
import os
import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def check_jwt_config():
    """检查JWT配置"""
    print("\n=== JWT配置检查 ===")
    
    jwt_secret = os.environ.get('JWT_SECRET_KEY')
    if not jwt_secret:
        print("❌ JWT_SECRET_KEY环境变量未设置")
        print("💡 请设置: export JWT_SECRET_KEY='your-secure-secret-key'")
        return False
    else:
        print(f"✅ JWT_SECRET_KEY已设置 (长度: {len(jwt_secret)} 字符)")
        if len(jwt_secret) < 32:
            print("⚠️ JWT密钥长度过短，建议至少32字符")
        return True

def check_database_config():
    """检查数据库配置"""
    print("\n=== 数据库配置检查 ===")
    
    db_type = os.environ.get('DATABASE_TYPE', 'mysql')
    print(f"📊 数据库类型: {db_type}")
    
    if db_type == 'mysql':
        mysql_host = os.environ.get('MYSQL_HOST', 'localhost')
        mysql_port = os.environ.get('MYSQL_PORT', '3306')
        mysql_user = os.environ.get('MYSQL_USERNAME', 'ai_docs_user')
        mysql_db = os.environ.get('MYSQL_DATABASE', 'ai_docs_db')
        
        print(f"🏠 MySQL主机: {mysql_host}:{mysql_port}")
        print(f"👤 MySQL用户: {mysql_user}")
        print(f"🗃️ MySQL数据库: {mysql_db}")
        
        # 检查密码
        mysql_password = os.environ.get('MYSQL_PASSWORD')
        if not mysql_password:
            print("❌ MYSQL_PASSWORD环境变量未设置")
            return False
        else:
            print(f"✅ MYSQL_PASSWORD已设置")
    
    return True

def check_application_config():
    """检查应用配置"""
    print("\n=== 应用配置检查 ===")
    
    try:
        from app.core.config import get_settings
        settings = get_settings()
        
        print(f"✅ 配置文件加载成功")
        print(f"📡 服务器地址: {settings.server_config.get('host')}:{settings.server_config.get('port')}")
        print(f"🔗 数据库类型: {settings.database_type}")
        print(f"🌐 外部访问URL: {settings.server_external_url}")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置文件加载失败: {e}")
        return False

def test_database_connection():
    """测试数据库连接"""
    print("\n=== 数据库连接测试 ===")
    
    try:
        from app.core.database import engine, SessionLocal
        from sqlalchemy import text
        
        print("🔧 测试数据库连接...")
        
        # 测试引擎连接
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ 数据库引擎连接成功")
        
        # 测试会话连接
        db = SessionLocal()
        try:
            result = db.execute(text("SELECT 1"))
            print("✅ 数据库会话连接成功")
            
            # 如果是MySQL，测试更多信息
            if 'mysql' in str(engine.url):
                try:
                    version_result = db.execute(text("SELECT VERSION()"))
                    version = version_result.fetchone()[0]
                    print(f"📊 MySQL版本: {version}")
                    
                    # 检查字符集
                    charset_result = db.execute(text("SHOW VARIABLES LIKE 'character_set_server'"))
                    charset = charset_result.fetchone()[1]
                    print(f"📝 字符集: {charset}")
                    
                    # 检查时区
                    timezone_result = db.execute(text("SELECT NOW(), UTC_TIMESTAMP()"))
                    times = timezone_result.fetchone()
                    print(f"⏰ 服务器时间: {times[0]}, UTC时间: {times[1]}")
                    
                except Exception as mysql_info_error:
                    print(f"⚠️ MySQL信息获取失败: {mysql_info_error}")
            
        finally:
            db.close()
            
        return True
        
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

def test_jwt_functionality():
    """测试JWT功能"""
    print("\n=== JWT功能测试 ===")
    
    try:
        from app.services.auth import AuthService
        from app.core.database import SessionLocal
        
        db = SessionLocal()
        try:
            auth_service = AuthService(db)
            
            # 创建测试token
            test_data = {"sub": "999999"}  # 使用不存在的用户ID
            token = auth_service.create_access_token(test_data)
            print(f"✅ JWT Token创建成功 (长度: {len(token)})")
            
            # 验证token（应该返回None因为用户不存在）
            user = auth_service.verify_token(token)
            if user is None:
                print("✅ JWT Token验证功能正常（未找到用户）")
            else:
                print(f"⚠️ JWT Token验证异常：找到了不应该存在的用户 {user.id}")
            
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ JWT功能测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 开始生产环境配置检查...")
    print(f"📁 工作目录: {os.getcwd()}")
    print(f"🕐 检查时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_checks = [
        ("JWT配置", check_jwt_config),
        ("数据库配置", check_database_config),
        ("应用配置", check_application_config),
        ("数据库连接", test_database_connection),
        ("JWT功能", test_jwt_functionality)
    ]
    
    results = {}
    for name, check_func in all_checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"❌ {name}检查异常: {e}")
            results[name] = False
    
    print("\n" + "="*50)
    print("📋 检查结果总览:")
    print("="*50)
    
    all_passed = True
    for name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} {name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 所有检查项目都通过了！")
        print("💡 如果仍有401错误，请检查:")
        print("   1. 前端是否使用正确的token")
        print("   2. 网络延迟是否导致token过期")
        print("   3. 负载均衡是否正确转发请求")
    else:
        print("\n⚠️ 发现配置问题，请根据上述提示进行修复")
        
    return 0 if all_passed else 1

if __name__ == "__main__":
    exit(main())