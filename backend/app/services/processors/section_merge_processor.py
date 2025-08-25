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
        判断是否应该合并两个章节
        
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
        current_level = current_section.get('level', 1)
        next_level = next_section.get('level', 1)
        
        # 规则1: 如果下一个章节内容太短，总是合并
        if next_content_length < min_chars:
            self.logger.debug(f"规则1触发: 下一章节太短 ({next_content_length} < {min_chars})")
            return True
        
        # 规则2: 如果合并后超过最大字符数，不合并
        if potential_length > max_chars:
            self.logger.debug(f"规则2触发: 合并后会超过最大限制 ({potential_length} > {max_chars})")
            return False
        
        # 规则3: 如果保持结构且下一个章节是更高层级（如从二级到一级），不合并
        if preserve_structure and next_level < current_level:
            self.logger.debug(f"规则3触发: 层级提升 ({next_level} < {current_level})")
            return False
        
        # 规则4: 如果当前合并章节还很短，可以合并
        current_length = len(current_section['content'])
        if current_length < max_chars * 0.7:  # 低于70%的限制时倾向于合并
            self.logger.debug(f"规则4触发: 当前章节较短，可以合并 ({current_length} < {max_chars * 0.7})")
            return True
        
        # 规则5: 如果保持结构且层级相同或更低，且不超过限制，可以合并
        if preserve_structure and next_level >= current_level:
            self.logger.debug(f"规则5触发: 相同或更低层级，可以合并 ({next_level} >= {current_level})")
            return True
        
        # 默认情况下不合并
        self.logger.debug("默认规则: 不合并")
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
        
        # 更新标题以反映合并状态
        if len(current_section['merged_sections']) == 2:
            # 第一次合并，更新标题格式
            original_title = current_section['merged_sections'][0]
            current_section['section_title'] = f"{original_title} (合并章节)"