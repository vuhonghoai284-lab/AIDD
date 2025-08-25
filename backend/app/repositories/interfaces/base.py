"""
基础Repository接口
"""
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional
from sqlalchemy.orm import Session

# 定义泛型类型
T = TypeVar('T')  # 实体类型
ID = TypeVar('ID')  # ID类型


class BaseRepository(ABC, Generic[T, ID]):
    """基础Repository抽象类"""
    
    def __init__(self, db: Session):
        self.db = db
    
    @abstractmethod
    def create(self, **kwargs) -> T:
        """创建实体"""
        pass
    
    @abstractmethod
    def get_by_id(self, entity_id: ID) -> Optional[T]:
        """根据ID获取实体"""
        pass
    
    @abstractmethod
    def get_all(self) -> List[T]:
        """获取所有实体"""
        pass
    
    @abstractmethod
    def update(self, entity_id: ID, **kwargs) -> Optional[T]:
        """更新实体"""
        pass
    
    @abstractmethod
    def delete(self, entity_id: ID) -> bool:
        """删除实体"""
        pass