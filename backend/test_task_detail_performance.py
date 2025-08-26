#!/usr/bin/env python3
"""
任务详情页面性能测试
"""
import sys
import os
import time
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.services.task import TaskService
from app.repositories.task import TaskRepository
from app.repositories.issue import IssueRepository
from app.repositories.file_info import FileInfoRepository
from app.repositories.ai_model import AIModelRepository
from app.models import Task, Issue, FileInfo, AIModel, User
from sqlalchemy import text


def create_test_data(db):
    """创建测试数据"""
    print("📦 创建测试数据...")
    
    # 先清理现有测试数据
    db.execute(text("DELETE FROM issues"))
    db.execute(text("DELETE FROM tasks"))
    db.execute(text("DELETE FROM file_infos"))
    db.execute(text("DELETE FROM ai_models"))
    db.execute(text("DELETE FROM users"))
    db.commit()
    
    # 创建用户
    user = User(uid="test_user_123", display_name="测试用户", email="test@example.com")
    db.add(user)
    db.flush()
    
    # 创建AI模型
    ai_model = AIModel(
        model_key="gpt-4o-mini-test",
        label="GPT-4o Mini",
        provider="openai", 
        model_name="gpt-4o-mini",
        is_active=True,
        is_default=True
    )
    db.add(ai_model)
    db.flush()
    
    # 创建文件
    file_info = FileInfo(
        original_name="test.pdf",
        stored_name="test_stored.pdf",
        file_path="/tmp/test.pdf",
        file_size=1000,
        file_type="pdf",
        mime_type="application/pdf",
        content_hash="abcd1234",
        encoding="utf-8",
        is_processed="completed"
    )
    db.add(file_info)
    db.flush()
    
    # 创建任务
    task = Task(
        title="测试任务",
        status="completed",
        progress=100,
        user_id=user.id,
        file_id=file_info.id,
        model_id=ai_model.id
    )
    db.add(task)
    db.flush()
    
    # 创建问题
    for i in range(50):  # 创建50个问题
        issue = Issue(
            task_id=task.id,
            issue_type="语法问题",
            description=f"测试问题 {i+1}",
            location=f"第{i+1}页",
            severity="一般",
            confidence=0.8,
            suggestion=f"建议修改 {i+1}",
            original_text=f"原文 {i+1}",
            user_impact="影响理解",
            reasoning="逻辑推理",
            context="上下文"
        )
        db.add(issue)
    
    db.commit()
    print(f"✅ 创建了1个任务，包含50个问题")
    return task.id


def test_old_method(db, task_id):
    """测试旧的查询方法（模拟多次查询）"""
    print("\n🧪 测试旧方法（多次单独查询）...")
    start_time = time.time()
    
    # 模拟旧的查询方式
    task_repo = TaskRepository(db)
    issue_repo = IssueRepository(db)
    file_repo = FileInfoRepository(db)
    model_repo = AIModelRepository(db)
    
    # 1. 查询任务
    task = task_repo.get_by_id(task_id)
    
    # 2. 单独查询关联数据（模拟N+1查询）
    file_info = file_repo.get_by_id(task.file_id) if task.file_id else None
    ai_model = model_repo.get_by_id(task.model_id) if task.model_id else None  
    
    # 3. 查询问题
    issues = issue_repo.get_by_task_id(task_id)
    processed_issues = task_repo.count_processed_issues(task_id)
    
    end_time = time.time()
    print(f"❌ 旧方法耗时: {(end_time - start_time)*1000:.1f}ms")
    print(f"   - 查询到 {len(issues)} 个问题")
    return end_time - start_time


def test_new_method(db, task_id):
    """测试新的优化方法"""
    print("\n🚀 测试新方法（JOIN预加载）...")
    start_time = time.time()
    
    task_service = TaskService(db)
    task_detail = task_service.get_task_detail(task_id)
    
    end_time = time.time()
    print(f"✅ 新方法总耗时: {(end_time - start_time)*1000:.1f}ms")
    print(f"   - 查询到 {len(task_detail.issues)} 个问题")
    return end_time - start_time


def test_multiple_requests(db, task_id, count=10):
    """测试多次请求的性能"""
    print(f"\n🔄 测试连续 {count} 次请求...")
    
    task_service = TaskService(db)
    
    times = []
    for i in range(count):
        start_time = time.time()
        task_detail = task_service.get_task_detail(task_id)
        end_time = time.time()
        times.append(end_time - start_time)
        print(f"   请求 {i+1}: {(end_time - start_time)*1000:.1f}ms")
    
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    print(f"\n📊 性能统计:")
    print(f"   - 平均耗时: {avg_time*1000:.1f}ms")
    print(f"   - 最快请求: {min_time*1000:.1f}ms")
    print(f"   - 最慢请求: {max_time*1000:.1f}ms")


def cleanup_test_data(db, task_id):
    """清理测试数据"""
    print(f"\n🧹 清理测试数据...")
    
    # 删除问题
    db.execute(text("DELETE FROM issues WHERE task_id = :task_id"), {"task_id": task_id})
    
    # 删除任务
    db.execute(text("DELETE FROM tasks WHERE id = :task_id"), {"task_id": task_id})
    
    # 删除文件和模型（如果需要）
    db.execute(text("DELETE FROM file_infos"))
    db.execute(text("DELETE FROM ai_models"))
    db.execute(text("DELETE FROM users"))
    
    db.commit()
    print("✅ 测试数据已清理")


def main():
    print("🚀 任务详情页面性能测试开始...\n")
    
    db = SessionLocal()
    try:
        # 创建测试数据
        task_id = create_test_data(db)
        
        # 测试旧方法
        old_time = test_old_method(db, task_id)
        
        # 测试新方法
        new_time = test_new_method(db, task_id)
        
        # 计算性能提升
        improvement = old_time / new_time if new_time > 0 else 0
        print(f"\n📈 性能提升: {improvement:.1f}x 倍")
        print(f"   减少耗时: {(old_time - new_time)*1000:.1f}ms")
        
        # 测试多次请求
        test_multiple_requests(db, task_id, 5)
        
        # 清理测试数据
        cleanup_test_data(db, task_id)
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
    
    print(f"\n✅ 任务详情性能测试完成!")


if __name__ == "__main__":
    main()