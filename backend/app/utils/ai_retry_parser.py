"""
AI响应重试解析器 - 为JSON解析失败提供重试机制
"""
import json
import re
import time
import logging
from typing import Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3  # 最大重试次数
    base_delay: float = 1.0  # 基础延迟时间(秒)
    backoff_multiplier: float = 2.0  # 退避倍数
    max_delay: float = 10.0  # 最大延迟时间(秒)


class AIRetryParser:
    """AI响应重试解析器"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
    
    async def parse_json_with_retry(
        self,
        ai_call_func: Callable[[], Awaitable[Any]],  # AI调用函数
        json_extractor: Callable[[str], Dict[str, Any]] = None,  # JSON提取函数
        retry_config: RetryConfig = None,
        operation_name: str = "AI调用"
    ) -> Dict[str, Any]:
        """
        带重试机制的JSON解析
        
        Args:
            ai_call_func: 返回AI响应的异步函数
            json_extractor: JSON提取函数，如果为None则使用默认提取器
            retry_config: 重试配置
            operation_name: 操作名称，用于日志
            
        Returns:
            解析成功的JSON数据
            
        Raises:
            Exception: 所有重试都失败后抛出异常
        """
        if retry_config is None:
            retry_config = RetryConfig()
        
        if json_extractor is None:
            json_extractor = self._default_json_extractor
        
        last_error = None
        delay = retry_config.base_delay
        
        for attempt in range(retry_config.max_retries + 1):
            try:
                self.logger.info(f"🔄 {operation_name} - 尝试 {attempt + 1}/{retry_config.max_retries + 1}")
                
                # 调用AI模型
                response = await ai_call_func()
                
                # 提取并解析JSON
                if hasattr(response, 'content'):
                    content = response.content
                else:
                    content = str(response)
                
                self.logger.debug(f"📥 收到响应，长度: {len(content)}字符")
                
                # 提取并解析JSON
                result = json_extractor(content)
                
                # 验证结果
                if not isinstance(result, dict):
                    raise ValueError(f"解析结果不是字典类型: {type(result)}")
                
                self.logger.info(f"✅ {operation_name} 解析成功 (尝试 {attempt + 1})")
                return result
                
            except (json.JSONDecodeError, ValueError) as e:
                last_error = e
                error_msg = f"JSON解析失败: {str(e)}"
                
                if attempt < retry_config.max_retries:
                    self.logger.warning(f"⚠️ {operation_name} {error_msg}，将在 {delay:.1f}秒后重试")
                    
                    # 等待后重试
                    await self._async_sleep(delay)
                    
                    # 计算下次延迟时间
                    delay = min(delay * retry_config.backoff_multiplier, retry_config.max_delay)
                else:
                    self.logger.error(f"❌ {operation_name} {error_msg}，已达到最大重试次数")
                    
            except Exception as e:
                last_error = e
                # 对于其他类型的错误（如网络错误），也进行重试
                error_msg = f"调用失败: {str(e)}"
                
                if attempt < retry_config.max_retries:
                    self.logger.warning(f"⚠️ {operation_name} {error_msg}，将在 {delay:.1f}秒后重试")
                    
                    # 等待后重试
                    await self._async_sleep(delay)
                    
                    # 计算下次延迟时间
                    delay = min(delay * retry_config.backoff_multiplier, retry_config.max_delay)
                else:
                    self.logger.error(f"❌ {operation_name} {error_msg}，已达到最大重试次数")
        
        # 所有重试都失败
        error_message = f"{operation_name} 失败，已重试 {retry_config.max_retries} 次"
        if last_error:
            error_message += f"，最后错误: {str(last_error)}"
        
        raise Exception(error_message)
    
    def _default_json_extractor(self, content: str) -> Dict[str, Any]:
        """
        默认JSON提取器
        
        Args:
            content: AI响应内容
            
        Returns:
            提取的JSON数据
            
        Raises:
            json.JSONDecodeError: JSON解析失败
            ValueError: 没有找到JSON内容
        """
        # 查找JSON内容
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        
        if not json_match:
            # 尝试查找更宽松的JSON模式
            json_match = re.search(r'\{[\s\S]*\}', content)
        
        if not json_match:
            # 尝试在代码块中查找JSON
            code_block_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', content)
            if code_block_match:
                json_match = code_block_match
                json_str = code_block_match.group(1)
            else:
                raise ValueError("未找到JSON格式内容")
        else:
            json_str = json_match.group()
        
        # 清理JSON字符串
        json_str = self._clean_json_string(json_str)
        
        # 解析JSON
        try:
            result = json.loads(json_str)
            return result
        except json.JSONDecodeError as e:
            self.logger.debug(f"JSON解析失败，内容: {json_str[:500]}...")
            raise e
    
    def _clean_json_string(self, json_str: str) -> str:
        """
        清理JSON字符串，修复常见格式问题
        
        Args:
            json_str: 原始JSON字符串
            
        Returns:
            清理后的JSON字符串
        """
        # 移除多余的空白字符
        json_str = json_str.strip()
        
        # 修复可能的字符编码问题
        json_str = json_str.replace('\u00a0', ' ')  # 非断行空格
        json_str = json_str.replace('\u2028', '\n')  # 行分隔符
        json_str = json_str.replace('\u2029', '\n\n')  # 段分隔符
        
        # 修复常见的JSON格式问题
        # 1. 修复尾随逗号
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        
        # 2. 修复未转义的引号（简单处理）
        # 这里可以添加更多的清理逻辑
        
        return json_str
    
    async def _async_sleep(self, seconds: float):
        """异步睡眠"""
        import asyncio
        await asyncio.sleep(seconds)


# 创建全局实例
ai_retry_parser = AIRetryParser()