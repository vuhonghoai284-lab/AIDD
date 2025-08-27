"""
AI输出数据访问层
"""
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, or_

from app.models import AIOutput
from app.dto.pagination import PaginationParams


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
    
    def get_paginated_ai_outputs_by_task_id(self, task_id: int, params: PaginationParams) -> Tuple[List[AIOutput], int]:
        """分页获取任务的AI输出记录
        
        Args:
            task_id: 任务ID
            params: 分页参数
            
        Returns:
            (AI输出列表, 总数量)
        """
        # 构建查询
        query = self.db.query(AIOutput).filter(AIOutput.task_id == task_id)
        
        # 操作类型过滤
        if hasattr(params, 'operation_type') and params.operation_type and params.operation_type != 'all':
            query = query.filter(AIOutput.operation_type == params.operation_type)
        
        # 状态过滤
        if params.status and params.status != 'all':
            query = query.filter(AIOutput.status == params.status)
        
        # 搜索过滤
        if params.search:
            search_term = f"%{params.search}%"
            query = query.filter(
                or_(
                    AIOutput.section_title.ilike(search_term),
                    AIOutput.input_text.ilike(search_term),
                    AIOutput.raw_output.ilike(search_term)
                )
            )
        
        # 排序
        if params.sort_by:
            sort_column = getattr(AIOutput, params.sort_by, None)
            if sort_column is not None:
                if params.sort_order == 'asc':
                    query = query.order_by(asc(sort_column))
                else:
                    query = query.order_by(desc(sort_column))
            else:
                # 默认按创建时间倒序
                query = query.order_by(desc(AIOutput.created_at))
        else:
            query = query.order_by(desc(AIOutput.created_at))
        
        # 获取总数
        total = query.count()
        
        # 分页
        offset = (params.page - 1) * params.page_size
        items = query.offset(offset).limit(params.page_size).all()
        
        return items, total