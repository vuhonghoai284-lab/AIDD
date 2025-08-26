"""
任务业务逻辑层
"""
import os
import hashlib
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException
import asyncio

from app.repositories.task import TaskRepository
from app.repositories.issue import IssueRepository
from app.repositories.ai_output import AIOutputRepository
from app.repositories.file_info import FileInfoRepository
from app.repositories.ai_model import AIModelRepository
from app.repositories.user import UserRepository
from app.dto.task import TaskResponse, TaskDetail
from app.dto.issue import IssueResponse
from app.core.config import get_settings
from app.services.interfaces.task_service import ITaskService
from datetime import datetime


class TaskService(ITaskService):
    """任务服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.task_repo = TaskRepository(db)
        self.issue_repo = IssueRepository(db)
        self.ai_output_repo = AIOutputRepository(db)
        self.file_repo = FileInfoRepository(db)
        self.model_repo = AIModelRepository(db)
        self.user_repo = UserRepository(db)
        self.settings = get_settings()
    
    async def create_task(self, file: UploadFile, title: Optional[str] = None, model_index: Optional[int] = None, user_id: Optional[int] = None) -> TaskResponse:
        """创建任务"""
        # 验证文件
        file_settings = self.settings.file_settings
        allowed_exts = ['.' + ext for ext in file_settings.get('allowed_extensions', ['pdf', 'docx', 'md'])]
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_exts:
            raise HTTPException(400, f"不支持的文件类型: {file_ext}")
        
        # 读取文件内容
        content = await file.read()
        file_size = len(content)
        max_size = file_settings.get('max_file_size', 10485760)
        if file_size > max_size:
            raise HTTPException(400, f"文件大小超过限制: {file_size / 1024 / 1024:.2f}MB")
        
        # 计算文件哈希
        content_hash = hashlib.sha256(content).hexdigest()
        
        # 检查文件是否已存在
        existing_file = self.file_repo.get_by_hash(content_hash)
        if existing_file:
            # 文件已存在，复用文件记录
            file_info = existing_file
        else:
            # 保存新文件
            file_name = file.filename
            upload_dir = self.settings.upload_dir
            os.makedirs(upload_dir, exist_ok=True)
            
            # 生成唯一文件名
            timestamp = datetime.now().timestamp()
            stored_name = f"{timestamp}_{file_name}"
            file_path = os.path.join(upload_dir, stored_name)
            
            with open(file_path, 'wb') as f:
                f.write(content)
            
            # 创建文件信息记录
            file_info = self.file_repo.create(
                original_name=file_name,
                stored_name=stored_name,
                file_path=file_path,
                file_size=file_size,
                file_type=file_ext[1:],
                mime_type=file.content_type or 'application/octet-stream',
                content_hash=content_hash,
                encoding='utf-8',  # 默认编码，实际应该检测
                is_processed='pending'
            )
        
        # 获取AI模型
        if model_index is not None:
            # 使用用户选择的模型索引
            active_models = self.model_repo.get_active_models()
            print(f"🎯 用户选择模型索引: {model_index}, 可用模型数量: {len(active_models)}")
            if model_index < len(active_models):
                ai_model = active_models[model_index]
                print(f"✅ 使用用户选择的模型: {ai_model.label}")
            else:
                # 索引超出范围，使用默认模型
                ai_model = self.model_repo.get_default_model()
                print(f"⚠️ 模型索引超出范围，使用默认模型: {ai_model.label if ai_model else 'None'}")
        else:
            # 使用默认模型
            ai_model = self.model_repo.get_default_model()
            print(f"🔧 未指定模型，使用默认模型: {ai_model.label if ai_model else 'None'}")
        
        if not ai_model:
            raise HTTPException(400, "没有可用的AI模型")
        
        # 创建任务记录
        task = self.task_repo.create(
            title=title or os.path.splitext(file.filename)[0],
            status='pending',
            progress=0,
            user_id=user_id,
            file_id=file_info.id,
            model_id=ai_model.id
        )
        
        # 异步处理任务 - 使用新的责任链处理器
        try:
            from app.services.new_task_processor import NewTaskProcessor
            processor = NewTaskProcessor(self.db)
            # 在测试环境中，可能没有运行的事件循环，使用try-except处理
            try:
                asyncio.create_task(processor.process_task(task.id))
                print(f"✅ 后台任务已启动，任务ID: {task.id}")
            except RuntimeError as e:
                # 没有运行的事件循环，在测试环境中是正常的
                print(f"⚠️ 无法启动后台任务（测试环境）: {e}")
                # 在测试环境中，我们可以选择同步运行或者跳过
                print(f"📝 任务 {task.id} 已创建，等待手动处理")
        except Exception as e:
            print(f"❌ 启动后台任务时出错: {e}")
            # 不抛出异常，让任务创建成功，只是处理会延后
        
        # 获取关联数据构建响应
        file_info = self.file_repo.get_by_id(task.file_id) if task.file_id else None
        ai_model = self.model_repo.get_by_id(task.model_id) if task.model_id else None
        user_info = self.user_repo.get_by_id(task.user_id) if task.user_id else None
        issue_count = self.task_repo.count_issues(task.id)
        processed_issues = self.task_repo.count_processed_issues(task.id)
        return TaskResponse.from_task_with_relations(task, file_info, ai_model, user_info, issue_count, processed_issues)
    
    def get_all_tasks(self) -> List[TaskResponse]:
        """获取所有任务"""
        tasks = self.task_repo.get_all()
        result = []
        for task in tasks:
            file_info = self.file_repo.get_by_id(task.file_id) if task.file_id else None
            ai_model = self.model_repo.get_by_id(task.model_id) if task.model_id else None
            user_info = self.user_repo.get_by_id(task.user_id) if task.user_id else None
            issue_count = self.task_repo.count_issues(task.id)
            processed_issues = self.task_repo.count_processed_issues(task.id)
            task_resp = TaskResponse.from_task_with_relations(task, file_info, ai_model, user_info, issue_count, processed_issues)
            result.append(task_resp)
        return result
    
    def get_all(self) -> List[TaskResponse]:
        """获取所有任务（基础接口方法）"""
        return self.get_all_tasks()
    
    def get_user_tasks(self, user_id: int) -> List[TaskResponse]:
        """获取指定用户的任务"""
        tasks = self.task_repo.get_by_user_id(user_id)
        result = []
        for task in tasks:
            file_info = self.file_repo.get_by_id(task.file_id) if task.file_id else None
            ai_model = self.model_repo.get_by_id(task.model_id) if task.model_id else None
            user_info = self.user_repo.get_by_id(task.user_id) if task.user_id else None
            issue_count = self.task_repo.count_issues(task.id)
            processed_issues = self.task_repo.count_processed_issues(task.id)
            task_resp = TaskResponse.from_task_with_relations(task, file_info, ai_model, user_info, issue_count, processed_issues)
            result.append(task_resp)
        return result
    
    def get_task_detail(self, task_id: int) -> TaskDetail:
        """获取任务详情"""
        print(f"🔍 正在查找任务: {task_id}")
        task = self.task_repo.get_by_id(task_id)
        print(f"🔍 找到任务: {task}")
        if not task:
            print(f"❌ 任务 {task_id} 不存在")
            raise HTTPException(404, "任务不存在")
        
        issues = self.issue_repo.get_by_task_id(task_id)
        
        file_info = self.file_repo.get_by_id(task.file_id) if task.file_id else None
        ai_model = self.model_repo.get_by_id(task.model_id) if task.model_id else None
        user_info = self.user_repo.get_by_id(task.user_id) if task.user_id else None
        processed_issues = self.task_repo.count_processed_issues(task_id)
        task_resp = TaskResponse.from_task_with_relations(task, file_info, ai_model, user_info, len(issues), processed_issues)
        
        return TaskDetail(
            task=task_resp,
            issues=[IssueResponse.from_orm(issue) for issue in issues]
        )
    
    def delete(self, entity_id: int) -> bool:
        """删除任务（基础接口方法）"""
        return self.delete_task(entity_id)
    
    def delete_task(self, task_id: int) -> bool:
        """删除任务"""
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise HTTPException(404, "任务不存在")
        
        # 获取关联的文件信息（在删除任务之前）
        file_info = None
        if hasattr(task, 'file_id') and task.file_id:
            file_info = self.file_repo.get_by_id(task.file_id)
        
        # 先删除任务（这会删除相关的问题和AI输出）
        task_deleted = self.task_repo.delete(task_id)
        
        # 如果任务删除成功且有关联文件，检查是否可以删除文件
        if task_deleted and file_info:
            # 检查是否还有其他任务使用这个文件
            from app.models import Task
            other_tasks_count = self.db.query(Task).filter(Task.file_id == file_info.id).count()
            
            # 如果没有其他任务使用这个文件，则删除文件
            if other_tasks_count == 0:
                if os.path.exists(file_info.file_path):
                    os.remove(file_info.file_path)
                self.file_repo.delete(file_info.id)
        
        return task_deleted
    
    def create(self, **kwargs) -> TaskResponse:
        """创建任务实体（同步版本）"""
        # 这里实现同步的创建逻辑，不过不常用
        raise NotImplementedError("请使用 create_task 方法")
    
    def get_by_id(self, entity_id: int) -> Optional[TaskResponse]:
        """根据ID获取任务"""
        task = self.task_repo.get_by_id(entity_id)
        if not task:
            return None
        
        file_info = self.file_repo.get_by_id(task.file_id) if task.file_id else None
        ai_model = self.model_repo.get_by_id(task.model_id) if task.model_id else None
        user_info = self.user_repo.get_by_id(task.user_id) if task.user_id else None
        issue_count = self.task_repo.count_issues(task.id)
        processed_issues = self.task_repo.count_processed_issues(task.id)
        return TaskResponse.from_task_with_relations(task, file_info, ai_model, user_info, issue_count, processed_issues)
    
    def update(self, entity_id: int, **kwargs) -> Optional[TaskResponse]:
        """更新任务"""
        updated_task = self.task_repo.update(entity_id, **kwargs)
        if not updated_task:
            return None
        
        file_info = self.file_repo.get_by_id(updated_task.file_id) if updated_task.file_id else None
        ai_model = self.model_repo.get_by_id(updated_task.model_id) if updated_task.model_id else None
        user_info = self.user_repo.get_by_id(updated_task.user_id) if updated_task.user_id else None
        issue_count = self.task_repo.count_issues(updated_task.id)
        processed_issues = self.task_repo.count_processed_issues(updated_task.id)
        return TaskResponse.from_task_with_relations(updated_task, file_info, ai_model, user_info, issue_count, processed_issues)