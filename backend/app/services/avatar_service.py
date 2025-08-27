"""
头像处理服务
提供安全的头像生成和处理功能，避免外部API依赖导致的网络问题
"""
import hashlib
import io
import base64
from typing import Optional
from app.core.config import get_settings


class AvatarService:
    """头像处理服务类"""
    
    def __init__(self):
        self.settings = get_settings()
    
    def generate_avatar_data_url(self, user_id: str, display_name: Optional[str] = None) -> str:
        """
        生成简单的SVG头像Data URL
        使用用户ID和显示名称生成一致的头像
        """
        # 基于用户ID生成一致的颜色
        hash_obj = hashlib.md5(user_id.encode())
        color_hash = hash_obj.hexdigest()
        
        # 生成背景色
        bg_color = f"#{color_hash[:6]}"
        
        # 生成文本颜色（与背景形成对比）
        bg_r = int(color_hash[:2], 16)
        bg_g = int(color_hash[2:4], 16)
        bg_b = int(color_hash[4:6], 16)
        
        # 计算亮度，选择合适的文字颜色
        brightness = (bg_r * 299 + bg_g * 587 + bg_b * 114) / 1000
        text_color = "#FFFFFF" if brightness < 128 else "#000000"
        
        # 生成显示文字（使用显示名称的首字符或用户ID的前两个字符）
        if display_name:
            display_text = display_name[0].upper()
        else:
            display_text = user_id[:2].upper()
        
        # 生成SVG头像
        svg_content = f'''
        <svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
            <circle cx="16" cy="16" r="16" fill="{bg_color}"/>
            <text x="16" y="20" text-anchor="middle" font-family="Arial, sans-serif" 
                  font-size="14" font-weight="bold" fill="{text_color}">{display_text}</text>
        </svg>
        '''.strip()
        
        # 编码为Data URL
        svg_base64 = base64.b64encode(svg_content.encode()).decode()
        return f"data:image/svg+xml;base64,{svg_base64}"
    
    def get_safe_avatar_url(self, user_id: str, original_avatar_url: Optional[str] = None, 
                           display_name: Optional[str] = None) -> Optional[str]:
        """
        获取安全的头像URL
        1. 如果原始头像URL来自可信域名，直接返回
        2. 否则返回None，让前端使用默认头像
        """
        if not original_avatar_url:
            return None
        
        # 定义可信的头像域名列表
        trusted_domains = [
            'avatar.githubusercontent.com',  # GitHub头像
            'avatars.githubusercontent.com', # GitHub头像备用域名
            'gravatar.com',                  # Gravatar
            'www.gravatar.com',             # Gravatar备用域名
            'gitee.com',                    # Gitee头像
            'portrait.gitee.com',           # Gitee头像域名
        ]
        
        # 检查URL是否来自可信域名
        try:
            from urllib.parse import urlparse
            parsed_url = urlparse(original_avatar_url)
            domain = parsed_url.netloc.lower()
            
            # 移除www.前缀进行比较
            if domain.startswith('www.'):
                domain = domain[4:]
            
            for trusted_domain in trusted_domains:
                if trusted_domain.startswith('www.'):
                    trusted_domain = trusted_domain[4:]
                if domain == trusted_domain or domain.endswith(f'.{trusted_domain}'):
                    return original_avatar_url
            
            # 如果不是来自可信域名，记录警告但不返回URL
            # 让前端使用默认头像，避免网络问题
            return None
            
        except Exception:
            # URL解析失败，返回None
            return None
    
    def process_third_party_avatar(self, user_id: str, provider_type: str, 
                                 avatar_url: Optional[str], display_name: Optional[str] = None) -> Optional[str]:
        """
        处理第三方登录的头像URL
        """
        if provider_type == "gitee":
            # Gitee头像通常是可信的
            return self.get_safe_avatar_url(user_id, avatar_url, display_name)
        else:
            # 其他提供者，保守处理，让前端使用默认头像
            return None