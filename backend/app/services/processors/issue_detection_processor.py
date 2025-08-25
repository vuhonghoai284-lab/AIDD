"""
问题检测处理器
"""
from typing import Dict, Any, Optional, Callable
from app.services.interfaces.task_processor import ITaskProcessor, TaskProcessingStep, ProcessingResult
from app.services.interfaces.ai_service import IAIServiceProvider


class IssueDetectionProcessor(ITaskProcessor):
    """问题检测处理器"""
    
    def __init__(self, ai_service_provider: IAIServiceProvider):
        super().__init__(TaskProcessingStep.ISSUE_DETECTION)
        self.ai_service_provider = ai_service_provider
    
    async def can_handle(self, context: Dict[str, Any]) -> bool:
        """检查是否有文档处理结果或章节合并结果"""
        return ('section_merge_result' in context or 
                'document_processing_result' in context)
    
    async def process(self, context: Dict[str, Any], progress_callback: Optional[Callable] = None) -> ProcessingResult:
        """执行问题检测"""
        # 优先使用合并后的章节，如果没有则使用原始章节
        sections = context.get('section_merge_result') or context.get('document_processing_result')
        task_id = context.get('task_id')
        
        if not sections:
            return ProcessingResult(
                success=False,
                error="没有可检测的章节内容"
            )
        
        # 记录使用的章节类型
        section_type = "merged" if 'section_merge_result' in context else "original"
        if progress_callback:
            await progress_callback(f"开始问题检测 (使用{section_type}章节)", 60)
        
        try:
            issue_detector = self.ai_service_provider.get_issue_detector()
            issues = await issue_detector.detect_issues(
                sections,
                task_id,
                progress_callback
            )
            
            # 将结果保存到上下文中
            context['issue_detection_result'] = issues
            
            return ProcessingResult(
                success=True,
                data=issues,
                metadata={
                    "issues_count": len(issues),
                    "processing_stage": "issue_detection"
                }
            )
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                error=f"问题检测失败: {str(e)}"
            )