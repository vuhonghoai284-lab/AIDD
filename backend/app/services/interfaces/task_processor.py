"""
任务处理器抽象接口
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
from enum import Enum


class ProcessingResult:
    """处理结果封装"""
    def __init__(self, success: bool, data: Any = None, error: str = None, metadata: Dict[str, Any] = None):
        self.success = success
        self.data = data
        self.error = error
        self.metadata = metadata or {}


class TaskProcessingStep(Enum):
    """任务处理步骤枚举"""
    FILE_PARSING = "file_parsing"
    DOCUMENT_PROCESSING = "document_processing"
    SECTION_MERGE = "section_merge"
    ISSUE_DETECTION = "issue_detection"
    RESULT_VALIDATION = "result_validation"
    REPORT_GENERATION = "report_generation"


class ITaskProcessor(ABC):
    """任务处理器抽象接口"""
    
    def __init__(self, step_type: TaskProcessingStep):
        self.step_type = step_type
        self.next_processor: Optional['ITaskProcessor'] = None
    
    def set_next(self, processor: 'ITaskProcessor') -> 'ITaskProcessor':
        """设置下一个处理器"""
        self.next_processor = processor
        return processor
    
    @abstractmethod
    async def can_handle(self, context: Dict[str, Any]) -> bool:
        """判断是否能处理当前任务"""
        pass
    
    @abstractmethod
    async def process(self, context: Dict[str, Any], progress_callback: Optional[Callable] = None) -> ProcessingResult:
        """处理任务步骤"""
        pass
    
    async def handle(self, context: Dict[str, Any], progress_callback: Optional[Callable] = None) -> ProcessingResult:
        """责任链处理逻辑"""
        if await self.can_handle(context):
            result = await self.process(context, progress_callback)
            
            # 如果处理成功，更新上下文
            if result.success:
                context.update(result.metadata)
                if result.data:
                    context[f"{self.step_type.value}_result"] = result.data
                
                # 如果有下一个处理器，继续传递
                if self.next_processor:
                    return await self.next_processor.handle(context, progress_callback)
            
            return result
        
        # 如果无法处理，传递给下一个处理器
        if self.next_processor:
            return await self.next_processor.handle(context, progress_callback)
        
        return ProcessingResult(
            success=False, 
            error=f"没有处理器能够处理步骤: {self.step_type.value}"
        )


class IFileParser(ABC):
    """文件解析抽象接口"""
    
    @abstractmethod
    async def can_parse(self, file_path: str, file_type: str) -> bool:
        """判断是否能解析指定类型的文件"""
        pass
    
    @abstractmethod
    async def parse(self, file_path: str, progress_callback: Optional[Callable] = None) -> ProcessingResult:
        """解析文件内容"""
        pass


class IProcessingChain(ABC):
    """处理链管理接口"""
    
    @abstractmethod
    def build_chain(self) -> ITaskProcessor:
        """构建处理链"""
        pass
    
    @abstractmethod
    async def execute(self, context: Dict[str, Any], progress_callback: Optional[Callable] = None) -> ProcessingResult:
        """执行处理链"""
        pass