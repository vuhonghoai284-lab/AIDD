"""
章节合并处理器
在文档处理和问题检测之间增加章节合并步骤，提升AI检测准确率
"""
import logging
from typing import Dict, Any, List, Optional, Callable
from app.services.interfaces.task_processor import ITaskProcessor, TaskProcessingStep, ProcessingResult
from app.core.config import get_settings


class SectionMergeProcessor(ITaskProcessor):
    """章节合并处理器 - 将小章节合并以提升AI检测准确率"""
    
    def __init__(self):
        super().__init__(TaskProcessingStep.SECTION_MERGE)
        self.settings = get_settings()
        self.merge_config = self.settings.section_merge_config
        
        # 初始化日志
        self.logger = logging.getLogger(f"section_merge_processor.{id(self)}")
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
    
    async def can_handle(self, context: Dict[str, Any]) -> bool:
        """检查是否有文档处理结果且启用了章节合并"""
        return (
            'document_processing_result' in context and 
            self.merge_config.get('enabled', True)
        )
    
    async def process(self, context: Dict[str, Any], progress_callback: Optional[Callable] = None) -> ProcessingResult:
        """执行章节合并"""
        sections = context.get('document_processing_result', [])
        
        if not sections:
            return ProcessingResult(
                success=False,
                error="没有可合并的章节数据"
            )
        
        if progress_callback:
            await progress_callback("开始章节合并优化...", 25)
        
        try:
            self.logger.info(f"📚 开始章节合并，原始章节数: {len(sections)}")
            
            merged_sections = self._merge_sections(sections)
            
            self.logger.info(f"✅ 章节合并完成: {len(sections)} -> {len(merged_sections)}")
            
            # 更新上下文中的章节数据，供问题检测器使用
            context['section_merge_result'] = merged_sections
            context['original_sections'] = sections  # 保留原始章节数据
            
            if progress_callback:
                await progress_callback(f"章节合并完成: {len(sections)} -> {len(merged_sections)}", 30)
            
            return ProcessingResult(
                success=True,
                data=merged_sections,
                metadata={
                    "original_sections_count": len(sections),
                    "merged_sections_count": len(merged_sections),
                    "merge_ratio": len(merged_sections) / len(sections) if sections else 0,
                    "processing_stage": "section_merge"
                }
            )
            
        except Exception as e:
            self.logger.error(f"❌ 章节合并失败: {str(e)}")
            return ProcessingResult(
                success=False,
                error=f"章节合并失败: {str(e)}"
            )
    
    def _merge_sections(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        合并章节的核心算法
        
        Args:
            sections: 原始章节列表
            
        Returns:
            合并后的章节列表
        """
        if not sections:
            return []
        
        max_chars = self.merge_config.get('max_chars', 5000)
        min_chars = self.merge_config.get('min_chars', 100)
        preserve_structure = self.merge_config.get('preserve_structure', True)
        
        merged_sections = []
        current_merged_section = None
        
        self.logger.info(f"🔧 合并配置 - 最大字符数: {max_chars}, 最小字符数: {min_chars}, 保持结构: {preserve_structure}")
        
        for i, section in enumerate(sections):
            section_content = section.get('content', '')
            section_title = section.get('section_title', '未命名章节')
            section_level = section.get('level', 1)
            content_length = len(section_content)
            
            self.logger.debug(f"处理章节 {i+1}: {section_title} (长度: {content_length}, 层级: {section_level})")
            
            # 如果是第一个章节，直接作为当前合并章节
            if current_merged_section is None:
                current_merged_section = self._create_merged_section(section)
                self.logger.debug(f"初始化合并章节: {section_title}")
                continue
            
            # 计算合并后的长度
            current_length = len(current_merged_section['content'])
            potential_length = current_length + content_length
            
            # 判断是否应该合并
            should_merge = self._should_merge_sections(
                current_merged_section, section, potential_length, max_chars, min_chars, preserve_structure
            )
            
            if should_merge:
                # 合并到当前章节
                self._merge_into_current(current_merged_section, section)
                self.logger.debug(f"合并章节 '{section_title}' 到 '{current_merged_section['section_title']}' (合并后长度: {len(current_merged_section['content'])})")
            else:
                # 完成当前合并章节，开始新的合并章节
                merged_sections.append(current_merged_section)
                current_merged_section = self._create_merged_section(section)
                self.logger.debug(f"完成合并章节，开始新章节: {section_title}")
        
        # 添加最后一个合并章节
        if current_merged_section is not None:
            merged_sections.append(current_merged_section)
        
        # 统计信息
        total_original_chars = sum(len(s.get('content', '')) for s in sections)
        total_merged_chars = sum(len(s.get('content', '')) for s in merged_sections)
        
        self.logger.info(f"📊 合并统计:")
        self.logger.info(f"  - 章节数量: {len(sections)} -> {len(merged_sections)}")
        self.logger.info(f"  - 总字符数: {total_original_chars} -> {total_merged_chars}")
        self.logger.info(f"  - 平均章节长度: {total_merged_chars // len(merged_sections) if merged_sections else 0}")
        
        return merged_sections
    
    def _should_merge_sections(
        self, 
        current_section: Dict[str, Any], 
        next_section: Dict[str, Any], 
        potential_length: int,
        max_chars: int,
        min_chars: int,
        preserve_structure: bool
    ) -> bool:
        """
        智能判断是否应该合并两个章节
        基于章节完整性、内容相关性和AI检测优化原则
        
        Args:
            current_section: 当前合并章节
            next_section: 下一个章节
            potential_length: 合并后的潜在长度
            max_chars: 最大字符数限制
            min_chars: 最小字符数
            preserve_structure: 是否保持结构
            
        Returns:
            是否应该合并
        """
        next_content_length = len(next_section.get('content', ''))
        current_length = len(current_section['content'])
        current_level = current_section.get('level', 1)
        next_level = next_section.get('level', 1)
        
        # === AI完整性标记优先规则 ===
        
        # 规则0: 基于AI完整性标记的合并决策
        current_completeness = current_section.get('completeness_status', 'unknown')
        next_completeness = next_section.get('completeness_status', 'unknown')
        
        # 如果当前章节被AI标记为不完整，应该与下一章节合并
        if current_completeness == 'incomplete':
            if potential_length <= max_chars * 1.1:  # 允许轻微超出
                self.logger.debug(f"🤖 AI驱动合并: 当前章节不完整")
                return True
        
        # 如果下一章节被标记为不完整，也可能需要合并以形成完整内容
        if next_completeness == 'incomplete' and next_content_length < min_chars * 2:
            if potential_length <= max_chars:
                self.logger.debug(f"🤖 AI驱动合并: 下一章节不完整且较短")
                return True
        
        # === 传统强制合并规则 ===
        
        # 规则1: 极短章节必须合并（可能是分割导致的片段）
        if next_content_length < min_chars:
            self.logger.debug(f"🔗 强制合并: 下一章节过短 ({next_content_length} < {min_chars})")
            return True
        
        # 规则2: 识别被分割的章节（标题相似或连续）
        if self._is_likely_split_section(current_section, next_section):
            if potential_length <= max_chars * 1.2:  # 允许轻微超出限制来修复分割
                self.logger.debug(f"🔗 强制合并: 检测到被分割的章节")
                return True
        
        # === 限制性规则 ===
        
        # 规则3: 硬性长度限制
        if potential_length > max_chars:
            self.logger.debug(f"❌ 拒绝合并: 超过最大限制 ({potential_length} > {max_chars})")
            return False
        
        # 规则4: 保护重要章节边界（层级提升）
        if preserve_structure and next_level < current_level:
            self.logger.debug(f"❌ 拒绝合并: 章节层级提升 ({next_level} < {current_level})")
            return False
        
        # === 基础合并规则 ===
        
        # 规则5: 同级章节的适度合并（如果当前章节较短）
        if (preserve_structure and next_level >= current_level and 
            current_length < max_chars * 0.6):  # 当前章节未达60%时可以合并
            self.logger.debug(f"🔗 适度合并: 同级章节且当前较短")
            return True
        
        # 默认不合并
        self.logger.debug("❌ 默认规则: 不合并")
        return False
    
    def _create_merged_section(self, section: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建一个新的合并章节
        
        Args:
            section: 原始章节
            
        Returns:
            新的合并章节
        """
        return {
            'section_title': section.get('section_title', '未命名章节'),
            'content': section.get('content', ''),
            'level': section.get('level', 1),
            'merged_sections': [section.get('section_title', '未命名章节')],  # 记录被合并的章节标题
            'original_section_count': 1,  # 记录合并的原始章节数量
            'is_merged': False  # 标记是否包含合并内容
        }
    
    def _merge_into_current(self, current_section: Dict[str, Any], new_section: Dict[str, Any]):
        """
        将新章节合并到当前章节
        
        Args:
            current_section: 当前合并章节（会被修改）
            new_section: 要合并的新章节
        """
        new_content = new_section.get('content', '')
        new_title = new_section.get('section_title', '未命名章节')
        
        # 合并内容，添加章节分隔符
        separator = f"\n\n=== {new_title} ===\n\n"
        current_section['content'] += separator + new_content
        
        # 更新合并信息
        current_section['merged_sections'].append(new_title)
        current_section['original_section_count'] += 1
        current_section['is_merged'] = True
        
        # 注意：按要求不修改章节标题，保持原始标题不变
    
    def _is_likely_split_section(self, current_section: Dict[str, Any], next_section: Dict[str, Any]) -> bool:
        """
        检测两个章节是否可能是被分割的同一章节
        
        Args:
            current_section: 当前章节
            next_section: 下一个章节
            
        Returns:
            是否可能是被分割的章节
        """
        current_title = current_section.get('section_title', '').strip()
        next_title = next_section.get('section_title', '').strip()
        current_content = current_section.get('content', '')
        next_content = next_section.get('content', '')
        
        # 检查1: 标题完全相同
        if current_title == next_title and current_title:
            return True
        
        # 检查2: 标题相似（去除数字和标点后比较）
        if self._normalize_title(current_title) == self._normalize_title(next_title) and current_title:
            return True
        
        # 检查3: 当前章节结尾不完整（没有句号、没有换行等）
        if current_content and not self._is_content_complete(current_content):
            # 且下一章节开头看起来是续写
            if next_content and self._is_content_continuation(next_content):
                return True
        
        # 检查4: 连续章节编号或相似模式
        if self._has_sequential_pattern(current_title, next_title):
            return True
        
        return False
    
    def _normalize_title(self, title: str) -> str:
        """标准化章节标题，移除数字、标点等"""
        if not title:
            return ""
        # 移除数字、标点、空白符，只保留核心文字
        import re
        normalized = re.sub(r'[0-9\.\s\-_\(\)\[\]]+', '', title).lower()
        return normalized
    
    def _is_content_complete(self, content: str) -> bool:
        """
        判断内容是否看起来完整
        
        Args:
            content: 章节内容
            
        Returns:
            内容是否完整
        """
        if not content:
            return False
        
        content = content.strip()
        
        # 检查是否以完整句子结尾
        sentence_endings = ['。', '！', '？', '.', '!', '?', '\n\n']
        if any(content.endswith(ending) for ending in sentence_endings):
            return True
        
        # 检查是否以列表、代码块等结构结尾
        structured_endings = ['```', '```', '- ', '* ', '1. ', '）', ')']
        if any(content.endswith(ending) for ending in structured_endings):
            return True
        
        # 如果内容很短，可能不完整
        if len(content) < 100:
            return False
        
        # 如果内容在句子中间结束，可能不完整
        if content.endswith(',') or content.endswith('，') or content.endswith('和'):
            return False
        
        return True
    
    def _is_content_continuation(self, content: str) -> bool:
        """
        判断内容是否看起来是接续内容
        
        Args:
            content: 章节内容
            
        Returns:
            是否是接续内容
        """
        if not content:
            return False
        
        content = content.strip()
        
        # 检查是否以小写字母或连接词开头（英文）
        continuation_starts = ['and ', 'but ', 'or ', 'so ', 'then ', 'also ']
        if any(content.lower().startswith(start) for start in continuation_starts):
            return True
        
        # 检查是否以中文连接词开头
        chinese_continuations = ['而且', '并且', '同时', '另外', '此外', '然后', '接着', '最后']
        if any(content.startswith(cont) for cont in chinese_continuations):
            return True
        
        # 检查是否不以标题或独立语句开头
        if not content[0].isupper() and not content[0] in '# ·•*-1234567890':
            return True
        
        return False
    
    def _has_sequential_pattern(self, current_title: str, next_title: str) -> bool:
        """
        检查是否有连续模式（如编号等）
        
        Args:
            current_title: 当前标题
            next_title: 下一个标题
            
        Returns:
            是否有连续模式
        """
        if not current_title or not next_title:
            return False
        
        import re
        
        # 提取数字模式
        current_nums = re.findall(r'\d+', current_title)
        next_nums = re.findall(r'\d+', next_title)
        
        if current_nums and next_nums:
            try:
                # 检查是否是连续数字
                current_num = int(current_nums[-1])  # 取最后一个数字
                next_num = int(next_nums[-1])
                if next_num == current_num + 1:
                    return True
            except ValueError:
                pass
        
        return False
