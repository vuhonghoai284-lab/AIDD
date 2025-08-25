"""AI服务统一接口 - 整合文档处理和问题检测功能"""
import time
import logging
from typing import List, Dict, Optional, Callable
from sqlalchemy.orm import Session

from app.services.ai_service_factory import ai_service_factory
from app.services.realtime_logger import TaskLoggerAdapter


class AIService:
    """AI服务统一接口 - 提供与原有ai_service.py兼容的接口"""
    
    def __init__(self, db_session: Optional[Session] = None, ai_model_index: Optional[int] = None, settings=None):
        """
        初始化AI服务
        
        Args:
            db_session: 数据库会话
            ai_model_index: 模型索引
            settings: 设置对象
        """
        self.db = db_session
        self.settings = settings
        self.ai_model_index = ai_model_index or (settings.default_model_index if settings else 0)
        
        # 初始化日志
        self.logger = logging.getLogger(f"ai_service.{id(self)}")
        self.logger.setLevel(logging.INFO)
        
        # 确保日志能输出到控制台
        if not self.logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # 获取AI服务组件
        if settings:
            self.services = ai_service_factory.get_service_for_model(
                self.ai_model_index, 
                settings, 
                db_session
            )
        else:
            # 如果没有设置，抛出异常
            raise ValueError("必须提供settings配置")
        
        self.logger.info(f"🤖 AI服务初始化完成，模型索引: {self.ai_model_index}")
        
        # 检查服务状态
        if self.services.get('document_processor') and self.services.get('issue_detector'):
            self.logger.info("✅ AI服务初始化完成")
        else:
            raise ValueError("AI服务初始化失败")
    
    async def preprocess_document(self, text: str, task_id: Optional[int] = None, progress_callback: Optional[Callable] = None) -> List[Dict]:
        """
        预处理文档：章节分割和内容整理
        
        Args:
            text: 文档文本内容
            task_id: 任务ID
            progress_callback: 进度回调函数
            
        Returns:
            章节列表
        """
        self.logger.info("📝 开始文档预处理...")
        
        # 创建任务日志适配器
        if task_id:
            task_logger = ai_service_factory.create_task_logger(task_id, "preprocess")
            await task_logger.info("开始文档预处理", {"text_length": len(text)})
        
        try:
            # 使用文档处理器
            sections = await self.services['document_processor'].preprocess_document(
                text, task_id, progress_callback
            )
            
            if task_id:
                await task_logger.info(f"文档预处理完成，获得 {len(sections)} 个章节")
            
            return sections
            
        except Exception as e:
            self.logger.error(f"❌ 文档预处理失败: {str(e)}")
            if task_id:
                await task_logger.error(f"文档预处理失败: {str(e)}")
            
            raise e
    
    async def detect_issues(self, text: str, progress_callback: Optional[Callable] = None, task_id: Optional[int] = None) -> List[Dict]:
        """
        检测文档问题
        
        Args:
            text: 文档文本内容
            progress_callback: 进度回调函数
            task_id: 任务ID
            
        Returns:
            问题列表
        """
        self.logger.info("🔍 开始问题检测...")
        
        # 创建任务日志适配器
        if task_id:
            task_logger = ai_service_factory.create_task_logger(task_id, "detect_issues")
            await task_logger.info("开始问题检测", {"text_length": len(text)})
        
        try:
            # 先进行文档预处理
            sections = await self.preprocess_document(text, task_id, progress_callback)
            
            # 使用问题检测器
            issues = await self.services['issue_detector'].detect_issues(
                sections, task_id, progress_callback
            )
            
            if task_id:
                await task_logger.info(f"问题检测完成，发现 {len(issues)} 个问题")
            
            return issues
            
        except Exception as e:
            self.logger.error(f"❌ 问题检测失败: {str(e)}")
            if task_id:
                await task_logger.error(f"问题检测失败: {str(e)}")
            
            raise e
    
    
