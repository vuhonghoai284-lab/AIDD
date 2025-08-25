"""
真实AI服务提供者 - 实现新的抽象接口
"""
from typing import List, Dict, Any, Optional, Callable
from sqlalchemy.orm import Session
from app.services.interfaces.ai_service import IAIServiceProvider, IAIDocumentProcessor, IAIIssueDetector
from app.services.document_processor import DocumentProcessor
from app.services.issue_detector import IssueDetector


class RealAIDocumentProcessor(IAIDocumentProcessor):
    """真实文档处理器适配器"""
    
    def __init__(self, document_processor: DocumentProcessor):
        self.processor = document_processor
    
    async def preprocess_document(self, text: str, task_id: Optional[int] = None, 
                                progress_callback: Optional[Callable] = None) -> List[Dict]:
        """文档预处理 - 章节分割"""
        return await self.processor.preprocess_document(text, task_id, progress_callback)


class RealAIIssueDetector(IAIIssueDetector):
    """真实问题检测器适配器"""
    
    def __init__(self, issue_detector: IssueDetector):
        self.detector = issue_detector
    
    async def detect_issues(self, sections: List[Dict], task_id: Optional[int] = None, 
                          progress_callback: Optional[Callable] = None) -> List[Dict]:
        """问题检测"""
        return await self.detector.detect_issues(sections, task_id, progress_callback)


class RealAIServiceProvider(IAIServiceProvider):
    """真实AI服务提供者"""
    
    def __init__(self, model_config: Dict[str, Any], db_session: Optional[Session] = None):
        self.model_config = model_config
        self.db_session = db_session
        
        # 创建真实的处理器实例
        self._document_processor_impl = DocumentProcessor(model_config, db_session)
        self._issue_detector_impl = IssueDetector(model_config, db_session)
        
        # 创建适配器
        self._document_processor = RealAIDocumentProcessor(self._document_processor_impl)
        self._issue_detector = RealAIIssueDetector(self._issue_detector_impl)
    
    def get_document_processor(self) -> IAIDocumentProcessor:
        """获取文档处理器"""
        return self._document_processor
    
    def get_issue_detector(self) -> IAIIssueDetector:
        """获取问题检测器"""
        return self._issue_detector
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        try:
            # 检查模型配置是否有效
            return (self.model_config is not None and 
                   'api_key' in self.model_config and 
                   self.model_config['api_key'])
        except Exception:
            return False
    
    def get_provider_name(self) -> str:
        """获取服务提供者名称"""
        model_name = self.model_config.get('model', 'unknown')
        provider = self.model_config.get('provider', 'unknown')
        return f"{provider} ({model_name})"
    
    def get_provider_info(self) -> Dict[str, Any]:
        """获取服务提供者信息"""
        return {
            'name': self.get_provider_name(),
            'type': 'real',
            'model': self.model_config.get('model', 'unknown'),
            'provider': self.model_config.get('provider', 'unknown'),
            'api_key_configured': bool(self.model_config.get('api_key')),
            'capabilities': ['document_processing', 'issue_detection']
        }
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            # 简单检查配置是否有效
            return (self.model_config is not None and 
                   'api_key' in self.model_config and 
                   bool(self.model_config['api_key']))
        except Exception:
            return False