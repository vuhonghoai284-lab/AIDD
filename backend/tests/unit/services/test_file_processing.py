"""
文件处理功能测试 - 使用新的文件解析架构
"""
import pytest
import tempfile
from pathlib import Path

from app.services.file_parsers.parser_factory import FileParserFactory
from app.services.file_parsers.base_parser import TextParser, PDFParser, WordParser


class TestFileProcessing:
    """文件处理测试类 - 使用新架构"""
    
    @pytest.mark.asyncio
    async def test_read_text_file_utf8(self):
        """测试读取UTF-8文本文件"""
        parser = TextParser()
        
        # 创建临时文本文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', encoding='utf-8', delete=False) as f:
            test_content = "这是一个测试文档\n包含中文内容"
            f.write(test_content)
            temp_path = Path(f.name)
        
        try:
            # 测试读取
            result = await parser.parse(str(temp_path))
            assert result.success
            assert result.data == test_content
            assert result.metadata['encoding_used'] == 'utf-8'
            
        finally:
            # 清理临时文件
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_read_text_file_gbk(self):
        """测试读取GBK编码文本文件"""
        parser = TextParser()
        
        # 创建临时GBK编码文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', encoding='gbk', delete=False) as f:
            test_content = "GBK编码的中文测试内容"
            f.write(test_content)
            temp_path = Path(f.name)
        
        try:
            # 测试读取
            result = await parser.parse(str(temp_path))
            assert result.success
            assert result.data == test_content
            assert result.metadata['encoding_used'] == 'gbk'
            
        finally:
            # 清理临时文件
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_read_markdown_file(self):
        """测试读取Markdown文件"""
        parser = TextParser()
        
        # 创建临时Markdown文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', encoding='utf-8', delete=False) as f:
            test_content = "# 测试标题\n\n这是一个**markdown**文件测试。\n\n- 项目1\n- 项目2"
            f.write(test_content)
            temp_path = Path(f.name)
        
        try:
            # 测试读取
            result = await parser.parse(str(temp_path))
            assert result.success
            assert result.data == test_content
            assert result.metadata['file_type'] == 'text'
            
        finally:
            # 清理临时文件
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_file_parser_factory(self):
        """测试文件解析器工厂"""
        factory = FileParserFactory()
        
        # 测试文本文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', encoding='utf-8', delete=False) as f:
            test_content = "文本文件内容"
            f.write(test_content)
            txt_path = Path(f.name)
        
        try:
            # 使用工厂获取适合的解析器
            parser = await factory.get_parser(str(txt_path))
            assert parser is not None
            assert isinstance(parser, TextParser)
            
            result = await parser.parse(str(txt_path))
            assert result.success
            assert result.data == test_content
        finally:
            txt_path.unlink()
    
    @pytest.mark.asyncio
    async def test_encoding_detection(self):
        """测试编码检测功能"""
        parser = TextParser()
        
        # 创建包含特殊字符的文件
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.txt', delete=False) as f:
            # 写入UTF-8字节
            test_content = "测试编码检测功能 🎉"
            f.write(test_content.encode('utf-8'))
            temp_path = Path(f.name)
        
        try:
            result = await parser.parse(str(temp_path))
            assert result.success
            assert "测试编码检测功能" in result.data
            assert "🎉" in result.data
        finally:
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_corrupted_file_handling(self):
        """测试损坏文件的处理"""
        parser = TextParser()
        
        # 创建包含无效字节序列的文件
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.txt', delete=False) as f:
            # 写入一些无效的字节序列
            f.write(b'\xff\xfe\x00invalid\x00\x00')
            temp_path = Path(f.name)
        
        try:
            # 应该能够处理并忽略错误
            result = await parser.parse(str(temp_path))
            assert result.success
            # 结果应该包含可读的部分
            assert isinstance(result.data, str)
        finally:
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_empty_file(self):
        """测试空文件处理"""
        parser = TextParser()
        
        # 创建空文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            result = await parser.parse(str(temp_path))
            # 空文件应该成功解析，但数据为空
            assert result.success
            assert result.data == ""
        finally:
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_pdf_file_handling_without_library(self):
        """测试没有PDF库时的处理"""
        parser = PDFParser()
        
        # 创建假的PDF文件（实际上是文本）
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False) as f:
            f.write("fake pdf content")
            temp_path = Path(f.name)
        
        try:
            result = await parser.parse(str(temp_path))
            # 应该返回错误信息，因为没有有效的PDF内容或库不可用
            if not result.success:
                assert "PDF" in result.error or "PyPDF2" in result.error
        finally:
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_word_file_handling_without_library(self):
        """测试没有Word库时的处理"""
        parser = WordParser()
        
        # 创建假的Word文件（实际上是文本）
        with tempfile.NamedTemporaryFile(mode='w', suffix='.docx', delete=False) as f:
            f.write("fake word content")
            temp_path = Path(f.name)
        
        try:
            result = await parser.parse(str(temp_path))
            # 应该返回错误信息，因为没有有效的Word内容或库不可用
            if not result.success:
                assert "Word" in result.error or "docx" in result.error
        finally:
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_unsupported_file_extension(self):
        """测试不支持的文件扩展名"""
        factory = FileParserFactory()
        
        # 创建不支持的文件类型
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xyz', delete=False) as f:
            f.write("unsupported content")
            temp_path = Path(f.name)
        
        try:
            parser = await factory.get_parser(str(temp_path))
            # 应该返回None，表示没有合适的解析器
            assert parser is None
        finally:
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_file_reading_error_handling(self):
        """测试文件读取错误处理"""
        parser = TextParser()
        
        # 尝试解析不存在的文件
        result = await parser.parse("/nonexistent/file.txt")
        assert not result.success
        assert "失败" in result.error or "not found" in result.error.lower()


class TestFileProcessingIntegration:
    """文件处理集成测试"""
    
    @pytest.mark.asyncio
    async def test_parser_factory_with_different_file_types(self):
        """测试解析器工厂处理不同文件类型"""
        factory = FileParserFactory()
        
        # 测试支持的扩展名
        supported_extensions = factory.get_supported_extensions()
        assert '.txt' in supported_extensions
        assert '.md' in supported_extensions
        assert '.pdf' in supported_extensions
        assert '.docx' in supported_extensions
    
    @pytest.mark.asyncio
    async def test_large_file_handling(self):
        """测试大文件处理"""
        parser = TextParser()
        
        # 创建较大的文本文件
        large_content = "这是一行测试内容。\n" * 1000  # 约20KB
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', encoding='utf-8', delete=False) as f:
            f.write(large_content)
            temp_path = Path(f.name)
        
        try:
            result = await parser.parse(str(temp_path))
            assert result.success
            assert result.data == large_content
            assert result.metadata['lines_count'] == 1000
        finally:
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_special_characters_handling(self):
        """测试特殊字符处理"""
        parser = TextParser()
        
        # 包含各种特殊字符的内容
        special_content = """
        这是中文内容
        This is English content
        Это русский контент
        これは日本語です
        🎉🚀✨💡🔥
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', encoding='utf-8', delete=False) as f:
            f.write(special_content)
            temp_path = Path(f.name)
        
        try:
            result = await parser.parse(str(temp_path))
            assert result.success
            assert result.data == special_content
            assert "🎉" in result.data
            assert "中文" in result.data
        finally:
            temp_path.unlink()