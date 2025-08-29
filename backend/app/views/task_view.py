"""
任务相关视图
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from fastapi_cache.decorator import cache
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.database import get_db
from app.models.user import User
from app.services.task import TaskService
from app.services.report_service import ReportService
from app.services.enhanced_concurrency_service import get_enhanced_concurrency_service, ConcurrencyLimitExceeded
from app.dto.task import TaskResponse, TaskDetail
from app.dto.issue import FeedbackRequest, IssueResponse
from app.dto.pagination import PaginationParams, PaginatedResponse
from app.views.base import BaseView


def build_statistics_cache_key(func, *args, **kwargs):
    """构建统计缓存键，安全处理None情况"""
    current_user = kwargs.get('current_user')
    if not current_user:
        return "task_statistics:anonymous"
    elif hasattr(current_user, 'is_admin') and current_user.is_admin:
        return "task_statistics:global"
    else:
        user_id = getattr(current_user, 'id', 'unknown')
        return f"task_statistics:{user_id}"


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
        self.router.add_api_route("/paginated", self.get_tasks_paginated, methods=["GET"], response_model=PaginatedResponse[TaskResponse])
        self.router.add_api_route("/statistics", self.get_task_statistics, methods=["GET"])
        self.router.add_api_route("/concurrency-status", self.get_concurrency_status, methods=["GET"])
        self.router.add_api_route("/user/{user_id}/concurrency-limit", self.update_user_concurrency_limit, methods=["PUT"])
        self.router.add_api_route("/recovery-status", self.get_recovery_status, methods=["GET"])
        self.router.add_api_route("/recover-timeout-tasks", self.recover_timeout_tasks, methods=["POST"])
        self.router.add_api_route("/schedule-pending-tasks", self.schedule_pending_tasks, methods=["POST"])
        self.router.add_api_route("/db-monitor", self.get_db_monitor_status, methods=["GET"])
        self.router.add_api_route("/queue-status", self.get_queue_status, methods=["GET"])
        self.router.add_api_route("/user/{user_id}/queue-status", self.get_user_queue_status, methods=["GET"])
        self.router.add_api_route("/{task_id}", self.get_task_detail, methods=["GET"], response_model=TaskDetail)
        self.router.add_api_route("/{task_id}", self.delete_task, methods=["DELETE"])
        self.router.add_api_route("/{task_id}/retry", self.retry_task, methods=["POST"])
        self.router.add_api_route("/{task_id}/report", self.download_report, methods=["GET"])
        self.router.add_api_route("/{task_id}/report/check", self.check_report_permission, methods=["GET"])
        self.router.add_api_route("/{task_id}/file", self.download_task_file, methods=["GET"])
        self.router.add_api_route("/{task_id}/issues", self.get_task_issues, methods=["GET"], response_model=PaginatedResponse[IssueResponse])
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
        # 检查并发限制
        try:
            allowed, status_info = await get_enhanced_concurrency_service().check_concurrency_limits(
                db, current_user, requested_tasks=1, raise_exception=True
            )
        except ConcurrencyLimitExceeded as e:
            # 返回详细的错误信息
            if e.limit_type == 'system':
                raise HTTPException(
                    status_code=429, 
                    detail={
                        "error": "system_concurrency_limit_exceeded",
                        "message": str(e),
                        "current_count": e.current_count,
                        "max_count": e.max_count,
                        "limit_type": "system"
                    }
                )
            elif e.limit_type == 'user':
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "user_concurrency_limit_exceeded", 
                        "message": str(e),
                        "current_count": e.current_count,
                        "max_count": e.max_count,
                        "limit_type": "user"
                    }
                )
            else:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "concurrency_limit_exceeded",
                        "message": str(e),
                        "limit_type": "both"
                    }
                )
        
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
        
        # 检查并发限制（批量任务需要检查请求的任务数量）
        try:
            allowed, status_info = await get_enhanced_concurrency_service().check_concurrency_limits(
                db, current_user, requested_tasks=len(files), raise_exception=True
            )
        except ConcurrencyLimitExceeded as e:
            # 获取当前状态信息用于错误处理
            _, status_info = await get_enhanced_concurrency_service().check_concurrency_limits(
                db, current_user, requested_tasks=0, raise_exception=False
            )
            
            # 提供批量任务的特殊错误处理
            if e.limit_type == 'system':
                available_slots = status_info['system']['available_slots']
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "system_concurrency_limit_exceeded",
                        "message": f"系统最多还能创建 {available_slots} 个任务，无法创建 {len(files)} 个任务",
                        "requested_tasks": len(files),
                        "available_slots": available_slots,
                        "current_count": e.current_count,
                        "max_count": e.max_count,
                        "limit_type": "system"
                    }
                )
            elif e.limit_type == 'user':
                available_slots = status_info['user']['available_slots']
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "user_concurrency_limit_exceeded",
                        "message": f"您最多还能创建 {available_slots} 个任务，无法创建 {len(files)} 个任务",
                        "requested_tasks": len(files),
                        "available_slots": available_slots,
                        "current_count": e.current_count,
                        "max_count": e.max_count,
                        "limit_type": "user"
                    }
                )
            else:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "concurrency_limit_exceeded",
                        "message": str(e),
                        "requested_tasks": len(files),
                        "limit_type": "both"
                    }
                )
        
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
        """获取任务列表（兼容性接口）"""
        service = TaskService(db)
        # 管理员可以查看所有任务，普通用户只能查看自己的任务
        if current_user.is_admin:
            return service.get_all_tasks()
        else:
            return service.get_user_tasks(current_user.id)
    
    async def get_tasks_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        status: Optional[str] = None,
        sort_by: Optional[str] = "created_at",
        sort_order: Optional[str] = "desc",
        current_user: User = Depends(BaseView.get_current_user),
        db: Session = Depends(get_db)
    ) -> PaginatedResponse[TaskResponse]:
        """分页获取任务列表"""
        import time
        start_time = time.time()
        print(f"🎯 TaskView.get_tasks_paginated 开始处理: page={page}, size={page_size}, status={status}, user={current_user.uid}")
        
        # 构建分页参数
        params = PaginationParams(
            page=page,
            page_size=page_size,
            search=search,
            status=status,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # 直接使用当前数据库会话进行查询（避免线程安全问题）
        service = TaskService(db)
        # 管理员可以查看所有任务，普通用户只能查看自己的任务
        if current_user.is_admin:
            result = service.get_paginated_tasks(params, user_id=None)
        else:
            result = service.get_paginated_tasks(params, user_id=current_user.id)
        
        total_time = (time.time() - start_time) * 1000
        print(f"✅ TaskView.get_tasks_paginated 处理完成: 耗时 {total_time:.1f}ms, 返回 {len(result.items)} 个任务")
        return result
    
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
        self.check_task_access_with_permission_service(task_id, current_user, db, 'read')
        
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
        self.check_task_access_with_permission_service(task_id, current_user, db, 'delete')
        
        success = service.delete_task(task_id)
        return {"success": success}
    
    async def retry_task(
        self,
        task_id: int,
        current_user: User = Depends(BaseView.get_current_user),
        db: Session = Depends(get_db)
    ):
        """重试任务"""
        from app.repositories.task import TaskRepository
        from app.services.task_recovery_service import task_recovery_service
        
        task_repo = TaskRepository(db)
        task = task_repo.get_by_id(task_id)
        if not task:
            raise HTTPException(404, "任务不存在")
        
        # 检查用户权限
        self.check_task_access_with_permission_service(task_id, current_user, db, 'write')
        
        # 检查任务状态是否可重试
        if task.status == 'pending':
            raise HTTPException(400, f"任务状态为 '{task.status}'，无法重试。待处理的任务不需要重试，请等待系统自动处理。")
        
        # 如果是正在处理的任务，先将其标记为失败，然后允许重试
        if task.status == 'processing':
            task_repo.update(task_id, status='failed', error_message="用户手动停止并重试任务")
        
        # 检查并发限制
        try:
            allowed, status_info = await get_enhanced_concurrency_service().check_concurrency_limits(
                db, current_user, requested_tasks=1, raise_exception=True
            )
        except ConcurrencyLimitExceeded as e:
            if e.limit_type == 'system':
                raise HTTPException(
                    status_code=429, 
                    detail={
                        "error": "system_concurrency_limit_exceeded",
                        "message": f"系统并发限制已达上限，任务已重置为pending状态，将在资源可用时自动执行",
                        "current_count": e.current_count,
                        "max_count": e.max_count,
                        "limit_type": "system"
                    }
                )
            elif e.limit_type == 'user':
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "user_concurrency_limit_exceeded", 
                        "message": f"用户并发限制已达上限，任务已重置为pending状态，将在资源可用时自动执行",
                        "current_count": e.current_count,
                        "max_count": e.max_count,
                        "limit_type": "user"
                    }
                )
        
        # 执行任务重试
        success = await task_recovery_service.retry_task(task_id, db)
        
        if not success:
            raise HTTPException(500, "任务重试失败")
        
        return {
            "success": True,
            "message": "任务重试已启动",
            "task_id": task_id
        }
    
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
        permission_check = report_service.check_download_permission_with_user(
            task_id=task_id,
            user=current_user
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
            def iter_excel():
                yield excel_data.read()
            
            # 处理中文文件名编码
            import urllib.parse
            import os
            
            # URL编码文件名用于UTF-8支持
            encoded_filename = urllib.parse.quote(filename, safe='')
            
            # 创建ASCII备选文件名（去除非ASCII字符，保持扩展名）
            file_base, file_ext = os.path.splitext(filename)
            ascii_filename = ''.join(c for c in file_base if ord(c) < 128)
            if not ascii_filename:
                ascii_filename = f"quality_report_{task_id}"
            ascii_filename = f"{ascii_filename}{file_ext}"
            
            return StreamingResponse(
                iter_excel(),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f'attachment; filename="{ascii_filename}"; filename*=UTF-8\'\'{encoded_filename}'
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
        permission_check = report_service.check_download_permission_with_user(
            task_id=task_id,
            user=current_user
        )
        
        print(f"📋 权限检查结果: {permission_check}")
        return permission_check
    
    def get_concurrency_status(
        self,
        current_user: User = Depends(BaseView.get_current_user),
        db: Session = Depends(get_db)
    ) -> dict:
        """获取并发状态信息"""
        return get_enhanced_concurrency_service().get_concurrency_status(db, current_user)
    
    def update_user_concurrency_limit(
        self,
        user_id: int,
        new_limit: int,
        current_user: User = Depends(BaseView.get_current_user),
        db: Session = Depends(get_db)
    ) -> dict:
        """更新用户并发限制（仅管理员）"""
        success = get_enhanced_concurrency_service().update_user_concurrency_limit(
            db, user_id, new_limit, current_user
        )
        if success:
            return {"message": f"成功更新用户 {user_id} 的并发限制为 {new_limit}"}
        else:
            raise HTTPException(403, "权限不足或操作失败")
    
    def download_task_file(
        self,
        task_id: int,
        current_user: User = Depends(BaseView.get_current_user),
        db: Session = Depends(get_db)
    ):
        """下载任务对应的原文件"""
        print(f"📁 用户 {current_user.uid} 请求下载任务 {task_id} 的原文件")
        
        try:
            # 创建任务服务
            task_service = TaskService(db)
            
            # 获取任务详情
            from app.repositories.task import TaskRepository
            task_repo = TaskRepository(db)
            task = task_repo.get_by_id(task_id)
            if not task:
                raise HTTPException(404, "任务不存在")
            
            # 检查用户权限
            self.check_task_access_with_permission_service(task_id, current_user, db, 'download')
            
            # 获取文件信息
            if not task.file_info:
                raise HTTPException(404, "任务关联的文件不存在")
                
            file_info = task.file_info
            file_path = file_info.file_path
            
            # 检查文件是否存在
            import os
            if not os.path.exists(file_path):
                print(f"❌ 文件不存在: {file_path}")
                raise HTTPException(404, "文件不存在或已被删除")
            
            print(f"✅ 找到文件: {file_path}, 大小: {file_info.file_size} bytes")
            
            # 创建文件流响应
            def iterfile():
                with open(file_path, mode="rb") as file_like:
                    yield from file_like
            
            # 处理文件名编码，支持中文文件名
            import urllib.parse
            encoded_filename = urllib.parse.quote(file_info.original_name, safe='')
            
            # 设置响应头，同时支持RFC 5987和传统filename格式以确保兼容性
            # 为传统浏览器提供ASCII fallback文件名，保持正确的文件扩展名
            original_ext = os.path.splitext(file_info.original_name)[1] or '.pdf'  # 获取原文件扩展名
            ascii_filename = file_info.original_name.encode('ascii', 'ignore').decode('ascii')
            if not ascii_filename or ascii_filename != file_info.original_name:
                # 使用任务标题作为fallback，如果标题也有非ASCII字符则使用task_id
                task_title = task.title.encode('ascii', 'ignore').decode('ascii') if task.title else ""
                if task_title and len(task_title.strip()) > 0:
                    ascii_filename = f"{task_title.strip()}{original_ext}"
                else:
                    ascii_filename = f"task_{task_id}_file{original_ext}"
            
            headers = {
                "Content-Disposition": f'attachment; filename="{ascii_filename}"; filename*=UTF-8\'\'{encoded_filename}',
                "Content-Length": str(file_info.file_size),
                "Content-Type": file_info.mime_type or "application/octet-stream"
            }
            
            print(f"📤 开始下载文件: {file_info.original_name}")
            
            return StreamingResponse(
                iterfile(), 
                media_type=file_info.mime_type or "application/octet-stream",
                headers=headers
            )
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ 文件下载失败: {e}")
            raise HTTPException(500, f"文件下载失败: {str(e)}")
    
    def get_recovery_status(
        self,
        current_user: User = Depends(BaseView.get_current_user),
        db: Session = Depends(get_db)
    ) -> dict:
        """获取任务恢复状态"""
        from app.services.task_recovery_service import task_recovery_service
        return task_recovery_service.get_recovery_status(db)
    
    async def recover_timeout_tasks(
        self,
        current_user: User = Depends(BaseView.get_current_user),
        db: Session = Depends(get_db)
    ) -> dict:
        """恢复超时任务（管理员功能）"""
        if not (current_user.is_admin or current_user.is_system_admin):
            raise HTTPException(403, "权限不足，仅管理员可执行此操作")
        
        from app.services.task_recovery_service import task_recovery_service
        recovered_count = await task_recovery_service.check_and_recover_timeout_tasks(db)
        
        return {
            "success": True,
            "message": f"已恢复 {recovered_count} 个超时任务",
            "recovered_count": recovered_count
        }
    
    async def schedule_pending_tasks(
        self,
        current_user: User = Depends(BaseView.get_current_user),
        db: Session = Depends(get_db)
    ) -> dict:
        """手动调度待处理任务（管理员功能）"""
        if not (current_user.is_admin or current_user.is_system_admin):
            raise HTTPException(403, "权限不足，仅管理员可执行此操作")
        
        from app.services.task_recovery_service import task_recovery_service
        scheduled_count = await task_recovery_service.schedule_pending_tasks_if_available(db)
        
        return {
            "success": True,
            "message": f"已调度 {scheduled_count} 个待处理任务",
            "scheduled_count": scheduled_count
        }
    
    def get_task_issues(
        self,
        task_id: int,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        severity: Optional[str] = None,
        issue_type: Optional[str] = None,
        feedback_status: Optional[str] = None,
        sort_by: Optional[str] = "id",
        sort_order: Optional[str] = "desc",
        current_user: User = Depends(BaseView.get_current_user),
        db: Session = Depends(get_db)
    ) -> PaginatedResponse[IssueResponse]:
        """分页获取任务的问题列表"""
        # 构建分页参数
        params = PaginationParams(
            page=page,
            page_size=page_size,
            search=search,
            severity=severity,
            issue_type=issue_type,
            feedback_status=feedback_status,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        service = TaskService(db)
        
        # 检查任务访问权限
        from app.repositories.task import TaskRepository
        task_repo = TaskRepository(db)
        task = task_repo.get_by_id(task_id)
        if not task:
            raise HTTPException(404, "任务不存在")
        
        self.check_task_access_with_permission_service(task_id, current_user, db, 'read')
        
        return service.get_task_issues_paginated(task_id, params)
    
    def get_db_monitor_status(
        self,
        current_user: User = Depends(BaseView.get_current_user),
        db: Session = Depends(get_db)
    ) -> dict:
        """获取数据库连接监控状态（管理员功能）"""
        if not (current_user.is_admin or current_user.is_system_admin):
            raise HTTPException(403, "权限不足，仅管理员可查看数据库监控状态")
        
        from app.core.database import get_db_monitor_status
        return get_db_monitor_status()
    
    async def get_queue_status(
        self,
        current_user: User = Depends(BaseView.get_current_user),
        db: Session = Depends(get_db)
    ) -> dict:
        """获取队列状态信息（管理员功能）"""
        if not (current_user.is_admin or current_user.is_system_admin):
            raise HTTPException(403, "权限不足，仅管理员可查看队列状态")
        
        from app.services.database_queue_service import get_database_queue_service
        queue_service = get_database_queue_service()
        return await queue_service.get_queue_status()
    
    async def get_user_queue_status(
        self,
        user_id: int,
        current_user: User = Depends(BaseView.get_current_user),
        db: Session = Depends(get_db)
    ) -> dict:
        """获取用户队列状态"""
        # 用户只能查看自己的状态，管理员可以查看任何用户的状态
        if user_id != current_user.id and not (current_user.is_admin or current_user.is_system_admin):
            raise HTTPException(403, "权限不足，只能查看自己的队列状态")
        
        from app.services.database_queue_service import get_database_queue_service
        queue_service = get_database_queue_service()
        return await queue_service.get_user_queue_status(user_id)
    
    def get_task_statistics(
        self,
        current_user: User = Depends(BaseView.get_current_user),
        db: Session = Depends(get_db)
    ) -> dict:
        """获取任务统计数据（临时移除缓存避免生产环境认证问题）"""
        try:
            # 额外的认证检查，确保用户有效
            if not current_user or not hasattr(current_user, 'id'):
                from fastapi import HTTPException
                raise HTTPException(status_code=401, detail="用户认证无效")
            
            service = TaskService(db)
            # 管理员可以查看所有任务统计，普通用户只能查看自己的任务统计
            if hasattr(current_user, 'is_admin') and current_user.is_admin:
                return service.get_task_statistics(user_id=None)
            else:
                return service.get_task_statistics(user_id=current_user.id)
                
        except Exception as e:
            print(f"❌ 获取任务统计失败: {e}")
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail=f"获取统计数据失败: {str(e)}")


# 创建视图实例并导出router
task_view = TaskView()
router = task_view.router