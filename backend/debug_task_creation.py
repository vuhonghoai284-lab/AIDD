#!/usr/bin/env python3
"""
调试任务创建API
"""
import requests
import json
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from tests.conftest import client
import pytest

def test_single_task_creation():
    """测试单个任务创建"""
    
    # 使用conftest中的client fixture
    pytest.main([__file__ + "::test_task_creation_debug", "-v", "-s"])

def test_task_creation_debug(client):
    """调试任务创建"""
    print("\n🔍 开始调试任务创建...")
    
    # 步骤1: 创建用户并获取token
    print("\n1. 创建用户认证...")
    
    # 使用第三方认证流程
    code_data = {"code": "debug_user_auth_code"}
    token_response = client.post("/api/auth/thirdparty/exchange-token", json=code_data)
    print(f"Token兑换响应: {token_response.status_code}")
    if token_response.status_code != 200:
        print(f"Token兑换失败: {token_response.text}")
        return
    
    token_data = token_response.json()
    access_token = token_data["access_token"]
    print(f"获取到access_token: {access_token[:20]}...")
    
    # 登录获取JWT
    login_data = {"access_token": access_token}
    login_response = client.post("/api/auth/thirdparty/login", json=login_data)
    print(f"登录响应: {login_response.status_code}")
    if login_response.status_code != 200:
        print(f"登录失败: {login_response.text}")
        return
    
    login_result = login_response.json()
    jwt_token = login_result["access_token"]
    user = login_result["user"]
    print(f"用户信息: {user['display_name']} (ID: {user['id']})")
    print(f"JWT Token: {jwt_token[:20]}...")
    
    # 步骤2: 验证用户信息
    print("\n2. 验证用户信息...")
    headers = {"Authorization": f"Bearer {jwt_token}"}
    user_response = client.get("/api/users/me", headers=headers)
    print(f"用户验证响应: {user_response.status_code}")
    if user_response.status_code == 200:
        user_info = user_response.json()
        print(f"验证成功: {user_info['display_name']}")
    else:
        print(f"用户验证失败: {user_response.text}")
        return
    
    # 步骤3: 创建任务
    print("\n3. 创建任务...")
    
    # 创建测试文件
    test_content_str = """# Test Document
    
## Chapter 1 Introduction
This is a test document for debugging task creation functionality.

### 1.1 Background
This document is used to test the system's document processing capabilities.

## Chapter 2 Content
This is the main content section.

### 2.1 Detailed Information
Contains some detailed information and explanations.

## Chapter 3 Summary
This is the summary section of the document.
"""
    test_content = test_content_str.encode('utf-8')
    
    task_response = client.post(
        "/api/tasks/",
        files={"file": ("debug_test.md", test_content, "text/markdown")},
        data={"title": "调试测试任务"},
        headers=headers
    )
    
    print(f"任务创建响应: {task_response.status_code}")
    if task_response.status_code == 201:
        task = task_response.json()
        print(f"✅ 任务创建成功!")
        print(f"   任务ID: {task['id']}")
        print(f"   任务标题: {task['title']}")
        print(f"   任务状态: {task['status']}")
    else:
        print(f"❌ 任务创建失败!")
        print(f"   错误信息: {task_response.text}")
        
        # 尝试解析JSON错误
        try:
            error_json = task_response.json()
            print(f"   详细错误: {json.dumps(error_json, indent=2, ensure_ascii=False)}")
        except:
            pass

if __name__ == "__main__":
    test_single_task_creation()