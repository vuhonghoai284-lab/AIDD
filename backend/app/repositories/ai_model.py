"""
AI模型数据访问层
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.ai_model import AIModel


class AIModelRepository:
    """AI模型仓库"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, **kwargs) -> AIModel:
        """创建AI模型记录"""
        model = AIModel(**kwargs)
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return model
    
    def get_by_id(self, model_id: int) -> Optional[AIModel]:
        """根据ID获取AI模型"""
        return self.db.query(AIModel).filter(AIModel.id == model_id).first()
    
    def get_by_key(self, model_key: str) -> Optional[AIModel]:
        """根据模型key获取AI模型"""
        return self.db.query(AIModel).filter(AIModel.model_key == model_key).first()
    
    def get_active_models(self) -> List[AIModel]:
        """获取活跃的AI模型"""
        return self.db.query(AIModel).filter(
            AIModel.is_active == True
        ).order_by(AIModel.sort_order).all()
    
    def get_default_model(self) -> Optional[AIModel]:
        """获取默认AI模型"""
        return self.db.query(AIModel).filter(
            AIModel.is_active == True,
            AIModel.is_default == True
        ).first()
    
    def update(self, model_id: int, **kwargs) -> Optional[AIModel]:
        """更新AI模型"""
        model = self.get_by_id(model_id)
        if model:
            for key, value in kwargs.items():
                setattr(model, key, value)
            self.db.commit()
            self.db.refresh(model)
        return model
    
    def delete(self, model_id: int) -> bool:
        """删除AI模型"""
        model = self.get_by_id(model_id)
        if model:
            self.db.delete(model)
            self.db.commit()
            return True
        return False
    
    def get_all(self) -> List[AIModel]:
        """获取所有AI模型"""
        return self.db.query(AIModel).order_by(AIModel.sort_order).all()