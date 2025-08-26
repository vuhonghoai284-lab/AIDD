"""
任务相关视图
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.database import get_db
from app.models.user import User
from app.services.task import TaskService
from app.services.report_service import ReportService
from app.dto.task import TaskResponse, TaskDetail
from app.dto.issue import FeedbackRequest
from app.views.base import BaseView


class TaskView(BaseView):
    """任务视图类"""
    
    def __init__(self):
        super().__init__()
        self.router = APIRouter(tags=["tasks"])
        self._setup_routes()
    
    def _setup_routes(self):
        """设置路由"""
        self.router.add_api_route("/", self.create_task, methods=["POST"], response_model=TaskResponse, status_code=201)
        self.router.add_api_route("/batch", self.batch_create_tasks, methods=["POST"], response_model=List[TaskResponse], status_code=201)
        self.router.add_api_route("/", self.get_tasks, methods=["GET"], response_model=List[TaskResponse])
        self.router.add_api_route("/{task_id}", self.get_task_detail, methods=["GET"], response_model=TaskDetail)
        self.router.add_api_route("/{task_id}", self.delete_task, methods=["DELETE"])
        self.router.add_api_route("/{task_id}/retry", self.retry_task, methods=["POST"])
        self.router.add_api_route("/{task_id}/report", self.download_report, methods=["GET"])
        self.router.add_api_route("/{task_id}/report/check", self.check_report_permission, methods=["GET"])
        print("🛠️  TaskView 路由已设置：")
        for route in self.router.routes:
            print(f"   {route.methods} {route.path}")
    
    async def create_task(
        self,
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        title: Optional[str] = Form(None),
        model_index: Optional[int] = Form(None),
        current_user: User = Depends(BaseView.get_current_user),
        db: Session = Depends(get_db)
    ) -> TaskResponse:
        """创建任务"""
        service = TaskService(db)
        return await service.create_task(file, title, model_index, user_id=current_user.id)
    
    async def batch_create_tasks(
        self,
        background_tasks: BackgroundTasks,
        files: List[UploadFile] = File(...),
        model_index: Optional[int] = Form(None),
        current_user: User = Depends(BaseView.get_current_user),
        db: Session = Depends(get_db)
    ) -> List[TaskResponse]:
        """批量创建任务"""
        print(f"🚀 批量创建任务请求: {len(files)} 个文件, model_index={model_index}, user={current_user.uid}")
        
        service = TaskService(db)
        
        # 准备文件数据
        files_data = []
        for file in files:
            files_data.append({
                'file': file,
                'title': None,  # 使用文件名作为标题
                'model_index': model_index
            })
        
        # 使用服务层的批量创建方法
        return await service.batch_create_tasks(files_data, user_id=current_user.id)
    
    def get_tasks(
        self,
        current_user: User = Depends(BaseView.get_current_user),
        db: Session = Depends(get_db)
    ) -> List[TaskResponse]:
        """获取任务列表"""
        service = TaskService(db)
        # 管理员可以查看所有任务，普通用户只能查看自己的任务
        if current_user.is_admin:
            return service.get_all_tasks()
        else:
            return service.get_user_tasks(current_user.id)
    
    def get_task_detail(
        self,
        task_id: int,
        current_user: User = Depends(BaseView.get_current_user),
        db: Session = Depends(get_db)
    ) -> TaskDetail:
        """获取任务详情"""
        print(f"🎯 TaskView.get_task_detail 被调用, task_id={task_id}, user={current_user.uid}")
        service = TaskService(db)
        task_detail = service.get_task_detail(task_id)
        
        # 检查用户权限
        self.check_task_access_permission(current_user, task_detail.task.user_id)
        
        return task_detail
    
    def delete_task(
        self,
        task_id: int,
        current_user: User = Depends(BaseView.get_current_user),
        db: Session = Depends(get_db)
    ):
        """删除任务"""
        service = TaskService(db)
        
        # 获取任务信息以检查所有者
        from app.repositories.task import TaskRepository
        task_repo = TaskRepository(db)
        task = task_repo.get_by_id(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 检查用户权限
        self.check_task_access_permission(current_user, task.user_id)
        
        success = service.delete_task(task_id)
        return {"success": success}
    
    def retry_task(
        self,
        task_id: int,
        current_user: User = Depends(BaseView.get_current_user),
        db: Session = Depends(get_db)
    ):
        """重试任务"""
        from app.repositories.task import TaskRepository
        task_repo = TaskRepository(db)
        task = task_repo.get_by_id(task_id)
        if not task:
            raise HTTPException(404, "任务不存在")
        
        # 检查用户权限
        self.check_task_access_permission(current_user, task.user_id)
        
        # TODO: 实现任务重试逻辑
        return {"message": "任务重试功能待实现"}
    
    def download_report(
        self,
        task_id: int,
        current_user: User = Depends(BaseView.get_current_user),
        db: Session = Depends(get_db)
    ):
        """下载任务报告"""
        print(f"📊 用户 {current_user.uid} 请求下载任务 {task_id} 的报告")
        
        # 创建报告服务
        report_service = ReportService(db)
        
        # 检查下载权限
        permission_check = report_service.check_download_permission(
            task_id=task_id,
            user_id=current_user.id,
            is_admin=current_user.is_admin or current_user.is_system_admin
        )
        
        if not permission_check["can_download"]:
            print(f"❌ 下载被拒绝: {permission_check['reason']}")
            # 返回详细的错误信息，包括统计数据
            error_data = {
                "detail": permission_check["reason"],
                "can_download": False
            }
            
            # 如果是问题未处理完的情况，返回详细统计
            if "total_issues" in permission_check:
                error_data.update({
                    "total_issues": permission_check["total_issues"],
                    "processed_issues": permission_check["processed_issues"],
                    "unprocessed_count": permission_check["unprocessed_count"]
                })
            
            raise HTTPException(403, error_data)
        
        print(f"✅ 权限检查通过: {permission_check['reason']}")
        
        try:
            # 生成Excel报告
            excel_data = report_service.generate_excel_report(task_id)
            filename = report_service.get_report_filename(task_id)
            
            print(f"📄 报告生成成功: {filename}")
            
            # 返回文件流
            return StreamingResponse(
                io=excel_data,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"'
                }
            )
            
        except Exception as e:
            print(f"❌ 报告生成失败: {e}")
            raise HTTPException(500, f"报告生成失败: {str(e)}")
    
    def check_report_permission(
        self,
        task_id: int,
        current_user: User = Depends(BaseView.get_current_user),
        db: Session = Depends(get_db)
    ):
        """检查报告下载权限"""
        print(f"🔍 检查用户 {current_user.uid} 对任务 {task_id} 的报告下载权限")
        
        # 创建报告服务
        report_service = ReportService(db)
        
        # 检查下载权限
        permission_check = report_service.check_download_permission(
            task_id=task_id,
            user_id=current_user.id,
            is_admin=current_user.is_admin or current_user.is_system_admin
        )
        
        print(f"📋 权限检查结果: {permission_check}")
        return permission_check


# 创建视图实例并导出router
task_view = TaskView()
router = task_view.router