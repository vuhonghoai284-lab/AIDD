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
        
        # 从配置中提取参数 - 直接从model_config获取，因为传入的已经是config部分
        self.provider = model_config.get('provider', 'openai')  # 这个字段可能不在config中
        self.api_key = model_config.get('api_key')
        self.api_base = model_config.get('base_url')
        self.model_name = model_config.get('model')
        self.temperature = model_config.get('temperature', 0.3)
        self.max_tokens = model_config.get('max_tokens', 4000)
        self.timeout = model_config.get('timeout', 60)
        self.max_retries = model_config.get('max_retries', 3)
        
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
            
            # 构建用户提示
            user_prompt = prompt_loader.get_user_prompt(
                'document_preprocess',
                format_instructions=self.structure_parser.get_format_instructions(),
                document_content=text[:10000]  # 限制长度以避免超出token限制
            )

            # 创建消息
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            if progress_callback:
                await progress_callback("正在调用AI模型分析文档...", 10)
            
            # 调用模型（仅在此处进行mock判断）
            self.logger.info("📤 调用AI模型进行文档预处理")
            response = await self._call_ai_model(messages)
            processing_time = time.time() - start_time
            
            self.logger.info(f"📥 收到预处理响应 (耗时: {processing_time:.2f}s)")
            
            # 保存AI输出到数据库
            if self.db and task_id:
                ai_output = AIOutput(
                    task_id=task_id,
                    operation_type="preprocess",
                    input_text=text[:10000],  # 保存部分输入文本
                    raw_output=response.content,
                    processing_time=processing_time,
                    status="success"
                )
            
            if progress_callback:
                await progress_callback("正在解析AI分析结果...", 15)
            
            # 解析响应
            try:
                content = response.content
                self.logger.debug(f"原始响应 (前500字符): {str(content)[:500]}")
                
                # 尝试解析JSON
                if isinstance(content, str):
                    self.logger.debug(f"响应长度: {len(content)} 字符")
                    
                    # 查找JSON内容
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group()
                        self.logger.debug(f"找到JSON (前200字符): {json_str[:200]}...")
                        
                        try:
                            result = json.loads(json_str)
                            sections_count = len(result.get('sections', []))
                            self.logger.info(f"✅ 预处理JSON解析成功，包含 {sections_count} 个章节")
                            
                            if progress_callback:
                                await progress_callback(f"文档解析完成，识别到 {sections_count} 个章节", 20)
                                
                        except json.JSONDecodeError as je:
                            self.logger.error(f"❌ 预处理JSON解析失败: {str(je)}")
                            self.logger.error(f"JSON内容: {json_str[:500]}...")
                            # 如果没有找到JSON，返回原文作为单一章节
                            result = {
                                "sections": [{
                                    "section_title": "文档内容",
                                    "content": text,
                                    "level": 1
                                }]
                            }
                    else:
                        self.logger.warning("⚠️ 预处理响应中未找到JSON格式")
                        self.logger.debug(f"完整响应: {content[:1000]}...")
                        # 如果没有找到JSON，返回原文作为单一章节
                        result = {
                            "sections": [{
                                "section_title": "文档内容",
                                "content": text,
                                "level": 1
                            }]
                        }
                else:
                    self.logger.warning(f"⚠️ 预处理响应不是字符串: {type(content)}")
                    result = {"sections": [{"section_title": "文档内容", "content": text, "level": 1}]}
                
                # 更新数据库中的解析结果
                if self.db and task_id:
                    ai_output.parsed_output = result
                    self.db.add(ai_output)
                    self.db.commit()
                
                sections_list = result.get('sections', [])
                self.logger.info(f"✅ 文档预处理完成，识别到 {len(sections_list)} 个章节")
                return sections_list
                
            except Exception as e:
                import traceback
                self.logger.error(f"⚠️ 文档结构解析失败，使用原始文本: {str(e)}")
                self.logger.error(f"错误类型: {type(e).__name__}")
                self.logger.error(f"完整堆栈:\n{traceback.format_exc()}")
                
                # 保存解析错误信息
                if self.db and task_id:
                    ai_output.status = "parsing_error"
                    ai_output.error_message = str(e)
                    self.db.add(ai_output)
                    self.db.commit()
                
                if progress_callback:
                    await progress_callback("文档解析失败，使用原始文档", 20)
                
                return [{"section_title": "文档内容", "content": text, "level": 1}]
                
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