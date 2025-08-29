"""
AI服务提供者工厂测试
"""
import pytest
from unittest.mock import Mock, patch
from app.services.ai_service_providers.service_provider_factory import AIServiceProviderFactory
from app.services.ai_service_providers.real_ai_service_provider import RealAIServiceProvider
from app.core.config import Settings

class TestAIServiceProviderFactory:
    """AI服务提供者工厂测试类"""
    
    @patch('app.services.ai_service_providers.service_provider_factory.RealAIServiceProvider')
    def test_create_provider_with_valid_config(self, mock_real_provider):
        """测试使用有效配置创建提供者"""
        # 创建模拟的设置对象
        mock_settings = Mock(spec=Settings)
        mock_settings.ai_models = [
            {
                'label': 'Test Model',
                'provider': 'test',
                'config': {
                    'api_key': 'test-key',
                    'base_url': 'http://test.com/v1',
                    'model': 'test-model'
                }
            }
        ]
        
        # 创建提供者
        provider = AIServiceProviderFactory.create_provider(mock_settings, 0)
        
        # 验证RealAIServiceProvider被正确调用
        mock_real_provider.assert_called_once_with(
            {
                'label': 'Test Model',
                'provider': 'test',
                'config': {
                    'api_key': 'test-key',
                    'base_url': 'http://test.com/v1',
                    'model': 'test-model'
                }
            },
            None
        )
        
    @patch('app.services.ai_service_providers.service_provider_factory.RealAIServiceProvider')
    def test_create_provider_with_different_model_index(self, mock_real_provider):
        """测试使用不同模型索引创建提供者"""
        # 创建模拟的设置对象
        mock_settings = Mock(spec=Settings)
        mock_settings.ai_models = [
            {
                'label': 'Model 1',
                'provider': 'provider1',
                'config': {
                    'api_key': 'key1',
                    'base_url': 'http://test1.com/v1',
                    'model': 'model1'
                }
            },
            {
                'label': 'Model 2',
                'provider': 'provider2',
                'config': {
                    'api_key': 'key2',
                    'base_url': 'http://test2.com/v1',
                    'model': 'model2'
                }
            }
        ]
        
        # 创建第二个模型的提供者
        provider = AIServiceProviderFactory.create_provider(mock_settings, 1)
        
        # 验证RealAIServiceProvider使用了正确的配置
        mock_real_provider.assert_called_once_with(
            {
                'label': 'Model 2',
                'provider': 'provider2',
                'config': {
                    'api_key': 'key2',
                    'base_url': 'http://test2.com/v1',
                    'model': 'model2'
                }
            },
            None
        )

if __name__ == "__main__":
    pytest.main([__file__])