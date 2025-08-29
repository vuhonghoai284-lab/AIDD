#!/usr/bin/env python3
"""
Alembic诊断和修复工具
用于诊断和修复Alembic版本相关的问题
"""
import os
import sys
from pathlib import Path
from sqlalchemy import text

# 添加项目路径
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

def diagnose_alembic():
    """诊断Alembic状态"""
    print("🔍 开始Alembic诊断...")
    
    try:
        from app.core.database import engine
        from app.core.config import get_settings
        
        settings = get_settings()
        print(f"📊 数据库类型: {settings.database_config.get('type', 'unknown')}")
        print(f"🔗 数据库URL: {settings.database_url[:50]}...")
        
        # 1. 检查versions目录
        versions_dir = backend_dir / 'alembic' / 'versions'
        print(f"\n📁 迁移文件目录: {versions_dir}")
        
        if versions_dir.exists():
            version_files = list(versions_dir.glob('*.py'))
            print(f"🗂️ 找到 {len(version_files)} 个版本文件:")
            for vf in version_files:
                print(f"  - {vf.name}")
        else:
            print("❌ versions目录不存在")
            return False
            
        # 2. 检查数据库中的版本表
        print("\n🗄️ 检查数据库版本表...")
        try:
            with engine.connect() as conn:
                # 检查alembic_version表是否存在
                result = conn.execute(text("""
                    SELECT COUNT(*) as count FROM information_schema.tables 
                    WHERE table_schema = DATABASE() AND table_name = 'alembic_version'
                """))
                table_exists = result.fetchone()[0] > 0
                
                if table_exists:
                    print("✅ alembic_version表存在")
                    
                    # 获取当前版本
                    result = conn.execute(text('SELECT version_num FROM alembic_version'))
                    current_versions = result.fetchall()
                    
                    if current_versions:
                        print("📝 数据库中的版本记录:")
                        for version in current_versions:
                            print(f"  - {version[0]}")
                    else:
                        print("⚠️ alembic_version表为空")
                        
                else:
                    print("❌ alembic_version表不存在")
                    
        except Exception as db_error:
            print(f"❌ 数据库检查失败: {db_error}")
            return False
            
        # 3. 检查版本一致性
        print("\n🔄 检查版本一致性...")
        if version_files and current_versions:
            # 提取文件版本号
            file_versions = []
            for vf in version_files:
                version_id = vf.name.split('_')[0]
                file_versions.append(version_id)
                
            db_versions = [v[0] for v in current_versions]
            
            print(f"📁 文件中的版本: {file_versions}")
            print(f"🗄️ 数据库中的版本: {db_versions}")
            
            # 检查是否匹配
            for db_ver in db_versions:
                if db_ver not in file_versions:
                    print(f"⚠️ 数据库版本 {db_ver} 在文件中不存在")
                    return False
                    
            print("✅ 版本一致性检查通过")
            
        return True
        
    except Exception as e:
        print(f"❌ 诊断过程发生错误: {e}")
        return False

def fix_version_mismatch():
    """修复版本不匹配问题"""
    print("\n🔧 开始修复版本问题...")
    
    try:
        from app.core.database import engine
        
        # 获取当前目录中的版本文件
        versions_dir = backend_dir / 'alembic' / 'versions'
        version_files = list(versions_dir.glob('*.py'))
        
        if not version_files:
            print("❌ 没有找到版本文件")
            return False
            
        # 假设最新的文件是当前版本（按文件名排序）
        latest_file = sorted(version_files)[-1]
        latest_version = latest_file.name.split('_')[0]
        
        print(f"🎯 将数据库版本设置为: {latest_version}")
        
        with engine.connect() as conn:
            # 清空版本表
            conn.execute(text('DELETE FROM alembic_version'))
            
            # 插入正确版本
            conn.execute(text('INSERT INTO alembic_version (version_num) VALUES (:version)'), 
                        {'version': latest_version})
            conn.commit()
            
        print("✅ 版本修复完成")
        return True
        
    except Exception as e:
        print(f"❌ 修复过程发生错误: {e}")
        return False

def create_clean_migration():
    """创建一个干净的初始迁移"""
    print("\n🆕 创建干净的初始迁移...")
    
    # 这需要手动操作，给出指导
    print("""
    要创建干净的迁移，请按以下步骤操作：
    
    1. 备份数据库数据（如果有重要数据）
    2. 删除alembic_version表：
       DROP TABLE IF EXISTS alembic_version;
    
    3. 删除现有版本文件：
       rm alembic/versions/*.py
    
    4. 创建新的初始迁移：
       python run_alembic.py revision --autogenerate -m "Initial migration"
    
    5. 应用迁移：
       python run_alembic.py upgrade head
    """)

def main():
    """主函数"""
    print("🔍 Alembic诊断和修复工具")
    print("=" * 50)
    
    # 诊断
    if not diagnose_alembic():
        print("\n❌ 诊断发现问题")
        
        response = input("\n是否尝试自动修复版本不匹配问题？(y/n): ")
        if response.lower() == 'y':
            if fix_version_mismatch():
                print("\n✅ 修复完成，请重新运行诊断验证")
            else:
                print("\n❌ 自动修复失败")
                create_clean_migration()
        else:
            create_clean_migration()
    else:
        print("\n✅ Alembic状态正常")

if __name__ == "__main__":
    main()