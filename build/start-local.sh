#!/bin/bash

# ============================================================================
# AI Document Testing System - 一键启动脚本
# ============================================================================
# 功能：快速启动本地开发环境
# 使用：./start-local.sh
# ============================================================================

set -euo pipefail

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 显示标题
echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                                                          ║"
echo "║   🚀 AI Document Testing System - 一键启动             ║"
echo "║                                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${BLUE}[INFO]${NC} 检查环境和依赖..."

# 进入项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 检查脚本是否存在
if [[ ! -f "./build/setup-local.sh" ]]; then
    echo -e "${YELLOW}[WARNING]${NC} setup-local.sh 不存在，使用基础启动流程"
    
    # 基础检查
    if ! command -v node &> /dev/null || ! command -v python3 &> /dev/null; then
        echo -e "${YELLOW}[ERROR]${NC} 缺少必需工具 (Node.js 或 Python)"
        echo "请安装后重试，或查看 build/LOCAL_DEPLOYMENT_GUIDE.md"
        exit 1
    fi
    
    # 基础构建和部署
    if [[ -f "./build/build-local.sh" && -f "./build/deploy-local.sh" ]]; then
        chmod +x ./build/build-local.sh ./build/deploy-local.sh
        echo -e "${BLUE}[INFO]${NC} 开始构建..."
        ./build/build-local.sh --skip-tests || {
            echo -e "${YELLOW}[WARNING]${NC} 构建失败，尝试直接部署..."
        }
        
        echo -e "${BLUE}[INFO]${NC} 开始部署..."
        ./build/deploy-local.sh --mode dev --skip-health-check
    else
        echo -e "${YELLOW}[ERROR]${NC} 缺少构建或部署脚本"
        exit 1
    fi
else
    # 使用完整的设置脚本
    echo -e "${BLUE}[INFO]${NC} 运行快速设置..."
    chmod +x ./build/setup-local.sh
    ./build/setup-local.sh --quick
fi

echo ""
echo -e "${GREEN}✅ 启动完成！${NC}"
echo -e "${BLUE}访问地址：${NC}"
echo "  前端: http://localhost:3000"
echo "  后端: http://localhost:8080"
echo ""
echo -e "${YELLOW}管理命令：${NC}"
echo "  停止: ./build/deploy-local.sh stop"
echo "  状态: ./build/deploy-local.sh status"
echo "  日志: ./build/deploy-local.sh logs"