#!/bin/bash

# AI文档测试系统 - 快速部署脚本
# 用于快速演示或测试部署，使用默认配置

set -e

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() { echo -e "${BLUE}ℹ️ $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️ $1${NC}"; }

echo -e "${BLUE}"
cat << 'EOF'
   ___    ____   ____    ____  
  /   |  /  _/  /  _ \  /  _ \ 
 / /| | / /   /  / / / / / / /
/ ___ |/ /   /  / / / / / / /  
/_/  |_/___/  /_/ /_/ /_/ /_/   

AI文档测试系统 - 快速部署
EOF
echo -e "${NC}"

print_info "开始快速部署..."

# 默认配置
REGISTRY="ghcr.io/wantiantian/ai_docs2"
VERSION="latest"
FRONTEND_PORT=3000
BACKEND_PORT=8080

# 创建必要目录
print_info "创建数据目录..."
mkdir -p data/{postgres,redis,uploads,reports} logs

# 生成快速部署的Docker Compose文件
print_info "生成Docker Compose配置..."
cat > docker-compose.quick.yml << EOF
version: '3.8'

services:
  backend:
    image: $REGISTRY/backend:$VERSION
    container_name: aidd-backend
    restart: unless-stopped
    ports:
      - "$BACKEND_PORT:8000"
    environment:
      - DATABASE_TYPE=sqlite
      - SQLITE_PATH=/app/data/app.db
      - CACHE_STRATEGY=memory
      - JWT_SECRET_KEY=quick-deploy-secret-key-change-in-production
      - ENVIRONMENT=development
      - DEBUG=true
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    networks:
      - aidd-network
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  frontend:
    image: $REGISTRY/frontend:$VERSION
    container_name: aidd-frontend
    restart: unless-stopped
    ports:
      - "$FRONTEND_PORT:80"
    environment:
      - REACT_APP_API_BASE_URL=http://localhost:$BACKEND_PORT
    depends_on:
      - backend
    networks:
      - aidd-network
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

networks:
  aidd-network:
    driver: bridge
EOF

# 检查Docker权限
if ! docker info >/dev/null 2>&1; then
    print_warning "检测到Docker权限问题，尝试使用sudo..."
    DOCKER_CMD="echo 'huawei1234' | sudo -S docker"
    COMPOSE_CMD="echo 'huawei1234' | sudo -S docker-compose"
else
    DOCKER_CMD="docker"
    COMPOSE_CMD="docker-compose"
fi

# 拉取镜像
print_info "拉取Docker镜像..."
echo 'huawei1234' | sudo -S docker pull $REGISTRY/backend:$VERSION
echo 'huawei1234' | sudo -S docker pull $REGISTRY/frontend:$VERSION

# 启动服务
print_info "启动服务..."
echo 'huawei1234' | sudo -S docker-compose -f docker-compose.quick.yml up -d

print_info "等待服务启动..."
sleep 30

# 健康检查
print_info "检查服务状态..."
if curl -f "http://localhost:$BACKEND_PORT/health" >/dev/null 2>&1; then
    print_success "后端服务运行正常"
else
    print_warning "后端服务可能还在启动中"
fi

if curl -f "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1; then
    print_success "前端服务运行正常"
else
    print_warning "前端服务可能还在启动中"
fi

echo ""
print_success "🎉 快速部署完成！"
echo ""
echo "📋 服务信息："
echo "🌐 前端地址: http://localhost:$FRONTEND_PORT"
echo "🔧 后端API: http://localhost:$BACKEND_PORT"
echo "📚 API文档: http://localhost:$BACKEND_PORT/docs"
echo ""
echo "📂 数据存储："
echo "📁 数据目录: $(pwd)/data"
echo "📋 日志目录: $(pwd)/logs"
echo ""
echo "🛠️ 管理命令："
echo "查看状态: docker-compose -f docker-compose.quick.yml ps"
echo "查看日志: docker-compose -f docker-compose.quick.yml logs -f"
echo "停止服务: docker-compose -f docker-compose.quick.yml down"
echo ""
echo "⚠️ 注意：此为快速演示版本，使用SQLite数据库，不适用于生产环境"
echo "生产环境请使用: ./deploy-from-github.sh"
EOF