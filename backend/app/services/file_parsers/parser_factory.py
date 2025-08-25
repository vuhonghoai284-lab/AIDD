"""
文件解析器工厂
"""
from pathlib import Path
from typing import List, Optional
from app.services.interfaces.task_processor import IFileParser
from .base_parser import PDFParser, WordParser, TextParser


class FileParserFactory:
    """文件解析器工厂"""
    
    def __init__(self):
        self._parsers: List[IFileParser] = [
            PDFParser(),
            WordParser(),
            TextParser()
        ]
    
    async def get_parser(self, file_path: str) -> Optional[IFileParser]:
        """根据文件路径获取合适的解析器"""
        file_extension = Path(file_path).suffix.lower()
        
        for parser in self._parsers:
            if await parser.can_parse(file_path, file_extension):
                return parser
        
        return None
    
    def register_parser(self, parser: IFileParser):
        """注册新的文件解析器"""
        self._parsers.append(parser)
    
    def get_supported_extensions(self) -> List[str]:
        """获取所有支持的文件扩展名"""
        extensions = []
        for parser in self._parsers:
            if hasattr(parser, 'supported_extensions'):
                extensions.extend(parser.supported_extensions)
        return list(set(extensions))