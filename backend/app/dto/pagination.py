"""
分页相关的数据传输对象
"""
from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel, Field

T = TypeVar('T')

class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(1, ge=1, description="页码，从1开始")
    page_size: int = Field(20, ge=1, le=100, description="每页大小，最大100")
    search: Optional[str] = Field(None, description="搜索关键词")
    status: Optional[str] = Field(None, description="状态筛选")
    sort_by: Optional[str] = Field("created_at", description="排序字段")
    sort_order: Optional[str] = Field("desc", description="排序顺序: asc/desc")
    
    # 问题特有的过滤参数
    severity: Optional[str] = Field(None, description="严重程度过滤")
    issue_type: Optional[str] = Field(None, description="问题类型过滤")  
    feedback_status: Optional[str] = Field(None, description="反馈状态过滤")
    
    # AI输出特有的过滤参数
    operation_type: Optional[str] = Field(None, description="操作类型过滤")

class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""
    items: List[T] = Field(description="数据项")
    total: int = Field(description="总数量")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页大小")
    pages: int = Field(description="总页数")
    has_prev: bool = Field(description="是否有上一页")
    has_next: bool = Field(description="是否有下一页")
    
    @classmethod
    def create(cls, items: List[T], total: int, page: int, page_size: int) -> 'PaginatedResponse[T]':
        """创建分页响应"""
        pages = (total + page_size - 1) // page_size if page_size > 0 else 1
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
            has_prev=page > 1,
            has_next=page < pages
        )