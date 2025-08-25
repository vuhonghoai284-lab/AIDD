"""提示词模板加载器"""
import yaml
import logging
from typing import Dict, Optional, Any
from pathlib import Path


class PromptLoader:
    """提示词模板加载和管理器"""
    
    def __init__(self, prompts_dir: str = None):
        """
        初始化提示词加载器
        
        Args:
            prompts_dir: 提示词模板目录路径，默认为项目根目录下的prompts文件夹
        """
        self.logger = logging.getLogger(f"prompt_loader.{id(self)}")
        
        if prompts_dir is None:
            # 从services目录向上找到backend目录，再找prompts
            current_dir = Path(__file__).parent
            backend_dir = current_dir.parent.parent  # 从 services -> app -> backend
            prompts_dir = backend_dir / 'prompts'
        
        self.prompts_dir = Path(prompts_dir)
        self.cache: Dict[str, Dict[str, Any]] = {}
        
        if not self.prompts_dir.exists():
            self.logger.error(f"提示词目录不存在: {self.prompts_dir}")
            raise ValueError(f"提示词目录不存在: {self.prompts_dir}")
        
        self.logger.info(f"📚 提示词加载器初始化，目录: {self.prompts_dir}")
    
    def load_template(self, template_name: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        加载提示词模板
        
        Args:
            template_name: 模板名称（不含扩展名）
            use_cache: 是否使用缓存
            
        Returns:
            模板内容字典
        """
        # 检查缓存
        if use_cache and template_name in self.cache:
            self.logger.debug(f"📖 从缓存加载模板: {template_name}")
            return self.cache[template_name]
        
        # 构建文件路径
        template_file = self.prompts_dir / f"{template_name}.yaml"
        
        if not template_file.exists():
            self.logger.error(f"模板文件不存在: {template_file}")
            raise FileNotFoundError(f"模板文件不存在: {template_file}")
        
        try:
            # 加载YAML文件
            with open(template_file, 'r', encoding='utf-8') as f:
                template_data = yaml.safe_load(f)
            
            # 缓存模板
            if use_cache:
                self.cache[template_name] = template_data
            
            self.logger.info(f"✅ 模板加载成功: {template_name}")
            return template_data
            
        except Exception as e:
            self.logger.error(f"❌ 模板加载失败 {template_name}: {str(e)}")
            raise
    
    def format_prompt(self, template_name: str, prompt_type: str, **kwargs) -> str:
        """
        格式化提示词
        
        Args:
            template_name: 模板名称
            prompt_type: 提示词类型（system_prompt 或 user_prompt_template）
            **kwargs: 模板参数
            
        Returns:
            格式化后的提示词
        """
        template_data = self.load_template(template_name)
        
        # 获取提示词模板
        if prompt_type not in template_data:
            self.logger.error(f"模板 {template_name} 中不存在 {prompt_type}")
            raise KeyError(f"模板中不存在 {prompt_type}")
        
        prompt_template = template_data[prompt_type]
        
        # 如果是用户提示词模板，需要格式化
        if prompt_type == 'user_prompt_template':
            # 验证必需参数
            if 'parameters' in template_data:
                for param_name, param_info in template_data['parameters'].items():
                    if param_info.get('required', False) and param_name not in kwargs:
                        self.logger.error(f"缺少必需参数: {param_name}")
                        raise ValueError(f"缺少必需参数: {param_name}")
                    
                    # 处理最大长度限制
                    if param_name in kwargs and 'max_length' in param_info:
                        max_len = param_info['max_length']
                        if isinstance(kwargs[param_name], str) and len(kwargs[param_name]) > max_len:
                            original_len = len(kwargs[param_name])
                            kwargs[param_name] = kwargs[param_name][:max_len]
                            self.logger.warning(f"参数 {param_name} 长度截断: {original_len} -> {max_len}")
            
            # 格式化模板
            try:
                formatted_prompt = prompt_template.format(**kwargs)
                self.logger.debug(f"📝 提示词格式化成功: {template_name}.{prompt_type}")
                return formatted_prompt
            except KeyError as e:
                self.logger.error(f"提示词格式化失败，缺少参数: {str(e)}")
                raise
        
        return prompt_template
    
    def get_system_prompt(self, template_name: str) -> str:
        """
        获取系统提示词
        
        Args:
            template_name: 模板名称
            
        Returns:
            系统提示词
        """
        return self.format_prompt(template_name, 'system_prompt')
    
    def get_user_prompt(self, template_name: str, **kwargs) -> str:
        """
        获取用户提示词
        
        Args:
            template_name: 模板名称
            **kwargs: 模板参数
            
        Returns:
            格式化后的用户提示词
        """
        return self.format_prompt(template_name, 'user_prompt_template', **kwargs)
    
    def get_detection_rules(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        获取检测规则配置
        
        Args:
            template_name: 模板名称
            
        Returns:
            检测规则配置，如果不存在返回None
        """
        template_data = self.load_template(template_name)
        return template_data.get('detection_rules')
    
    def get_severity_mapping(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        获取严重程度映射配置
        
        Args:
            template_name: 模板名称
            
        Returns:
            严重程度映射配置，如果不存在返回None
        """
        template_data = self.load_template(template_name)
        return template_data.get('severity_mapping')
    
    def list_templates(self) -> list:
        """
        列出所有可用的模板
        
        Returns:
            模板名称列表
        """
        templates = []
        for file_path in self.prompts_dir.glob('*.yaml'):
            templates.append(file_path.stem)
        self.logger.info(f"📋 可用模板: {templates}")
        return templates
    
    def reload_template(self, template_name: str) -> Dict[str, Any]:
        """
        重新加载模板（不使用缓存）
        
        Args:
            template_name: 模板名称
            
        Returns:
            模板内容字典
        """
        # 清除缓存
        if template_name in self.cache:
            del self.cache[template_name]
            self.logger.info(f"🔄 清除模板缓存: {template_name}")
        
        # 重新加载
        return self.load_template(template_name, use_cache=False)
    
    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
        self.logger.info("🗑️ 清空所有模板缓存")


# 创建全局实例
prompt_loader = PromptLoader()