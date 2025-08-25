"""
运营数据统计API视图
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.core.database import get_db
from app.services.analytics import AnalyticsService
from app.dto.analytics import (
    UserStatsResponse, TaskStatsResponse, SystemStatsResponse,
    IssueStatsResponse, ErrorStatsResponse, OverallAnalyticsResponse,
    DateRangeRequest
)
from app.views.base import BaseView
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["运营数据统计"])


@router.get("/overview", response_model=OverallAnalyticsResponse)
async def get_analytics_overview(
    days: int = Query(30, ge=1, le=365, description="统计天数，默认30天"),
    current_user: User = Depends(BaseView.get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取综合运营数据概览
    
    需要管理员权限
    """
    BaseView.check_admin_permission(current_user)
    
    try:
        analytics_service = AnalyticsService(db)
        result = analytics_service.get_overall_analytics(days)
        
        logger.info(f"管理员 {current_user.display_name} 查看了运营数据概览")
        return result
        
    except Exception as e:
        logger.error(f"获取运营数据概览失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取运营数据失败")


@router.get("/users", response_model=UserStatsResponse)
async def get_user_analytics(
    days: int = Query(30, ge=1, le=365, description="统计天数，默认30天"),
    current_user: User = Depends(BaseView.get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取用户统计数据
    
    需要管理员权限
    """
    BaseView.check_admin_permission(current_user)
    
    try:
        analytics_service = AnalyticsService(db)
        result = analytics_service.get_user_stats(days)
        
        logger.info(f"管理员 {current_user.display_name} 查看了用户统计数据")
        return result
        
    except Exception as e:
        logger.error(f"获取用户统计数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取用户统计数据失败")


@router.get("/tasks", response_model=TaskStatsResponse)
async def get_task_analytics(
    days: int = Query(30, ge=1, le=365, description="统计天数，默认30天"),
    current_user: User = Depends(BaseView.get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取任务统计数据
    
    需要管理员权限
    """
    BaseView.check_admin_permission(current_user)
    
    try:
        analytics_service = AnalyticsService(db)
        result = analytics_service.get_task_stats(days)
        
        logger.info(f"管理员 {current_user.display_name} 查看了任务统计数据")
        return result
        
    except Exception as e:
        logger.error(f"获取任务统计数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取任务统计数据失败")


@router.get("/system", response_model=SystemStatsResponse)
async def get_system_analytics(
    days: int = Query(30, ge=1, le=365, description="统计天数，默认30天"),
    current_user: User = Depends(BaseView.get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取系统资源统计数据
    
    需要管理员权限
    """
    BaseView.check_admin_permission(current_user)
    
    try:
        analytics_service = AnalyticsService(db)
        result = analytics_service.get_system_stats(days)
        
        logger.info(f"管理员 {current_user.display_name} 查看了系统资源统计数据")
        return result
        
    except Exception as e:
        logger.error(f"获取系统资源统计数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取系统资源统计数据失败")


@router.get("/issues", response_model=IssueStatsResponse)
async def get_issue_analytics(
    days: int = Query(30, ge=1, le=365, description="统计天数，默认30天"),
    current_user: User = Depends(BaseView.get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取问题统计数据
    
    需要管理员权限
    """
    BaseView.check_admin_permission(current_user)
    
    try:
        analytics_service = AnalyticsService(db)
        result = analytics_service.get_issue_stats(days)
        
        logger.info(f"管理员 {current_user.display_name} 查看了问题统计数据")
        return result
        
    except Exception as e:
        logger.error(f"获取问题统计数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取问题统计数据失败")


@router.get("/errors", response_model=ErrorStatsResponse)
async def get_error_analytics(
    days: int = Query(30, ge=1, le=365, description="统计天数，默认30天"),
    current_user: User = Depends(BaseView.get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取错误统计数据
    
    需要管理员权限
    """
    BaseView.check_admin_permission(current_user)
    
    try:
        analytics_service = AnalyticsService(db)
        result = analytics_service.get_error_stats(days)
        
        logger.info(f"管理员 {current_user.display_name} 查看了错误统计数据")
        return result
        
    except Exception as e:
        logger.error(f"获取错误统计数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取错误统计数据失败")


@router.get("/health")
async def analytics_health_check():
    """
    运营数据统计模块健康检查
    """
    return {
        "status": "healthy",
        "module": "analytics",
        "timestamp": "2024-01-01T00:00:00Z"
    }