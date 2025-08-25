"""
重构后的用户认证服务 - 使用抽象OAuth提供商架构
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import jwt
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.user import UserRepository
from app.dto.user import UserCreate, ThirdPartyTokenResponse, ThirdPartyUserInfoResponse
from app.core.config import get_settings
from app.services.interfaces.auth_service import IAuthService
from app.services.oauth import create_oauth_provider, IOAuthProvider


class AuthService(IAuthService):
    """重构后的用户认证服务类 - 分离JWT管理和OAuth认证逻辑"""
    
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.settings = get_settings()
        
        # 初始化JWT配置
        self._init_jwt_config()
        
        # 初始化OAuth提供商
        self.oauth_provider = self._create_oauth_provider()
    
    def _init_jwt_config(self):
        """初始化JWT配置"""
        jwt_config = self.settings.jwt_config
        self.SECRET_KEY = jwt_config.get("secret_key", "ai_doc_test_secret_key")
        self.ALGORITHM = jwt_config.get("algorithm", "HS256")
        self.ACCESS_TOKEN_EXPIRE_MINUTES = jwt_config.get("access_token_expire_minutes", 30)
    
    def _create_oauth_provider(self) -> IOAuthProvider:
        """
        创建OAuth提供商实例
        
        Returns:
            OAuth提供商实例
            
        Raises:
            ValueError: 当提供商配置无效时
        """
        try:
            third_party_config = self.settings.third_party_auth_config
            provider_type = third_party_config.get("provider_type", "generic")
            
            # 使用工厂创建提供商
            provider = create_oauth_provider(provider_type, third_party_config, self.settings)
            
            print(f"✓ 成功初始化OAuth提供商: {provider.get_provider_name()} (类型: {provider_type})")
            return provider
            
        except Exception as e:
            print(f"✗ OAuth提供商初始化失败: {e}")
            print("将使用默认的通用OAuth提供商配置")
            # 回退到最小配置
            fallback_config = {
                "provider_type": "generic",
                "client_id": "fallback_client",
                "client_secret": "fallback_secret",
                "frontend_domain": "http://localhost:5173",
                "api_endpoints": {
                    "authorization_url": "http://localhost:8080/mock/oauth/authorize",
                    "token_url": "http://localhost:8080/mock/oauth/token",
                    "userinfo_url": "http://localhost:8080/mock/oauth/userinfo"
                }
            }
            return create_oauth_provider("generic", fallback_config, self.settings)
    
    # ===== JWT 令牌管理方法 =====
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        """创建访问令牌"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[User]:
        """验证令牌"""
        try:
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            user_id: str = payload.get("sub")
            if user_id is None:
                return None
            user = self.user_repo.get_by_id(int(user_id))
            return user
        except jwt.PyJWTError:
            return None
    
    def generate_token(self, user: User) -> str:
        """生成访问令牌"""
        access_token_expires = timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)
        return self.create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )
    
    # ===== 用户管理方法 =====
    
    def authenticate_user(self, uid: str) -> Optional[User]:
        """验证用户是否存在"""
        return self.user_repo.get_by_uid(uid)
    
    def create_user(self, user_data: UserCreate) -> User:
        """创建新用户"""
        return self.user_repo.create(user_data)
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        return self.user_repo.get_by_id(user_id)
    
    def update_last_login(self, user_id: int) -> Optional[User]:
        """更新用户最后登录时间"""
        return self.user_repo.update_last_login(user_id)
    
    def login_user(self, uid: str, display_name: str = None, email: str = None, 
                   avatar_url: str = None, is_admin: bool = False, 
                   is_system_admin: bool = False) -> Optional[Dict[str, Any]]:
        """
        用户登录处理逻辑
        
        Args:
            uid: 用户唯一标识
            display_name: 显示名称
            email: 邮箱
            avatar_url: 头像URL
            is_admin: 是否为管理员
            is_system_admin: 是否为系统管理员
            
        Returns:
            登录结果字典，包含用户信息和访问令牌
        """
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # 查找用户
                user = self.user_repo.get_by_uid(uid)
                
                # 如果用户不存在，创建新用户
                if not user:
                    user_create = UserCreate(
                        uid=uid,
                        display_name=display_name,
                        email=email,
                        avatar_url=avatar_url,
                        is_admin=is_admin,
                        is_system_admin=is_system_admin
                    )
                    user = self.user_repo.create(user_create)
                else:
                    # 更新用户最后登录时间
                    self.user_repo.update_last_login(user.id)
                
                # 如果成功，跳出重试循环
                break
                
            except Exception as e:
                retry_count += 1
                error_msg = str(e)
                
                # 处理各种并发问题
                if ("UNIQUE constraint failed" in error_msg or 
                    "IntegrityError" in error_msg or 
                    "NULL identity key" in error_msg or
                    "FlushError" in error_msg or
                    "database is locked" in error_msg):
                    
                    # 回滚当前事务
                    try:
                        self.db.rollback()
                    except:
                        pass
                    
                    # 重新查找用户（可能被其他线程创建了）
                    user = self.user_repo.get_by_uid(uid)
                    if user:
                        break  # 找到用户，成功
                    
                    # 如果还有重试次数，稍等片刻再重试
                    if retry_count < max_retries:
                        import time
                        time.sleep(0.1 * retry_count)  # 递增延迟
                        continue
                    else:
                        raise e  # 重试次数用完，抛出异常
                else:
                    raise e  # 非并发问题，直接抛出
        
        # 创建访问令牌
        access_token = self.generate_token(user)
        
        return {
            "user": user,
            "access_token": access_token,
            "token_type": "bearer"
        }
    
    # ===== OAuth 认证方法 - 委托给OAuth提供商 =====
    
    def get_authorization_url(self, state: str = "12345678") -> str:
        """
        获取第三方认证授权URL
        
        Args:
            state: 状态参数，用于防止CSRF攻击
            
        Returns:
            完整的授权URL
        """
        try:
            return self.oauth_provider.get_authorization_url(state)
        except Exception as e:
            print(f"获取授权URL失败: {e}")
            raise ValueError(f"无法生成OAuth授权URL: {e}")
    
    async def exchange_code_for_token(self, code: str) -> ThirdPartyTokenResponse:
        """
        使用authorization code交换access token
        
        Args:
            code: 授权码
            
        Returns:
            令牌响应对象
        """
        try:
            return await self.oauth_provider.exchange_code_for_token(code)
        except Exception as e:
            print(f"令牌交换失败: {e}")
            raise ValueError(f"OAuth令牌交换失败: {e}")
    
    async def get_third_party_user_info(self, access_token: str) -> ThirdPartyUserInfoResponse:
        """
        获取第三方用户信息
        
        Args:
            access_token: 访问令牌
            
        Returns:
            用户信息响应对象
        """
        try:
            return await self.oauth_provider.get_user_info(access_token)
        except Exception as e:
            print(f"获取用户信息失败: {e}")
            raise ValueError(f"获取OAuth用户信息失败: {e}")
    
    # ===== 系统信息和调试方法 =====
    
    def get_oauth_provider_info(self) -> dict:
        """
        获取当前OAuth提供商信息
        
        Returns:
            提供商信息字典
        """
        try:
            return {
                "provider_name": self.oauth_provider.get_provider_name(),
                "provider_type": type(self.oauth_provider).__name__,
                "config_valid": self.oauth_provider.validate_config(),
                "mock_enabled": self.oauth_provider.is_mock_enabled(),
                "module": type(self.oauth_provider).__module__
            }
        except Exception as e:
            return {
                "error": f"无法获取提供商信息: {e}",
                "provider_type": "Unknown"
            }
    
    def validate_oauth_config(self) -> Dict[str, Any]:
        """
        验证OAuth配置
        
        Returns:
            验证结果字典
        """
        try:
            config_valid = self.oauth_provider.validate_config()
            provider_info = self.get_oauth_provider_info()
            
            # 测试授权URL生成
            try:
                test_auth_url = self.oauth_provider.get_authorization_url("test_state")
                auth_url_valid = bool(test_auth_url and "client_id" in test_auth_url)
            except Exception as e:
                auth_url_valid = False
                auth_url_error = str(e)
            else:
                auth_url_error = None
            
            return {
                "config_valid": config_valid,
                "provider_info": provider_info,
                "auth_url_valid": auth_url_valid,
                "auth_url_error": auth_url_error,
                "redirect_uri": self.oauth_provider.get_redirect_url() if config_valid else None
            }
        except Exception as e:
            return {
                "config_valid": False,
                "error": str(e)
            }
    
    # ===== BaseService接口实现 =====
    
    def create(self, **kwargs) -> User:
        """创建用户实体"""
        user_data = UserCreate(**kwargs)
        return self.user_repo.create(user_data)
    
    def get_by_id(self, entity_id: int) -> Optional[User]:
        """根据ID获取用户"""
        return self.user_repo.get_by_id(entity_id)
    
    def get_all(self) -> List[User]:
        """获取所有用户"""
        return self.user_repo.get_all()
    
    def update(self, entity_id: int, **kwargs) -> Optional[User]:
        """更新用户"""
        return self.user_repo.update(entity_id, **kwargs)
    
    def delete(self, entity_id: int) -> bool:
        """删除用户"""
        return self.user_repo.delete(entity_id)