"""
应用配置管理
"""
import os
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path


class Settings:
    """应用配置类"""
    
    def __init__(self, config_file: Optional[str] = None):
        # 支持通过环境变量或参数指定配置文件
        if config_file:
            self.config_file = config_file
        else:
            self.config_file = os.getenv('CONFIG_FILE', 'config.yaml')
        
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        config_path = Path(self.config_file)
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_file}")
            
        print(f"加载配置文件: {self.config_file}")
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        # 处理环境变量替换
        self._replace_env_vars(config)
        return config
    
    def _replace_env_vars(self, config: Any) -> None:
        """递归替换配置中的环境变量"""
        if isinstance(config, dict):
            for key, value in config.items():
                if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                    env_var_spec = value[2:-1]  # 移除 ${ 和 }
                    env_var, default_value = self._parse_env_var_spec(env_var_spec)
                    env_value = os.getenv(env_var, default_value)
                    
                    # 类型转换
                    env_value = self._convert_type(env_value)
                    
                    print(f"🔄 环境变量替换: {key}={value} -> {env_var}={env_value}")
                    config[key] = env_value
                elif isinstance(value, (dict, list)):
                    self._replace_env_vars(value)
        elif isinstance(config, list):
            for i, item in enumerate(config):
                if isinstance(item, str) and item.startswith('${') and item.endswith('}'):
                    env_var_spec = item[2:-1]
                    env_var, default_value = self._parse_env_var_spec(env_var_spec)
                    env_value = os.getenv(env_var, default_value)
                    env_value = self._convert_type(env_value)
                    config[i] = env_value
                elif isinstance(item, (dict, list)):
                    self._replace_env_vars(item)
    
    def _parse_env_var_spec(self, env_var_spec: str) -> tuple[str, str]:
        """解析环境变量规范，支持默认值格式 VAR_NAME:default_value"""
        if ':' in env_var_spec:
            env_var, default_value = env_var_spec.split(':', 1)
            return env_var, default_value
        else:
            return env_var_spec, ""
    
    def _convert_type(self, value: str) -> Any:
        """将字符串值转换为合适的类型"""
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # 尝试转换为整数
        try:
            if '.' not in value:
                return int(value)
        except ValueError:
            pass
        
        # 尝试转换为浮点数
        try:
            return float(value)
        except ValueError:
            pass
        
        # 保持为字符串
        return value
    
    
    @property
    def database_url(self) -> str:
        """数据库连接URL"""
        db_config = self.config.get('database', {})
        
        # 兼容旧配置格式（直接为字符串）
        if isinstance(db_config, str):
            db_path = db_config
            if not db_path.startswith('sqlite://'):
                db_path = f'sqlite:///{db_path}'
            return db_path
        
        # 新配置格式（字典）
        db_type = db_config.get('type', 'sqlite').lower()
        
        if db_type == 'mysql':
            mysql_config = db_config.get('mysql', {})
            host = mysql_config.get('host', 'localhost')
            port = mysql_config.get('port', 3306)
            username = mysql_config.get('username', 'root')
            password = mysql_config.get('password', '')
            database = mysql_config.get('database', 'ai_doc_test')
            charset = mysql_config.get('charset', 'utf8mb4')
            
            return f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}?charset={charset}"
        else:
            # 默认使用SQLite
            sqlite_config = db_config.get('sqlite', {})
            db_path = sqlite_config.get('path', './data/app.db')
            if not db_path.startswith('sqlite://'):
                db_path = f'sqlite:///{db_path}'
            return db_path
    
    @property
    def database_config(self) -> Dict[str, Any]:
        """获取数据库配置"""
        return self.config.get('database', {})
    
    @property
    def database_type(self) -> str:
        """获取数据库类型"""
        db_config = self.config.get('database', {})
        if isinstance(db_config, str):
            return 'sqlite'
        return db_config.get('type', 'sqlite').lower()
    
    @property
    def upload_dir(self) -> str:
        """文件上传目录"""
        dirs = self.config.get('directories', {})
        return dirs.get('upload_dir', './data/uploads')
    
    @property
    def data_dir(self) -> str:
        """数据目录"""
        dirs = self.config.get('directories', {})
        return dirs.get('data_dir', './data')
    
    @property
    def ai_models(self) -> List[Dict[str, Any]]:
        """AI模型配置"""
        return self.config.get('ai_models', {}).get('models', [])
    
    @property
    def default_model_index(self) -> int:
        """默认模型索引"""
        return self.config.get('ai_models', {}).get('default_index', 0)
    
    @property
    def file_settings(self) -> Dict[str, Any]:
        """文件设置"""
        return self.config.get('file_settings', {})
    
    @property
    def cors_origins(self) -> List[str]:
        """CORS允许的源"""
        cors_config = self.config.get('cors', {})
        if not cors_config.get('enabled', True):
            return []
        
        origins = cors_config.get('origins', [
            "http://localhost:3000", 
            "http://localhost:5173", 
            "http://127.0.0.1:3000", 
            "http://127.0.0.1:5173"
        ])
        
        # 过滤掉空值和环境变量占位符
        filtered_origins = []
        for origin in origins:
            if origin and not origin.startswith("${") and origin != "null":
                filtered_origins.append(origin)
            elif origin.startswith("${") and origin.endswith("}"):
                # 处理环境变量
                env_var = origin[2:-1].split(":")[0]  # 获取环境变量名，忽略默认值
                env_value = os.getenv(env_var)
                if env_value and env_value != "null":
                    filtered_origins.append(env_value)
        
        # 开发模式：允许更宽松的CORS
        development_mode = cors_config.get('development_mode', False)
        if isinstance(development_mode, str):
            development_mode = development_mode.lower() in ['true', '1', 'yes']
        
        if development_mode or os.getenv('CORS_DEVELOPMENT_MODE', '').lower() in ['true', '1', 'yes']:
            # 开发模式下添加常用的开发地址模式
            dev_origins = [
                "http://localhost:3000",
                "http://localhost:3001", 
                "http://localhost:5173",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173"
            ]
            for dev_origin in dev_origins:
                if dev_origin not in filtered_origins:
                    filtered_origins.append(dev_origin)
        
        return filtered_origins
    
    
    
    @property
    def server_config(self) -> Dict[str, Any]:
        """服务器配置"""
        return self.config.get('server', {
            'host': '0.0.0.0',
            'port': 8080,
            'debug': False,
            'reload': False,
            'external_host': 'localhost',
            'external_port': 8080,
            'external_protocol': 'http'
        })
    
    @property
    def server_external_url(self) -> str:
        """服务器外部访问URL"""
        server_config = self.server_config
        protocol = server_config.get('external_protocol', 'http')
        host = server_config.get('external_host', 'localhost')
        port = server_config.get('external_port', 8080)
        
        # 标准端口不需要显示
        if (protocol == 'http' and port == 80) or (protocol == 'https' and port == 443):
            return f"{protocol}://{host}"
        else:
            return f"{protocol}://{host}:{port}"
    
    @property
    def third_party_auth_config(self) -> Dict[str, Any]:
        """第三方登录配置"""
        return self.config.get('third_party_auth', {})
    
    @property
    def jwt_config(self) -> Dict[str, Any]:
        """JWT配置"""
        return self.config.get('jwt', {
            'secret_key': 'ai_doc_test_secret_key',
            'algorithm': 'HS256',
            'access_token_expire_minutes': 30
        })
    
    @property
    def cache_config(self) -> Dict[str, Any]:
        """缓存配置"""
        return self.config.get('cache', {
            'strategy': 'memory',
            'default_ttl': 30,
            'memory': {'max_entries': 1000, 'cleanup_interval': 60},
            'redis': {'host': 'localhost', 'port': 6379, 'password': '', 'database': 0}
        })
    
    @property
    def task_processing_config(self) -> Dict[str, Any]:
        """任务处理配置"""
        return self.config.get('task_processing', {})
    
    @property
    def document_processing_config(self) -> Dict[str, Any]:
        """文档处理配置"""
        task_config = self.task_processing_config
        return task_config.get('document_processing', {
            'max_document_chars': 1000000,
            'enable_intelligent_chunking': True,
            'chunk_overlap_chars': 200,
            'min_chunk_chars': 1000,
            'max_chunks_per_document': 50
        })
    
    @property
    def section_merge_config(self) -> Dict[str, Any]:
        """章节合并配置"""
        task_config = self.task_processing_config
        return task_config.get('section_merge', {
            'enabled': True,
            'max_chars': 5000,
            'min_chars': 100,
            'preserve_structure': True
        })
    
    def reload(self, config_file: Optional[str] = None):
        """重新加载配置"""
        if config_file:
            self.config_file = config_file
        self.config = self._load_config()


# 全局配置实例（延迟初始化）
settings: Optional[Settings] = None

def get_settings() -> Settings:
    """获取配置实例"""
    global settings
    if settings is None:
        settings = Settings()
    return settings

def init_settings(config_file: Optional[str] = None) -> Settings:
    """初始化配置"""
    global settings
    settings = Settings(config_file)
    return settings