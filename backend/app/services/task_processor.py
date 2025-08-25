"""
任务处理器 - 支持测试模式
"""
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.repositories.task import TaskRepository
from app.repositories.issue import IssueRepository
from app.repositories.ai_output import AIOutputRepository
from app.repositories.file_info import FileInfoRepository
from app.repositories.ai_model import AIModelRepository
from app.services.ai_service_factory import AIServiceFactory
from app.core.config import get_settings
from app.services.websocket import manager
from app.models import TaskLog


class TaskProcessor:
    """任务处理器"""
    
    def __init__(self, db: Session):
        self.db = db
        self.task_repo = TaskRepository(db)
        self.issue_repo = IssueRepository(db)
        self.ai_output_repo = AIOutputRepository(db)
        self.file_repo = FileInfoRepository(db)
        self.model_repo = AIModelRepository(db)
        self.settings = get_settings()
        self.ai_service_factory = AIServiceFactory()
    
    async def process_task(self, task_id: int):
        """处理任务"""
        try:
            # 记录开始日志
            await self._log(task_id, "INFO", "开始处理任务", "初始化", 0)
            
            # 获取任务信息
            task = self.task_repo.get(task_id)
            if not task:
                raise ValueError(f"任务不存在: {task_id}")
            
            # 更新状态为处理中
            self.task_repo.update(task_id, status="processing", progress=10)
            await manager.send_status(task_id, "processing")
            # 获取文件信息
            file_info = None
            if task.file_id:
                file_info = self.file_repo.get_by_id(task.file_id)
            
            file_name = file_info.original_name if file_info else "未知文件"
            await self._log(task_id, "INFO", f"正在处理文档: {file_name}", "文档解析", 10)
            
            # 获取AI模型信息
            ai_model = None
            if task.model_id:
                ai_model = self.model_repo.get_by_id(task.model_id)
            
            if not ai_model:
                ai_model = self.model_repo.get_default_model()
                
            if not ai_model:
                raise ValueError("没有可用的AI模型")
            
            # 获取AI服务（暂时使用默认模型索引，这里需要改进）
            # TODO: 需要改进AI服务工厂以支持通过模型键获取服务
            ai_services = self.ai_service_factory.get_service_for_model(self.settings.default_model_index, self.settings)
            
            # 根据测试模式选择合适的服务
            if self.settings.is_test_mode and 'mock_service' in ai_services and ai_services['mock_service']:
                document_processor = ai_services['mock_service']
                issue_detector = ai_services['mock_service']
            else:
                # 获取真实的AI服务组件
                document_processor = ai_services.get('document_processor')
                issue_detector = ai_services.get('issue_detector')
                
                # 如果真实服务不可用，降级到mock服务
                if not document_processor or not issue_detector:
                    if ai_services.get('mock_service'):
                        document_processor = ai_services['mock_service']
                        issue_detector = ai_services['mock_service']
                    else:
                        raise ValueError("无法获取AI服务")
            
            if not document_processor or not issue_detector:
                raise ValueError("无法获取AI服务")
            
            # 如果是Mock服务，设置WebSocket上下文
            if hasattr(document_processor, 'set_context'):
                await document_processor.set_context(task_id, manager)
            if hasattr(issue_detector, 'set_context'):
                await issue_detector.set_context(task_id, manager)
            
            # 读取文件内容
            file_path = None
            if file_info and file_info.file_path:
                file_path = Path(file_info.file_path)
            
            if file_path and file_path.exists():
                # 根据文件类型读取文件内容
                file_content = await self._read_file_content(file_path, file_name)
            elif self.settings.is_test_mode:
                # 测试模式下，如果文件不存在，使用模拟内容
                file_content = self._generate_test_content(file_name)
            else:
                # 生产模式下，文件必须存在
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            # 记录文档字符数
            self.task_repo.update(task_id, document_chars=len(file_content))
            await self._log(task_id, "INFO", f"文档读取完成，共{len(file_content)}字符", "文档解析", 20)
            
            # 第一步：文档预处理
            self.task_repo.update(task_id, progress=30)
            await manager.send_progress(task_id, 30, "文档预处理")
            await self._log(task_id, "INFO", "开始文档预处理", "文档预处理", 30)
            preprocess_result = await document_processor.analyze_document(
                file_content, 
                prompt_type="preprocess"
            )
            
            # 保存预处理结果
            self._save_ai_output(
                task_id=task_id,
                operation_type="preprocess",
                input_text=file_content[:1000],  # 只保存前1000字符
                result=preprocess_result
            )
            
            # 第二步：问题检测
            self.task_repo.update(task_id, progress=60)
            await manager.send_progress(task_id, 60, "问题检测")
            await self._log(task_id, "INFO", "开始检测文档问题", "问题检测", 60)
            issues_result = await issue_detector.analyze_document(
                file_content,
                prompt_type="detect_issues"
            )
            
            # 保存问题检测结果
            self._save_ai_output(
                task_id=task_id,
                operation_type="detect_issues",
                input_text=file_content[:1000],
                result=issues_result
            )
            
            # 第三步：保存检测到的问题
            self.task_repo.update(task_id, progress=80)
            await manager.send_progress(task_id, 80, "保存结果")
            await self._log(task_id, "INFO", "正在保存检测结果", "保存结果", 80)
            
            if issues_result['status'] == 'success':
                issues_data = issues_result['data']
                if 'issues' in issues_data:
                    issue_count = len(issues_data['issues'])
                    await self._log(task_id, "INFO", f"检测到{issue_count}个问题", "保存结果", 85)
                    for issue in issues_data['issues']:
                        self.issue_repo.create(
                            task_id=task_id,
                            issue_type=issue.get('issue_type', '未知'),
                            description=issue.get('description', ''),
                            location=issue.get('location', ''),
                            severity=issue.get('severity', '一般'),
                            confidence=issue.get('confidence'),
                            suggestion=issue.get('suggestion', ''),
                            original_text=issue.get('original_text'),
                            user_impact=issue.get('user_impact'),
                            reasoning=issue.get('reasoning'),
                            context=issue.get('context')
                        )
            
            # 完成任务
            # 重新获取任务以避免会话问题
            task = self.task_repo.get(task_id)
            processing_time = time.time() - task.created_at.timestamp()
            self.task_repo.update(
                task_id, 
                status="completed",
                progress=100,
                processing_time=processing_time,
                completed_at=datetime.now()
            )
            await manager.send_progress(task_id, 100, "完成")
            await manager.send_status(task_id, "completed")
            await self._log(task_id, "INFO", f"任务处理完成，耗时{processing_time:.2f}秒", "完成", 100)
            
        except Exception as e:
            # 记录错误
            await self._log(task_id, "ERROR", f"任务处理失败: {str(e)}", "错误", 0)
            await manager.send_status(task_id, "failed")
            self.task_repo.update(
                task_id, 
                status="failed", 
                error_message=str(e)
            )
            raise
    
    def _save_ai_output(self, task_id: int, operation_type: str, 
                       input_text: str, result: Dict[str, Any]):
        """保存AI输出结果"""
        self.ai_output_repo.create(
            task_id=task_id,
            operation_type=operation_type,
            input_text=input_text,
            raw_output=result.get('raw_output', json.dumps(result)),
            parsed_output=result.get('data'),
            status=result.get('status', 'success'),
            error_message=result.get('error_message'),
            tokens_used=result.get('tokens_used'),
            processing_time=result.get('processing_time')
        )
    
    def _generate_test_content(self, filename: str) -> str:
        """生成测试文档内容"""
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
    
    async def _log(self, task_id: int, level: str, message: str, stage: str = None, progress: int = None):
        """记录日志并实时推送"""
        # 保存到数据库
        log = TaskLog(
            task_id=task_id,
            level=level,
            message=message,
            stage=stage,
            progress=progress
        )
        self.db.add(log)
        self.db.commit()
        
        # 实时推送
        await manager.send_log(task_id, level, message, stage, progress)
    
    async def _read_file_content(self, file_path: Path, file_name: str) -> str:
        """根据文件类型读取文件内容"""
        file_extension = file_path.suffix.lower()
        
        try:
            if file_extension == '.pdf':
                # PDF文件处理
                return await self._read_pdf_file(file_path)
            elif file_extension in ['.docx', '.doc']:
                # Word文档处理
                return await self._read_word_file(file_path)
            elif file_extension in ['.md', '.txt']:
                # 文本文件处理
                return await self._read_text_file(file_path)
            else:
                # 默认尝试文本文件处理
                return await self._read_text_file(file_path)
        except Exception as e:
            raise ValueError(f"文件读取失败 [{file_name}]: {str(e)}")
    
    async def _read_pdf_file(self, file_path: Path) -> str:
        """读取PDF文件内容"""
        try:
            import PyPDF2
            text_content = ""
            
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                num_pages = len(pdf_reader.pages)
                
                for page_num in range(num_pages):
                    page = pdf_reader.pages[page_num]
                    text_content += page.extract_text() + "\n"
            
            if not text_content.strip():
                return "PDF文件无法提取文本内容，可能是扫描版PDF或包含复杂格式。"
            
            return text_content.strip()
            
        except ImportError:
            # 如果没有PyPDF2库，返回提示信息
            return f"PDF文件解析需要安装PyPDF2库。文件路径: {file_path}"
        except Exception as e:
            raise ValueError(f"PDF文件解析失败: {str(e)}")
    
    async def _read_word_file(self, file_path: Path) -> str:
        """读取Word文档内容"""
        try:
            import docx
            doc = docx.Document(file_path)
            text_content = ""
            
            for paragraph in doc.paragraphs:
                text_content += paragraph.text + "\n"
            
            if not text_content.strip():
                return "Word文档无法提取文本内容。"
            
            return text_content.strip()
            
        except ImportError:
            # 如果没有python-docx库，返回提示信息
            return f"Word文档解析需要安装python-docx库。文件路径: {file_path}"
        except Exception as e:
            raise ValueError(f"Word文档解析失败: {str(e)}")
    
    async def _read_text_file(self, file_path: Path) -> str:
        """读取文本文件内容"""
        # 尝试多种编码
        encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16', 'latin-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    if content.strip():  # 确保内容不为空
                        return content
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception as e:
                raise ValueError(f"文本文件读取失败: {str(e)}")
        
        # 所有编码都失败，尝试二进制读取并转换
        try:
            with open(file_path, 'rb') as f:
                raw_content = f.read()
                # 尝试检测编码
                import chardet
                detected = chardet.detect(raw_content)
                if detected['encoding']:
                    return raw_content.decode(detected['encoding'], errors='ignore')
                else:
                    return raw_content.decode('utf-8', errors='ignore')
        except ImportError:
            # 如果没有chardet库，用ignore错误的方式读取
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            raise ValueError(f"文件读取完全失败: {str(e)}")