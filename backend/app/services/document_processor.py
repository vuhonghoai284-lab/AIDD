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
        self.max_tokens = config.get('max_tokens', 8000)
        self.timeout = config.get('timeout', 60)
        self.max_retries = config.get('max_retries', 3)
        
        # 分块配置 - 基于模型的max_tokens和reserved_tokens
        self.reserved_tokens = config.get('reserved_tokens', 2000)
        self.chunk_overlap = 200  # 分块重叠字符数
        # 计算可用于文档内容的字符数（1个token约等于4个字符）
        self.available_tokens = self.max_tokens - self.reserved_tokens
        self.max_chunk_chars = self.available_tokens * 4
        
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
                self.logger.debug(f"🔧 第{chunk_idx + 1}批次：构建AI提示")
                user_prompt = prompt_loader.get_user_prompt(
                    'document_preprocess',
                    format_instructions=self.structure_parser.get_format_instructions(),
                    document_content=chunk
                )
                
                self.logger.debug(f"📏 第{chunk_idx + 1}批次：提示长度 - 系统提示: {len(system_prompt)}字符, 用户提示: {len(user_prompt)}字符")
                
                # 创建消息
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt)
                ]
                
                # 调用AI模型处理单个批次
                self.logger.debug(f"📤 第{chunk_idx + 1}批次：发送请求到AI模型")
                batch_start_time = time.time()
                response = await self._call_ai_model(messages)
                batch_time = time.time() - batch_start_time
                
                self.logger.info(f"📥 第{chunk_idx + 1}批次：收到AI响应 - 耗时: {batch_time:.2f}s, 响应长度: {len(response.content)}字符")
                
                # 解析这个批次的AI响应结果
                self.logger.debug(f"🔍 第{chunk_idx + 1}批次：开始解析AI响应")
                chunk_sections = self._parse_response(response.content, f"batch_{chunk_idx + 1}")
                if chunk_sections:
                    self.logger.info(f"✅ 第{chunk_idx + 1}批次完成：识别到{len(chunk_sections)}个章节 (耗时: {batch_time:.2f}s)")
                    all_sections.extend(chunk_sections)
                else:
                    self.logger.warning(f"⚠️ 第{chunk_idx + 1}批次未识别到有效章节")
            
            # 第二阶段：大模型质量检查和优化 (16%-18%的进度)
            if progress_callback:
                await progress_callback(f"大模型评估{len(all_sections)}个章节的分割质量...", 16)
            
            self.logger.info(f"🤖 开始大模型质量检查{total_chunks}个批次得到的{len(all_sections)}个章节")
            optimized_sections = await self._ai_optimize_sections(all_sections, text)
            self.logger.info(f"✅ AI优化完成：{len(all_sections)} -> {len(optimized_sections)}个优化章节")
            
            # 第三阶段：验证和清理章节 (18%-20%的进度)
            if progress_callback:
                await progress_callback(f"验证{len(optimized_sections)}个优化章节...", 18)
            
            self.logger.info(f"🔍 开始验证优化后的{len(optimized_sections)}个章节")
            merged_sections = self.validate_sections(optimized_sections)
            self.logger.info(f"✅ 章节验证完成：{len(optimized_sections)} -> {len(merged_sections)}个有效章节")
            
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
        基于模型token限制分割文档
        
        Args:
            text: 原始文档文本
            
        Returns:
            分割后的批次列表，每批次适合AI处理
        """
        # 使用模型配置计算批次大小
        # max_tokens - reserved_tokens = available_tokens
        # available_tokens * 4 = available_chars (1 token ≈ 4 chars)
        batch_chars = self.max_chunk_chars
        min_batch_chars = max(1000, batch_chars // 10)  # 最小批次不少于1000字符
        
        self.logger.info(f"📐 分割参数：文档{len(text)}字符，批次大小={batch_chars}字符 (基于{self.available_tokens} tokens)")
        
        if len(text) <= batch_chars:
            self.logger.info(f"📄 文档较小({len(text)}字符 <= {batch_chars})，单批次处理")
            return [text]
        
        batches = []
        current_batch = ""
        
        # 第一步：尝试按章节分割（标题模式：# 、## 、### 等）
        sections = re.split(r'\n(?=#{1,6}\s)', text)
        self.logger.info(f"📖 文档按章节分割为{len(sections)}个部分")
        
        # 如果章节很少但文档较长，按段落分割
        if len(sections) <= 2 and len(text) > batch_chars:
            self.logger.info(f"📄 章节较少({len(sections)}个)且文档较长，按段落分割")
            return self._split_by_paragraphs(text, batch_chars, min_batch_chars)
        
        # 按章节组装批次
        for section in sections:
            # 如果当前批次加上这个章节会超过限制
            if current_batch and len(current_batch + section) > batch_chars:
                # 保存当前批次
                if current_batch.strip():
                    batches.append(current_batch.strip())
                    self.logger.debug(f"📦 完成批次{len(batches)}：{len(current_batch)}字符")
                current_batch = section
            else:
                # 添加到当前批次
                current_batch += "\n" + section if current_batch else section
            
            # 如果单个章节过长，按段落分割
            if len(section) > batch_chars:
                self.logger.warning(f"⚠️ 章节过长({len(section)}字符)，按段落分割")
                
                # 如果当前批次不是该章节本身，先保存之前的内容
                if current_batch != section and current_batch.strip():
                    batches.append(current_batch.replace(section, "").strip())
                
                # 分割超长章节
                section_batches = self._split_by_paragraphs(section, batch_chars, min_batch_chars)
                batches.extend(section_batches)
                current_batch = ""
        
        # 添加最后一个批次
        if current_batch.strip():
            batches.append(current_batch.strip())
        
        self.logger.info(f"📊 文档分割完成：{len(batches)}个批次，平均{sum(len(b) for b in batches) // len(batches) if batches else 0}字符/批次")
        
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
    
    def _split_by_paragraphs(self, text: str, batch_chars: int, min_batch_chars: int) -> List[str]:
        """
        按段落分割文本，增强分割策略
        
        Args:
            text: 要分割的文本
            batch_chars: 批次大小限制
            min_batch_chars: 最小批次大小
            
        Returns:
            分割后的批次列表
        """
        batches = []
        current_batch = ""
        
        # 尝试多种分割策略
        # 1. 首先按双换行符分割
        paragraphs = text.split('\n\n')
        self.logger.info(f"📄 按段落(\\n\\n)分割得到{len(paragraphs)}个段落")
        
        # 如果段落数量太少，尝试单换行符分割
        if len(paragraphs) <= 3 and len(text) > batch_chars:
            paragraphs = text.split('\n')
            self.logger.info(f"📄 按行(\\n)分割得到{len(paragraphs)}个行")
            
            # 如果还是太少，按固定长度强制分割
            if len(paragraphs) <= 10:
                return self._force_split_by_length(text, batch_chars, min_batch_chars)
        
        for i, paragraph in enumerate(paragraphs):
            paragraph = paragraph.strip()
            if not paragraph:  # 跳过空段落
                continue
                
            # 如果单个段落就超过批次大小，进一步分割
            if len(paragraph) > batch_chars:
                # 保存当前批次
                if current_batch.strip():
                    batches.append(current_batch.strip())
                    current_batch = ""
                
                # 按句号分割超长段落
                sentences = paragraph.split('。')
                for sentence in sentences:
                    if sentence.strip():
                        sentence_with_period = sentence.strip() + '。' if not sentence.endswith('。') else sentence.strip()
                        
                        if current_batch and len(current_batch + sentence_with_period) > batch_chars:
                            if len(current_batch) >= min_batch_chars:
                                batches.append(current_batch.strip())
                                current_batch = sentence_with_period
                            else:
                                current_batch += sentence_with_period
                        else:
                            current_batch += sentence_with_period if not current_batch else '\n' + sentence_with_period
                continue
            
            # 正常段落处理
            if current_batch and len(current_batch + '\n\n' + paragraph) > batch_chars:
                if len(current_batch) >= min_batch_chars:
                    batches.append(current_batch.strip())
                    self.logger.debug(f"📦 完成段落批次{len(batches)}：{len(current_batch)}字符")
                    current_batch = paragraph
                else:
                    current_batch += '\n\n' + paragraph
            else:
                current_batch += '\n\n' + paragraph if current_batch else paragraph
        
        # 添加最后一个批次
        if current_batch.strip():
            batches.append(current_batch.strip())
        
        # 验证分割效果
        total_chars = sum(len(batch) for batch in batches)
        self.logger.info(f"📊 段落分割完成：{len(batches)}个批次，总计{total_chars}字符，平均{total_chars // len(batches) if batches else 0}字符/批次")
        
        return batches
    
    def _force_split_by_length(self, text: str, batch_chars: int, min_batch_chars: int) -> List[str]:
        """
        强制按长度分割文档
        
        Args:
            text: 文档文本
            batch_chars: 目标批次大小
            min_batch_chars: 最小批次大小
            
        Returns:
            分割后的批次列表
        """
        batches = []
        start = 0
        
        while start < len(text):
            # 计算这个批次的结束位置
            end = start + batch_chars
            
            # 如果不是最后一批次，尝试在合适位置分割（避免在单词中间）
            if end < len(text):
                # 向后查找合适的分割点（换行符、句号、空格）
                search_start = max(start + min_batch_chars, end - 500)  # 在目标位置前500字符内查找
                for split_char in ['\n\n', '\n', '。', '！', '？', '，', ' ']:
                    split_pos = text.rfind(split_char, search_start, end)
                    if split_pos > search_start:
                        end = split_pos + len(split_char)
                        break
            
            # 提取这个批次
            batch = text[start:end].strip()
            if batch and len(batch) >= min_batch_chars:
                batches.append(batch)
                self.logger.debug(f"📦 强制分割批次{len(batches)}：{len(batch)}字符")
            
            start = end
        
        self.logger.info(f"🔨 强制分割完成：{len(batches)}个批次")
        return batches
    
    async def _ai_optimize_sections(self, sections: List[Dict], original_text: str) -> List[Dict]:
        """
        使用大模型评估和优化章节分割质量
        
        Args:
            sections: 初步识别的章节列表
            original_text: 原始文档文本
            
        Returns:
            优化后的章节列表
        """
        if not sections:
            return sections
        
        try:
            # 构建质量评估提示
            quality_assessment = await self._assess_section_quality(sections, original_text)
            
            if quality_assessment.get('needs_optimization', False):
                self.logger.info(f"🔄 大模型建议优化章节分割：{quality_assessment.get('reason', '未知原因')}")
                
                # 根据大模型建议进行优化
                optimized_sections = await self._apply_ai_optimization(sections, quality_assessment)
                
                return optimized_sections
            else:
                self.logger.info(f"✅ 大模型确认章节分割质量良好")
                return sections
                
        except Exception as e:
            self.logger.error(f"❌ AI优化过程失败: {str(e)}，使用原始章节")
            return sections
    
    async def _assess_section_quality(self, sections: List[Dict], original_text: str) -> Dict:
        """
        让大模型评估章节分割质量
        
        Args:
            sections: 章节列表
            original_text: 原始文档文本
            
        Returns:
            质量评估结果
        """
        # 构建章节摘要信息
        section_summaries = []
        for i, section in enumerate(sections):
            title = section.get('section_title', f'章节{i+1}')
            content_preview = section.get('content', '')[:200] + "..." if len(section.get('content', '')) > 200 else section.get('content', '')
            content_length = len(section.get('content', ''))
            level = section.get('level', 1)
            
            section_summaries.append(f"""
章节 {i+1}: {title} (层级: {level}, 长度: {content_length}字符)
内容预览: {content_preview}
""")
        
        # 构建评估提示
        system_prompt = """你是一个文档结构分析专家。请逐个评估以下章节的完整性和分割质量：

## 主要检测点：
1. **章节完整性检测**：章节内容是否在句子、段落或逻辑单元中间被切断
2. **边界合理性**：章节开始和结束位置是否符合文档逻辑结构  
3. **内容连续性**：是否有相关内容被不合理分离到不同章节
4. **分割准确性**：章节边界是否准确识别了标题和内容的分界线

## 完整性判断标准：
- **完整(complete)**：章节有明确开头和结尾，内容逻辑完整
- **不完整(incomplete)**：内容在句子/段落中间截断，或缺少开头/结尾
- **需合并(need_merge)**：与相邻章节应该合并为一个逻辑单元
- **需分割(need_split)**：包含了应该分开的多个逻辑单元

请以JSON格式返回评估结果：
{
  "needs_optimization": true/false,
  "overall_quality": "good/fair/poor",
  "section_completeness": [
    {
      "section_index": 0,
      "completeness_status": "complete/incomplete/need_merge/need_split", 
      "confidence": 0.9,
      "issues": ["具体问题描述"],
      "content_boundary_analysis": "开头/结尾边界分析"
    }
  ],
  "recommendations": {
    "merge_pairs": [[索引1, 索引2]],
    "split_suggestions": [{"section_index": 索引, "reason": "原因"}]
  },
  "reason": "主要问题总结"
}"""
        
        user_prompt = f"""
## 文档基本信息
- 文档总长度: {len(original_text)}字符
- 识别到的章节数量: {len(sections)}

## 章节详细信息
{''.join(section_summaries)}

## 任务要求
请逐个分析每个章节的完整性状态，重点检查：
1. 每个章节的开头是否是自然的开始点（如标题、段落开头）
2. 每个章节的结尾是否是自然的结束点（如段落结尾、完整句子）
3. 章节内容是否构成一个完整的逻辑单元
4. 是否有章节应该合并或分割

请为每个章节提供明确的完整性标记和建议。
"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = await self._call_ai_model(messages)
        
        # 解析AI响应
        return self._parse_quality_assessment(response.content)
    
    def _parse_quality_assessment(self, content: str) -> Dict:
        """
        解析质量评估响应
        
        Args:
            content: AI响应内容
            
        Returns:
            解析后的评估结果
        """
        try:
            import json
            import re
            
            # 查找JSON内容
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                self.logger.debug(f"🔍 AI质量评估结果: {result}")
                return result
            else:
                self.logger.warning("⚠️ AI响应中未找到JSON格式的评估结果")
                return {'needs_optimization': False, 'overall_quality': 'fair'}
                
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ 质量评估JSON解析失败: {str(e)}")
            return {'needs_optimization': False, 'overall_quality': 'fair'}
        except Exception as e:
            self.logger.error(f"❌ 质量评估解析完全失败: {str(e)}")
            return {'needs_optimization': False, 'overall_quality': 'fair'}
    
    async def _apply_ai_optimization(self, sections: List[Dict], assessment: Dict) -> List[Dict]:
        """
        根据AI评估结果应用优化
        
        Args:
            sections: 原始章节列表
            assessment: AI评估结果
            
        Returns:
            优化后的章节列表
        """
        optimized_sections = sections.copy()
        
        # 首先处理章节完整性标记
        section_completeness = assessment.get('section_completeness', [])
        if section_completeness:
            self.logger.info(f"📋 处理{len(section_completeness)}个章节的完整性标记")
            optimized_sections = self._apply_completeness_fixes(optimized_sections, section_completeness)
        
        # 然后应用其他建议
        recommendations = assessment.get('recommendations', {})
        
        # 应用合并建议
        merge_pairs = recommendations.get('merge_pairs', [])
        if merge_pairs:
            self.logger.info(f"📋 应用AI合并建议: {len(merge_pairs)}对章节")
            optimized_sections = self._apply_merge_recommendations(optimized_sections, merge_pairs)
        
        return optimized_sections
    
    def _apply_completeness_fixes(self, sections: List[Dict], completeness_data: List[Dict]) -> List[Dict]:
        """
        根据大模型的完整性标记应用修复
        
        Args:
            sections: 原始章节列表
            completeness_data: 完整性检测结果
            
        Returns:
            修复后的章节列表
        """
        # 为每个章节添加完整性标记
        for completion_info in completeness_data:
            section_idx = completion_info.get('section_index', -1)
            if 0 <= section_idx < len(sections):
                section = sections[section_idx]
                
                # 添加AI分析结果到章节信息中
                section['ai_completeness_status'] = completion_info.get('completeness_status', 'unknown')
                section['ai_confidence'] = completion_info.get('confidence', 0.0)
                section['ai_issues'] = completion_info.get('issues', [])
                section['ai_boundary_analysis'] = completion_info.get('content_boundary_analysis', '')
                
                # 记录日志
                status = completion_info.get('completeness_status', 'unknown')
                confidence = completion_info.get('confidence', 0.0)
                issues = completion_info.get('issues', [])
                
                if status == 'incomplete':
                    self.logger.warning(f"⚠️ 章节{section_idx} '{section.get('section_title', '')}' 标记为不完整 (置信度: {confidence:.2f})")
                    if issues:
                        self.logger.warning(f"   问题: {'; '.join(issues)}")
                elif status == 'need_merge':
                    self.logger.info(f"🔗 章节{section_idx} '{section.get('section_title', '')}' 建议合并 (置信度: {confidence:.2f})")
                elif status == 'need_split':
                    self.logger.info(f"✂️ 章节{section_idx} '{section.get('section_title', '')}' 建议分割 (置信度: {confidence:.2f})")
                elif status == 'complete':
                    self.logger.debug(f"✅ 章节{section_idx} '{section.get('section_title', '')}' 完整性良好 (置信度: {confidence:.2f})")
                
        self.logger.info(f"📊 完整性标记统计:")
        status_counts = {}
        for completion_info in completeness_data:
            status = completion_info.get('completeness_status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        for status, count in status_counts.items():
            self.logger.info(f"   - {status}: {count}个章节")
        
        return sections
    
    def _apply_merge_recommendations(self, sections: List[Dict], merge_pairs: List[List[int]]) -> List[Dict]:
        """
        应用合并建议
        
        Args:
            sections: 章节列表
            merge_pairs: 需要合并的章节索引对
            
        Returns:
            合并后的章节列表
        """
        merged_sections = []
        merged_indices = set()
        
        # 按索引排序合并对，从后往前处理避免索引变化
        merge_pairs.sort(key=lambda x: max(x), reverse=True)
        
        for pair in merge_pairs:
            if len(pair) >= 2:
                idx1, idx2 = pair[0], pair[1]
                
                # 确保索引有效且未被处理
                if (0 <= idx1 < len(sections) and 0 <= idx2 < len(sections) and 
                    idx1 not in merged_indices and idx2 not in merged_indices):
                    
                    # 合并内容
                    section1 = sections[idx1]
                    section2 = sections[idx2]
                    
                    merged_section = {
                        'section_title': f"{section1.get('section_title', '')} (AI合并)",
                        'content': section1.get('content', '') + '\n\n' + section2.get('content', ''),
                        'level': min(section1.get('level', 1), section2.get('level', 1)),
                        'merged_by_ai': True,
                        'original_indices': [idx1, idx2]
                    }
                    
                    # 标记为已合并
                    merged_indices.update([idx1, idx2])
                    
                    self.logger.debug(f"🔗 AI建议合并章节 {idx1} 和 {idx2}")
        
        # 构建最终章节列表
        for i, section in enumerate(sections):
            if i not in merged_indices:
                merged_sections.append(section)
        
        # 添加合并后的章节
        for pair in merge_pairs:
            if len(pair) >= 2:
                idx1, idx2 = pair[0], pair[1]
                if (0 <= idx1 < len(sections) and 0 <= idx2 < len(sections)):
                    section1 = sections[idx1]
                    section2 = sections[idx2]
                    
                    merged_section = {
                        'section_title': f"{section1.get('section_title', '')} (AI合并)",
                        'content': section1.get('content', '') + '\n\n' + section2.get('content', ''),
                        'level': min(section1.get('level', 1), section2.get('level', 1)),
                        'merged_by_ai': True,
                        'original_indices': [idx1, idx2]
                    }
                    merged_sections.append(merged_section)
        
        return merged_sections
    
    async def _apply_boundary_adjustments(self, sections: List[Dict], adjustments: List[Dict]) -> List[Dict]:
        """
        应用边界调整建议
        
        Args:
            sections: 章节列表
            adjustments: 边界调整建议
            
        Returns:
            调整后的章节列表
        """
        # 这里可以实现更复杂的边界调整逻辑
        # 目前返回原始章节，避免过度复杂化
        self.logger.info(f"📋 收到{len(adjustments)}项边界调整建议，暂时保持原有边界")
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