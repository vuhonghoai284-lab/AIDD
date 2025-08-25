"""
数据传输对象
"""
from app.dto.task import TaskResponse, TaskDetail, TaskCreate
from app.dto.issue import IssueResponse, FeedbackRequest
from app.dto.ai_output import AIOutputResponse
from app.dto.model import ModelsResponse, ModelInfo
from app.dto.user import UserResponse, UserCreate, UserUpdate, UserLoginResponse, ThirdPartyAuthRequest, ThirdPartyTokenResponse, ThirdPartyUserInfoResponse

__all__ = [
    "TaskResponse", "TaskDetail", "TaskCreate",
    "IssueResponse", "FeedbackRequest",
    "AIOutputResponse",
    "ModelsResponse", "ModelInfo",
    "UserResponse", "UserCreate", "UserUpdate", "UserLoginResponse",
    "ThirdPartyAuthRequest", "ThirdPartyTokenResponse", "ThirdPartyUserInfoResponse"
]