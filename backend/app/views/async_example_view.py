"""
异步API示例
展示如何使用异步数据库连接和高并发处理
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio

from app.core.database import get_async_db
from app.models.task import Task
from app.models.user import User

router = APIRouter()


@router.get("/async-tasks", response_model=List[dict])
async def get_async_tasks(
    limit: int = 10,
    db: AsyncSession = Depends(get_async_db)
):
    """
    异步获取任务列表
    支持高并发处理
    """
    try:
        # 异步查询
        result = await db.execute(
            select(Task)
            .limit(limit)
            .order_by(Task.created_at.desc())
        )
        tasks = result.scalars().all()
        
        # 并行获取用户信息
        user_tasks = []
        for task in tasks:
            if task.user_id:
                user_result = await db.execute(
                    select(User).where(User.id == task.user_id)
                )
                user = user_result.scalar_one_or_none()
                task_dict = task.to_dict()
                task_dict['user'] = {
                    'id': user.id,
                    'display_name': user.display_name
                } if user else None
                user_tasks.append(task_dict)
            else:
                user_tasks.append(task.to_dict())
        
        return user_tasks
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务失败: {str(e)}")


@router.get("/async-stats")
async def get_async_stats(db: AsyncSession = Depends(get_async_db)):
    """
    异步获取统计信息
    并发执行多个查询
    """
    try:
        # 并发执行多个查询
        total_tasks_query = select(Task).count()
        completed_tasks_query = select(Task).where(Task.status == 'completed').count()
        total_users_query = select(User).count()
        
        # 并行执行查询
        results = await asyncio.gather(
            db.scalar(total_tasks_query),
            db.scalar(completed_tasks_query), 
            db.scalar(total_users_query),
            return_exceptions=True
        )
        
        total_tasks, completed_tasks, total_users = results
        
        return {
            "total_tasks": total_tasks or 0,
            "completed_tasks": completed_tasks or 0,
            "total_users": total_users or 0,
            "completion_rate": (completed_tasks / total_tasks * 100) if total_tasks else 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")


@router.post("/async-batch-update")
async def async_batch_update(
    task_ids: List[int],
    status: str,
    db: AsyncSession = Depends(get_async_db)
):
    """
    异步批量更新任务状态
    高并发批处理示例
    """
    try:
        # 批量查询任务
        result = await db.execute(
            select(Task).where(Task.id.in_(task_ids))
        )
        tasks = result.scalars().all()
        
        if not tasks:
            raise HTTPException(status_code=404, detail="未找到指定任务")
        
        # 批量更新
        update_tasks = []
        for task in tasks:
            task.status = status
            update_tasks.append(task)
        
        # 批量提交
        db.add_all(update_tasks)
        await db.commit()
        
        return {
            "message": f"成功更新 {len(update_tasks)} 个任务状态",
            "updated_count": len(update_tasks)
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"批量更新失败: {str(e)}")