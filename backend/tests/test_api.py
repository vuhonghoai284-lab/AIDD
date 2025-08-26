"""
API端点测试
"""
import pytest
from fastapi.testclient import TestClient


def test_root(client: TestClient):
    """测试根路径"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "AI文档测试系统后端API v2.0"


def test_get_models(client: TestClient):
    """测试获取模型列表"""
    response = client.get("/api/models")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert "default_index" in data
    assert isinstance(data["models"], list)


def test_create_task(client: TestClient, sample_file, auth_headers):
    """测试创建任务"""
    filename, content, content_type = sample_file
    files = {"file": (filename, content, content_type)}
    data = {"title": "Test Task", "ai_model_index": 0}
    
    response = client.post("/api/tasks/", files=files, data=data, headers=auth_headers)
    # 201 is correct for POST creating a resource
    assert response.status_code == 201
    task = response.json()
    assert task["title"] == "Test Task"
    assert task["file_name"] == filename
    assert task["status"] == "pending"
    return task["id"]


def test_get_tasks(client: TestClient, auth_headers):
    """测试获取任务列表"""
    response = client.get("/api/tasks/", headers=auth_headers)
    assert response.status_code == 200
    tasks = response.json()
    assert isinstance(tasks, list)


def test_get_task_detail(client: TestClient, sample_file, auth_headers):
    """测试获取任务详情"""
    # 先创建一个任务
    filename, content, content_type = sample_file
    files = {"file": (filename, content, content_type)}
    create_response = client.post("/api/tasks/", files=files, headers=auth_headers)
    if create_response.status_code == 201:
        task_id = create_response.json()["id"]
    else:
        pytest.skip(f"无法创建任务进行测试: {create_response.status_code}")
    
    # 获取任务详情
    response = client.get(f"/api/tasks/{task_id}", headers=auth_headers)
    assert response.status_code == 200
    detail = response.json()
    assert "task" in detail
    assert "issues" in detail
    assert detail["task"]["id"] == task_id


def test_submit_feedback(client: TestClient, auth_headers):
    """测试提交问题反馈"""
    # 这个测试需要先有问题数据，这里只测试API是否可调用
    feedback_data = {
        "feedback_type": "accept",
        "comment": "测试评论"
    }
    # 使用一个不存在的ID会返回404
    response = client.put("/api/issues/999/feedback", json=feedback_data, headers=auth_headers)
    assert response.status_code == 404


def test_submit_satisfaction_rating(client: TestClient, auth_headers):
    """测试提交满意度评分"""
    # 测试有效的评分
    rating_data = {
        "satisfaction_rating": 4.5
    }
    # 使用一个不存在的ID会返回404
    response = client.put("/api/issues/999/satisfaction", json=rating_data, headers=auth_headers)
    assert response.status_code == 404
    
    # 测试无效评分（超出范围）
    invalid_rating_data = {
        "satisfaction_rating": 6.0
    }
    response = client.put("/api/issues/999/satisfaction", json=invalid_rating_data, headers=auth_headers)
    assert response.status_code == 422  # 验证错误
    
    # 测试无效评分（小于1）
    invalid_rating_data = {
        "satisfaction_rating": 0.5
    }
    response = client.put("/api/issues/999/satisfaction", json=invalid_rating_data, headers=auth_headers)
    assert response.status_code == 422  # 验证错误


def test_get_ai_outputs(client: TestClient, sample_file, auth_headers):
    """测试获取AI输出"""
    # 先创建一个任务
    filename, content, content_type = sample_file
    files = {"file": (filename, content, content_type)}
    create_response = client.post("/api/tasks/", files=files, headers=auth_headers)
    if create_response.status_code == 201:
        task_id = create_response.json()["id"]
    else:
        pytest.skip(f"无法创建任务进行测试: {create_response.status_code}")
    
    # 获取AI输出
    response = client.get(f"/api/tasks/{task_id}/ai-outputs", headers=auth_headers)
    assert response.status_code == 200
    outputs = response.json()
    assert isinstance(outputs, list)


def test_delete_task(client: TestClient, sample_file, auth_headers):
    """测试删除任务"""
    # 先创建一个任务
    filename, content, content_type = sample_file
    files = {"file": (filename, content, content_type)}
    create_response = client.post("/api/tasks/", files=files, headers=auth_headers)
    task_id = create_response.json()["id"]
    
    # 删除任务
    response = client.delete(f"/api/tasks/{task_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["success"] == True
    
    # 验证任务已删除
    response = client.get(f"/api/tasks/{task_id}", headers=auth_headers)
    assert response.status_code == 404