#!/usr/bin/env python3
"""
Alembic运行辅助脚本
确保在任何环境下都能正确运行Alembic命令
"""
import os
import sys
import subprocess
from pathlib import Path

def main():
    """主函数：设置环境并运行Alembic"""
    # 确保在backend目录
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    # 设置PYTHONPATH
    env = os.environ.copy()
    env['PYTHONPATH'] = str(backend_dir)
    
    # 获取命令行参数
    if len(sys.argv) < 2:
        print("Usage: python run_alembic.py <alembic_command> [args...]")
        print("Examples:")
        print("  python run_alembic.py current")
        print("  python run_alembic.py upgrade head")
        print("  python run_alembic.py revision --autogenerate -m 'description'")
        sys.exit(1)
    
    # 构建alembic命令
    alembic_args = ['alembic'] + sys.argv[1:]
    
    print(f"🔧 工作目录: {backend_dir}")
    print(f"🐍 PYTHONPATH: {env.get('PYTHONPATH')}")
    print(f"⚡ 运行命令: {' '.join(alembic_args)}")
    
    try:
        # 运行alembic命令
        result = subprocess.run(
            alembic_args,
            env=env,
            cwd=backend_dir,
            check=True
        )
        print(f"✅ 命令执行成功，退出码: {result.returncode}")
    except subprocess.CalledProcessError as e:
        print(f"❌ 命令执行失败，退出码: {e.returncode}")
        sys.exit(e.returncode)
    except FileNotFoundError:
        print("❌ 找不到alembic命令，请确保已安装alembic")
        print("💡 安装方法: pip install alembic")
        sys.exit(1)

if __name__ == "__main__":
    main()