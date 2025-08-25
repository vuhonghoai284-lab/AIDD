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


# 定义文档章节模型
class DocumentSection(BaseModel):
    """文档章节"""
    section_title: str = Field(description="章节标题")
    content: str = Field(description="章节内容")
    level: int = Field(description="章节层级，1为一级标题，2为二级标题等")


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
        self.max_tokens = config.get('max_tokens', 4000)
        self.timeout = config.get('timeout', 60)
        self.max_retries = config.get('max_retries', 3)
        
        # 智能分块配置
        self.context_window = config.get('context_window', 128000)
        self.reserved_tokens = config.get('reserved_tokens', 2000)
        self.chunk_overlap = 200  # 分块重叠字符数
        # 计算可用于文档内容的字符数（粗略估算：1个token约等于4个字符）
        self.max_chunk_chars = (self.context_window - self.reserved_tokens) * 4
        
        # 检查API密钥是否正确获取
        if not self.api_key:
            self.logger.error(f"❌ 未找到API密钥，模型配置: {model_config}")
            raise ValueError(f"未找到API密钥，请检查环境变量和配置文件")
        
        self.logger.info(f"📚 文档处理器初始化: Provider={self.provider}, Model={self.model_name}")
        self.logger.info(f"🔑 API密钥状态: {'已配置' if self.api_key else '未配置'} (前6位: {self.api_key[:6]}...)")
        
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
        预处理文档：章节分割和内容整理 - 通过AI一次性完成
        
        Args:
            text: 文档文本内容
            task_id: 任务ID
            progress_callback: 进度回调函数
            
        Returns:
            章节列表
        """
        self.logger.info("📝 开始文档预处理...")
        start_time = time.time()
        
        if progress_callback:
            await progress_callback("开始分析文档结构...", 5)
        
        try:
            # 从模板加载提示词
            system_prompt = prompt_loader.get_system_prompt('document_preprocess')
            
            # 智能分块处理大文档
            chunks = self._split_document_intelligently(text)
            
            all_sections = []
            total_chunks = len(chunks)
            
            for chunk_idx, chunk in enumerate(chunks):
                if progress_callback:
                    progress = 10 + (chunk_idx / total_chunks) * 10  # 10%-20%的进度
                    await progress_callback(f"正在分析第{chunk_idx + 1}/{total_chunks}个文档片段...", int(progress))
                
                # 构建用户提示
                user_prompt = prompt_loader.get_user_prompt(
                    'document_preprocess',
                    format_instructions=self.structure_parser.get_format_instructions(),
                    document_content=chunk
                )
                
                # 创建消息
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt)
                ]
                
                # 调用模型处理单个分块
                self.logger.info(f"📤 调用AI模型处理第{chunk_idx + 1}/{total_chunks}个文档片段")
                response = await self._call_ai_model(messages)
                
                # 解析这个分块的结果
                chunk_sections = self._parse_response(response.content, f"chunk_{chunk_idx}")
                if chunk_sections:
                    all_sections.extend(chunk_sections)
            
            # 合并相邻的相似章节（去重）
            merged_sections = self._merge_similar_sections(all_sections)
            
            processing_time = time.time() - start_time
            self.logger.info(f"📥 文档预处理完成，共处理{total_chunks}个片段，得到{len(merged_sections)}个章节 (耗时: {processing_time:.2f}s)")

            # 保存合并后的结果到数据库
            if self.db and task_id:
                ai_output = AIOutput(
                    task_id=task_id,
                    operation_type="preprocess",
                    input_text=text[:1000],  # 保存前1000字符作为样本
                    raw_output=json.dumps({"sections": merged_sections}, ensure_ascii=False),
                    parsed_output={"sections": merged_sections},
                    processing_time=processing_time,
                    status="success"
                )
                self.db.add(ai_output)
                self.db.commit()
            
            if progress_callback:
                await progress_callback(f"文档解析完成，识别到 {len(merged_sections)} 个章节", 20)
            
            self.logger.info(f"✅ 文档预处理完成，识别到 {len(merged_sections)} 个章节")
            return merged_sections
                
        except Exception as e:
            self.logger.error(f"❌ 文档预处理失败: {str(e)}")
            processing_time = time.time() - start_time
            
            # 保存错误信息到数据库
            if self.db and task_id:
                ai_output = AIOutput(
                    task_id=task_id,
                    operation_type="preprocess",
                    input_text=text[:10000],
                    raw_output="",
                    status="failed",
                    error_message=str(e),
                    processing_time=processing_time
                )
                self.db.add(ai_output)
                self.db.commit()
            
            if progress_callback:
                await progress_callback("文档预处理失败，使用原始文档", 20)
            
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
        
        self.logger.info(f"📊 章节验证完成: {len(sections)} -> {len(valid_sections)}")
        return valid_sections
    
    def _split_document_intelligently(self, text: str) -> List[str]:
        """
        智能分割文档，优先按章节分割，其次按段落分割
        
        Args:
            text: 原始文档文本
            
        Returns:
            分割后的文本块列表
        """
        if len(text) <= self.max_chunk_chars:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        # 首先尝试按章节分割（标题模式：# 、## 、### 等）
        sections = re.split(r'\n(?=#{1,6}\s)', text)
        
        self.logger.info(f"📄 文档按章节分割为 {len(sections)} 个部分")
        
        for section in sections:
            # 如果单个章节就超过限制，需要进一步分割
            if len(section) > self.max_chunk_chars:
                # 保存当前累积的内容
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                # 对超长章节按段落分割
                paragraphs = section.split('\n\n')
                section_chunk = ""
                
                for paragraph in paragraphs:
                    if len(section_chunk + paragraph) > self.max_chunk_chars:
                        if section_chunk:
                            chunks.append(section_chunk.strip())
                        section_chunk = paragraph + "\n\n"
                    else:
                        section_chunk += paragraph + "\n\n"
                
                if section_chunk.strip():
                    chunks.append(section_chunk.strip())
            else:
                # 检查加入当前章节后是否超过限制
                if len(current_chunk + section) > self.max_chunk_chars:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = section
                else:
                    current_chunk += "\n" + section if current_chunk else section
        
        # 添加最后一个分块
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        self.logger.info(f"📊 文档最终分割为 {len(chunks)} 个处理单元，平均长度: {sum(len(c) for c in chunks) // len(chunks)} 字符")
        return chunks
    
    def _parse_response(self, content: str, chunk_id: str) -> List[Dict]:
        """
        解析AI响应内容
        
        Args:
            content: AI返回的原始内容
            chunk_id: 分块标识
            
        Returns:
            解析出的章节列表
        """
        try:
            # 查找JSON内容
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                sections = result.get('sections', [])
                self.logger.info(f"✅ {chunk_id} 解析成功，得到 {len(sections)} 个章节")
                return sections
            else:
                self.logger.warning(f"⚠️ {chunk_id} 响应中未找到JSON格式，尝试文本解析")
                return self._parse_text_fallback(content)
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ {chunk_id} JSON解析失败: {str(e)}，尝试文本解析")
            return self._parse_text_fallback(content)
        except Exception as e:
            self.logger.error(f"❌ {chunk_id} 解析完全失败: {str(e)}")
            return []
    
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
    
    def _merge_similar_sections(self, sections: List[Dict]) -> List[Dict]:
        """
        合并相邻的相似章节，去除重复内容
        
        Args:
            sections: 原始章节列表
            
        Returns:
            合并后的章节列表
        """
        if not sections:
            return sections
        
        merged = [sections[0]]
        
        for current in sections[1:]:
            last_merged = merged[-1]
            
            # 检查标题相似度
            if (current.get('section_title', '').strip() == last_merged.get('section_title', '').strip() and
                current.get('level', 1) == last_merged.get('level', 1)):
                # 合并内容
                last_merged['content'] = last_merged.get('content', '') + '\n\n' + current.get('content', '')
                self.logger.debug(f"🔄 合并重复章节: {current.get('section_title', '未知')}")
            else:
                merged.append(current)
        
        self.logger.info(f"📋 章节合并完成: {len(sections)} -> {len(merged)}")
        return merged
    
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
    
    async def analyze_document(self, text: str, prompt_type: str = "preprocess") -> Dict[str, Any]:
        """
        统一的文档分析接口，兼容task_processor的调用
        
        Args:
            text: 文档文本内容
            prompt_type: 提示类型，对于DocumentProcessor仅支持"preprocess"
            
        Returns:
            分析结果
        """
        if prompt_type != "preprocess":
            raise ValueError(f"DocumentProcessor只支持preprocess类型，收到: {prompt_type}")
        
        # 调用预处理方法
        sections = await self.preprocess_document(text)
        
        # 构建返回格式，兼容task_processor的期望
        return {
            "status": "success",
            "data": {
                "document_type": "技术文档",
                "structure": {
                    "total_sections": len(sections),
                    "sections": sections
                }
            },
            "raw_output": json.dumps({"sections": sections}, ensure_ascii=False, indent=2),
            "tokens_used": 100,  # 估算值
            "processing_time": 1.0  # 估算值
        }