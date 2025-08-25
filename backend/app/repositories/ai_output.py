"""
AI输出数据访问层
"""
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models import AIOutput


class AIOutputRepository:
    """AI输出仓库"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, **kwargs) -> AIOutput:
        """创建AI输出记录"""
        ai_output = AIOutput(**kwargs)
        self.db.add(ai_output)
        self.db.commit()
        self.db.refresh(ai_output)
        return ai_output
    
    def get_by_id(self, output_id: int) -> Optional[AIOutput]:
        """根据ID获取AI输出"""
        return self.db.query(AIOutput).filter(AIOutput.id == output_id).first()
    
    def get_by_task_id(self, task_id: int, operation_type: Optional[str] = None) -> List[AIOutput]:
        """获取任务的AI输出记录"""
        query = self.db.query(AIOutput).filter(AIOutput.task_id == task_id)
        if operation_type:
            query = query.filter(AIOutput.operation_type == operation_type)
        return query.order_by(AIOutput.created_at.desc()).all()
    
    def delete_by_task_id(self, task_id: int):
        """删除任务的所有AI输出"""
        self.db.query(AIOutput).filter(AIOutput.task_id == task_id).delete()
        self.db.commit()