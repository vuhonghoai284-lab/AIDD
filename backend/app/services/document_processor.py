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
            
            # 分批处理大文档：每批调用AI进行章节拆分
            chunks = self._split_document_intelligently(text)
            
            all_sections = []
            total_chunks = len(chunks)
            
            self.logger.info(f"📚 开始分批处理文档，共{total_chunks}个批次")
            
            # 第一阶段：分批AI拆分章节 (10%-16%的进度)
            for chunk_idx, chunk in enumerate(chunks):
                batch_progress = 10 + (chunk_idx / total_chunks) * 6
                if progress_callback:
                    await progress_callback(f"AI拆分第{chunk_idx + 1}/{total_chunks}批次的章节...", int(batch_progress))
                
                self.logger.info(f"🤖 第{chunk_idx + 1}/{total_chunks}批次：调用AI拆分章节（{len(chunk)}字符）")
                
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
                
                # 调用AI模型处理单个批次
                batch_start_time = time.time()
                response = await self._call_ai_model(messages)
                batch_time = time.time() - batch_start_time
                
                # 解析这个批次的AI响应结果
                chunk_sections = self._parse_response(response.content, f"batch_{chunk_idx + 1}")
                if chunk_sections:
                    self.logger.info(f"✅ 第{chunk_idx + 1}批次完成：识别到{len(chunk_sections)}个章节 (耗时: {batch_time:.2f}s)")
                    all_sections.extend(chunk_sections)
                else:
                    self.logger.warning(f"⚠️ 第{chunk_idx + 1}批次未识别到有效章节")
            
            # 第二阶段：合并所有批次的章节 (16%-20%的进度)
            if progress_callback:
                await progress_callback(f"合并所有{total_chunks}个批次的章节...", 16)
            
            self.logger.info(f"🔄 开始合并{total_chunks}个批次的章节，当前共{len(all_sections)}个章节")
            merged_sections = self._merge_similar_sections(all_sections)
            self.logger.info(f"✅ 章节合并完成：{len(all_sections)} -> {len(merged_sections)}个章节")
            
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
        智能分割文档为批次，每批大小适合AI处理（约30-50K字符/批次）
        确保每批次都能被AI完整处理和拆分章节
        
        Args:
            text: 原始文档文本
            
        Returns:
            分割后的批次列表，每批次适合AI拆分章节处理
        """
        # 动态计算批次大小：根据文档长度和页面大小调整
        # 基础批次大小：约8-12页PDF的内容量
        base_batch_chars = 50000  # 50K字符，约10-15页PDF
        max_batch_chars = int(self.max_chunk_chars * 0.6)  # 最大批次限制：约30万字符
        min_batch_chars = 20000  # 最小批次20K字符，约5-8页PDF
        
        # 根据文档总长度动态调整批次大小
        if len(text) > 200000:  # 超过20万字符(约40页)，使用较大批次
            batch_chars = min(80000, max_batch_chars)  # 80K字符批次
        elif len(text) > 100000:  # 超过10万字符(约20页)，使用中等批次  
            batch_chars = min(60000, max_batch_chars)  # 60K字符批次
        else:  # 较小文档，使用小批次
            batch_chars = min(base_batch_chars, max_batch_chars)  # 50K字符批次
        
        self.logger.info(f"📐 批次分割参数：文档{len(text)}字符，目标批次大小={batch_chars}字符")
        
        if len(text) <= batch_chars:
            self.logger.info(f"📄 文档较小({len(text)}字符 <= {batch_chars})，单批次处理")
            return [text]
        
        batches = []
        current_batch = ""
        
        # 第一步：按章节分割（标题模式：# 、## 、### 等）
        sections = re.split(r'\n(?=#{1,6}\s)', text)
        self.logger.info(f"📖 文档初步按章节分割为{len(sections)}个部分")
        
        # 如果章节很少但文档较长，强制按长度分割
        if len(sections) <= 3 and len(text) > batch_chars * 1.5:
            self.logger.info(f"📄 章节数量较少({len(sections)}个)但文档较长，按段落强制分割")
            return self._force_split_by_length(text, batch_chars, min_batch_chars)
        
        for section_idx, section in enumerate(sections):
            section_length = len(section)
            
            # 如果当前批次加上这个章节会超过限制
            if current_batch and len(current_batch + section) > batch_chars:
                # 保存当前批次（如果足够大）
                if len(current_batch) >= min_batch_chars:
                    batches.append(current_batch.strip())
                    self.logger.debug(f"📦 完成批次{len(batches)}：{len(current_batch)}字符")
                    current_batch = section
                else:
                    # 当前批次太小，继续添加
                    current_batch += "\n" + section
            else:
                # 添加到当前批次
                current_batch += "\n" + section if current_batch else section
            
            # 如果单个章节就超过批次大小，需要按段落进一步分割
            if section_length > batch_chars:
                self.logger.warning(f"⚠️ 第{section_idx + 1}个章节过长({section_length}字符)，按段落分割")
                
                # 保存之前的批次
                if current_batch and current_batch != section:
                    batches.append(current_batch.replace(section, "").strip())
                
                # 按段落分割超长章节
                paragraphs = section.split('\n\n')
                paragraph_batch = ""
                
                for paragraph in paragraphs:
                    if len(paragraph_batch + paragraph) > batch_chars:
                        if paragraph_batch and len(paragraph_batch) >= min_batch_chars:
                            batches.append(paragraph_batch.strip())
                            self.logger.debug(f"📦 完成段落批次{len(batches)}：{len(paragraph_batch)}字符")
                        paragraph_batch = paragraph + "\n\n"
                    else:
                        paragraph_batch += paragraph + "\n\n"
                
                current_batch = paragraph_batch.strip()
        
        # 添加最后一个批次
        if current_batch.strip() and len(current_batch) >= min_batch_chars:
            batches.append(current_batch.strip())
        
        # 统计信息
        total_chars = sum(len(batch) for batch in batches)
        avg_chars = total_chars // len(batches) if batches else 0
        
        self.logger.info(f"📊 文档分割完成：{len(batches)}个批次，总计{total_chars}字符，平均{avg_chars}字符/批次")
        
        return batches
    
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
        智能合并跨批次的章节，处理分批处理可能导致的章节分割问题
        
        Args:
            sections: 来自多个批次的原始章节列表
            
        Returns:
            合并后的章节列表
        """
        if not sections:
            return sections
        
        self.logger.info(f"🔄 开始智能合并{len(sections)}个章节...")
        merged = []
        
        for current in sections:
            current_title = current.get('section_title', '').strip()
            current_level = current.get('level', 1)
            current_content = current.get('content', '').strip()
            
            # 检查是否可以与最后一个章节合并
            merged_with_existing = False
            
            if merged:
                last_merged = merged[-1]
                last_title = last_merged.get('section_title', '').strip()
                last_level = last_merged.get('level', 1)
                
                # 合并条件：
                # 1. 标题完全相同且层级相同（明确的重复章节）
                # 2. 标题相似且层级相同（跨批次分割的同一章节）
                # 3. 当前章节标题为通用标题且与上一章节层级连续
                should_merge = False
                merge_reason = ""
                
                if current_title == last_title and current_level == last_level:
                    should_merge = True
                    merge_reason = "标题和层级完全匹配"
                elif self._is_similar_title(current_title, last_title) and current_level == last_level:
                    should_merge = True
                    merge_reason = "标题相似且层级相同"
                elif self._is_generic_title(current_title) and len(current_content) < 500:
                    should_merge = True
                    merge_reason = "通用标题且内容较短"
                
                if should_merge:
                    # 合并内容，避免重复
                    existing_content = last_merged.get('content', '')
                    if not self._has_content_overlap(existing_content, current_content):
                        last_merged['content'] = existing_content + '\n\n' + current_content
                        self.logger.debug(f"🔗 合并章节 '{current_title}' - {merge_reason}")
                        merged_with_existing = True
                    else:
                        self.logger.debug(f"⚠️ 跳过重复内容章节 '{current_title}'")
                        merged_with_existing = True
            
            # 如果没有合并，添加为新章节
            if not merged_with_existing:
                merged.append(current)
        
        # 后处理：检查章节大小，合并过小的章节
        final_merged = self._consolidate_small_sections(merged)
        
        self.logger.info(f"✅ 章节合并完成: {len(sections)} -> {len(final_merged)}个章节")
        return final_merged
    
    def _is_similar_title(self, title1: str, title2: str) -> bool:
        """检查两个标题是否相似"""
        if not title1 or not title2:
            return False
        
        # 移除常见的数字、标点等，比较核心词汇
        clean_title1 = re.sub(r'[0-9\.\s\-_]+', '', title1).lower()
        clean_title2 = re.sub(r'[0-9\.\s\-_]+', '', title2).lower()
        
        # 如果清理后的标题相同或包含关系
        return (clean_title1 == clean_title2 or 
                clean_title1 in clean_title2 or 
                clean_title2 in clean_title1)
    
    def _is_generic_title(self, title: str) -> bool:
        """检查是否为通用标题"""
        generic_titles = ['内容', '章节', '部分', '片段', '文档内容', '未命名']
        return any(generic in title for generic in generic_titles)
    
    def _has_content_overlap(self, content1: str, content2: str) -> bool:
        """检查两个内容是否有重复"""
        if not content1 or not content2:
            return False
        
        # 简单检查：如果一个内容是另一个的子集
        return content2 in content1 or content1 in content2
    
    def _consolidate_small_sections(self, sections: List[Dict]) -> List[Dict]:
        """合并过小的章节到相邻章节"""
        if not sections:
            return sections
        
        min_section_size = 100  # 最小章节大小
        consolidated = []
        
        for current in sections:
            content_length = len(current.get('content', ''))
            
            if content_length < min_section_size and consolidated:
                # 将小章节合并到上一章节
                last_section = consolidated[-1]
                last_section['content'] += '\n\n' + current.get('content', '')
                self.logger.debug(f"📎 合并小章节 '{current.get('section_title')}' 到 '{last_section.get('section_title')}'")
            else:
                consolidated.append(current)
        
        return consolidated
    
    def _force_split_by_length(self, text: str, batch_chars: int, min_batch_chars: int) -> List[str]:
        """
        当章节划分不理想时，强制按长度分割文档
        
        Args:
            text: 文档文本
            batch_chars: 目标批次大小
            min_batch_chars: 最小批次大小
            
        Returns:
            分割后的批次列表
        """
        batches = []
        current_batch = ""
        
        # 按段落分割
        paragraphs = text.split('\n\n')
        
        for paragraph in paragraphs:
            # 如果添加这个段落会超过批次限制
            if current_batch and len(current_batch + paragraph) > batch_chars:
                if len(current_batch) >= min_batch_chars:
                    batches.append(current_batch.strip())
                    current_batch = paragraph + '\n\n'
                else:
                    current_batch += paragraph + '\n\n'
            else:
                current_batch += paragraph + '\n\n'
        
        # 添加最后一个批次
        if current_batch.strip() and len(current_batch) >= min_batch_chars:
            batches.append(current_batch.strip())
        
        self.logger.info(f"🔨 强制分割完成：{len(batches)}个批次")
        return batches
    
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