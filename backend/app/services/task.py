"""
任务业务逻辑层
"""
import os
import hashlib
import time
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
from app.dto.pagination import PaginationParams, PaginatedResponse
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
        
        # 异步处理任务 - 使用优化的并发安全处理器
        try:
            from app.services.new_task_processor import NewTaskProcessor
            # 不传递数据库会话，让处理器自己创建独立的会话
            processor = NewTaskProcessor()
            
            # 检查当前是否在异步环境中
            try:
                # 尝试获取当前事件循环
                loop = asyncio.get_running_loop()
                # 在独立的任务中处理，避免阻塞主线程
                task_future = asyncio.create_task(
                    self._safe_process_task(processor, task.id)
                )
                print(f"✅ 后台任务已启动，任务ID: {task.id}")
            except RuntimeError:
                # 没有运行的事件循环，在测试环境或同步环境中是正常的
                print(f"⚠️ 无法启动后台任务（非异步环境），任务ID: {task.id}")
                print(f"📝 任务已创建，等待异步环境处理")
                
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
    
    async def _safe_process_task(self, processor, task_id: int):
        """安全的任务处理包装器，处理异常和错误恢复"""
        try:
            await processor.process_task(task_id)
        except Exception as e:
            print(f"❌ 任务 {task_id} 处理失败: {e}")
            # 这里可以添加更多的错误恢复逻辑，比如重试机制
            # 或者发送错误通知等
            
    async def batch_create_tasks(self, files_data: List[dict], user_id: Optional[int] = None, max_concurrent: int = 5) -> List[TaskResponse]:
        """批量并发创建任务
        
        Args:
            files_data: 文件数据列表，每个元素包含file, title, model_index等
            user_id: 用户ID
            max_concurrent: 最大并发数，默认5个
            
        Returns:
            List[TaskResponse]: 创建的任务列表
        """
        print(f"🚀 开始批量创建 {len(files_data)} 个任务，最大并发数: {max_concurrent}")
        
        # 使用信号量控制并发数
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def create_single_task(file_data: dict) -> TaskResponse:
            """创建单个任务（使用独立数据库会话，避免锁竞争）"""
            async with semaphore:
                from app.core.database import get_independent_db_session
                # 使用独立会话函数，包含SQLite优化设置
                db_session = get_independent_db_session()
                try:
                    # 创建独立的TaskService实例
                    task_service = TaskService(db_session)
                    result = await task_service.create_task(
                        file=file_data.get('file'),
                        title=file_data.get('title'),
                        model_index=file_data.get('model_index'),
                        user_id=user_id
                    )
                    return result
                except Exception as e:
                    print(f"❌ 创建任务失败: {e}")
                    # 发生异常时回滚事务
                    try:
                        db_session.rollback()
                    except:
                        pass
                    raise
                finally:
                    # 确保数据库会话正确关闭
                    try:
                        db_session.close()
                    except:
                        pass
        
        # 并发创建所有任务
        start_time = time.time()
        tasks = await asyncio.gather(
            *[create_single_task(file_data) for file_data in files_data],
            return_exceptions=True
        )
        
        # 处理结果
        successful_tasks = []
        failed_tasks = []
        
        for i, result in enumerate(tasks):
            if isinstance(result, Exception):
                failed_tasks.append({
                    'index': i,
                    'file': files_data[i].get('file', {}).get('filename', 'unknown'),
                    'error': str(result)
                })
            else:
                successful_tasks.append(result)
        
        total_time = time.time() - start_time
        print(f"✅ 批量创建完成，耗时: {total_time:.2f}s")
        print(f"   成功: {len(successful_tasks)} 个")
        print(f"   失败: {len(failed_tasks)} 个")
        
        if failed_tasks:
            print("❌ 失败的任务:")
            for failed in failed_tasks:
                print(f"   - {failed['file']}: {failed['error']}")
        
        return successful_tasks
    
    def get_all_tasks(self) -> List[TaskResponse]:
        """获取所有任务（性能优化版）"""
        print("🚀 开始获取任务列表（使用性能优化查询）...")
        start_time = time.time()
        
        # 1. 使用JOIN预加载关联数据，避免N+1查询
        tasks = self.task_repo.get_all_with_relations()
        print(f"📊 查询到 {len(tasks)} 个任务，耗时: {(time.time() - start_time)*1000:.1f}ms")
        
        if not tasks:
            return []
        
        # 2. 批量统计问题数量，避免逐个查询
        batch_start = time.time()
        task_ids = [task.id for task in tasks]
        issue_stats = self.task_repo.batch_count_issues(task_ids)
        print(f"📊 批量统计问题数量，耗时: {(time.time() - batch_start)*1000:.1f}ms")
        
        # 3. 构建响应对象
        result = []
        for task in tasks:
            # 关联数据已预加载，无需额外查询
            file_info = task.file_info
            ai_model = task.ai_model  
            user_info = task.user
            
            # 从批量统计结果中获取问题数量
            stats = issue_stats.get(task.id, {"issue_count": 0, "processed_issues": 0})
            issue_count = stats["issue_count"]
            processed_issues = stats["processed_issues"]
            
            task_resp = TaskResponse.from_task_with_relations(
                task, file_info, ai_model, user_info, issue_count, processed_issues
            )
            result.append(task_resp)
        
        total_time = time.time() - start_time
        print(f"✅ 任务列表获取完成，总耗时: {total_time*1000:.1f}ms")
        return result
    
    def get_paginated_tasks(self, params: PaginationParams, user_id: Optional[int] = None) -> PaginatedResponse[TaskResponse]:
        """分页获取任务列表（高性能版）"""
        print(f"🚀 开始分页获取任务列表: page={params.page}, size={params.page_size}, user_id={user_id}")
        start_time = time.time()
        
        # 检查数据库会话状态
        if not self.db.is_active:
            print("⚠️ 数据库会话已失效，重新获取")
            from app.core.database import SessionLocal
            self.db = SessionLocal()
            # 重新初始化所有仓库
            self.task_repo = TaskRepository(self.db)
            self.issue_repo = IssueRepository(self.db)
            self.ai_output_repo = AIOutputRepository(self.db)
            self.file_repo = FileInfoRepository(self.db)
            self.model_repo = AIModelRepository(self.db)
            self.user_repo = UserRepository(self.db)
        
        try:
            # 1. 分页查询任务（设置查询超时）
            query_start = time.time()
            tasks, total = self.task_repo.get_paginated_tasks(params, user_id)
            query_time = (time.time() - query_start) * 1000
            print(f"📊 分页查询完成: {len(tasks)}/{total} 任务，耗时: {query_time:.1f}ms")
            
            # 如果查询时间过长，记录警告
            if query_time > 5000:  # 5秒
                print(f"⚠️ 分页查询耗时异常: {query_time:.1f}ms，可能存在数据库锁竞争")
            
            if not tasks:
                return PaginatedResponse.create([], total, params.page, params.page_size)
            
            # 2. 批量统计问题数量（优化版）
            batch_start = time.time()
            task_ids = [task.id for task in tasks]
            
            # 检查是否有大量未完成的任务（可能影响问题统计性能）
            pending_processing_count = sum(1 for task in tasks if task.status in ['pending', 'processing'])
            if pending_processing_count > 5:
                print(f"⚠️ 检测到 {pending_processing_count} 个正在处理的任务，可能影响查询性能")
            
            issue_stats = self.task_repo.batch_count_issues(task_ids)
            batch_time = (time.time() - batch_start) * 1000
            print(f"📊 批量统计问题数量，耗时: {batch_time:.1f}ms")
            
            # 3. 构建响应对象
            response_start = time.time()
            result = []
            for task in tasks:
                # 关联数据已预加载，无需额外查询
                file_info = task.file_info
                ai_model = task.ai_model
                user_info = task.user
                
                # 从批量统计结果中获取问题数量
                issue_stat = issue_stats.get(task.id, {"issue_count": 0, "processed_issues": 0})
                
                # 使用from_task_with_relations方法确保所有字段正确设置
                task_resp = TaskResponse.from_task_with_relations(
                    task, file_info, ai_model, user_info, 
                    issue_stat["issue_count"], issue_stat["processed_issues"]
                )
                result.append(task_resp)
            
            response_time = (time.time() - response_start) * 1000
            total_time = (time.time() - start_time) * 1000
            print(f"📄 响应构建耗时: {response_time:.1f}ms")
            print(f"✅ 分页任务获取完成，总耗时: {total_time:.1f}ms")
            
            # 如果总耗时超过10秒，记录详细性能信息
            if total_time > 10000:
                print(f"🚨 分页查询性能警告：总耗时 {total_time:.1f}ms")
                print(f"   - 查询耗时: {query_time:.1f}ms")
                print(f"   - 统计耗时: {batch_time:.1f}ms") 
                print(f"   - 构建耗时: {response_time:.1f}ms")
                print(f"   - 任务数量: {len(tasks)}")
                print(f"   - 处理中任务: {pending_processing_count}")
            
            return PaginatedResponse.create(result, total, params.page, params.page_size)
            
        except Exception as e:
            total_time = (time.time() - start_time) * 1000
            print(f"❌ 分页查询异常，耗时: {total_time:.1f}ms，错误: {e}")
            raise
    
    def get_all(self) -> List[TaskResponse]:
        """获取所有任务（基础接口方法）"""
        return self.get_all_tasks()
    
    def get_user_tasks(self, user_id: int) -> List[TaskResponse]:
        """获取指定用户的任务（性能优化版）"""
        print(f"🚀 开始获取用户 {user_id} 的任务列表（使用性能优化查询）...")
        start_time = time.time()
        
        # 1. 使用JOIN预加载关联数据，避免N+1查询
        tasks = self.task_repo.get_by_user_id_with_relations(user_id)
        print(f"📊 查询到用户 {user_id} 的 {len(tasks)} 个任务，耗时: {(time.time() - start_time)*1000:.1f}ms")
        
        if not tasks:
            return []
        
        # 2. 批量统计问题数量，避免逐个查询
        batch_start = time.time()
        task_ids = [task.id for task in tasks]
        issue_stats = self.task_repo.batch_count_issues(task_ids)
        print(f"📊 批量统计问题数量，耗时: {(time.time() - batch_start)*1000:.1f}ms")
        
        # 3. 构建响应对象
        result = []
        for task in tasks:
            # 关联数据已预加载，无需额外查询
            file_info = task.file_info
            ai_model = task.ai_model
            user_info = task.user
            
            # 从批量统计结果中获取问题数量
            stats = issue_stats.get(task.id, {"issue_count": 0, "processed_issues": 0})
            issue_count = stats["issue_count"]
            processed_issues = stats["processed_issues"]
            
            task_resp = TaskResponse.from_task_with_relations(
                task, file_info, ai_model, user_info, issue_count, processed_issues
            )
            result.append(task_resp)
        
        total_time = time.time() - start_time
        print(f"✅ 用户任务列表获取完成，总耗时: {total_time*1000:.1f}ms")
        return result
    
    def get_task_detail(self, task_id: int) -> TaskDetail:
        """获取任务详情（懒加载模式，不包含问题列表）"""
        print(f"🚀 开始获取任务详情: {task_id}（懒加载模式）...")
        start_time = time.time()
        
        # 1. 使用JOIN查询预加载关联数据，避免N+1查询
        task = self.task_repo.get_by_id_with_relations(task_id)
        print(f"📊 任务查询耗时: {(time.time() - start_time)*1000:.1f}ms")
        
        if not task:
            print(f"❌ 任务 {task_id} 不存在")
            raise HTTPException(404, "任务不存在")
        
        # 2. 获取问题统计摘要而非完整问题列表
        stats_start = time.time()
        
        # 统计总问题数和已处理问题数
        total_issues = self.task_repo.count_issues(task_id)
        processed_issues = self.task_repo.count_processed_issues(task_id)
        
        # 按严重程度统计
        from sqlalchemy import func
        from app.models import Issue
        severity_stats = dict(self.db.query(Issue.severity, func.count(Issue.id))
                            .filter(Issue.task_id == task_id)
                            .group_by(Issue.severity).all())
        
        # 按问题类型统计
        type_stats = dict(self.db.query(Issue.issue_type, func.count(Issue.id))
                         .filter(Issue.task_id == task_id)
                         .group_by(Issue.issue_type).all())
        
        # 按反馈状态统计
        feedback_stats = {
            'processed': processed_issues,
            'unprocessed': total_issues - processed_issues,
            'accept': self.db.query(Issue).filter(Issue.task_id == task_id, Issue.feedback_type == 'accept').count(),
            'reject': self.db.query(Issue).filter(Issue.task_id == task_id, Issue.feedback_type == 'reject').count(),
        }
        
        issue_summary = {
            'total': total_issues,
            'processed': processed_issues,
            'unprocessed': total_issues - processed_issues,
            'by_severity': severity_stats,
            'by_type': type_stats,
            'by_feedback': feedback_stats,
        }
        
        print(f"📊 问题统计耗时: {(time.time() - stats_start)*1000:.1f}ms")
        
        # 3. 统计AI输出数量
        ai_outputs_start = time.time()
        
        from app.models import AIOutput
        total_ai_outputs = self.db.query(AIOutput).filter(AIOutput.task_id == task_id).count()
        successful_ai_outputs = self.db.query(AIOutput).filter(
            AIOutput.task_id == task_id,
            AIOutput.status == 'success'
        ).count()
        
        ai_output_summary = {
            'total': total_ai_outputs,
            'successful': successful_ai_outputs,
            'failed': total_ai_outputs - successful_ai_outputs
        }
        
        print(f"📊 AI输出统计耗时: {(time.time() - ai_outputs_start)*1000:.1f}ms")
        
        # 4. 关联数据已预加载，无需额外查询
        file_info = task.file_info
        ai_model = task.ai_model  
        user_info = task.user
        
        task_resp = TaskResponse.from_task_with_relations(
            task, file_info, ai_model, user_info, total_issues, processed_issues
        )
        
        total_time = time.time() - start_time
        print(f"✅ 任务详情获取完成（懒加载），总耗时: {total_time*1000:.1f}ms")
        
        return TaskDetail(
            task=task_resp,
            issue_summary=issue_summary,
            ai_output_summary=ai_output_summary
        )
    
    def get_task_issues_paginated(self, task_id: int, params: PaginationParams) -> PaginatedResponse['IssueResponse']:
        """分页获取任务的问题列表"""
        print(f"🚀 开始分页获取任务 {task_id} 的问题: page={params.page}, size={params.page_size}")
        start_time = time.time()
        
        # 验证任务是否存在
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise HTTPException(404, "任务不存在")
        
        # 分页查询问题
        issues, total = self.issue_repo.get_paginated_issues_by_task_id(task_id, params)
        
        # 转换为响应对象
        issue_responses = [IssueResponse.model_validate(issue) for issue in issues]
        
        total_time = time.time() - start_time
        print(f"✅ 问题分页查询完成: {len(issue_responses)}/{total}，耗时: {total_time*1000:.1f}ms")
        
        return PaginatedResponse.create(issue_responses, total, params.page, params.page_size)
    
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
        """根据ID获取任务（性能优化版）"""
        print(f"🚀 查询任务 {entity_id}（使用性能优化查询）...")
        start_time = time.time()
        
        # 使用JOIN预加载关联数据，避免N+1查询
        task = self.task_repo.get_by_id_with_relations(entity_id)
        if not task:
            return None
        
        # 关联数据已预加载，无需额外查询
        file_info = task.file_info
        ai_model = task.ai_model
        user_info = task.user
        
        issue_count = self.task_repo.count_issues(task.id)
        processed_issues = self.task_repo.count_processed_issues(task.id)
        
        result = TaskResponse.from_task_with_relations(task, file_info, ai_model, user_info, issue_count, processed_issues)
        
        total_time = time.time() - start_time
        print(f"✅ 任务查询完成，耗时: {total_time*1000:.1f}ms")
        return result
    
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