"""
AI输出相关的DTO
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, Union, List
from datetime import datetime


class AIOutputResponse(BaseModel):
    """AI输出响应"""
    id: int
    task_id: int
    operation_type: str
    section_title: Optional[str] = None
    section_index: Optional[int] = None
    input_text: str
    raw_output: str
    parsed_output: Optional[Union[Dict[str, Any], List[Any]]] = None  # 支持字典和列表两种类型
    status: str
    error_message: Optional[str] = None
    tokens_used: Optional[int] = None
    processing_time: Optional[float] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)