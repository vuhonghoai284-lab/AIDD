"""
模型相关的DTO
"""
from pydantic import BaseModel
from typing import List


class ModelInfo(BaseModel):
    """模型信息"""
    index: int
    label: str
    description: str
    provider: str
    is_default: bool


class ModelsResponse(BaseModel):
    """模型列表响应"""
    models: List[ModelInfo]
    default_index: int