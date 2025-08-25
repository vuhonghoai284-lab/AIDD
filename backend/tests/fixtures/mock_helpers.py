"""
测试辅助函数和mock对象
"""
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any, Optional
import pytest


def create_mock_dependencies():
    """创建mock依赖对象"""
    # Mock数据库会话
    mock_db = Mock()
    mock_db.add = Mock()
    mock_db.commit = Mock()
    mock_db.rollback = Mock()
    mock_db.query = Mock()
    mock_db.refresh = Mock()
    
    # Mock文件存储服务
    mock_file_storage = Mock()
    mock_file_storage.save_file = Mock(return_value="/fake/path/test_file.txt")
    mock_file_storage.delete_file = Mock(return_value=True)
    mock_file_storage.get_file_url = Mock(return_value="http://localhost:8080/files/test_file.txt")
    
    # Mock AI服务
    mock_ai_service = AsyncMock()
    mock_ai_service.analyze_document = AsyncMock(return_value={
        "status": "success",
        "data": {
            "structure": {
                "sections": [
                    {"title": "测试章节", "content": "这是测试内容", "level": 1}
                ]
            },
            "issues": [
                {"type": "语法错误", "description": "测试问题", "severity": "medium"}
            ]
        }
    })
    
    # Mock任务服务
    mock_task_service = Mock()
    mock_task_service.create_task = Mock(return_value=Mock(id=1, status="pending"))
    mock_task_service.update_task_status = Mock()
    mock_task_service.get_task = Mock(return_value=Mock(id=1, status="completed"))
    
    return {
        'db': mock_db,
        'file_storage': mock_file_storage,
        'ai_service': mock_ai_service,
        'task_service': mock_task_service
    }


def create_test_user(user_id: int = 1, is_admin: bool = False, is_system_admin: bool = False):
    """创建测试用户对象"""
    user = Mock()
    user.id = user_id
    user.uid = f"test_user_{user_id}"
    user.display_name = f"测试用户{user_id}"
    user.email = f"user{user_id}@test.com"
    user.is_admin = is_admin
    user.is_system_admin = is_system_admin
    return user


def create_test_task(task_id: int = 1, user_id: int = 1, status: str = "pending"):
    """创建测试任务对象"""
    task = Mock()
    task.id = task_id
    task.user_id = user_id
    task.status = status
    task.title = f"测试任务{task_id}"
    task.description = f"这是测试任务{task_id}的描述"
    task.file_path = f"/fake/path/task_{task_id}.txt"
    task.created_at = "2023-01-01T00:00:00Z"
    task.updated_at = "2023-01-01T00:00:00Z"
    return task


def create_test_file_info(file_id: int = 1, task_id: int = 1):
    """创建测试文件信息对象"""
    file_info = Mock()
    file_info.id = file_id
    file_info.task_id = task_id
    file_info.filename = f"test_file_{file_id}.txt"
    file_info.file_path = f"/fake/path/test_file_{file_id}.txt"
    file_info.content_type = "text/plain"
    file_info.file_size = 1024
    file_info.uploaded_at = "2023-01-01T00:00:00Z"
    return file_info


def create_test_ai_output(output_id: int = 1, task_id: int = 1):
    """创建测试AI输出对象"""
    ai_output = Mock()
    ai_output.id = output_id
    ai_output.task_id = task_id
    ai_output.content = '{"test": "这是测试AI输出内容"}'
    ai_output.output_type = "document_analysis"
    ai_output.model_used = "test-model"
    ai_output.created_at = "2023-01-01T00:00:00Z"
    return ai_output


def create_test_issue(issue_id: int = 1, task_id: int = 1, ai_output_id: int = 1):
    """创建测试问题对象"""
    issue = Mock()
    issue.id = issue_id
    issue.task_id = task_id
    issue.ai_output_id = ai_output_id
    issue.issue_type = "语法错误"
    issue.description = "测试问题描述"
    issue.severity = "medium"
    issue.location = "测试章节"
    issue.suggestion = "修改建议"
    issue.is_resolved = False
    issue.created_at = "2023-01-01T00:00:00Z"
    return issue


# 常用的mock数据
MOCK_USER_DATA = {
    "uid": "test_user_001",
    "display_name": "测试用户001",
    "email": "user001@test.com"
}

MOCK_TASK_DATA = {
    "title": "测试任务",
    "description": "这是一个测试任务",
    "file_path": "/fake/path/test.txt"
}

MOCK_FILE_DATA = {
    "filename": "test.txt",
    "content_type": "text/plain",
    "file_size": 1024
}

MOCK_AI_OUTPUT_DATA = {
    "content": '{"analysis": "测试AI分析结果"}',
    "output_type": "document_analysis"
}