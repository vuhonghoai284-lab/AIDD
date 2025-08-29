"""
运营数据API视图 - 支持异步加载和缓存
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.models.user import User
from app.services.operations_service import OperationsService
from app.dto.operations import (
    OperationsOverview, OperationsRequest, OperationsTimeRange, 
    TimeRangeType
)
from app.views.base import BaseView


class OperationsView(BaseView):
    """运营数据视图类 - 支持异步响应和缓存优化"""
    
    def __init__(self):
        super().__init__()
        self.router = APIRouter(tags=["operations"])  # 去除prefix，在main.py中统一添加
        self._setup_routes()
    
    def _setup_routes(self):
        """设置路由"""
        self.router.add_api_route(
            "/overview", 
            self.get_operations_overview, 
            methods=["GET"], 
            response_model=OperationsOverview,
            description="获取运营总览数据（支持异步加载）"
        )
        
        self.router.add_api_route(
            "/overview", 
            self.get_operations_overview_by_request, 
            methods=["POST"], 
            response_model=OperationsOverview,
            description="通过请求参数获取运营总览数据"
        )
        
        print("🛠️  OperationsView 路由已设置：")
        for route in self.router.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                print(f"   {route.methods} {route.path}")
    
    async def get_operations_overview(
        self,
        time_range_type: Optional[str] = "30days",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        include_trends: bool = True,
        include_critical_issues: bool = True,
        max_critical_issues: int = 20,
        current_user: User = Depends(BaseView.get_current_user),
        db: Session = Depends(get_db)
    ) -> OperationsOverview:
        """
        获取运营总览数据（GET方式，支持查询参数）
        
        Args:
            time_range_type: 时间范围类型 (7days, 30days, 6months, this_year, 1year, custom)
            start_date: 自定义开始日期 (YYYY-MM-DD，仅time_range_type=custom时需要)
            end_date: 自定义结束日期 (YYYY-MM-DD，仅time_range_type=custom时需要)
            include_trends: 是否包含趋势数据
            include_critical_issues: 是否包含关键问题
            max_critical_issues: 最大关键问题数量
        
        Returns:
            运营总览数据
        """
        print(f"🚀 用户 {current_user.uid} 请求运营总览数据，时间范围: {time_range_type}")
        
        # 检查权限（仅管理员可访问）
        if not (current_user.is_admin or current_user.is_system_admin):
            raise HTTPException(403, "权限不足，仅管理员可查看运营数据")
        
        try:
            # 构建时间范围对象
            time_range = OperationsTimeRange(type=TimeRangeType(time_range_type))
            
            # 处理自定义时间范围
            if time_range_type == "custom":
                if not start_date or not end_date:
                    raise HTTPException(400, "自定义时间范围需要提供start_date和end_date参数")
                
                from datetime import datetime
                try:
                    time_range.start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                    time_range.end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                except ValueError:
                    raise HTTPException(400, "日期格式错误，请使用YYYY-MM-DD格式")
            
            # 创建运营服务并获取数据
            service = OperationsService(db)
            overview = await service.get_operations_overview_async(
                time_range=time_range,
                include_trends=include_trends,
                include_critical_issues=include_critical_issues,
                max_critical_issues=max_critical_issues
            )
            
            print(f"✅ 运营总览数据获取成功，返回数据给用户 {current_user.uid}")
            return overview
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ 获取运营总览数据失败: {e}")
            raise HTTPException(500, f"获取运营数据失败: {str(e)}")
    
    async def get_operations_overview_by_request(
        self,
        request: OperationsRequest,
        current_user: User = Depends(BaseView.get_current_user),
        db: Session = Depends(get_db)
    ) -> OperationsOverview:
        """
        通过请求体获取运营总览数据（POST方式）
        
        Args:
            request: 运营数据请求参数
            
        Returns:
            运营总览数据
        """
        print(f"🚀 用户 {current_user.uid} 通过POST请求运营总览数据")
        
        # 检查权限（仅管理员可访问）
        if not (current_user.is_admin or current_user.is_system_admin):
            raise HTTPException(403, "权限不足，仅管理员可查看运营数据")
        
        try:
            # 创建运营服务并获取数据
            service = OperationsService(db)
            overview = await service.get_operations_overview_async(
                time_range=request.time_range,
                include_trends=request.include_trends,
                include_critical_issues=request.include_critical_issues,
                max_critical_issues=request.max_critical_issues
            )
            
            print(f"✅ 运营总览数据获取成功（POST），返回数据给用户 {current_user.uid}")
            return overview
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ 获取运营总览数据失败（POST）: {e}")
            raise HTTPException(500, f"获取运营数据失败: {str(e)}")


# 创建视图实例并导出router
operations_view = OperationsView()
router = operations_view.router