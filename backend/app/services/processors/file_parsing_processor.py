"""
文件解析处理器
"""
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from app.services.interfaces.task_processor import ITaskProcessor, TaskProcessingStep, ProcessingResult
from app.services.file_parsers.parser_factory import FileParserFactory


class FileParsingProcessor(ITaskProcessor):
    """文件解析处理器"""
    
    def __init__(self):
        super().__init__(TaskProcessingStep.FILE_PARSING)
        self.parser_factory = FileParserFactory()
    
    async def can_handle(self, context: Dict[str, Any]) -> bool:
        """检查是否包含需要解析的文件"""
        # 测试模式下，只需要有file_name即可
        if context.get('test_mode', False):
            return 'file_name' in context and bool(context['file_name'])
        # 正常模式下需要file_path
        return 'file_path' in context and bool(context['file_path'])
    
    async def process(self, context: Dict[str, Any], progress_callback: Optional[Callable] = None) -> ProcessingResult:
        """执行文件解析"""
        file_path = context.get('file_path')
        file_name = context.get('file_name', Path(file_path).name if file_path else "未知文件")
        
        if progress_callback:
            await progress_callback(f"开始解析文件: {file_name}", 10)
        
        # 检查文件是否存在
        if not file_path or not Path(file_path).exists():
            # 测试模式下生成模拟内容
            if context.get('test_mode', False):
                content = self._generate_test_content(file_name)
                return ProcessingResult(
                    success=True,
                    data=content,
                    metadata={
                        "file_type": "mock",
                        "content_length": len(content),
                        "note": "测试模式生成的模拟内容"
                    }
                )
            else:
                return ProcessingResult(
                    success=False,
                    error=f"文件不存在: {file_path}"
                )
        
        # 获取合适的解析器
        parser = await self.parser_factory.get_parser(file_path)
        if not parser:
            return ProcessingResult(
                success=False,
                error=f"不支持的文件类型: {Path(file_path).suffix}"
            )
        
        # 定义内部进度回调，将内部进度映射到10-20范围
        async def internal_progress_callback(message: str, internal_progress: int):
            # 将内部进度(0-100)映射到外部进度(10-20)
            mapped_progress = 10 + int((internal_progress / 100) * 10)
            if progress_callback:
                await progress_callback(f"文件解析: {message}", mapped_progress)
        
        # 执行文件解析
        result = await parser.parse(file_path, internal_progress_callback)
        
        if progress_callback:
            await progress_callback(f"文件解析完成: {file_name}", 20)
        
        # 如果解析成功，将结果保存到上下文中
        if result.success:
            context['file_parsing_result'] = result.data
            
            # 更新文档字符数（如果有数据库会话）
            if 'task_id' in context:
                # 这里需要通过回调或其他方式更新数据库
                pass
        
        return result
    
    def _generate_test_content(self, filename: str) -> str:
        """生成测试文档内容（从TaskProcessor迁移）"""
        return f"""# {filename} - 测试文档

## 第一章 简介

这是一个用于测试的示例文档。本文档包含了多个章节，用于演示文档分析功能。

### 1.1 背景

在软件开发过程中，文档质量的重要性不言而喻。高质量的文档能够帮助开发者快速理解系统架构和实现细节。

### 1.2 目标

本文档的目标是：
1. 提供清晰的系统说明
2. 演示文档结构
3. 测试AI分析功能

## 第二章 系统架构

系统采用前后端分离的架构设计，主要包括以下几个模块：

### 2.1 前端模块
- React框架
- TypeScript语言
- Ant Design组件库

### 2.2 后端模块
- FastAPI框架
- Python语言
- SQLAlchemy ORM

## 第三章 功能说明

### 3.1 文档上传
用户可以上传PDF、Word、Markdown等格式的文档进行分析。

### 3.2 AI分析
系统使用AI模型对文档进行全面分析，检测潜在的问题。

### 3.3 报告生成
分析完成后，系统会生成详细的测试报告。

## 总结

本文档演示了一个完整的技术文档结构。通过AI分析，可以发现文档中的各种问题并提供改进建议。
"""