"""
文件信息数据访问层
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.file_info import FileInfo


class FileInfoRepository:
    """文件信息仓库"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, **kwargs) -> FileInfo:
        """创建文件信息记录"""
        file_info = FileInfo(**kwargs)
        self.db.add(file_info)
        self.db.commit()
        self.db.refresh(file_info)
        return file_info
    
    def get_by_id(self, file_id: int) -> Optional[FileInfo]:
        """根据ID获取文件信息"""
        return self.db.query(FileInfo).filter(FileInfo.id == file_id).first()
    
    def get_by_hash(self, content_hash: str) -> Optional[FileInfo]:
        """根据内容哈希获取文件信息"""
        return self.db.query(FileInfo).filter(FileInfo.content_hash == content_hash).first()
    
    def update(self, file_id: int, **kwargs) -> Optional[FileInfo]:
        """更新文件信息"""
        file_info = self.get_by_id(file_id)
        if file_info:
            for key, value in kwargs.items():
                setattr(file_info, key, value)
            self.db.commit()
            self.db.refresh(file_info)
        return file_info
    
    def delete(self, file_id: int) -> bool:
        """删除文件信息"""
        file_info = self.get_by_id(file_id)
        if file_info:
            self.db.delete(file_info)
            self.db.commit()
            return True
        return False
    
    def get_all(self) -> List[FileInfo]:
        """获取所有文件信息"""
        return self.db.query(FileInfo).order_by(FileInfo.created_at.desc()).all()