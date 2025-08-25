"""
问题相关的DTO
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal


class IssueResponse(BaseModel):
    """问题响应"""
    id: int
    issue_type: str
    description: str
    location: Optional[str] = None
    severity: str
    confidence: Optional[float] = None
    suggestion: Optional[str] = None
    original_text: Optional[str] = None
    user_impact: Optional[str] = None
    reasoning: Optional[str] = None
    context: Optional[str] = None
    feedback_type: Optional[str] = None
    feedback_comment: Optional[str] = None
    satisfaction_rating: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)


class FeedbackRequest(BaseModel):
    """反馈请求"""
    feedback_type: Optional[Literal["accept", "reject", ""]] = Field(None, description="反馈类型，可以是 accept、reject 或空字符串（用于清除反馈）")
    comment: Optional[str] = None


class SatisfactionRatingRequest(BaseModel):
    """满意度评分请求"""
    satisfaction_rating: float = Field(..., ge=1.0, le=5.0, description="满意度评分，范围1-5星")