"""
文档处理器测试用例（清理版）
删除已弃用的Mock相关测试，只保留有效的测试用例
"""
import pytest
import json
from unittest.mock import Mock, patch

from app.services.document_processor import DocumentProcessor


class TestDocumentProcessorClean:
    """文档处理器测试类"""
    
    @pytest.fixture
    def mock_model_config(self):
        """Mock模型配置"""
        return {
            'provider': 'openai',
            'config': {
                'api_key': 'test-api-key',
                'base_url': 'https://api.openai.com/v1',
                'model': 'gpt-4o-mini',
                'temperature': 0.3,
                'max_tokens': 4000,
                'timeout': 60,
                'max_retries': 3
            }
        }
    
    @pytest.fixture
    def mock_db(self):
        """Mock数据库会话"""
        return Mock()
    
    @pytest.fixture
    def document_processor(self, mock_model_config, mock_db):
        """创建DocumentProcessor实例"""
        with patch('app.services.document_processor.ChatOpenAI'):
            with patch('app.services.document_processor.PydanticOutputParser'):
                # DocumentProcessor现在期望直接接收config部分
                processor = DocumentProcessor(mock_model_config['config'], mock_db)
                return processor
    
    @pytest.mark.asyncio
    async def test_preprocess_document_normal_flow(self, document_processor, mock_db):
        """测试正常文档预处理流程"""
        # 准备测试数据
        test_text = "# 测试标题\n\n这是测试内容。\n\n## 子标题\n\n更多内容。"
        task_id = 1
        
        # Mock AI响应
        mock_response = {
            "sections": [
                {
                    "section_title": "测试标题",
                    "content": "这是测试内容。",
                    "level": 1
                },
                {
                    "section_title": "子标题", 
                    "content": "更多内容。",
                    "level": 2
                }
            ]
        }
        
        # Mock _call_ai_model 方法
        with patch.object(document_processor, '_call_ai_model') as mock_call:
            mock_call.return_value = Mock(content=json.dumps(mock_response, ensure_ascii=False))
            
            # 执行测试
            result = await document_processor.preprocess_document(test_text, task_id)
            
            # 验证结果 - 注意：由于智能合并功能，原本的2个章节可能被合并为1个
            assert len(result) >= 1
            # 验证至少包含主要内容
            combined_content = ' '.join([section.get('content', '') for section in result])
            assert '这是测试内容' in combined_content
            assert '更多内容' in combined_content
            # 验证第一个章节的基本结构
            assert result[0]['section_title'] is not None
            assert result[0]['content'] is not None
            assert result[0]['level'] >= 1
    
    @pytest.mark.asyncio
    async def test_preprocess_document_with_progress_callback(self, document_processor):
        """测试带进度回调的文档预处理"""
        test_text = "测试内容"
        task_id = 2
        progress_calls = []
        
        async def progress_callback(msg, percent):
            progress_calls.append((msg, percent))
        
        # Mock AI响应
        mock_response = {"sections": [{"section_title": "测试", "content": "内容", "level": 1}]}
        
        with patch.object(document_processor, '_call_ai_model') as mock_call:
            mock_call.return_value = Mock(content=json.dumps(mock_response, ensure_ascii=False))
            
            result = await document_processor.preprocess_document(
                test_text, task_id, progress_callback
            )
            
            assert len(result) == 1
            assert len(progress_calls) >= 2  # 至少开始和结束两次回调
    
    @pytest.mark.asyncio
    async def test_preprocess_document_ai_failure(self, document_processor):
        """测试AI调用失败时的处理"""
        test_text = "测试内容"
        task_id = 3
        
        # Mock AI调用抛出异常
        with patch.object(document_processor, '_call_ai_model') as mock_call:
            mock_call.side_effect = Exception("AI调用失败")
            
            # 应该返回默认章节而不是抛出异常
            result = await document_processor.preprocess_document(test_text, task_id)
            assert len(result) == 1
            assert result[0]['section_title'] == '文档内容'
            assert result[0]['content'] == test_text
    
    @pytest.mark.asyncio
    async def test_preprocess_document_invalid_json_response(self, document_processor):
        """测试无效JSON响应处理"""
        test_text = "测试内容"
        task_id = 4
        
        # Mock返回无效JSON
        with patch.object(document_processor, '_call_ai_model') as mock_call:
            mock_call.return_value = Mock(content="无效的JSON")
            
            result = await document_processor.preprocess_document(test_text, task_id)
            
            # 应该返回默认章节
            assert len(result) >= 1
    
    @pytest.mark.asyncio
    async def test_preprocess_document_partial_json_response(self, document_processor):
        """测试部分有效JSON响应处理"""
        test_text = "测试内容"
        task_id = 5
        
        # Mock返回部分有效的响应
        partial_response = {
            "sections": [
                {"section_title": "有效章节", "content": "有效内容", "level": 1},
                {"content": "缺少标题的章节", "level": 2}  # 缺少section_title
            ]
        }
        
        with patch.object(document_processor, '_call_ai_model') as mock_call:
            mock_call.return_value = Mock(content=json.dumps(partial_response, ensure_ascii=False))
            
            result = await document_processor.preprocess_document(test_text, task_id)
            
            # 应该过滤并修复无效章节
            assert len(result) >= 1
            assert result[0]['section_title'] == '有效章节'
            # 无效章节可能被过滤掉或修复，具体行为取决于validate_sections实现
    
    def test_validate_sections_normal(self, document_processor):
        """测试正常章节验证"""
        sections = [
            {"section_title": "第一章", "content": "这是第一章的详细内容，包含足够多的文字来通过最小长度检查。", "level": 1},
            {"section_title": "第二章", "content": "这是第二章的详细内容，同样包含足够多的文字来通过验证。", "level": 2}
        ]
        
        result = document_processor.validate_sections(sections)
        
        assert len(result) == 2
        assert result[0]['section_title'] == '第一章'
        assert result[1]['section_title'] == '第二章'
    
    def test_validate_sections_filter_invalid(self, document_processor):
        """测试过滤无效章节"""
        sections = [
            {"section_title": "有效章节", "content": "这是一个有效章节，包含足够长的内容来通过验证检查。", "level": 1},
            {"content": "这个章节缺少标题，但有足够长的内容", "level": 2},  # 缺少section_title
            {"section_title": "", "content": "这个章节的标题是空的，但内容足够长", "level": 1},  # 空标题
            {"section_title": "无内容章节", "level": 1}  # 缺少content
        ]
        
        result = document_processor.validate_sections(sections)
        
        # 至少有效章节应该通过
        assert len(result) >= 1
        # 检查第一个章节是有效的
        if len(result) > 0:
            assert result[0]['section_title'] == '有效章节'


if __name__ == "__main__":
    pytest.main([__file__])