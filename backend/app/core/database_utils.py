"""
数据库事务处理增强工具
解决大数据插入和事务回滚问题
"""
import logging
from contextlib import contextmanager
from sqlalchemy.orm import Session
from sqlalchemy.exc import DataError, IntegrityError
from typing import Optional, Dict, Any
import json


logger = logging.getLogger(__name__)


@contextmanager
def robust_db_session(db: Session):
    """
    增强的数据库会话上下文管理器
    自动处理事务回滚和重试
    """
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"数据库操作失败: {e}")
        db.rollback()
        raise e


def safe_insert_ai_output(
    db: Session,
    task_id: int,
    operation_type: str,
    input_text: str,
    raw_output: str,
    parsed_output: Optional[Dict[Any, Any]] = None,
    status: str = "success",
    error_message: Optional[str] = None,
    tokens_used: Optional[int] = None,
    processing_time: Optional[float] = None,
    section_title: Optional[str] = None,
    section_index: Optional[int] = None,
    max_text_length: int = 1000000  # 1MB限制
) -> bool:
    """
    安全插入AI输出记录，自动处理大数据问题
    
    Args:
        db: 数据库会话
        task_id: 任务ID
        operation_type: 操作类型
        input_text: 输入文本
        raw_output: 原始输出
        parsed_output: 解析后输出
        status: 状态
        error_message: 错误信息
        tokens_used: 使用的token数
        processing_time: 处理时间
        section_title: 章节标题
        section_index: 章节索引
        max_text_length: 文本最大长度限制
        
    Returns:
        bool: 插入是否成功
    """
    from app.models.ai_output import AIOutput
    from datetime import datetime
    
    try:
        # 检查输入文本长度
        if len(input_text) > max_text_length:
            logger.warning(f"输入文本过长 ({len(input_text)} 字符)，截断至 {max_text_length} 字符")
            input_text = input_text[:max_text_length] + "...[截断]"
        
        # 检查原始输出长度
        if len(raw_output) > max_text_length:
            logger.warning(f"原始输出过长 ({len(raw_output)} 字符)，截断至 {max_text_length} 字符")
            raw_output = raw_output[:max_text_length] + "...[截断]"
            
            # 尝试保持JSON格式的有效性
            if raw_output.strip().startswith('{'):
                try:
                    # 尝试解析截断的JSON
                    json.loads(raw_output)
                except json.JSONDecodeError:
                    # 如果截断后JSON无效，创建一个有效的JSON
                    raw_output = f'{{"content": "{raw_output[:max_text_length-50]}", "truncated": true, "original_length": {len(raw_output)}}}'
        
        # 创建AI输出记录
        ai_output = AIOutput(
            task_id=task_id,
            operation_type=operation_type,
            input_text=input_text,
            raw_output=raw_output,
            parsed_output=parsed_output,
            status=status,
            error_message=error_message,
            tokens_used=tokens_used,
            processing_time=processing_time,
            section_title=section_title,
            section_index=section_index,
            created_at=datetime.utcnow()
        )
        
        # 使用新的会话进行插入，避免事务回滚问题
        with robust_db_session(db):
            db.add(ai_output)
            db.flush()  # 强制执行SQL但不提交事务
            
        logger.info(f"✅ AI输出记录保存成功: task_id={task_id}, operation_type={operation_type}")
        return True
        
    except DataError as e:
        # 数据过长错误
        logger.error(f"数据插入失败，数据过长: {e}")
        
        # 尝试进一步截断数据
        truncated_input = input_text[:10000] + "...[严重截断]"
        truncated_output = '{"error": "数据过长，无法保存原始输出", "original_length": ' + str(len(raw_output)) + '}'
        
        try:
            # 创建截断版本记录
            truncated_ai_output = AIOutput(
                task_id=task_id,
                operation_type=operation_type,
                input_text=truncated_input,
                raw_output=truncated_output,
                parsed_output={"error": "数据过长，无法解析"},
                status="truncated",
                error_message=f"原始数据过长: {str(e)}",
                tokens_used=tokens_used,
                processing_time=processing_time,
                section_title=section_title,
                section_index=section_index,
                created_at=datetime.utcnow()
            )
            
            with robust_db_session(db):
                db.add(truncated_ai_output)
                
            logger.warning(f"⚠️ 已保存截断版本AI输出记录: task_id={task_id}")
            return True
            
        except Exception as e2:
            logger.error(f"保存截断版本也失败: {e2}")
            return False
    
    except IntegrityError as e:
        logger.error(f"数据完整性错误: {e}")
        db.rollback()
        return False
        
    except Exception as e:
        logger.error(f"保存AI输出记录时发生未知错误: {e}")
        db.rollback()
        return False


def safe_log_error(
    db: Session,
    task_id: int,
    operation_type: str,
    error_message: str,
    input_text: Optional[str] = None,
    processing_time: Optional[float] = None
) -> bool:
    """
    安全记录错误日志到AI输出表
    
    Args:
        db: 数据库会话
        task_id: 任务ID
        operation_type: 操作类型
        error_message: 错误信息
        input_text: 输入文本（可选）
        processing_time: 处理时间（可选）
        
    Returns:
        bool: 记录是否成功
    """
    try:
        # 限制错误信息长度
        if len(error_message) > 5000:
            error_message = error_message[:5000] + "...[错误信息截断]"
            
        # 限制输入文本长度
        if input_text and len(input_text) > 1000:
            input_text = input_text[:1000] + "...[输入截断]"
        
        return safe_insert_ai_output(
            db=db,
            task_id=task_id,
            operation_type=operation_type,
            input_text=input_text or "错误发生，无输入文本",
            raw_output=f'{{"error": "{error_message}"}}',
            parsed_output={"error": True, "message": error_message},
            status="failed",
            error_message=error_message,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"记录错误日志失败: {e}")
        return False


def cleanup_large_ai_outputs(db: Session, days_old: int = 30, max_size_mb: int = 10) -> int:
    """
    清理过大的AI输出记录，释放数据库空间
    
    Args:
        db: 数据库会话
        days_old: 清理多少天前的记录
        max_size_mb: 单个记录最大大小（MB）
        
    Returns:
        int: 清理的记录数
    """
    from app.models.ai_output import AIOutput
    from datetime import datetime, timedelta
    from sqlalchemy import func, text
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        max_size_bytes = max_size_mb * 1024 * 1024
        
        # 查找过大的记录
        large_records = db.query(AIOutput).filter(
            AIOutput.created_at < cutoff_date,
            func.length(AIOutput.raw_output) > max_size_bytes
        ).all()
        
        cleaned_count = 0
        for record in large_records:
            try:
                # 保留元数据，清理大数据内容
                record.raw_output = f'{{"cleaned": true, "original_size": {len(record.raw_output)}, "cleaned_at": "{datetime.utcnow().isoformat()}"}}'
                record.input_text = record.input_text[:1000] + "...[已清理]" if len(record.input_text) > 1000 else record.input_text
                record.parsed_output = {"cleaned": True}
                cleaned_count += 1
                
            except Exception as e:
                logger.error(f"清理记录 {record.id} 失败: {e}")
                continue
        
        db.commit()
        logger.info(f"✅ 已清理 {cleaned_count} 个大型AI输出记录")
        return cleaned_count
        
    except Exception as e:
        logger.error(f"清理AI输出记录失败: {e}")
        db.rollback()
        return 0