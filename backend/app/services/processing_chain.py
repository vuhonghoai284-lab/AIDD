"""
处理链管理器
"""
from typing import Dict, Any, Optional, Callable
from app.services.interfaces.task_processor import ITaskProcessor, IProcessingChain, ProcessingResult
from app.services.interfaces.ai_service import IAIServiceProvider
from app.services.processors.file_parsing_processor import FileParsingProcessor
from app.services.processors.document_processing_processor import DocumentProcessingProcessor
from app.services.processors.section_merge_processor import SectionMergeProcessor
from app.services.processors.issue_detection_processor import IssueDetectionProcessor


class TaskProcessingChain(IProcessingChain):
    """任务处理链管理器"""
    
    def __init__(self, ai_service_provider: IAIServiceProvider):
        self.ai_service_provider = ai_service_provider
    
    def build_chain(self) -> ITaskProcessor:
        """构建标准的任务处理链"""
        # 文件解析处理器
        file_parser = FileParsingProcessor()
        
        # 文档处理处理器
        doc_processor = DocumentProcessingProcessor(self.ai_service_provider)
        
        # 章节合并处理器
        section_merger = SectionMergeProcessor()
        
        # 问题检测处理器
        issue_processor = IssueDetectionProcessor(self.ai_service_provider)
        
        # 构建链式结构: 文件解析 -> 文档处理 -> 章节合并 -> 问题检测
        file_parser.set_next(doc_processor).set_next(section_merger).set_next(issue_processor)
        
        return file_parser
    
    async def execute(self, context: Dict[str, Any], progress_callback: Optional[Callable] = None) -> ProcessingResult:
        """执行处理链"""
        chain = self.build_chain()
        result = await chain.handle(context, progress_callback)
        
        # 将最终结果保存到上下文中
        if result.success:
            context['final_result'] = result.data
            context['processing_metadata'] = result.metadata
        
        return result