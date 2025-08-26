#!/usr/bin/env python3
"""
简单的任务创建测试
"""
import json
import os
import sys

# 添加测试目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tests'))

# 导入测试fixtures
import pytest
from tests.conftest import client

def test_task_api(client):
    print("\n=== 简单任务创建测试 ===")
    
    # 1. 用户认证
    print("1. 用户认证...")
    code_data = {"code": "simple_test_auth_code"}
    token_response = client.post("/api/auth/thirdparty/exchange-token", json=code_data)
    print(f"Token exchange: {token_response.status_code}")
    
    if token_response.status_code != 200:
        print(f"Token exchange failed: {token_response.text}")
        return
    
    token_data = token_response.json()
    login_data = {"access_token": token_data["access_token"]}
    login_response = client.post("/api/auth/thirdparty/login", json=login_data)
    print(f"Login: {login_response.status_code}")
    
    if login_response.status_code != 200:
        print(f"Login failed: {login_response.text}")
        return
    
    login_result = login_response.json()
    headers = {"Authorization": f"Bearer {login_result['access_token']}"}
    print(f"User: {login_result['user']['display_name']}")
    
    # 2. 测试任务创建
    print("\n2. 任务创建...")
    test_content = b"# Simple Test\n\nThis is a simple test document."
    
    try:
        response = client.post(
            "/api/tasks/",
            files={"file": ("simple_test.md", test_content, "text/markdown")},
            data={"title": "Simple Test Task"},
            headers=headers
        )
        
        print(f"Task creation status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 201:
            task_data = response.json()
            print(f"✅ Success! Task ID: {task_data['id']}")
            print(f"Task status: {task_data['status']}")
        else:
            print(f"❌ Failed with status {response.status_code}")
            print(f"Response text: {response.text}")
            
            # Try to parse JSON error
            try:
                error_data = response.json()
                print(f"Error JSON: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
            except Exception as e:
                print(f"Could not parse JSON: {e}")
                
    except Exception as e:
        print(f"❌ Exception during task creation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple()