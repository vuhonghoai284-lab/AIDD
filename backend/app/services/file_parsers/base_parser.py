"""
基础文件解析器
"""
import asyncio
from pathlib import Path
from typing import List, Optional, Callable
from app.services.interfaces.task_processor import IFileParser, ProcessingResult


class BaseFileParser(IFileParser):
    """基础文件解析器"""
    
    def __init__(self, supported_extensions: List[str]):
        self.supported_extensions = [ext.lower() for ext in supported_extensions]
    
    async def can_parse(self, file_path: str, file_type: str) -> bool:
        """检查是否支持指定文件类型"""
        return file_type.lower() in self.supported_extensions


class PDFParser(BaseFileParser):
    """PDF文件解析器"""
    
    def __init__(self):
        super().__init__(['.pdf'])
    
    async def parse(self, file_path: str, progress_callback: Optional[Callable] = None) -> ProcessingResult:
        """解析PDF文件"""
        try:
            if progress_callback:
                await progress_callback("开始解析PDF文件...", 10)
            
            try:
                import PyPDF2
            except ImportError:
                return ProcessingResult(
                    success=False,
                    error="PDF文件解析需要安装PyPDF2库"
                )
            
            text_content = ""
            file_stats = Path(file_path).stat()
            
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                num_pages = len(pdf_reader.pages)
                
                for page_num in range(num_pages):
                    if progress_callback:
                        progress = 10 + int(80 * (page_num + 1) / num_pages)
                        await progress_callback(f"正在解析第{page_num + 1}/{num_pages}页...", progress)
                    
                    page = pdf_reader.pages[page_num]
                    text_content += page.extract_text() + "\n"
                    
                    # 模拟处理延迟
                    await asyncio.sleep(0.1)
            
            if not text_content.strip():
                return ProcessingResult(
                    success=False,
                    error="PDF文件无法提取文本内容，可能是扫描版PDF或包含复杂格式"
                )
            
            if progress_callback:
                await progress_callback("PDF文件解析完成", 100)
            
            return ProcessingResult(
                success=True,
                data=text_content.strip(),
                metadata={
                    "file_type": "pdf",
                    "pages_count": num_pages,
                    "content_length": len(text_content),
                    "file_size": file_stats.st_size
                }
            )
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                error=f"PDF文件解析失败: {str(e)}"
            )


class WordParser(BaseFileParser):
    """Word文档解析器"""
    
    def __init__(self):
        super().__init__(['.docx', '.doc'])
    
    async def parse(self, file_path: str, progress_callback: Optional[Callable] = None) -> ProcessingResult:
        """解析Word文档"""
        try:
            if progress_callback:
                await progress_callback("开始解析Word文档...", 10)
            
            try:
                import docx
            except ImportError:
                return ProcessingResult(
                    success=False,
                    error="Word文档解析需要安装python-docx库"
                )
            
            doc = docx.Document(file_path)
            text_content = ""
            
            paragraphs = doc.paragraphs
            total_paragraphs = len(paragraphs)
            
            for i, paragraph in enumerate(paragraphs):
                if progress_callback and i % 10 == 0:  # 每10段更新一次进度
                    progress = 10 + int(80 * (i + 1) / total_paragraphs)
                    await progress_callback(f"正在解析段落 {i + 1}/{total_paragraphs}...", progress)
                
                text_content += paragraph.text + "\n"
                
                # 适当延迟避免阻塞
                if i % 50 == 0:
                    await asyncio.sleep(0.01)
            
            if not text_content.strip():
                return ProcessingResult(
                    success=False,
                    error="Word文档无法提取文本内容"
                )
            
            if progress_callback:
                await progress_callback("Word文档解析完成", 100)
            
            file_stats = Path(file_path).stat()
            return ProcessingResult(
                success=True,
                data=text_content.strip(),
                metadata={
                    "file_type": "word",
                    "paragraphs_count": total_paragraphs,
                    "content_length": len(text_content),
                    "file_size": file_stats.st_size
                }
            )
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                error=f"Word文档解析失败: {str(e)}"
            )


class TextParser(BaseFileParser):
    """文本文件解析器"""
    
    def __init__(self):
        super().__init__(['.txt', '.md', '.markdown'])
    
    async def parse(self, file_path: str, progress_callback: Optional[Callable] = None) -> ProcessingResult:
        """解析文本文件"""
        encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16', 'latin-1']
        
        if progress_callback:
            await progress_callback("开始解析文本文件...", 10)
        
        for i, encoding in enumerate(encodings):
            try:
                if progress_callback:
                    progress = 10 + int(70 * (i + 1) / len(encodings))
                    await progress_callback(f"尝试编码: {encoding}...", progress)
                
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    
                    if content.strip():  # 确保内容不为空
                        if progress_callback:
                            await progress_callback("文本文件解析完成", 100)
                        
                        file_stats = Path(file_path).stat()
                        return ProcessingResult(
                            success=True,
                            data=content,
                            metadata={
                                "file_type": "text",
                                "encoding_used": encoding,
                                "content_length": len(content),
                                "file_size": file_stats.st_size,
                                "lines_count": len(content.split('\n'))
                            }
                        )
                        
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception as e:
                return ProcessingResult(
                    success=False,
                    error=f"文本文件读取失败: {str(e)}"
                )
        
        # 所有编码都失败，尝试自动检测
        try:
            try:
                import chardet
                with open(file_path, 'rb') as f:
                    raw_content = f.read()
                    detected = chardet.detect(raw_content)
                    if detected['encoding']:
                        content = raw_content.decode(detected['encoding'], errors='ignore')
                    else:
                        content = raw_content.decode('utf-8', errors='ignore')
            except ImportError:
                # 如果没有chardet库，用ignore错误的方式读取
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            
            if progress_callback:
                await progress_callback("文本文件解析完成（自动检测编码）", 100)
            
            file_stats = Path(file_path).stat()
            encoding_info = detected.get('encoding', 'utf-8') if 'detected' in locals() else 'utf-8'
            confidence = detected.get('confidence', 0.0) if 'detected' in locals() else 0.0
            
            return ProcessingResult(
                success=True,
                data=content,
                metadata={
                    "file_type": "text",
                    "encoding_used": encoding_info,
                    "encoding_confidence": confidence,
                    "content_length": len(content),
                    "file_size": file_stats.st_size,
                    "lines_count": len(content.split('\n')),
                    "note": "使用自动检测编码" if 'detected' in locals() else "使用UTF-8编码，忽略错误字符"
                }
            )
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                error=f"文件读取完全失败: {str(e)}"
            )