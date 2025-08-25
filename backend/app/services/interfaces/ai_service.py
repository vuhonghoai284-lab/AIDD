"""
AI服务抽象接口
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable


class IAIDocumentProcessor(ABC):
    """文档处理抽象接口"""
    
    @abstractmethod
    async def preprocess_document(
        self, 
        text: str, 
        task_id: Optional[int] = None,
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """
        预处理文档，返回章节列表
        
        Args:
            text: 文档文本内容
            task_id: 任务ID，用于日志追踪
            progress_callback: 进度回调函数
            
        Returns:
            章节列表，格式：[{'section_title': str, 'content': str, 'level': int}]
        """
        pass


class IAIIssueDetector(ABC):
    """问题检测抽象接口"""
    
    @abstractmethod
    async def detect_issues(
        self,
        sections: List[Dict[str, Any]],
        task_id: Optional[int] = None,
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """
        检测问题，返回问题列表
        
        Args:
            sections: 文档章节列表
            task_id: 任务ID，用于日志追踪
            progress_callback: 进度回调函数
            
        Returns:
            问题列表，格式：[{'type': str, 'description': str, 'severity': str, ...}]
        """
        pass


class IAIServiceProvider(ABC):
    """AI服务提供者统一接口"""
    
    @abstractmethod
    def get_document_processor(self) -> IAIDocumentProcessor:
        """获取文档处理器"""
        pass
        
    @abstractmethod
    def get_issue_detector(self) -> IAIIssueDetector:
        """获取问题检测器"""
        pass
        
    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""
        pass
        
    @abstractmethod
    def get_provider_info(self) -> Dict[str, Any]:
        """获取提供者信息"""
        pass