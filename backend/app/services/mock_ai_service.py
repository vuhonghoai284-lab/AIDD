"""
Mock AI服务实现 - 用于测试目的
"""
import asyncio
import json
from typing import Dict, Any, List, Optional
import time


class MockAIService:
    """Mock AI服务类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.response_delay = self.config.get('response_delay', 0.1)
        self.model_name = self.config.get('model', 'mock-model')
        self.context = {}
    
    async def set_context(self, task_id: int):
        """设置上下文"""
        self.context['task_id'] = task_id
    
    async def analyze_document(self, text: str, analysis_type: str = "general") -> Dict[str, Any]:
        """模拟文档分析"""
        # 模拟处理延迟
        await asyncio.sleep(self.response_delay)
        
        # 根据分析类型返回不同的模拟结果
        if analysis_type == "preprocess":
            return self._mock_preprocess_result(text)
        elif analysis_type == "detect_issues":
            return self._mock_issue_detection_result(text)
        else:
            return self._mock_general_result(text)
    
    def _mock_preprocess_result(self, text: str) -> Dict[str, Any]:
        """模拟文档预处理结果"""
        # 简单的章节分割
        paragraphs = text.split('\n\n')
        sections = []
        
        for i, paragraph in enumerate(paragraphs):
            if paragraph.strip() and len(paragraph.strip()) > 10:
                sections.append({
                    'title': f'第{i+1}节',
                    'content': paragraph.strip(),
                    'level': 1
                })
        
        return {
            "status": "success",
            "data": {
                "structure": {
                    "sections": sections[:10],  # 限制最多10个章节
                    "total_sections": len(sections)
                },
                "metadata": {
                    "word_count": len(text.split()),
                    "char_count": len(text),
                    "paragraph_count": len(paragraphs)
                }
            }
        }
    
    def _mock_issue_detection_result(self, text: str) -> Dict[str, Any]:
        """模拟问题检测结果"""
        issues = []
        
        # 检测一些常见的问题
        if '的的' in text:
            issues.append({
                'type': '错别字',
                'description': '发现重复字词：的的',
                'severity': 'medium',
                'confidence': 0.95,
                'suggestion': '将"的的"修改为"的"'
            })
        
        if '了了' in text:
            issues.append({
                'type': '错别字',
                'description': '发现重复字词：了了',
                'severity': 'medium',
                'confidence': 0.95,
                'suggestion': '将"了了"修改为"了"'
            })
        
        # 检测过长的句子
        sentences = text.split('。')
        for i, sentence in enumerate(sentences):
            if len(sentence) > 100:
                issues.append({
                    'type': '句子过长',
                    'description': f'第{i+1}个句子过长',
                    'severity': 'low',
                    'confidence': 0.8,
                    'suggestion': '建议将长句拆分为多个短句'
                })
        
        return {
            "status": "success",
            "data": {
                "issues": issues,
                "summary": {
                    "total_issues": len(issues),
                    "critical_issues": len([i for i in issues if i.get('severity') == 'high']),
                    "medium_issues": len([i for i in issues if i.get('severity') == 'medium']),
                    "low_issues": len([i for i in issues if i.get('severity') == 'low'])
                }
            }
        }
    
    def _mock_general_result(self, text: str) -> Dict[str, Any]:
        """模拟通用分析结果"""
        return {
            "status": "success",
            "data": {
                "analysis": f"对文档进行了{self.model_name}模型分析",
                "summary": {
                    "word_count": len(text.split()),
                    "char_count": len(text)
                },
                "suggestions": [
                    "建议检查文档格式",
                    "建议补充更多细节内容"
                ]
            }
        }
    
    async def generate_feedback_response(self, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """模拟反馈响应生成"""
        await asyncio.sleep(self.response_delay)
        
        return {
            "status": "success",
            "data": {
                "response": "感谢您的反馈，我们已经收到并会认真考虑您的建议。",
                "acknowledgment": f"反馈ID: {feedback_data.get('feedback_id', 'unknown')}"
            }
        }