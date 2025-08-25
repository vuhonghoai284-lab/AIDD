"""文档预处理服务 - 负责章节提取和文档结构分析"""
import json
import re
import time
import logging
import asyncio
from typing import List, Dict, Optional, Callable, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
try:
    from langchain_core.output_parsers import PydanticOutputParser
except ImportError:
    from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.services.prompt_loader import prompt_loader
from app.models.ai_output import AIOutput
from app.utils.ai_retry_parser import ai_retry_parser, RetryConfig


# 定义文档章节模型
class DocumentSection(BaseModel):
    """文档章节"""
    section_title: str = Field(description="章节标题")
    content: str = Field(description="章节内容")
    level: int = Field(description="章节层级，1为一级标题，2为二级标题等")
    completeness_status: str = Field(
        description="章节完整性状态：complete(完整)/incomplete(不完整)", 
        default="complete"
    )


class DocumentStructure(BaseModel):
    """文档结构"""
    sections: List[DocumentSection] = Field(description="文档章节列表")


class DocumentProcessor:
    """文档预处理服务 - 专门负责文档结构分析和章节提取"""
    
    def __init__(self, model_config: Dict, db_session: Optional[Session] = None):
        """
        初始化文档处理器
        
        Args:
            model_config: AI模型配置
            db_session: 数据库会话
        """
        self.db = db_session
        self.model_config = model_config
        
        # 初始化日志
        self.logger = logging.getLogger(f"document_processor.{id(self)}")
        self.logger.setLevel(logging.INFO)
        
        # 确保日志能输出到控制台
        if not self.logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # 从配置中提取参数 - 兼容两种配置格式
        if 'config' in model_config:
            # 新格式：model_config包含provider和config
            config = model_config['config']
            self.provider = model_config.get('provider', 'openai')
        else:
            # 旧格式：model_config直接包含配置
            config = model_config
            self.provider = model_config.get('provider', 'openai')
        
        self.api_key = config.get('api_key')
        self.api_base = config.get('base_url')
        self.model_name = config.get('model')
        self.temperature = config.get('temperature', 0.3)
        self.max_tokens = config.get('max_tokens', 8000)
        self.timeout = config.get('timeout', 60)
        self.max_retries = config.get('max_retries', 3)
        
        # 分块配置 - 基于模型的max_tokens和reserved_tokens
        self.reserved_tokens = config.get('reserved_tokens', 2000)
        # 计算可用于文档内容的字符数（1个token约等于4个字符）
        self.available_tokens = self.max_tokens - self.reserved_tokens
        self.max_chunk_chars = self.available_tokens * 4
        
        # 配置JSON解析重试
        self.retry_config = RetryConfig(
            max_retries=config.get('json_parse_retries', 3),
            base_delay=config.get('json_retry_delay', 1.0),
            backoff_multiplier=2.0,
            max_delay=10.0
        )
        
        # 检查API密钥是否正确获取
        if not self.api_key:
            self.logger.error(f"❌ 未找到API密钥，模型配置: {model_config}")
            raise ValueError(f"未找到API密钥，请检查环境变量和配置文件")
        
        self.logger.info(f"📚 文档处理器初始化: Provider={self.provider}, Model={self.model_name}")
        self.logger.info(f"🔑 API密钥状态: {'已配置' if self.api_key else '未配置'} (前6位: {self.api_key[:6]}...)")
        self.logger.info(f"🔄 JSON解析重试配置: 最大重试{self.retry_config.max_retries}次, 基础延迟{self.retry_config.base_delay}秒")
        
        try:
            # 初始化ChatOpenAI模型 - 支持多种兼容OpenAI API的提供商
            self.model = ChatOpenAI(
                api_key=self.api_key,
                base_url=self.api_base,
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                request_timeout=self.timeout,
                max_retries=self.max_retries
            )
            
            # 初始化解析器
            self.structure_parser = PydanticOutputParser(pydantic_object=DocumentStructure)
            self.logger.info("✅ 文档处理器初始化成功")
            
        except Exception as e:
            self.logger.error(f"❌ 文档处理器初始化失败: {str(e)}")
            raise
    
    async def preprocess_document(
        self, 
        text: str, 
        task_id: Optional[int] = None,
        progress_callback: Optional[Callable] = None
    ) -> List[Dict]:
        """
        预处理文档：按批次大小分割文本，然后逐批次进行章节提取
        
        Args:
            text: 文档文本内容
            task_id: 任务ID
            progress_callback: 进度回调函数
            
        Returns:
            章节列表
        """
        self.logger.info("📝 开始文档预处理 - 批次分割 + 章节提取...")
        start_time = time.time()
        
        if progress_callback:
            await progress_callback("开始文档分割...", 5)
        
        try:
            # 第一步：按批次大小分割文档
            batches = self._split_text_by_batch_size(text)
            self.logger.info(f"📚 文档分割完成：{len(text)}字符 -> {len(batches)}个批次")
            
            if progress_callback:
                await progress_callback(f"分割完成，开始逐批次分析...", 10)
            
            # 第二步：逐批次进行AI章节提取
            all_sections = []
            for batch_idx, batch_text in enumerate(batches):
                batch_progress = 10 + int((batch_idx / len(batches)) * 80)
                if progress_callback:
                    await progress_callback(f"分析批次 {batch_idx + 1}/{len(batches)}...", batch_progress)
                
                batch_sections = await self._extract_sections_from_batch(batch_text, batch_idx)
                all_sections.extend(batch_sections)
                
                self.logger.info(f"📄 批次 {batch_idx + 1} 完成：识别到 {len(batch_sections)} 个章节")
            
            # 第三步：验证和清理章节
            if progress_callback:
                await progress_callback(f"验证章节结构...", 90)
            
            final_sections = self.validate_sections(all_sections)
            processing_time = time.time() - start_time
            
            self.logger.info(f"✅ 文档预处理完成：{len(all_sections)} -> {len(final_sections)}个有效章节 (耗时: {processing_time:.2f}s)")

            # 保存结果到数据库
            if self.db and task_id:
                ai_output = AIOutput(
                    task_id=task_id,
                    operation_type="preprocess",
                    input_text=text[:1000],  # 保存前1000字符作为样本
                    raw_output=json.dumps({"sections": final_sections}, ensure_ascii=False),
                    parsed_output={"sections": final_sections},
                    processing_time=processing_time,
                    status="success"
                )
                self.db.add(ai_output)
                self.db.commit()
            
            if progress_callback:
                await progress_callback(f"文档预处理完成，识别到 {len(final_sections)} 个章节", 100)
            
            return final_sections
                
        except Exception as e:
            self.logger.error(f"❌ 文档预处理失败: {str(e)}")
            processing_time = time.time() - start_time
            
            # 保存错误信息到数据库
            if self.db and task_id:
                ai_output = AIOutput(
                    task_id=task_id,
                    operation_type="preprocess",
                    input_text=text[:1000],
                    raw_output="",
                    status="failed",
                    error_message=str(e),
                    processing_time=processing_time
                )
                self.db.add(ai_output)
                self.db.commit()
            
            if progress_callback:
                await progress_callback("文档预处理失败，使用原始文档", 100)
            
            # 返回原始文本作为单一章节
            return [{"section_title": "文档内容", "content": text, "level": 1}]
    
    def validate_sections(self, sections: List[Dict]) -> List[Dict]:
        """
        验证和过滤章节
        
        Args:
            sections: 章节列表
            
        Returns:
            有效的章节列表
        """
        valid_sections = []
        
        for section in sections:
            # 检查必需字段
            if not isinstance(section, dict):
                self.logger.warning("⚠️ 跳过非字典类型的章节")
                continue
                
            if 'content' not in section or not section['content']:
                self.logger.warning("⚠️ 跳过没有内容的章节")
                continue
                
            # 检查内容长度
            content = section['content']
            if len(content.strip()) < 20:
                self.logger.warning(f"⚠️ 跳过内容太短的章节: {section.get('section_title', '未知')}")
                continue
            
            # 设置默认值
            if 'section_title' not in section:
                section['section_title'] = '未命名章节'
            if 'level' not in section:
                section['level'] = 1
                
            valid_sections.append(section)
        
        # 为每个章节添加默认完整性状态（如果未设置）
        for section in valid_sections:
            if 'completeness_status' not in section:
                section['completeness_status'] = 'unknown'
        
        self.logger.info(f"📊 章节验证完成: {len(sections)} -> {len(valid_sections)}")
        return valid_sections
    
    def _split_text_by_batch_size(self, text: str) -> List[str]:
        """
        按批次大小直接分割文本
        
        Args:
            text: 原始文档文本
            
        Returns:
            分割后的批次列表
        """
        # 计算批次大小（基于模型的token限制）
        batch_chars = self.max_chunk_chars  # 已经考虑了reserved_tokens
        
        self.logger.info(f"📐 分割参数：文档{len(text)}字符，批次大小={batch_chars}字符")
        
        # 如果文档小于批次大小，直接返回
        if len(text) <= batch_chars:
            self.logger.info(f"📄 文档较小，单批次处理")
            return [text]
        
        batches = []
        start = 0
        
        while start < len(text):
            # 直接按固定长度分割
            end = start + batch_chars
            batch_content = text[start:end]
            
            if batch_content:  # 跳过空内容
                batches.append(batch_content)
                self.logger.debug(f"📦 批次 {len(batches)}: {len(batch_content)}字符")
            
            start = end
        
        self.logger.info(f"✅ 文档分割完成：{len(batches)}个批次，平均{sum(len(b) for b in batches) // len(batches) if batches else 0}字符/批次")
        return batches
    
    async def _extract_sections_from_batch(self, batch_text: str, batch_index: int) -> List[Dict]:
        """
        从单个批次中提取章节，并标记完整性
        
        Args:
            batch_text: 批次文本内容
            batch_index: 批次索引
            
        Returns:
            章节列表，包含完整性标记
        """
        self.logger.info(f"📄 处理批次 {batch_index + 1}：{len(batch_text)}字符")
        
        try:
            # 加载系统提示
            system_prompt = prompt_loader.get_system_prompt('document_preprocess')
            
            # 构建用户提示
            user_prompt = prompt_loader.get_user_prompt(
                'document_preprocess',
                format_instructions=self.structure_parser.get_format_instructions(),
                document_content=batch_text
            )
            
            # 创建消息
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            # 调用AI模型
            response = await self._call_ai_model(messages)
            
            # 使用重试解析器进行JSON解析
            async def ai_call_func():
                return response  # 直接返回已有的响应
            
            # 定义JSON提取函数
            def json_extractor(content: str) -> Dict[str, Any]:
                # 查找JSON内容
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    result = json.loads(json_str)
                    # 验证结果结构
                    if 'sections' not in result:
                        result = {'sections': []}
                    return result
                else:
                    raise ValueError("未找到JSON格式内容")
            
            try:
                # 使用带重试的解析器
                result = await ai_retry_parser.parse_json_with_retry(
                    ai_call_func=ai_call_func,
                    json_extractor=json_extractor,
                    retry_config=self.retry_config,
                    operation_name=f"解析批次 {batch_index + 1}"
                )
                
                sections = result.get('sections', [])
                
                if not sections:
                    # 如果解析成功但没有章节，创建默认章节
                    sections = [{
                        "section_title": f"批次 {batch_index + 1}",
                        "content": batch_text,
                        "level": 1,
                        "completeness_status": "incomplete"
                    }]
                    
            except Exception as e:
                self.logger.error(f"❌ 批次 {batch_index + 1} JSON解析失败 (包含重试): {str(e)}")
                # 如果重试解析都失败，使用文本回退方案
                sections = self._parse_text_fallback(response.content)
                if not sections:
                    sections = [{
                        "section_title": f"批次 {batch_index + 1} (解析失败)",
                        "content": batch_text,
                        "level": 1,
                        "completeness_status": "incomplete"
                    }]
            
            self.logger.info(f"✅ 批次 {batch_index + 1} 处理完成：识别到 {len(sections)} 个章节")
            
            # 记录完整性统计
            completeness_stats = {}
            for section in sections:
                status = section.get('completeness_status', 'unknown')
                completeness_stats[status] = completeness_stats.get(status, 0) + 1
            
            if completeness_stats:
                self.logger.info(f"📊 批次 {batch_index + 1} 完整性统计: {completeness_stats}")
            
            return sections
            
        except Exception as e:
            self.logger.error(f"❌ 批次 {batch_index + 1} 处理失败: {str(e)}")
            # 返回默认章节
            return [{
                "section_title": f"批次 {batch_index + 1} (处理失败)",
                "content": batch_text,
                "level": 1,
                "completeness_status": "incomplete"
            }]
    
    
    def _parse_text_fallback(self, content: str) -> List[Dict]:
        """
        当JSON解析失败时的文本解析后备方案
        
        Args:
            content: AI响应内容
            
        Returns:
            解析出的章节列表
        """
        sections = []
        # 简单的基于标题的文本分割
        parts = re.split(r'\n(?=#{1,6}\s)', content)
        
        for i, part in enumerate(parts):
            if part.strip():
                title_match = re.match(r'^(#{1,6})\s*(.+)', part.strip())
                if title_match:
                    level = len(title_match.group(1))
                    title = title_match.group(2)
                    content_text = part[len(title_match.group(0)):].strip()
                else:
                    level = 1
                    title = f"章节 {i+1}"
                    content_text = part.strip()
                
                if len(content_text) > 20:  # 过滤太短的内容
                    sections.append({
                        "section_title": title,
                        "content": content_text,
                        "level": level
                    })
        
        # 如果没有找到任何有效章节，返回默认章节
        if not sections:
            sections.append({
                "section_title": "文档内容",
                "content": content,
                "level": 1
            })
        
        return sections
    
    async def _call_ai_model(self, messages):
        """
        调用AI模型（仅在此方法内进行mock判断）
        
        Args:
            messages: 消息列表
            
        Returns:
            AI模型响应
        """
        # 直接进行真实的AI调用
        return await asyncio.to_thread(self.model.invoke, messages)
    
