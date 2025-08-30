#!/bin/bash

# ============================================================================
# AI Document Testing System - 项目根目录快速启动脚本
# ============================================================================
# 功能：从项目根目录快速启动本地开发环境
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
echo "║   🚀 AI Document Testing System - 快速启动             ║"
echo "║                                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 检查build目录中的脚本
if [[ -f "./build/start-local.sh" ]]; then
    echo -e "${BLUE}[INFO]${NC} 使用build目录中的启动脚本..."
    chmod +x ./build/start-local.sh
    ./build/start-local.sh "$@"
else
    echo -e "${YELLOW}[ERROR]${NC} 未找到 build/start-local.sh"
    echo "请确保构建脚本位于 build/ 目录中"
    exit 1
fi