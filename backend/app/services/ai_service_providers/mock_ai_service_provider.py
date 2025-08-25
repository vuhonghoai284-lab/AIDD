"""
Mock AI服务提供者 - 实现新的抽象接口
"""
import json
from typing import List, Dict, Any, Optional, Callable
from app.services.interfaces.ai_service import IAIServiceProvider, IAIDocumentProcessor, IAIIssueDetector


class MockAIDocumentProcessor(IAIDocumentProcessor):
    """Mock文档处理器"""
    
    def __init__(self, mock_service: MockAIService):
        self.mock_service = mock_service
    
    async def preprocess_document(self, text: str, task_id: Optional[int] = None, 
                                progress_callback: Optional[Callable] = None) -> List[Dict]:
        """文档预处理 - 章节分割"""
        if task_id and hasattr(self.mock_service, 'set_context'):
            await self.mock_service.set_context(task_id)
        
        result = await self.mock_service.analyze_document(text, "preprocess")
        
        # 从mock结果中提取章节信息
        if result.get("status") == "success" and "data" in result:
            data = result["data"]
            if "structure" in data and "sections" in data["structure"]:
                sections = []
                for i, section in enumerate(data["structure"]["sections"]):
                    sections.append({
                        'section_title': section.get('title', f'第{i+1}节'),
                        'content': section.get('content', ''),
                        'level': 1,
                        'section_number': i + 1
                    })
                return sections
        
        # 降级到简单分割
        return self._simple_document_split(text)
    
    def _simple_document_split(self, text: str) -> List[Dict]:
        """简单的文档分割方法"""
        paragraphs = text.split('\n\n')
        sections = []
        
        for i, paragraph in enumerate(paragraphs):
            if paragraph.strip() and len(paragraph.strip()) > 20:
                sections.append({
                    'section_title': f'第{i+1}段',
                    'content': paragraph.strip(),
                    'level': 1,
                    'section_number': i + 1
                })
        
        if not sections:
            sections = [{
                'section_title': '文档内容',
                'content': text,
                'level': 1,
                'section_number': 1
            }]
        
        return sections


class MockAIIssueDetector(IAIIssueDetector):
    """Mock问题检测器"""
    
    def __init__(self, mock_service: MockAIService):
        self.mock_service = mock_service
    
    async def detect_issues(self, sections: List[Dict], task_id: Optional[int] = None, 
                          progress_callback: Optional[Callable] = None) -> List[Dict]:
        """问题检测"""
        if task_id and hasattr(self.mock_service, 'set_context'):
            await self.mock_service.set_context(task_id)
        
        # 将章节合并为文本进行分析
        text = '\n\n'.join([f"{section.get('section_title', '')}\n{section.get('content', '')}" 
                           for section in sections])
        
        result = await self.mock_service.analyze_document(text, "detect_issues")
        
        if result.get("status") == "success" and "data" in result:
            data = result["data"]
            if "issues" in data:
                return data["issues"]
        
        # 降级到简单问题检测
        return self._simple_issue_detection(sections)
    
    def _simple_issue_detection(self, sections: List[Dict]) -> List[Dict]:
        """简单的问题检测"""
        issues = []
        
        for section in sections:
            content = section.get('content', '')
            section_title = section.get('section_title', '未知章节')
            
            # 检查重复字词
            common_typos = ['的的', '了了', '是是', '在在']
            for typo in common_typos:
                if typo in content:
                    issues.append({
                        'issue_type': '错别字',
                        'description': f'发现重复字词：{typo}',
                        'location': section_title,
                        'severity': '一般',
                        'confidence': 0.9,
                        'suggestion': f'将"{typo}"修改为"{typo[0]}"',
                        'original_text': typo,
                        'user_impact': '影响阅读流畅性',
                        'reasoning': '重复字词影响文档质量',
                        'context': f'在章节"{section_title}"中发现'
                    })
            
            # 检查句子长度
            sentences = content.split('。')
            for sentence in sentences:
                if len(sentence) > 200:
                    issues.append({
                        'issue_type': '句子过长',
                        'description': '句子过长，建议拆分为多个短句以提高可读性',
                        'location': section_title,
                        'severity': '提示',
                        'confidence': 0.7,
                        'suggestion': '建议将长句拆分为多个短句',
                        'original_text': sentence[:50] + '...',
                        'user_impact': '可能影响理解',
                        'reasoning': '过长的句子影响阅读理解',
                        'context': f'在章节"{section_title}"中'
                    })
        
        return issues


class MockAIServiceProvider(IAIServiceProvider):
    """Mock AI服务提供者"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.mock_service = MockAIService(config)
        self._document_processor = MockAIDocumentProcessor(self.mock_service)
        self._issue_detector = MockAIIssueDetector(self.mock_service)
    
    def get_document_processor(self) -> IAIDocumentProcessor:
        """获取文档处理器"""
        return self._document_processor
    
    def get_issue_detector(self) -> IAIIssueDetector:
        """获取问题检测器"""
        return self._issue_detector
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return True
    
    def get_provider_name(self) -> str:
        """获取服务提供者名称"""
        return f"MockAI ({self.config.get('model', 'mock-model')})"
    
    def get_provider_info(self) -> Dict[str, Any]:
        """获取服务提供者信息"""
        return {
            'name': self.get_provider_name(),
            'type': 'mock',
            'model': self.config.get('model', 'mock-model'),
            'version': '1.0.0',
            'capabilities': ['document_processing', 'issue_detection']
        }
    
    def health_check(self) -> bool:
        """健康检查"""
        return True