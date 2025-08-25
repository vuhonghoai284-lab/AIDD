"""
认证相关视图
"""
from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict
import time
import asyncio

from app.core.database import get_db
from app.models.user import User
from app.services.auth import AuthService
from app.dto.user import (
    UserResponse, UserLoginResponse, ThirdPartyAuthRequest,
    ThirdPartyTokenExchangeRequest, ThirdPartyLoginRequest, ThirdPartyTokenResponse
)
from app.views.base import BaseView


class AuthView(BaseView):
    """认证视图类"""
    
    def __init__(self):
        super().__init__()
        self.router = APIRouter(tags=["auth"])
        # 已处理的授权码缓存 {code: timestamp}
        self._processed_codes: Dict[str, float] = {}
        # 用于防止并发的锁
        self._code_lock = asyncio.Lock()
        self._setup_routes()
    
    def _setup_routes(self):
        """设置路由"""
        # 第三方认证相关路由
        self.router.add_api_route("/thirdparty/url", self.get_third_party_auth_url, methods=["GET"])
        self.router.add_api_route("/thirdparty/exchange-token", self.exchange_third_party_token, methods=["POST"], response_model=ThirdPartyTokenResponse)
        self.router.add_api_route("/thirdparty/login", self.third_party_login, methods=["POST"], response_model=UserLoginResponse)
        # 兼容旧接口（已废弃）
        self.router.add_api_route("/thirdparty/login-legacy", self.third_party_login_legacy, methods=["POST"], response_model=UserLoginResponse)
        # 系统登录
        self.router.add_api_route("/system/login", self.system_admin_login, methods=["POST"], response_model=UserLoginResponse)
    
    def _cleanup_expired_codes(self):
        """清理过期的授权码记录（超过10分钟）"""
        current_time = time.time()
        expired_codes = [
            code for code, timestamp in self._processed_codes.items()
            if current_time - timestamp > 600  # 10分钟
        ]
        for code in expired_codes:
            self._processed_codes.pop(code, None)
    
    def get_third_party_auth_url(self, db: Session = Depends(get_db)):
        """获取第三方认证URL"""
        auth_service = AuthService(db)
        auth_url = auth_service.get_authorization_url()
        return {"auth_url": auth_url}
    
    async def exchange_third_party_token(
        self,
        request: ThirdPartyTokenExchangeRequest,
        db: Session = Depends(get_db)
    ) -> ThirdPartyTokenResponse:
        """兑换第三方Access Token"""
        auth_service = AuthService(db)
        
        # 使用锁确保检查和标记操作的原子性
        async with self._code_lock:
            # 清理过期的授权码记录
            self._cleanup_expired_codes()
            
            # 检查授权码是否已被使用过
            if request.code in self._processed_codes:
                print(f'⚠️  授权码已被使用，拒绝重复兑换: {request.code[:10]}...')
                raise HTTPException(status_code=400, detail="授权码已被使用，请重新获取授权")
            
            # 原子性地标记授权码为已处理
            self._processed_codes[request.code] = time.time()
            print(f'🔄 开始兑换第三方Token，授权码: {request.code[:10]}...')
        
        try:
            # 使用authorization code交换access token
            token_response = await auth_service.exchange_code_for_token(request.code)
            
            print(f'✅ Token兑换成功，有效期: {token_response.expires_in}秒')
            
            return token_response
            
        except Exception as e:
            # 兑换失败时，清除授权码标记，允许重试
            async with self._code_lock:
                self._processed_codes.pop(request.code, None)
            print(f"❌ Token兑换失败: {e}")
            raise HTTPException(status_code=400, detail=f"Token兑换失败: {str(e)}")
    
    async def third_party_login(
        self,
        request: ThirdPartyLoginRequest,
        db: Session = Depends(get_db)
    ) -> UserLoginResponse:
        """使用第三方Access Token登录"""
        auth_service = AuthService(db)
        
        print(f'🔐 开始第三方Token登录，Token: {request.access_token[:10]}...')

        try:
            # 使用access token获取用户信息
            user_info = await auth_service.get_third_party_user_info(request.access_token)
            
            # 登录用户
            login_result = auth_service.login_user(
                uid=user_info.uid,
                display_name=user_info.display_name,
                email=user_info.email,
                avatar_url=user_info.avatar_url
            )
            
            if not login_result:
                raise HTTPException(status_code=401, detail="用户登录失败")
            
            print(f'✅ 第三方登录成功，用户: {user_info.display_name}')
            
            return UserLoginResponse(
                user=UserResponse.from_orm(login_result["user"]),
                access_token=login_result["access_token"],
                token_type=login_result["token_type"]
            )
        except Exception as e:
            print(f"❌ 第三方登录失败: {e}")
            raise HTTPException(status_code=401, detail=f"第三方登录失败: {str(e)}")
    
    async def third_party_login_legacy(
        self,
        auth_request: ThirdPartyAuthRequest,
        db: Session = Depends(get_db)
    ) -> UserLoginResponse:
        """第三方登录（已废弃，兼容旧版本）"""
        auth_service = AuthService(db)
        
        # 使用锁确保检查和标记操作的原子性
        async with self._code_lock:
            # 清理过期的授权码记录（超过10分钟的记录）
            self._cleanup_expired_codes()
            
            # 检查授权码是否已被使用过
            if auth_request.code in self._processed_codes:
                print(f'⚠️  授权码已被处理过，拒绝重复请求: {auth_request.code[:10]}...')
                raise HTTPException(status_code=400, detail="授权码已被使用，请重新授权")
            
            # 标记授权码为已处理（记录时间戳）
            self._processed_codes[auth_request.code] = time.time()
            print(f'🔐 [废弃接口] 开始第三方登录处理，授权码: {auth_request.code[:10]}...')

        try:
            
            # 使用authorization code交换access token
            token_response = await auth_service.exchange_code_for_token(auth_request.code)
            # 使用access token获取用户信息
            user_info = await auth_service.get_third_party_user_info(token_response.access_token)
            
            # 登录用户
            login_result = auth_service.login_user(
                uid=user_info.uid,
                display_name=user_info.display_name,
                email=user_info.email,
                avatar_url=user_info.avatar_url
            )
            
            if not login_result:
                # 登录失败时，从已处理字典中移除授权码，允许重试
                async with self._code_lock:
                    self._processed_codes.pop(auth_request.code, None)
                raise HTTPException(status_code=401, detail="登录失败")
            
            print(f'✅ [废弃接口] 第三方登录成功，用户: {user_info.display_name}')
            
            return UserLoginResponse(
                user=UserResponse.from_orm(login_result["user"]),
                access_token=login_result["access_token"],
                token_type=login_result["token_type"]
            )
        except HTTPException:
            # HTTPException 直接抛出，不需要额外处理
            raise
        except Exception as e:
            # 其他异常时，从已处理字典中移除授权码，允许重试
            async with self._code_lock:
                self._processed_codes.pop(auth_request.code, None)
            print(f"❌ [废弃接口] 第三方登录失败: {e}")
            raise HTTPException(status_code=401, detail="第三方登录失败")
    
    def system_admin_login(
        self,
        username: str = Form(...),
        password: str = Form(...),
        db: Session = Depends(get_db)
    ) -> UserLoginResponse:
        """系统管理员登录"""
        auth_service = AuthService(db)
        
        # 验证管理员凭据（在实际应用中应该使用加密密码验证）
        if username == "admin" and password == "admin123":
            # 创建或获取系统管理员用户
            login_result = auth_service.login_user(
                uid="sys_admin",
                display_name="系统管理员",
                email="admin@example.com",
                is_system_admin=True,
                is_admin=True
            )
            
            if not login_result:
                raise HTTPException(status_code=401, detail="登录失败")
            
            return UserLoginResponse(
                user=UserResponse.from_orm(login_result["user"]),
                access_token=login_result["access_token"],
                token_type=login_result["token_type"]
            )
        else:
            raise HTTPException(status_code=401, detail="用户名或密码错误")


# 创建视图实例并导出router
auth_view = AuthView()
router = auth_view.router