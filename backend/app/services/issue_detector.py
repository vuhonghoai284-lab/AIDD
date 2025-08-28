"""静态问题检测服务 - 负责检测文档中的质量问题"""
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
from app.core.config import get_settings
from app.utils.ai_retry_parser import ai_retry_parser, RetryConfig


# 定义结构化输出模型
class DocumentIssue(BaseModel):
    """文档问题模型"""
    type: str = Field(description="问题类型：2-6个字的简短描述，如'错别字'、'语法错误'、'逻辑不通'、'内容缺失'、'格式问题'等，由模型根据实际问题自行判断")
    description: str = Field(description="详细的问题描述，清晰说明具体问题点，包括问题的表现、位置和影响，至少30字以上")
    location: str = Field(description="问题所在位置")
    severity: str = Field(description="基于用户影响程度的严重等级：致命（导致无法使用或严重误导）/严重（影响核心功能理解）/一般（影响质量但不影响理解）/提示（优化建议）")
    confidence: float = Field(description="模型对此问题判定的置信度，范围0.0-1.0", default=0.8)
    suggestion: str = Field(description="修改建议：直接给出修改后的完整内容，而不是描述如何修改")
    original_text: str = Field(description="包含问题的原文内容关键片段，10~30字符", default="")
    user_impact: str = Field(description="该问题对用户阅读理解的影响，10~30字符", default="")
    reasoning: str = Field(description="判定为问题的详细分析和推理过程，20~100字符", default="")
    context: str = Field(description="问题所在的上下文环境（20-200字）：请严格输出包含原文片段的上下文段落的完整内容", default="")


class DocumentIssues(BaseModel):
    """文档问题列表"""
    issues: List[DocumentIssue] = Field(description="发现的所有问题", default=[])


class IssueDetector:
    """静态问题检测服务 - 专门负责文档质量问题检测"""
    
    def __init__(self, model_config: Dict, db_session: Optional[Session] = None):
        """
        初始化问题检测器
        
        Args:
            model_config: AI模型配置
            db_session: 数据库会话
        """
        self.db = db_session
        self.model_config = model_config
        
        # 初始化日志
        self.logger = logging.getLogger(f"issue_detector.{id(self)}")
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
        
        # 配置JSON解析重试
        self.retry_config = RetryConfig(
            max_retries=config.get('json_parse_retries', 3),
            base_delay=config.get('json_retry_delay', 1.0),
            backoff_multiplier=2.0,
            max_delay=10.0
        )
        
        self.logger.info(f"🔍 问题检测器初始化: Provider={self.provider}, Model={self.model_name}")
        self.logger.info(f"🔄 JSON解析重试配置: 最大重试{self.retry_config.max_retries}次, 基础延迟{self.retry_config.base_delay}秒")
        
        try:
            # 不在这里初始化ChatOpenAI模型，改为动态创建以支持模型切换
            # 只初始化解析器
            self.issues_parser = PydanticOutputParser(pydantic_object=DocumentIssues)
            self.logger.info("✅ 问题检测器初始化成功")
            
        except Exception as e:
            self.logger.error(f"❌ 问题检测器初始化失败: {str(e)}")
            raise
    
    async def detect_issues(
        self, 
        sections: List[Dict], 
        task_id: Optional[int] = None,
        progress_callback: Optional[Callable] = None
    ) -> List[Dict]:
        """
        检测文档问题 - 使用异步批量处理
        
        Args:
            sections: 文档章节列表
            task_id: 任务ID
            progress_callback: 进度回调函数
            
        Returns:
            问题列表
        """
        self.logger.info(f"🔍 开始检测文档问题，共 {len(sections)} 个章节")
        
        # 过滤掉太短的章节
        valid_sections = [
            section for section in sections 
            if len(section.get('content', '')) >= 20
        ]
        
        if not valid_sections:
            if progress_callback:
                await progress_callback("没有有效的章节需要检测", 100)
            return []
        
        self.logger.info(f"📊 准备检测 {len(valid_sections)} 个有效章节")
        
        if progress_callback:
            await progress_callback(f"开始检测 {len(valid_sections)} 个章节的问题...", 25)
        
        # 创建异步检测任务
        async def detect_section_issues(section: Dict, index: int) -> List[Dict]:
            """异步检测单个章节的问题"""
            section_title = section.get('section_title', '未知章节')
            section_content = section.get('content', '')
            section_start_time = time.time()
            
            # 更新进度
            progress = 25 + int((index / len(valid_sections)) * 65)
            if progress_callback:
                await progress_callback(f"正在检测章节 {index + 1}/{len(valid_sections)}: {section_title}", progress)
            
            self.logger.debug(f"🔍 [{index + 1}/{len(valid_sections)}] 检测章节: {section_title}")
            self.logger.debug(f"📊 [{index + 1}] 章节信息 - 标题: '{section_title}', 内容长度: {len(section_content)}字符")
            
            try:
                # 从模板加载提示词
                self.logger.debug(f"🔧 [{index + 1}] 加载系统提示模板")
                system_prompt = prompt_loader.get_system_prompt('document_detect_issues')
                
                # 检查章节内容长度，但不截取 - 相信前置的分割和合并已经优化过
                section_content_chars = len(section_content)
                context_window = self.model_config.get('config', {}).get('context_window', 8000)
                
                # 计算理论上下文使用量（仅用于日志和警告）
                system_prompt_length = len(system_prompt) if system_prompt else 0
                format_instructions_length = len(self.issues_parser.get_format_instructions())
                reserved_length = system_prompt_length + format_instructions_length + 500
                estimated_total_chars = reserved_length + section_content_chars
                estimated_tokens = estimated_total_chars // 4  # 粗略估算
                
                self.logger.debug(f"📏 [{index + 1}] 上下文使用 - 章节: {section_content_chars}字符, 预计总计: {estimated_tokens} tokens (窗口: {context_window})")
                
                # 如果内容很长，记录警告但不截取（相信前面的分割合并已经处理过）
                if estimated_tokens > context_window * 0.9:  # 超过90%容量才警告
                    self.logger.warning(f"⚠️ [{index + 1}] 章节 '{section_title}' 内容较长({section_content_chars}字符, ~{estimated_tokens} tokens)，可能接近模型上下文限制")
                    self.logger.info(f"   💡 依赖前置的文档分割和章节合并优化，不在此步骤截取内容")
                
                # 使用完整的章节内容，不截取
                section_content_full = section_content
                
                user_prompt = prompt_loader.get_user_prompt(
                    'document_detect_issues',
                    section_title=section_title,
                    format_instructions=self.issues_parser.get_format_instructions(),
                    section_content=section_content_full
                )

                # 创建消息
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt)
                ]
                
                # 使用重试解析器进行AI调用和JSON解析
                self.logger.info(f"📤 调用模型检测章节 '{section_title}' (支持重试)")
                
                # 定义AI调用函数
                async def ai_call_func():
                    return await self._call_ai_model(messages)
                
                # 定义JSON提取函数
                def json_extractor(content: str) -> Dict[str, Any]:
                    # 查找JSON内容
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group()
                        result = json.loads(json_str)
                        # 验证结果结构
                        if 'issues' not in result:
                            result = {'issues': []}
                        return result
                    else:
                        raise ValueError("未找到JSON格式内容")
                
                try:
                    # 使用带重试的解析器
                    result = await ai_retry_parser.parse_json_with_retry(
                        ai_call_func=ai_call_func,
                        json_extractor=json_extractor,
                        retry_config=self.retry_config,
                        operation_name=f"检测章节 '{section_title}'"
                    )
                    
                    processing_time = time.time() - section_start_time
                    issues = result.get('issues', [])
                    
                    self.logger.info(f"✅ 章节 '{section_title}' 检测完成，发现 {len(issues)} 个问题 (耗时: {processing_time:.2f}s)")
                    
                    # 保存成功结果到数据库 (只添加，不提交)
                    if self.db and task_id:
                        try:
                            # 验证task_id是否有效，避免外键约束失败
                            from app.models.task import Task
                            task_exists = self.db.query(Task.id).filter(Task.id == task_id).first()
                            
                            if task_exists:
                                # 保持原始输入文本内容，不进行任何修改
                                display_input_text = section_content
                                
                                ai_output = AIOutput(
                                    task_id=task_id,
                                    operation_type="detect_issues",
                                    section_title=section_title,
                                    section_index=index,
                                    input_text=display_input_text,
                                    raw_output=json.dumps(result, ensure_ascii=False),
                                    parsed_output=result,
                                    processing_time=processing_time,
                                    status="success"
                                )
                                self.db.add(ai_output)
                                # 移除即时提交，改为批量提交
                            else:
                                self.logger.warning(f"⚠️ task_id {task_id} 不存在，跳过AI输出记录保存")
                        except Exception as db_error:
                            self.logger.error(f"❌ 保存AI输出成功记录时发生错误: {db_error}")
                            # 回滚以避免影响主事务
                            self.db.rollback()
                    
                    # 为每个问题添加章节信息
                    for issue in issues:
                        if 'location' in issue and section_title not in issue.get('location', ''):
                            issue['location'] = f"{section_title} - {issue['location']}"
                    
                    return issues
                
                except Exception as e:
                    import traceback
                    processing_time = time.time() - section_start_time
                    self.logger.error(f"❌ 章节 '{section_title}' 检测失败 (包含重试): {str(e)}")
                    self.logger.error(f"错误类型: {type(e).__name__}")
                    self.logger.debug(f"完整堆栈:\n{traceback.format_exc()}")
                    
                    # 保存失败结果到数据库
                    if self.db and task_id:
                        try:
                            # 验证task_id是否有效，避免外键约束失败
                            from app.models.task import Task
                            task_exists = self.db.query(Task.id).filter(Task.id == task_id).first()
                            
                            if task_exists:
                                # 保持原始输入文本内容，不进行任何修改
                                display_input_text = section_content
                                
                                ai_output = AIOutput(
                                    task_id=task_id,
                                    operation_type="detect_issues",
                                    section_title=section_title,
                                    section_index=index,
                                    input_text=display_input_text,
                                    raw_output="",
                                    processing_time=processing_time,
                                    status="failed_with_retry",
                                    error_message=str(e)
                                )
                                self.db.add(ai_output)
                                # 移除即时提交，改为批量提交
                            else:
                                self.logger.warning(f"⚠️ task_id {task_id} 不存在，跳过AI输出记录保存")
                        except Exception as db_error:
                            self.logger.error(f"❌ 保存AI输出失败记录时发生错误: {db_error}")
                            # 回滚以避免影响主事务
                            self.db.rollback()
                    
                    return []
                    
            except Exception as e:
                import traceback
                self.logger.error(f"❌ 检测章节 '{section_title}' 失败: {str(e)}")
                self.logger.error(f"错误类型: {type(e).__name__}")
                self.logger.error(f"完整堆栈:\n{traceback.format_exc()}")
                processing_time = time.time() - section_start_time
                
                # 保存错误信息到数据库
                if self.db and task_id:
                    try:
                        # 验证task_id是否有效，避免外键约束失败
                        from app.models.task import Task
                        task_exists = self.db.query(Task.id).filter(Task.id == task_id).first()
                        
                        if task_exists:
                            # 智能截取输入文本，避免在句子中间截断
                            display_input_text = self._smart_truncate_text(section_content, 1000)
                            
                            ai_output = AIOutput(
                                task_id=task_id,
                                operation_type="detect_issues",
                                section_title=section_title,
                                section_index=index,
                                input_text=display_input_text,
                                raw_output="",
                                status="failed",
                                error_message=str(e),
                                processing_time=processing_time
                            )
                            self.db.add(ai_output)
                            # 移除即时提交，改为批量提交
                        else:
                            self.logger.warning(f"⚠️ task_id {task_id} 不存在，跳过AI输出记录保存")
                    except Exception as db_error:
                        self.logger.error(f"❌ 保存AI输出错误记录时发生错误: {db_error}")
                        # 回滚以避免影响主事务
                        self.db.rollback()
                
                return []
        
        # 批量并发执行所有章节的检测
        self.logger.info(f"🚀 开始并发检测 {len(valid_sections)} 个章节...")
        
        # 创建所有检测任务
        tasks = [
            detect_section_issues(section, index) 
            for index, section in enumerate(valid_sections)
        ]
        
        # 并发执行所有任务
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 合并所有检测结果
        all_issues = []
        for result in results:
            if isinstance(result, list):
                all_issues.extend(result)
            elif isinstance(result, Exception):
                self.logger.warning(f"⚠️ 某个章节检测出现异常: {str(result)}")
        
        # 批量提交所有数据库操作（解决锁竞争问题）
        if self.db:
            try:
                commit_start = time.time()
                self.db.commit()
                commit_time = (time.time() - commit_start) * 1000
                self.logger.info(f"📝 批量提交AI输出记录完成，耗时: {commit_time:.1f}ms")
            except Exception as commit_error:
                self.logger.error(f"❌ 批量提交AI输出记录失败: {commit_error}")
                try:
                    self.db.rollback()
                    self.logger.info("🔄 数据库回滚完成")
                except Exception as rollback_error:
                    self.logger.error(f"❌ 数据库回滚失败: {rollback_error}")
        
        # 更新进度：完成
        if progress_callback:
            await progress_callback(f"问题检测完成，共发现 {len(all_issues)} 个问题", 100)
        
        self.logger.info(f"✅ 文档检测完成，共发现 {len(all_issues)} 个问题")
        return all_issues
    
    def filter_issues_by_severity(self, issues: List[Dict], min_confidence: float = 0.6) -> List[Dict]:
        """
        根据置信度过滤问题
        
        Args:
            issues: 问题列表
            min_confidence: 最小置信度阈值
            
        Returns:
            过滤后的问题列表
        """
        filtered_issues = []
        
        for issue in issues:
            confidence = issue.get('confidence', 0.8)
            
            # 处理非数字置信度
            try:
                confidence_float = float(confidence)
                if confidence_float >= min_confidence:
                    filtered_issues.append(issue)
                else:
                    self.logger.debug(f"过滤低置信度问题: {issue.get('type', 'Unknown')} (置信度: {confidence})")
            except (ValueError, TypeError):
                # 无效的置信度，跳过此问题
                self.logger.warning(f"跳过无效置信度问题: {issue.get('type', 'Unknown')} (置信度: {confidence})")
        
        self.logger.info(f"问题过滤完成: {len(issues)} -> {len(filtered_issues)} (置信度 >= {min_confidence})")
        return filtered_issues
    
    def categorize_issues(self, issues: List[Dict]) -> Dict[str, List[Dict]]:
        """
        按严重等级分类问题
        
        Args:
            issues: 问题列表
            
        Returns:
            按严重等级分类的问题字典
        """
        categories = {
            '致命': [],
            '严重': [],
            '一般': [],
            '提示': []
        }
        
        for issue in issues:
            severity = issue.get('severity', '一般')
            if severity in categories:
                categories[severity].append(issue)
            else:
                categories['一般'].append(issue)
        
        # 记录统计信息
        for severity, severity_issues in categories.items():
            if severity_issues:
                self.logger.info(f"📊 {severity}问题: {len(severity_issues)} 个")
        
        return categories
    
    async def _call_ai_model(self, messages):
        """
        调用AI模型（动态创建模型实例以支持模型切换）
        
        Args:
            messages: 消息列表
            
        Returns:
            AI模型响应
        """
        # 动态创建ChatOpenAI实例，确保使用最新的模型配置
        model = ChatOpenAI(
            api_key=self.api_key,
            base_url=self.api_base,
            model=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            request_timeout=self.timeout,
            max_retries=self.max_retries
        )
        
        # 记录实际使用的模型信息
        self.logger.debug(f"🤖 动态创建AI模型: {self.model_name} @ {self.api_base}")
        
        # 调用模型
        return await asyncio.to_thread(model.invoke, messages)
    
    async def analyze_document(self, text: str, prompt_type: str = "detect_issues") -> Dict[str, Any]:
        """
        统一的文档分析接口，兼容task_processor的调用
        
        Args:
            text: 文档文本内容
            prompt_type: 提示类型，对于IssueDetector仅支持"detect_issues"
            
        Returns:
            分析结果
        """
        if prompt_type != "detect_issues":
            raise ValueError(f"IssueDetector只支持detect_issues类型，收到: {prompt_type}")
        
        # 将文本转换为章节格式，以便调用detect_issues方法
        sections = [{"section_title": "文档内容", "content": text, "level": 1}]
        
        # 调用问题检测方法
        issues = await self.detect_issues(sections)
        
        # 构建返回格式，兼容task_processor的期望
        return {
            "status": "success",
            "data": {
                "issues": issues,
                "summary": {
                    "total_issues": len(issues),
                    "critical": sum(1 for i in issues if i.get("severity") == "致命"),
                    "major": sum(1 for i in issues if i.get("severity") == "严重"),
                    "normal": sum(1 for i in issues if i.get("severity") == "一般"),
                    "minor": sum(1 for i in issues if i.get("severity") == "提示")
                }
            },
            "raw_output": json.dumps({"issues": issues}, ensure_ascii=False, indent=2),
            "tokens_used": 200,  # 估算值
            "processing_time": 2.0  # 估算值
        }