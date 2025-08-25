"""
文档处理处理器
"""
from typing import Dict, Any, Optional, Callable
from app.services.interfaces.task_processor import ITaskProcessor, TaskProcessingStep, ProcessingResult
from app.services.interfaces.ai_service import IAIServiceProvider


class DocumentProcessingProcessor(ITaskProcessor):
    """文档处理处理器"""
    
    def __init__(self, ai_service_provider: IAIServiceProvider):
        super().__init__(TaskProcessingStep.DOCUMENT_PROCESSING)
        self.ai_service_provider = ai_service_provider
    
    async def can_handle(self, context: Dict[str, Any]) -> bool:
        """检查是否有文件解析结果"""
        return 'file_parsing_result' in context
    
    async def process(self, context: Dict[str, Any], progress_callback: Optional[Callable] = None) -> ProcessingResult:
        """执行文档预处理"""
        text_content = context.get('file_parsing_result')
        task_id = context.get('task_id')
        
        if not text_content:
            return ProcessingResult(
                success=False,
                error="没有可处理的文本内容"
            )
        
        if progress_callback:
            await progress_callback("开始文档预处理", 20)
        
        try:
            document_processor = self.ai_service_provider.get_document_processor()
            sections = await document_processor.preprocess_document(
                text_content,
                task_id,
                progress_callback
            )
            
            # 将结果保存到上下文中，供下一个处理器使用
            context['document_processing_result'] = sections
            
            return ProcessingResult(
                success=True,
                data=sections,
                metadata={
                    "sections_count": len(sections),
                    "processing_stage": "document_processing"
                }
            )
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                error=f"文档预处理失败: {str(e)}"
            )