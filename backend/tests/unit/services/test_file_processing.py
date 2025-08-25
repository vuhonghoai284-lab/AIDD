"""
文件处理功能测试
"""
import pytest
import asyncio
import tempfile
from pathlib import Path
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from app.services.task_processor import TaskProcessor
from tests.conftest import test_db_session


class TestFileProcessing:
    """文件处理测试类"""
    
    @pytest.mark.asyncio
    async def test_read_text_file_utf8(self, test_db_session):
        """测试读取UTF-8文本文件"""
        processor = TaskProcessor(test_db_session)
        
        # 创建临时文本文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', encoding='utf-8', delete=False) as f:
            test_content = "这是一个测试文档\n包含中文内容"
            f.write(test_content)
            temp_path = Path(f.name)
        
        try:
            # 测试读取
            result = await processor._read_text_file(temp_path)
            assert result == test_content
            
        finally:
            # 清理临时文件
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_read_text_file_gbk(self, test_db_session):
        """测试读取GBK编码文本文件"""
        processor = TaskProcessor(test_db_session)
        
        # 创建临时GBK编码文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', encoding='gbk', delete=False) as f:
            test_content = "GBK编码的中文测试内容"
            f.write(test_content)
            temp_path = Path(f.name)
        
        try:
            # 测试读取
            result = await processor._read_text_file(temp_path)
            assert result == test_content
            
        finally:
            # 清理临时文件
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_read_markdown_file(self, test_db_session):
        """测试读取Markdown文件"""
        processor = TaskProcessor(test_db_session)
        
        # 创建临时Markdown文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', encoding='utf-8', delete=False) as f:
            test_content = "# 测试标题\n\n这是一个**markdown**文件测试。\n\n- 项目1\n- 项目2"
            f.write(test_content)
            temp_path = Path(f.name)
        
        try:
            # 测试读取
            result = await processor._read_file_content(temp_path, "test.md")
            assert result == test_content
            
        finally:
            # 清理临时文件
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_read_file_content_by_extension(self, test_db_session):
        """测试根据文件扩展名选择处理方式"""
        processor = TaskProcessor(test_db_session)
        
        # 测试文本文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', encoding='utf-8', delete=False) as f:
            test_content = "文本文件内容"
            f.write(test_content)
            txt_path = Path(f.name)
        
        try:
            result = await processor._read_file_content(txt_path, "test.txt")
            assert result == test_content
        finally:
            txt_path.unlink()
    
    @pytest.mark.asyncio
    async def test_read_binary_file_with_encoding_detection(self, test_db_session):
        """测试二进制文件的编码检测"""
        processor = TaskProcessor(test_db_session)
        
        # 创建包含特殊字符的文件
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.txt', delete=False) as f:
            # 写入UTF-8字节
            test_content = "测试编码检测功能 🎉"
            f.write(test_content.encode('utf-8'))
            temp_path = Path(f.name)
        
        try:
            result = await processor._read_text_file(temp_path)
            assert "测试编码检测功能" in result
        finally:
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_read_corrupted_file_handling(self, test_db_session):
        """测试读取损坏文件的处理"""
        processor = TaskProcessor(test_db_session)
        
        # 创建包含无效UTF-8序列的文件
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.txt', delete=False) as f:
            # 写入无效UTF-8字节序列
            f.write(b'\xff\xfe\x00\x01\x02\x03')
            temp_path = Path(f.name)
        
        try:
            # 应该能处理这种情况而不抛出异常
            result = await processor._read_text_file(temp_path)
            # 结果应该是一个字符串（可能包含替换字符）
            assert isinstance(result, str)
        finally:
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_read_empty_file(self, test_db_session):
        """测试读取空文件"""
        processor = TaskProcessor(test_db_session)
        
        # 创建空文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            pass  # 创建空文件
            temp_path = Path(f.name)
        
        try:
            result = await processor._read_text_file(temp_path)
            assert result == ""
        finally:
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_pdf_file_handling_without_library(self, test_db_session):
        """测试PDF文件处理（测试错误处理）"""
        processor = TaskProcessor(test_db_session)
        
        # 创建一个假的PDF文件（无效的PDF内容，用于测试错误处理）
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            # 写入无效的PDF内容来触发错误处理
            f.write(b'%PDF-1.4\ninvalid PDF content')
            temp_path = Path(f.name)
        
        try:
            # 应该抛出ValueError异常
            with pytest.raises(ValueError) as exc_info:
                await processor._read_pdf_file(temp_path)
            
            # 验证异常消息包含相关信息
            error_message = str(exc_info.value)
            assert "PDF" in error_message or "解析失败" in error_message
        finally:
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_word_file_handling_without_library(self, test_db_session):
        """测试Word文件处理（测试错误处理）"""
        processor = TaskProcessor(test_db_session)
        
        # 创建一个假的Word文件（无效的DOCX内容，用于测试错误处理）
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            f.write(b'PK\x03\x04invalid DOCX content')  # 无效的ZIP内容
            temp_path = Path(f.name)
        
        try:
            # 应该抛出ValueError异常
            with pytest.raises(ValueError) as exc_info:
                await processor._read_word_file(temp_path)
            
            # 验证异常消息包含相关信息
            error_message = str(exc_info.value)
            assert "Word" in error_message or "解析失败" in error_message
        finally:
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_unsupported_file_extension(self, test_db_session):
        """测试不支持的文件扩展名"""
        processor = TaskProcessor(test_db_session)
        
        # 创建一个不常见扩展名的文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xyz', encoding='utf-8', delete=False) as f:
            test_content = "未知扩展名文件内容"
            f.write(test_content)
            temp_path = Path(f.name)
        
        try:
            # 应该回退到文本文件处理
            result = await processor._read_file_content(temp_path, "test.xyz")
            assert result == test_content
        finally:
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_file_reading_error_handling(self, test_db_session):
        """测试文件读取错误处理"""
        processor = TaskProcessor(test_db_session)
        
        # 测试不存在的文件
        non_existent_path = Path("/tmp/non_existent_file.txt")
        
        with pytest.raises(ValueError) as exc_info:
            await processor._read_file_content(non_existent_path, "non_existent.txt")
        
        assert "文件读取失败" in str(exc_info.value)
        assert "non_existent.txt" in str(exc_info.value)


class TestFileProcessingIntegration:
    """文件处理集成测试"""
    
    @pytest.mark.asyncio
    async def test_task_processor_with_different_file_types(self, test_db_session):
        """测试任务处理器处理不同类型文件"""
        processor = TaskProcessor(test_db_session)
        
        test_cases = [
            ('.txt', 'utf-8', "这是TXT文件测试内容"),
            ('.md', 'utf-8', "# Markdown测试\n\n这是**markdown**内容"),
        ]
        
        for ext, encoding, content in test_cases:
            with tempfile.NamedTemporaryFile(mode='w', suffix=ext, encoding=encoding, delete=False) as f:
                f.write(content)
                temp_path = Path(f.name)
            
            try:
                result = await processor._read_file_content(temp_path, f"test{ext}")
                assert result == content
                
                # 测试通过文件名识别
                assert len(result) > 0
                assert isinstance(result, str)
                
            finally:
                temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_large_file_handling(self, test_db_session):
        """测试大文件处理"""
        processor = TaskProcessor(test_db_session)
        
        # 创建一个相对较大的文件（1MB左右）
        large_content = "测试内容 " * 50000  # 约500KB
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', encoding='utf-8', delete=False) as f:
            f.write(large_content)
            temp_path = Path(f.name)
        
        try:
            result = await processor._read_file_content(temp_path, "large_test.txt")
            assert len(result) == len(large_content)
            assert result == large_content
        finally:
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_special_characters_handling(self, test_db_session):
        """测试特殊字符处理"""
        processor = TaskProcessor(test_db_session)
        
        # 包含各种特殊字符的内容
        special_content = "测试特殊字符: 🎉 ✅ ❌ 📝 🔍 \n包含emoji和符号\n\t缩进和换行\n\"引号\"和'单引号'"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', encoding='utf-8', delete=False) as f:
            f.write(special_content)
            temp_path = Path(f.name)
        
        try:
            result = await processor._read_file_content(temp_path, "special_chars.txt")
            assert result == special_content
            # 验证emoji和特殊字符保持完整
            assert "🎉" in result
            assert "✅" in result
        finally:
            temp_path.unlink()