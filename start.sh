#!/bin/bash

# AIDD (AI Document Detector) - 快速启动脚本

set -e

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}"
cat << "EOF"
    _    _____ _____  ____  
   / \  |_   _|  ___||  _ \ 
  / _ \   | | | |_   | | | |
 / ___ \  | | |  _|  | |_| |
/_/   \_\ |_| |_|    |____/ 

AI Document Detector - 快速启动
EOF
echo -e "${NC}"

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}❌ 未安装Docker，请先安装Docker${NC}"
    exit 1
fi

# 检查Docker Compose
DOCKER_COMPOSE=""
if docker compose version &> /dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    echo -e "${YELLOW}❌ 未安装Docker Compose，请先安装Docker Compose${NC}"
    exit 1
fi

echo -e "${BLUE}🚀 启动AIDD系统...${NC}"

# 创建默认环境文件
if [ ! -f .env ]; then
    echo -e "${YELLOW}📝 创建默认配置文件...${NC}"
    cat > .env << 'EOF'
# AIDD 开发环境配置
DATABASE_TYPE=sqlite
DATABASE_URL=sqlite:///app/data/app.db
REDIS_URL=redis://redis:6379/0

# 应用配置
DEBUG=true
ENVIRONMENT=development
LOG_LEVEL=INFO

# 端口配置
BACKEND_PORT=8000
FRONTEND_PORT=3000

# 安全配置 (开发环境默认值)
JWT_SECRET_KEY=dev-secret-key-change-in-production
OAUTH_CLIENT_SECRET=dev-oauth-secret

# AI服务配置 (请填入真实的API Key)
OPENAI_API_KEY=your-openai-api-key-here
EOF
fi

# 启动服务
$DOCKER_COMPOSE up -d

echo ""
echo -e "${GREEN}✅ AIDD系统启动完成！${NC}"
echo ""
echo "📋 访问地址:"
echo "   前端界面: http://localhost:3000"
echo "   后端API:  http://localhost:8000"
echo "   API文档:  http://localhost:8000/docs"
echo ""
echo "🔧 管理命令:"
echo "   查看日志: $DOCKER_COMPOSE logs -f"
echo "   停止系统: $DOCKER_COMPOSE down"
echo "   重启系统: $DOCKER_COMPOSE restart"
echo ""
echo -e "${YELLOW}💡 提示: 请编辑 .env 文件配置OpenAI API Key${NC}"