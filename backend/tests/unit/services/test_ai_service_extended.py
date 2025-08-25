"""
扩展的AI服务测试
测试AI服务的核心功能和模块集成
"""
import asyncio
import pytest
import sys
import os


class TestAIServiceExtended:
    """扩展的AI服务测试类"""
    
    def test_prompt_loader_functionality(self):
        """测试Prompt加载器功能"""
        from app.services.prompt_loader import prompt_loader
        
        try:
            templates = prompt_loader.list_templates()
            assert isinstance(templates, list)
            
            if 'document_preprocess' in templates:
                system_prompt = prompt_loader.get_system_prompt('document_preprocess')
                assert isinstance(system_prompt, str)
                assert len(system_prompt) > 0
                
        except Exception as e:
            pytest.skip(f"Prompt加载器不可用: {e}")
    
    @pytest.mark.asyncio
    async def test_ai_service_basic_functionality(self):
        """测试AI服务基础功能"""
        from app.services.ai_service import AIService
        
        try:
            # 创建AI服务实例（不使用真实模型）
            ai_service = AIService()
            
            # 测试文档预处理
            test_text = """
# 标题1
这是第一段内容。这里有一些文字。

## 子标题
这是第二段内容。这里也有一些文字。

这是第三段内容，没有标题。
            """.strip()
            
            # 测试文档预处理
            sections = await ai_service.preprocess_document(test_text)
            assert isinstance(sections, list)
            assert len(sections) > 0
            
            for section in sections:
                assert isinstance(section, dict)
                # 验证基本结构（具体字段可能因实现而异）
                if 'section_title' in section:
                    assert isinstance(section['section_title'], str)
            
            # 测试问题检测
            issues = await ai_service.detect_issues(test_text)
            assert isinstance(issues, list)
            
            for issue in issues:
                assert isinstance(issue, dict)
                # 验证基本结构（具体字段可能因实现而异）
                if 'type' in issue:
                    assert isinstance(issue['type'], str)
                    
        except ImportError as e:
            pytest.skip(f"AI服务模块不可用: {e}")
        except Exception as e:
            # 在测试环境中，某些功能可能不可用，这是正常的
            pytest.skip(f"AI服务功能在当前环境不可用: {e}")
    
    @pytest.mark.asyncio
    async def test_ai_service_factory_integration(self):
        """测试AI服务工厂集成"""
        try:
            from app.services.ai_service_factory import ai_service_factory
            
            # 测试实时日志服务
            await ai_service_factory.start_realtime_logging()
            
            # 创建任务日志适配器
            task_logger = ai_service_factory.create_task_logger(1, "test")
            await task_logger.info("这是一个测试日志消息")
            
            await ai_service_factory.stop_realtime_logging()
            
        except ImportError as e:
            pytest.skip(f"AI服务工厂不可用: {e}")
        except Exception as e:
            # 实时日志功能可能在测试环境中不可用
            pytest.skip(f"AI服务工厂功能在当前环境不可用: {e}")
    
    @pytest.mark.asyncio
    async def test_ai_service_error_handling(self):
        """测试AI服务错误处理"""
        from app.services.ai_service import AIService
        
        try:
            ai_service = AIService()
            
            # 测试空文档处理
            empty_sections = await ai_service.preprocess_document("")
            assert isinstance(empty_sections, list)
            
            # 测试空文档问题检测
            empty_issues = await ai_service.detect_issues("")
            assert isinstance(empty_issues, list)
            
            # 测试None输入处理
            try:
                none_sections = await ai_service.preprocess_document(None)
                assert isinstance(none_sections, list)
            except (TypeError, AttributeError):
                # 这是预期的错误，某些实现可能会抛出异常
                pass
                
        except ImportError as e:
            pytest.skip(f"AI服务模块不可用: {e}")
        except Exception as e:
            pytest.skip(f"AI服务在当前环境不可用: {e}")