"""
文件信息数据模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class FileInfo(Base):
    """文件信息表"""
    __tablename__ = "file_infos"
    
    id = Column(Integer, primary_key=True, index=True)
    # 文件基本信息
    original_name = Column(String(255), nullable=False)  # 原始文件名
    stored_name = Column(String(255), nullable=False)    # 存储文件名
    file_path = Column(String(500), nullable=False)      # 文件存储路径
    file_size = Column(BigInteger, nullable=False)       # 文件大小（字节）
    file_type = Column(String(50), nullable=False)       # 文件类型扩展名
    mime_type = Column(String(100))                      # MIME类型
    
    # 文件内容信息
    content_hash = Column(String(64), index=True)        # 文件内容哈希（SHA-256）
    encoding = Column(String(50))                        # 文件编码
    document_chars = Column(Integer)                     # 文档字符数
    
    # 处理状态
    is_processed = Column(String(20), default='pending') # pending, processing, completed, failed
    process_error = Column(Text)                         # 处理错误信息
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系定义
    tasks = relationship("Task", back_populates="file_info")
    
    def __repr__(self):
        return f"<FileInfo(id={self.id}, name='{self.original_name}', size={self.file_size})>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'original_name': self.original_name,
            'stored_name': self.stored_name,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'file_type': self.file_type,
            'mime_type': self.mime_type,
            'content_hash': self.content_hash,
            'encoding': self.encoding,
            'document_chars': self.document_chars,
            'is_processed': self.is_processed,
            'process_error': self.process_error,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }