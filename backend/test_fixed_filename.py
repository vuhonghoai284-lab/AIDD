#!/usr/bin/env python3
"""
测试修复后的文件名下载功能
"""
import sys
import os
sys.path.append('.')
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.user import User

def mock_get_current_user():
    """Mock当前用户"""
    db = SessionLocal()
    try:
        user = db.query(User).first()
        if not user:
            user = User(
                id=1,
                uid='test_admin',
                display_name='测试管理员',
                email='admin@test.com',
                is_admin=True,
                is_system_admin=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user
    finally:
        db.close()

def test_fixed_filename():
    """测试修复后的文件名"""
    print("🔍 测试修复后的文件名下载...")
    
    # Mock认证
    from app.views.base import BaseView
    app.dependency_overrides[BaseView.get_current_user] = mock_get_current_user
    
    client = TestClient(app)
    
    try:
        # 发起下载请求
        response = client.get("/api/tasks/1/file")
        
        print(f"📊 响应状态: {response.status_code}")
        
        if response.status_code == 200:
            # 检查Content-Disposition头
            content_disposition = response.headers.get('content-disposition')
            print(f"\n🔍 Content-Disposition:")
            print(f"  完整头部: {content_disposition}")
            
            if content_disposition:
                # 解析filename参数
                import re
                filename_match = re.search(r'filename="([^"]+)"', content_disposition)
                if filename_match:
                    ascii_filename = filename_match.group(1)
                    print(f"  ASCII文件名: {ascii_filename}")
                
                # 解析filename*参数
                utf8_match = re.search(r"filename\*=UTF-8''([^;,\n]*)", content_disposition)
                if utf8_match:
                    encoded_filename = utf8_match.group(1)
                    print(f"  UTF-8编码文件名: {encoded_filename}")
                    
                    # URL解码
                    import urllib.parse
                    decoded_filename = urllib.parse.unquote(encoded_filename)
                    print(f"  解码后文件名: {decoded_filename}")
                    
                    # 验证文件名和扩展名
                    expected_filename = "MindIE 2.1.RC1 安装指南 01.pdf"
                    if decoded_filename == expected_filename:
                        print("  ✅ UTF-8文件名正确!")
                    else:
                        print(f"  ❌ UTF-8文件名不正确，期望: {expected_filename}")
                        
                # 检查ASCII fallback是否有正确的扩展名
                if ascii_filename and ascii_filename.endswith('.pdf'):
                    print("  ✅ ASCII fallback扩展名正确!")
                else:
                    print(f"  ❌ ASCII fallback扩展名错误: {ascii_filename}")
            else:
                print("  ❌ 响应中没有Content-Disposition头")
                
        else:
            print(f"❌ 请求失败: {response.text}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        app.dependency_overrides.clear()

if __name__ == "__main__":
    test_fixed_filename()