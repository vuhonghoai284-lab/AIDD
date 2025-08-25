"""
用户相关的数据传输对象
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """用户基础模型"""
    uid: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    is_admin: Optional[bool] = False
    is_system_admin: Optional[bool] = False


class UserCreate(UserBase):
    """创建用户模型"""
    pass


class UserUpdate(BaseModel):
    """更新用户模型"""
    display_name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    is_admin: Optional[bool] = None


class UserResponse(UserBase):
    """用户响应模型"""
    id: int
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserLoginResponse(BaseModel):
    """用户登录响应模型"""
    user: UserResponse
    access_token: str
    token_type: str = "bearer"


class ThirdPartyAuthRequest(BaseModel):
    """第三方认证请求模型"""
    code: str


class ThirdPartyTokenExchangeRequest(BaseModel):
    """第三方令牌兑换请求模型"""
    code: str


class ThirdPartyLoginRequest(BaseModel):
    """第三方登录请求模型"""
    access_token: str


class ThirdPartyTokenResponse(BaseModel):
    """第三方令牌响应模型"""
    access_token: str
    refresh_token: Optional[str] = None
    scope: str
    expires_in: int


class ThirdPartyUserInfoResponse(BaseModel):
    """第三方用户信息响应模型"""
    uid: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None