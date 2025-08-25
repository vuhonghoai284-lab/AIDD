#!/usr/bin/env python
"""
启动脚本
"""
import sys
import os
import argparse
import uvicorn
from pathlib import Path
from dotenv import load_dotenv 

load_dotenv()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='AI文档测试系统后端服务')
    parser.add_argument(
        '--config',
        type=str,
        help='指定配置文件路径'
    )
    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='服务监听地址'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8080,
        help='服务监听端口'
    )
    parser.add_argument(
        '--reload',
        action='store_true',
        help='启用自动重载'
    )
    
    args = parser.parse_args()
    
    
    # 确保在正确的目录
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # 初始化配置
    from app.core.config import init_settings
    
    if args.config:
        settings = init_settings(args.config)
    else:
        settings = init_settings('config.yaml')
    
    # 创建必要的目录
    dirs_to_create = [
        settings.upload_dir,
        settings.data_dir,
        Path(settings.upload_dir).parent / 'reports',
        Path(settings.upload_dir).parent / 'logs',
        Path(settings.upload_dir).parent / 'temp'
    ]
    
    for dir_path in dirs_to_create:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    # 导入应用
    from app.main import app
    
    # 显示启动信息
    print("="*60)
    print("🚀 启动服务")
    print(f"🤖 AI模式: API调用")
    print("="*60)
    print(f"📁 配置文件: {settings.config_file}")
    print(f"📊 数据库: {settings.database_url}")
    print(f"🌐 服务地址: http://{args.host}:{args.port}")
    print(f"📚 API文档: http://localhost:{args.port}/docs")
    print("="*60)
    print("提示: 使用 Ctrl+C 停止服务")
    print()
    
    # 启动服务器
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload or settings.server_config.get('reload', False),
        log_level="debug" if settings.server_config.get('debug') else "info"
    )

if __name__ == "__main__":
    main()