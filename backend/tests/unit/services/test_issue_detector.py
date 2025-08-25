"""
IssueDetector单元测试
"""
import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from app.services.issue_detector import IssueDetector
from tests.fixtures.mock_helpers import create_mock_dependencies


class TestIssueDetector:
    """问题检测器单元测试"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock数据库会话"""
        db = Mock()
        db.add = Mock()
        db.commit = Mock()
        return db
    
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
    def issue_detector(self, mock_model_config, mock_db):
        """创建IssueDetector实例"""
        with patch('app.services.issue_detector.ChatOpenAI'):
            with patch('app.services.issue_detector.PydanticOutputParser'):
                detector = IssueDetector(mock_model_config['config'], mock_db)
                return detector
    
    @pytest.fixture
    def mock_sections(self):
        """Mock文档章节数据"""
        return [
            {
                "section_title": "介绍",
                "content": "这是一个测试文档的介绍章节，包含足够的内容用于问题检测。",
                "level": 1
            },
            {
                "section_title": "详细说明",
                "content": "这个章节包含详细说明，有更多的内容可以用来检测各种问题。内容应该足够长以满足检测要求。",
                "level": 2
            }
        ]
    
    @pytest.mark.asyncio
    async def test_detect_issues_normal_flow(self, issue_detector, mock_sections, mock_db):
        """测试正常问题检测流程"""
        task_id = 1
        
        # Mock AI响应
        mock_response = {
            "issues": [
                {
                    "type": "语法错误",
                    "description": "发现语法错误，需要修正",
                    "location": "第1行",
                    "severity": "一般",
                    "confidence": 0.85,
                    "suggestion": "修正建议",
                    "original_text": "错误文本",
                    "user_impact": "影响理解",
                    "reasoning": "语法不规范",
                    "context": "上下文"
                }
            ]
        }
        
        # Mock _call_ai_model 方法
        with patch.object(issue_detector, '_call_ai_model') as mock_call:
            mock_call.return_value = Mock(content=json.dumps(mock_response, ensure_ascii=False))
            
            # 执行测试
            result = await issue_detector.detect_issues(mock_sections, task_id)
            
            # 验证结果
            assert len(result) >= 1
            assert result[0]['type'] == '语法错误'
            assert result[0]['description'] == '发现语法错误，需要修正'
            
            # 验证AI模型被调用（每个章节一次）
            assert mock_call.call_count == len(mock_sections)
            
            # 验证数据库操作
            assert mock_db.add.call_count >= len(mock_sections)
            assert mock_db.commit.call_count >= len(mock_sections)
    
    @pytest.mark.asyncio
    async def test_detect_issues_with_progress_callback(self, issue_detector, mock_sections):
        """测试带进度回调的问题检测"""
        progress_calls = []
        
        async def mock_progress_callback(message, progress):
            progress_calls.append((message, progress))
        
        # Mock AI响应
        mock_response = {"issues": []}
        
        with patch.object(issue_detector, '_call_ai_model') as mock_call:
            mock_call.return_value = Mock(content=json.dumps(mock_response))
            
            # 执行测试
            result = await issue_detector.detect_issues(
                mock_sections,
                progress_callback=mock_progress_callback
            )
            
            # 验证进度回调被调用
            assert len(progress_calls) >= 3
            assert any("开始检测" in call[0] for call in progress_calls)
            assert any("检测完成" in call[0] for call in progress_calls)
    
    @pytest.mark.asyncio
    async def test_detect_issues_empty_sections(self, issue_detector):
        """测试空章节列表"""
        empty_sections = []
        
        result = await issue_detector.detect_issues(empty_sections)
        
        # 验证返回空结果
        assert result == []
    
    @pytest.mark.asyncio
    async def test_detect_issues_short_sections_filtered(self, issue_detector):
        """测试过滤太短的章节"""
        short_sections = [
            {
                "section_title": "短章节",
                "content": "短",  # 内容太短，应被过滤
                "level": 1
            },
            {
                "section_title": "正常章节",
                "content": "这是正常长度的章节内容，应该被检测，需要足够的字符数来通过长度验证",
                "level": 1
            }
        ]
        
        # Mock AI响应
        mock_response = {"issues": []}
        
        with patch.object(issue_detector, '_call_ai_model') as mock_call:
            mock_call.return_value = Mock(content=json.dumps(mock_response))
            
            # 执行测试
            result = await issue_detector.detect_issues(short_sections)
            
            # 验证只检测了有效章节
            assert mock_call.call_count == 1  # 只有1个有效章节
    
    @pytest.mark.asyncio
    async def test_detect_issues_ai_failure(self, issue_detector, mock_sections, mock_db):
        """测试AI服务调用失败"""
        task_id = 1
        
        # Mock AI调用失败
        with patch.object(issue_detector, '_call_ai_model') as mock_call:
            mock_call.side_effect = Exception("AI服务不可用")
            
            # 执行测试
            result = await issue_detector.detect_issues(mock_sections, task_id)
            
            # 验证返回空结果（错误被处理）
            assert result == []
            
            # 验证错误记录到数据库
            assert mock_db.add.call_count >= len(mock_sections)
            assert mock_db.commit.call_count >= len(mock_sections)
    
    @pytest.mark.asyncio
    async def test_detect_issues_invalid_json_response(self, issue_detector, mock_sections):
        """测试AI返回无效JSON格式"""
        
        # Mock AI返回无效JSON
        with patch.object(issue_detector, '_call_ai_model') as mock_call:
            mock_call.return_value = Mock(content="这是无效的JSON响应")
            
            # 执行测试
            result = await issue_detector.detect_issues(mock_sections)
            
            # 验证返回空结果
            assert result == []
    
    @pytest.mark.asyncio
    async def test_detect_issues_partial_json_response(self, issue_detector, mock_sections):
        """测试AI返回部分有效的JSON响应"""
        
        # Mock AI返回包含JSON的文本响应
        response_content = '''
        这是一些前置文本
        {"issues": [{"type": "测试问题", "description": "测试描述", "location": "测试位置", "severity": "一般", "confidence": 0.8}]}
        这是一些后置文本
        '''
        
        with patch.object(issue_detector, '_call_ai_model') as mock_call:
            mock_call.return_value = Mock(content=response_content)
            
            # 执行测试
            result = await issue_detector.detect_issues(mock_sections)
            
            # 验证能正确提取JSON部分
            assert len(result) >= 1
            # 因为有2个章节，每个都会检测，所以可能有多个结果
            found_test_issue = any(issue['type'] == '测试问题' for issue in result)
            assert found_test_issue
    
    @pytest.mark.asyncio
    async def test_detect_issues_concurrent_processing(self, issue_detector, mock_db):
        """测试并发处理多个章节"""
        # 创建多个章节
        many_sections = [
            {
                "section_title": f"章节{i}",
                "content": f"这是第{i}个章节的内容，足够长以满足检测要求。" * 3,
                "level": 1
            }
            for i in range(5)
        ]
        
        # Mock AI响应
        mock_response = {"issues": []}
        
        with patch.object(issue_detector, '_call_ai_model') as mock_call:
            mock_call.return_value = Mock(content=json.dumps(mock_response))
            
            # 执行测试
            result = await issue_detector.detect_issues(many_sections, task_id=1)
            
            # 验证所有章节都被处理
            assert mock_call.call_count == len(many_sections)
    
    def test_filter_issues_by_severity(self, issue_detector):
        """测试根据置信度过滤问题"""
        issues = [
            {"type": "高置信度问题", "confidence": 0.9},
            {"type": "中等置信度问题", "confidence": 0.7},
            {"type": "低置信度问题", "confidence": 0.5},
            {"type": "默认置信度问题"},  # 没有confidence字段，使用默认值0.8
        ]
        
        # 使用0.6的阈值过滤
        filtered = issue_detector.filter_issues_by_severity(issues, min_confidence=0.6)
        
        # 验证只保留高于阈值的问题
        assert len(filtered) == 3
        assert filtered[0]['type'] == '高置信度问题'
        assert filtered[1]['type'] == '中等置信度问题'
        assert filtered[2]['type'] == '默认置信度问题'
    
    def test_categorize_issues(self, issue_detector):
        """测试按严重等级分类问题"""
        issues = [
            {"type": "致命问题", "severity": "致命"},
            {"type": "严重问题", "severity": "严重"},
            {"type": "一般问题1", "severity": "一般"},
            {"type": "一般问题2", "severity": "一般"},
            {"type": "提示问题", "severity": "提示"},
            {"type": "未知严重度问题", "severity": "未知"},  # 未知类型，归入一般
            {"type": "无严重度字段问题"},  # 无字段，归入一般
        ]
        
        categorized = issue_detector.categorize_issues(issues)
        
        # 验证分类结果
        assert len(categorized['致命']) == 1
        assert len(categorized['严重']) == 1
        assert len(categorized['一般']) == 4  # 包括2个一般问题 + 1个未知 + 1个无字段
        assert len(categorized['提示']) == 1
        
        assert categorized['致命'][0]['type'] == '致命问题'
        assert categorized['严重'][0]['type'] == '严重问题'
        assert categorized['提示'][0]['type'] == '提示问题'
    
    @pytest.mark.asyncio
    async def test_call_ai_model_integration(self, issue_detector):
        """测试AI模型调用集成"""
        messages = [Mock(content="测试消息")]
        
        # Mock settings返回生产模式，简化测试
        with patch('app.services.issue_detector.get_settings') as mock_settings:
            mock_settings_instance = Mock()
            mock_settings_instance.is_service_mocked.return_value = False
            mock_settings.return_value = mock_settings_instance
            
            # Mock asyncio.to_thread来模拟AI调用
            mock_response = Mock(content='{"issues": [{"type": "测试问题", "description": "这是一个测试问题"}]}')
            with patch('asyncio.to_thread') as mock_to_thread:
                mock_to_thread.return_value = mock_response
                
                # 执行测试
                result = await issue_detector._call_ai_model(messages)
                
                # 验证返回响应
                assert result == mock_response
                mock_to_thread.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_call_ai_model_production_mode(self, issue_detector):
        """测试生产模式下的AI调用"""
        messages = [Mock(content="测试消息")]
        
        # Mock settings返回非Mock模式
        with patch('app.services.issue_detector.get_settings') as mock_settings:
            mock_settings_instance = Mock()
            mock_settings_instance.is_service_mocked.return_value = False
            mock_settings.return_value = mock_settings_instance
            
            # Mock asyncio.to_thread
            mock_response = Mock(content='{"issues": []}')
            with patch('asyncio.to_thread') as mock_to_thread:
                mock_to_thread.return_value = mock_response
                
                # 执行测试
                result = await issue_detector._call_ai_model(messages)
                
                # 验证调用真实AI模型
                assert result == mock_response
                mock_to_thread.assert_called_once()
    
    
    def test_issue_detection_performance(self, issue_detector):
        """测试问题检测性能"""
        import time
        
        # 测试多个章节的处理性能
        sections = [
            {"section_title": f"章节{i}", "content": f"这是第{i}个章节的内容" * 10}
            for i in range(5)
        ]
        
        start_time = time.time()
        issues = issue_detector.filter_issues_by_severity([
            {"type": "测试问题", "confidence": 0.8, "severity": "一般"}
            for _ in range(100)
        ])
        end_time = time.time()
        
        # 验证性能（应该在100ms内完成）
        processing_time = (end_time - start_time) * 1000
        assert processing_time < 100, f"问题过滤过慢: {processing_time}ms"
    
    def test_issue_structure_validation(self, issue_detector):
        """测试问题结构验证"""
        # 测试各种问题结构
        test_issues = [
            {
                'type': '错别字',
                'description': '发现错别字问题',
                'location': '第1段',
                'severity': '一般',
                'confidence': 0.8
            },
            {
                'type': '语法错误', 
                'description': '发现语法问题',
                'location': '第2段',
                'severity': '严重',
                'confidence': 0.9
            }
        ]
        
        # 验证过滤功能
        filtered = issue_detector.filter_issues_by_severity(test_issues, min_confidence=0.7)
        assert len(filtered) == 2
        
        # 验证分类功能
        categorized = issue_detector.categorize_issues(test_issues)
        assert len(categorized['严重']) == 1
        assert len(categorized['一般']) == 1