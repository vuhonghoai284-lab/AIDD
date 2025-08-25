"""
新任务处理器 - 使用责任链模式
"""
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.repositories.task import TaskRepository
from app.repositories.issue import IssueRepository
from app.repositories.ai_output import AIOutputRepository
from app.repositories.file_info import FileInfoRepository
from app.repositories.ai_model import AIModelRepository
from app.core.config import get_settings
from app.services.websocket import manager
from app.models import TaskLog
from app.services.processing_chain import TaskProcessingChain
from app.services.ai_service_providers.service_provider_factory import ai_service_provider_factory


class NewTaskProcessor:
    """新任务处理器 - 使用责任链模式"""
    
    def __init__(self, db: Session):
        self.db = db
        self.task_repo = TaskRepository(db)
        self.issue_repo = IssueRepository(db)
        self.ai_output_repo = AIOutputRepository(db)
        self.file_repo = FileInfoRepository(db)
        self.model_repo = AIModelRepository(db)
        self.settings = get_settings()
        self.start_time = None  # 记录任务开始时间
    
    async def process_task(self, task_id: int):
        """处理任务"""
        try:
            # 记录任务开始时间（使用UTC时间戳）
            self.start_time = time.time()
            
            # 记录开始日志
            await self._log(task_id, "INFO", "开始处理任务", "初始化", 0)
            
            # 获取任务信息
            task = self.task_repo.get(task_id)
            if not task:
                raise ValueError(f"任务不存在: {task_id}")
            
            # 更新状态为处理中
            self.task_repo.update(task_id, status="processing", progress=10)
            await manager.send_status(task_id, "processing")
            
            # 准备处理上下文
            context = await self._prepare_context(task_id, task)
            
            # 获取任务关联的AI模型并找到对应的索引
            task_model_index = self.settings.default_model_index  # 默认值
            if task.model_id:
                # 根据model_id查找模型配置
                ai_model = self.model_repo.get_by_id(task.model_id)
                if ai_model:
                    # 在settings的模型列表中查找对应的索引
                    for index, model_config in enumerate(self.settings.ai_models):
                        config_model_name = model_config.get('config', {}).get('model')
                        config_provider = model_config.get('provider')
                        
                        # 使用model_name和provider进行匹配
                        if (config_model_name == ai_model.model_name and 
                            config_provider == ai_model.provider):
                            task_model_index = index
                            self.logger.info(f"🎯 找到用户选择的模型: {ai_model.label} (model: {ai_model.model_name}, provider: {ai_model.provider}, 索引: {index})")
                            break
                    else:
                        self.logger.warning(f"⚠️ 未找到匹配的模型配置，使用默认模型。模型信息: label={ai_model.label}, model={ai_model.model_name}, provider={ai_model.provider}")
                        self.logger.info("可用模型配置:")
                        for i, cfg in enumerate(self.settings.ai_models):
                            cfg_model = cfg.get('config', {}).get('model', 'unknown')
                            cfg_provider = cfg.get('provider', 'unknown')
                            self.logger.info(f"  [{i}] {cfg.get('label', 'unknown')} - {cfg_provider} ({cfg_model})")
                else:
                    self.logger.warning(f"⚠️ 任务关联的模型不存在(model_id={task.model_id})，使用默认模型")
            
            # 创建AI服务提供者
            ai_service_provider = ai_service_provider_factory.create_provider(
                settings=self.settings,
                model_index=task_model_index,
                db_session=self.db
            )
            
            # 创建处理链
            processing_chain = TaskProcessingChain(ai_service_provider)
            
            # 执行处理链
            await self._log(task_id, "INFO", f"使用AI服务: {ai_service_provider.get_provider_name()}", "初始化", 10)
            
            async def progress_callback(message: str, progress: int):
                """进度回调函数"""
                # 记录日志并推送消息
                await self._log(task_id, "INFO", message, "处理中", progress)
                # 更新任务进度
                self.task_repo.update(task_id, progress=progress)
                # 发送进度状态更新（不重复发送消息）
                await manager.send_status(task_id, "processing")
            
            context['progress_callback'] = progress_callback
            
            # 执行完整的处理链
            result = await processing_chain.execute(context, progress_callback)
            
            if not result.success:
                raise ValueError(f"任务处理失败: {result.error}")
            
            # 保存处理结果
            await self._save_processing_results(task_id, context, result)
            
            # 完成任务
            # 使用任务实际开始时间计算耗时，避免时区转换问题
            processing_time = time.time() - self.start_time if self.start_time else 0
            self.task_repo.update(
                task_id, 
                status="completed",
                progress=100,
                processing_time=processing_time,
                completed_at=datetime.utcnow()  # 使用UTC时间保持一致性
            )
            await manager.send_progress(task_id, 100, "完成")
            await manager.send_status(task_id, "completed")
            await self._log(task_id, "INFO", f"任务处理完成，耗时{processing_time:.2f}秒", "完成", 100)
            
        except Exception as e:
            # 记录错误
            await self._log(task_id, "ERROR", f"任务处理失败: {str(e)}", "错误", 0)
            await manager.send_status(task_id, "failed")
            self.task_repo.update(
                task_id, 
                status="failed", 
                error_message=str(e)
            )
            raise
    
    async def _prepare_context(self, task_id: int, task) -> Dict[str, Any]:
        """准备处理上下文"""
        context = {
            'task_id': task_id
        }
        
        # 获取文件信息
        file_info = None
        if task.file_id:
            file_info = self.file_repo.get_by_id(task.file_id)
        
        if file_info:
            context['file_path'] = file_info.file_path
            context['file_name'] = file_info.original_name
            await self._log(task_id, "INFO", f"正在处理文档: {file_info.original_name}", "文档解析", 10)
        else:
            context['file_name'] = "测试文档"
            await self._log(task_id, "INFO", "使用测试模式文档", "文档解析", 10)
        
        return context
    
    async def _save_processing_results(self, task_id: int, context: Dict[str, Any], result):
        """保存处理结果"""
        await self._log(task_id, "INFO", "正在保存处理结果", "保存结果", 85)
        
        # 保存文件解析结果（非AI步骤，保存处理记录）
        if 'file_parsing_result' in context:
            self._save_ai_output(
                task_id=task_id,
                operation_type="file_parsing",
                input_text=str(context.get('file_path', 'test')),
                result={
                    'status': 'success',
                    'data': {'content': context['file_parsing_result'][:1000]},  # 只保存前1000字符
                    'processing_stage': 'file_parsing'
                }
            )
        
        # 章节合并结果记录（非AI步骤，保存处理记录）
        if 'section_merge_result' in context:
            original_count = len(context.get('document_processing_result', []))
            merged_count = len(context['section_merge_result'])
            self._save_ai_output(
                task_id=task_id,
                operation_type="section_merge",
                input_text=f"原始章节数: {original_count}",
                result={
                    'status': 'success',
                    'data': {
                        'original_sections_count': original_count,
                        'merged_sections_count': merged_count,
                        'merge_ratio': merged_count / original_count if original_count > 0 else 0,
                        'merged_sections': context['section_merge_result'][:3]  # 保存前3个合并章节的概要
                    },
                    'processing_stage': 'section_merge'
                }
            )
        
        # 保存问题到数据库（问题检测的AI输出已由IssueDetector保存）
        if 'issue_detection_result' in context:
            issues = context['issue_detection_result']
            
            # 保存问题到数据库
            issue_count = len(issues) if issues else 0
            await self._log(task_id, "INFO", f"检测到{issue_count}个问题", "保存结果", 90)
            
            for issue in (issues or []):
                self.issue_repo.create(
                    task_id=task_id,
                    issue_type=issue.get('issue_type', '未知'),
                    description=issue.get('description', ''),
                    location=issue.get('location', ''),
                    severity=issue.get('severity', '一般'),
                    confidence=issue.get('confidence'),
                    suggestion=issue.get('suggestion', ''),
                    original_text=issue.get('original_text'),
                    user_impact=issue.get('user_impact'),
                    reasoning=issue.get('reasoning'),
                    context=issue.get('context')
                )
    
    def _save_ai_output(self, task_id: int, operation_type: str, 
                       input_text: str, result: Dict[str, Any]):
        """保存AI输出结果"""
        self.ai_output_repo.create(
            task_id=task_id,
            operation_type=operation_type,
            input_text=input_text,
            raw_output=result.get('raw_output', json.dumps(result)),
            parsed_output=result.get('data'),
            status=result.get('status', 'success'),
            error_message=result.get('error_message'),
            tokens_used=result.get('tokens_used'),
            processing_time=result.get('processing_time')
        )
    
    async def _log(self, task_id: int, level: str, message: str, stage: str = None, progress: int = None):
        """记录日志并实时推送"""
        # 过滤空消息，避免产生无用的日志记录
        if not message or not str(message).strip():
            return
            
        # 保存到数据库
        log = TaskLog(
            task_id=task_id,
            level=level,
            message=str(message).strip(),
            stage=stage,
            progress=progress
        )
        self.db.add(log)
        self.db.commit()
        
        # 实时推送
        await manager.send_log(task_id, level, message, stage, progress)