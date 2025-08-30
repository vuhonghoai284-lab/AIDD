"""
安全的数据库初始化和管理工具
替代Alembic，提供更简单但安全的数据库schema管理
"""
import logging
from contextlib import contextmanager
from sqlalchemy import inspect, text, MetaData
from sqlalchemy.orm import Session
from sqlalchemy.exc import DataError, IntegrityError, SQLAlchemyError
from typing import Optional, Dict, Any, List
from pathlib import Path
import json

from app.core.database import engine, Base
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理器 - 提供安全的schema操作"""
    
    def __init__(self):
        self.settings = get_settings()
        self.engine = engine
        self.inspector = inspect(engine)
    
    def get_existing_tables(self) -> List[str]:
        """获取现有表列表"""
        return self.inspector.get_table_names()
    
    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        return table_name in self.get_existing_tables()
    
    def get_table_columns(self, table_name: str) -> Dict[str, str]:
        """获取表的列信息"""
        if not self.table_exists(table_name):
            return {}
        
        columns = self.inspector.get_columns(table_name)
        return {col['name']: str(col['type']) for col in columns}
    
    def backup_data_if_needed(self, table_name: str) -> Optional[str]:
        """如果需要，备份表数据（仅SQLite）"""
        if self.settings.database_type != 'sqlite':
            return None
            
        if not self.table_exists(table_name):
            return None
            
        backup_table = f"{table_name}_backup_{int(__import__('time').time())}"
        
        try:
            with self.engine.connect() as conn:
                # 创建备份表
                conn.execute(text(f"CREATE TABLE {backup_table} AS SELECT * FROM {table_name}"))
                conn.commit()
                logger.info(f"✓ 表 {table_name} 数据已备份到 {backup_table}")
                return backup_table
        except Exception as e:
            logger.warning(f"⚠️ 备份表 {table_name} 失败: {e}")
            return None
    
    def create_tables_safely(self):
        """安全地创建表结构"""
        logger.info("开始安全创建数据库表...")
        
        existing_tables = self.get_existing_tables()
        logger.info(f"现有表: {existing_tables}")
        
        # 获取所有模型定义的表
        model_tables = list(Base.metadata.tables.keys())
        logger.info(f"模型定义的表: {model_tables}")
        
        # 新表（不存在的表）
        new_tables = [table for table in model_tables if table not in existing_tables]
        
        if new_tables:
            logger.info(f"将创建新表: {new_tables}")
            
            # 只创建新表，避免影响现有数据
            for table_name in new_tables:
                table_obj = Base.metadata.tables[table_name]
                try:
                    table_obj.create(bind=self.engine, checkfirst=True)
                    logger.info(f"✓ 成功创建表: {table_name}")
                except Exception as e:
                    logger.error(f"✗ 创建表 {table_name} 失败: {e}")
                    raise
        else:
            logger.info("✓ 所有必需的表已存在，无需创建新表")
        
        # 验证关键表是否存在
        critical_tables = ['users', 'tasks', 'file_infos', 'ai_models', 'issues']
        missing_critical = [t for t in critical_tables if not self.table_exists(t)]
        
        if missing_critical:
            logger.error(f"✗ 缺少关键表: {missing_critical}")
            # 尝试创建缺少的关键表
            logger.info("尝试创建缺少的关键表...")
            Base.metadata.create_all(bind=self.engine, checkfirst=True)
            
            # 再次检查
            still_missing = [t for t in critical_tables if not self.table_exists(t)]
            if still_missing:
                raise RuntimeError(f"无法创建关键表: {still_missing}")
            else:
                logger.info("✓ 成功创建所有关键表")
        
        logger.info("✓ 数据库表创建/验证完成")
    
    def verify_database_integrity(self) -> bool:
        """验证数据库完整性"""
        try:
            # 检查关键表
            critical_tables = ['users', 'tasks', 'file_infos', 'ai_models']
            for table in critical_tables:
                if not self.table_exists(table):
                    logger.error(f"✗ 关键表缺失: {table}")
                    return False
            
            # 简单的连接测试
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            logger.info("✓ 数据库完整性验证通过")
            return True
            
        except Exception as e:
            logger.error(f"✗ 数据库完整性验证失败: {e}")
            return False
    
    def get_database_info(self) -> Dict:
        """获取数据库信息"""
        try:
            tables = self.get_existing_tables()
            table_info = {}
            
            for table_name in tables:
                try:
                    with self.engine.connect() as conn:
                        result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                        count = result.scalar()
                        table_info[table_name] = count
                except Exception as e:
                    table_info[table_name] = f"Error: {e}"
            
            return {
                'database_type': self.settings.database_type,
                'database_url': self.settings.database_url,
                'total_tables': len(tables),
                'table_names': tables,
                'table_row_counts': table_info
            }
            
        except Exception as e:
            return {'error': str(e)}


async def safe_create_tables():
    """安全地创建数据库表（异步接口）"""
    db_manager = DatabaseManager()
    
    try:
        # 创建必要的目录
        settings = get_settings()
        if settings.database_type == 'sqlite':
            db_url = settings.database_url.replace('sqlite:///', '')
            db_path = Path(db_url) if not db_url.startswith('./') else Path(db_url)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"确保SQLite数据库目录存在: {db_path.parent}")
        
        # 安全创建表
        db_manager.create_tables_safely()
        
        # 验证数据库完整性
        if not db_manager.verify_database_integrity():
            raise RuntimeError("数据库完整性验证失败")
        
        logger.info("✅ 数据库初始化完成")
        
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        raise


def create_tables_sync():
    """同步方式创建表（用于脚本调用）"""
    db_manager = DatabaseManager()
    db_manager.create_tables_safely()


def get_db_status() -> Dict:
    """获取数据库状态（用于健康检查）"""
    db_manager = DatabaseManager()
    return db_manager.get_database_info()


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
        # 验证task_id是否有效，避免外键约束失败
        from app.models.task import Task
        task_exists = db.query(Task.id).filter(Task.id == task_id).first()
        
        if not task_exists:
            logger.warning(f"⚠️ task_id {task_id} 不存在，跳过AI输出记录保存")
            return False
        
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