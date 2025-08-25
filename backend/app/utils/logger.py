"""
统一的日志配置模块
提供标准化的日志器配置和格式化
"""
import logging
import logging.handlers
from pathlib import Path
from typing import Optional
from app.core.config import get_settings

def setup_logger(name: str, log_file: Optional[str] = None, level: str = None) -> logging.Logger:
    """
    设置标准化的日志器
    
    Args:
        name: 日志器名称
        log_file: 可选的日志文件名
        level: 日志级别
        
    Returns:
        配置好的日志器
    """
    # 获取配置
    settings = get_settings()
    logging_config = settings.config.get('logging', {})
    
    # 使用传入的级别或配置中的级别
    log_level = level or logging_config.get('level', 'INFO')
    log_format = logging_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - [线程:%(thread)d] - %(message)s')
    
    # 创建日志器
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 创建格式化器
    formatter = logging.Formatter(
        log_format,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器
    if log_file:
        log_dir = Path("./data/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / log_file
    else:
        log_path = Path(logging_config.get('file', './data/logs/app.log'))
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 使用轮转文件处理器
    max_size = logging_config.get('max_size', 10485760)  # 10MB
    backup_count = logging_config.get('backup_count', 5)
    
    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=max_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)  # 文件中记录所有级别
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

def get_task_logger(task_id: int) -> logging.Logger:
    """
    获取任务专用的日志器
    
    Args:
        task_id: 任务ID
        
    Returns:
        任务专用日志器
    """
    return setup_logger(f"task.{task_id}", f"task_{task_id}.log")

def get_service_logger(service_name: str) -> logging.Logger:
    """
    获取服务专用的日志器
    
    Args:
        service_name: 服务名称
        
    Returns:
        服务专用日志器
    """
    return setup_logger(f"service.{service_name}", f"{service_name}.log")

class TaskLoggerContext:
    """任务日志器上下文管理器"""
    
    def __init__(self, task_id: int, service_name: str):
        self.task_id = task_id
        self.service_name = service_name
        self.logger = None
        
    def __enter__(self):
        self.logger = setup_logger(
            f"{self.service_name}.task_{self.task_id}",
            f"{self.service_name}_task_{self.task_id}.log"
        )
        return self.logger
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        # 清理处理器避免内存泄漏
        if self.logger:
            for handler in self.logger.handlers[:]:
                handler.close()
                self.logger.removeHandler(handler)