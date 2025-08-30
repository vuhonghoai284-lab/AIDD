#!/bin/bash

# AIDD - 本机构建和部署脚本
# 完全不依赖GitHub Actions，在本机完成构建、测试和部署

set -e

# 配置变量
PROJECT_NAME="aidd"
VERSION=${VERSION:-"local-$(date +%Y%m%d-%H%M%S)"}
LOCAL_REGISTRY=${LOCAL_REGISTRY:-"local"}
BUILD_ONLY=${BUILD_ONLY:-false}

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${PURPLE}[STEP]${NC} $1"
}

# 显示LOGO
show_banner() {
    echo -e "${BLUE}"
    cat << "EOF"
╔═══════════════════════════════════════╗
║          AIDD 本机构建部署             ║
║     AI Document Detector v2.0         ║
║                                       ║
║     🏗️  本机构建 Docker 镜像          ║
║     🚀 一键部署到本地环境             ║
║     📦 无需外部依赖                   ║
╚═══════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

# 显示帮助信息
show_help() {
    cat << EOF
AIDD 本机构建部署脚本

用法: $0 [选项] [动作]

选项:
  -v, --version VERSION    指定版本标签 (默认: local-YYYYMMDD-HHMMSS)
  -r, --registry REGISTRY  本地镜像标签前缀 (默认: local)
  -b, --build-only         仅构建镜像，不启动服务
  -c, --clean             构建前清理旧镜像
  -t, --test              构建后运行测试
  -p, --production        使用生产环境配置
  -h, --help              显示此帮助信息

动作:
  build                   构建所有镜像 (默认)
  deploy                  构建并部署服务
  start                   启动已构建的服务
  stop                    停止服务
  restart                 重启服务
  clean                   清理镜像和容器
  test                    运行测试
  logs                    查看日志
  status                  查看状态

环境变量:
  VERSION                 镜像版本标签
  LOCAL_REGISTRY         本地镜像标签前缀
  BUILD_ONLY             仅构建模式
  ENVIRONMENT            环境类型 (dev/prod)

示例:
  $0                      # 构建并部署开发环境
  $0 -p deploy            # 构建并部署生产环境
  $0 -b build             # 仅构建镜像
  $0 -t deploy            # 构建、部署并测试
  $0 clean                # 清理所有资源
  $0 logs                 # 查看运行日志

快速开始:
  $0 deploy               # 一键构建并部署
EOF
}

# 检查环境依赖
check_environment() {
    log_step "检查环境依赖..."
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    # 检查Docker服务
    if ! docker info &> /dev/null; then
        log_error "Docker服务未启动，请启动Docker服务"
        exit 1
    fi
    
    # 检查Docker Compose
    if docker compose version &> /dev/null 2>&1; then
        DOCKER_COMPOSE="docker compose"
    elif command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE="docker-compose"
    else
        log_error "Docker Compose未安装，请安装Docker Compose"
        exit 1
    fi
    
    log_success "环境检查通过"
    
    # 显示环境信息
    echo "  Docker版本: $(docker --version)"
    echo "  Compose版本: $($DOCKER_COMPOSE --version)"
    echo "  可用内存: $(free -h | awk '/^Mem:/ {print $7}')"
    echo "  可用磁盘: $(df -h . | awk 'NR==2 {print $4}')"
}

# 创建构建环境
setup_build_environment() {
    log_step "准备构建环境..."
    
    # 创建构建目录
    mkdir -p ./build-logs
    mkdir -p ./build-cache
    
    # 设置环境变量
    export DOCKER_BUILDKIT=1
    export COMPOSE_DOCKER_CLI_BUILD=1
    
    # 创建构建配置
    cat > ./build-config.env << EOF
# 本机构建配置
BUILD_TIME=$(date -Iseconds)
BUILD_VERSION=$VERSION
BUILD_HOST=$(hostname)
BUILD_USER=$(whoami)
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
EOF
    
    log_success "构建环境已准备"
}

# 构建后端镜像
build_backend() {
    log_step "构建后端镜像..."
    
    local image_tag="${LOCAL_REGISTRY}/${PROJECT_NAME}-backend:${VERSION}"
    local latest_tag="${LOCAL_REGISTRY}/${PROJECT_NAME}-backend:latest"
    
    echo "构建镜像: $image_tag"
    
    # 构建参数
    docker build \
        --build-arg BUILD_VERSION="$VERSION" \
        --build-arg BUILD_TIME="$(date -Iseconds)" \
        --build-arg GIT_COMMIT="$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')" \
        --tag "$image_tag" \
        --tag "$latest_tag" \
        --file ./backend/Dockerfile \
        --progress=plain \
        ./backend/ 2>&1 | tee ./build-logs/backend-build.log
    
    if [ $? -eq 0 ]; then
        log_success "后端镜像构建成功: $image_tag"
        echo "  镜像大小: $(docker images --format 'table {{.Size}}' "$image_tag" | tail -n 1)"
    else
        log_error "后端镜像构建失败"
        exit 1
    fi
}

# 构建前端镜像
build_frontend() {
    log_step "构建前端镜像..."
    
    local image_tag="${LOCAL_REGISTRY}/${PROJECT_NAME}-frontend:${VERSION}"
    local latest_tag="${LOCAL_REGISTRY}/${PROJECT_NAME}-frontend:latest"
    
    echo "构建镜像: $image_tag"
    
    # 构建参数
    docker build \
        --build-arg BUILD_VERSION="$VERSION" \
        --build-arg BUILD_TIME="$(date -Iseconds)" \
        --tag "$image_tag" \
        --tag "$latest_tag" \
        --file ./frontend/Dockerfile \
        --progress=plain \
        ./frontend/ 2>&1 | tee ./build-logs/frontend-build.log
    
    if [ $? -eq 0 ]; then
        log_success "前端镜像构建成功: $image_tag"
        echo "  镜像大小: $(docker images --format 'table {{.Size}}' "$image_tag" | tail -n 1)"
    else
        log_error "前端镜像构建失败"
        exit 1
    fi
}

# 运行镜像测试
test_images() {
    log_step "测试构建的镜像..."
    
    local backend_image="${LOCAL_REGISTRY}/${PROJECT_NAME}-backend:${VERSION}"
    local frontend_image="${LOCAL_REGISTRY}/${PROJECT_NAME}-frontend:${VERSION}"
    
    # 测试后端镜像
    echo "测试后端镜像..."
    if docker run --rm "$backend_image" python -c "
import sys
print(f'Python版本: {sys.version}')
print('后端镜像测试通过 ✓')
" 2>/dev/null; then
        log_success "后端镜像测试通过"
    else
        log_error "后端镜像测试失败"
        return 1
    fi
    
    # 测试前端镜像
    echo "测试前端镜像..."
    if docker run --rm "$frontend_image" nginx -t 2>/dev/null; then
        log_success "前端镜像测试通过"
    else
        log_error "前端镜像测试失败"
        return 1
    fi
    
    # 检查镜像信息
    echo ""
    log_info "镜像信息:"
    docker images | grep "${LOCAL_REGISTRY}/${PROJECT_NAME}" | head -10
}

# 创建部署配置
create_deployment_config() {
    log_step "创建部署配置..."
    
    local env_file=".env.local"
    local compose_file="docker-compose.local.yml"
    local db_type=${DATABASE_TYPE:-sqlite}
    
    # 生成数据库配置
    generate_database_config() {
        case $db_type in
            mysql)
                local mysql_password=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-16)
                cat << EOF
# MySQL数据库配置
DATABASE_TYPE=mysql
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_USERNAME=aidd
MYSQL_PASSWORD=$mysql_password
MYSQL_DATABASE=aidd_db
DATABASE_URL=mysql://aidd:$mysql_password@mysql:3306/aidd_db
EOF
                ;;
            postgresql)
                local pg_password=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-16)
                cat << EOF
# PostgreSQL数据库配置
DATABASE_TYPE=postgresql
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=aidd
POSTGRES_PASSWORD=$pg_password
POSTGRES_DB=aidd_db
DATABASE_URL=postgresql://aidd:$pg_password@postgres:5432/aidd_db
EOF
                ;;
            sqlite|*)
                cat << EOF
# SQLite数据库配置
DATABASE_TYPE=sqlite
DATABASE_URL=sqlite:///app/data/app.db
EOF
                ;;
        esac
    }
    
    # 创建环境配置文件
    cat > "$env_file" << EOF
# AIDD 本机部署配置
# 生成时间: $(date)

# 基础配置
PROJECT_NAME=$PROJECT_NAME
VERSION=$VERSION
ENVIRONMENT=${ENVIRONMENT:-development}

# 数据库配置
$(generate_database_config)

# Redis配置
REDIS_URL=redis://redis:6379/0

# 应用配置
DEBUG=true
LOG_LEVEL=INFO
BACKEND_PORT=8080
FRONTEND_PORT=3000

# 安全配置 (请修改)
JWT_SECRET_KEY=local-dev-key-$(openssl rand -hex 16)
OAUTH_CLIENT_SECRET=local-oauth-secret

# AI服务配置
OPENAI_API_KEY=${OPENAI_API_KEY:-your-openai-api-key-here}

# Docker镜像配置
BACKEND_IMAGE=${LOCAL_REGISTRY}/${PROJECT_NAME}-backend:${VERSION}
FRONTEND_IMAGE=${LOCAL_REGISTRY}/${PROJECT_NAME}-frontend:${VERSION}
EOF

    # 创建Docker Compose文件
    cat > "$compose_file" << 'EOF'
version: '3.8'

services:
  # 后端服务
  backend:
    image: ${BACKEND_IMAGE}
    container_name: ${PROJECT_NAME}-backend
    restart: unless-stopped
    ports:
      - "${BACKEND_PORT}:8000"
    environment:
      - CONFIG_FILE=/app/config.yaml
      - ENVIRONMENT=${ENVIRONMENT}
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - PYTHONPATH=/app
      - DEBUG=${DEBUG}
      - LOG_LEVEL=${LOG_LEVEL}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - backend_data:/app/data
      - backend_logs:/app/logs
      - ./backend/config.yaml:/app/config.yaml:ro
    depends_on:
      - redis
    networks:
      - aidd-local-network
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # 前端服务
  frontend:
    image: ${FRONTEND_IMAGE}
    container_name: ${PROJECT_NAME}-frontend
    restart: unless-stopped
    ports:
      - "${FRONTEND_PORT}:80"
    depends_on:
      - backend
    networks:
      - aidd-local-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/"]
      interval: 30s
      timeout: 3s
      retries: 3

  # Redis服务
  redis:
    image: redis:7-alpine
    container_name: ${PROJECT_NAME}-redis
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - aidd-local-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

volumes:
  backend_data:
    driver: local
  backend_logs:
    driver: local
  redis_data:
    driver: local

networks:
  aidd-local-network:
    driver: bridge
EOF
    
    log_success "部署配置已创建"
    echo "  环境文件: $env_file"
    echo "  Compose文件: $compose_file"
}

# 部署服务
deploy_services() {
    log_step "部署服务..."
    
    local env_file=".env.local"
    local compose_file="docker-compose.local.yml"
    
    # 启动服务
    $DOCKER_COMPOSE -f "$compose_file" --env-file "$env_file" up -d
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 15
    
    # 检查服务状态
    if check_service_health; then
        log_success "服务部署成功！"
        show_access_info
    else
        log_error "服务部署失败，请检查日志"
        show_logs
    fi
}

# 检查服务健康状态
check_service_health() {
    local max_attempts=30
    local attempt=0
    
    log_info "检查服务健康状态..."
    
    while [ $attempt -lt $max_attempts ]; do
        # 检查后端健康状态
        if curl -s -f "http://localhost:8080/health" >/dev/null 2>&1; then
            log_success "后端服务健康 ✓"
            
            # 检查前端健康状态
            if curl -s -f "http://localhost:3000/" >/dev/null 2>&1; then
                log_success "前端服务健康 ✓"
                return 0
            fi
        fi
        
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    log_warning "服务健康检查超时"
    return 1
}

# 显示访问信息
show_access_info() {
    cat << EOF

${GREEN}🎉 AIDD 部署成功！${NC}

📋 访问地址:
  🌐 前端界面: http://localhost:3000
  🔧 后端API:  http://localhost:8080
  📚 API文档:  http://localhost:8080/docs
  📊 健康检查: http://localhost:8080/health

🛠️ 管理命令:
  查看状态:   $0 status
  查看日志:   $0 logs
  重启服务:   $0 restart
  停止服务:   $0 stop
  清理资源:   $0 clean

📁 数据文件:
  环境配置:   .env.local
  Compose:   docker-compose.local.yml
  构建日志:   ./build-logs/

${YELLOW}💡 提示:${NC}
  - 首次启动可能需要几分钟初始化数据库
  - 请在 .env.local 中配置 OPENAI_API_KEY
  - 数据将持久保存在 Docker 卷中

EOF
}

# 显示日志
show_logs() {
    log_info "显示服务日志..."
    $DOCKER_COMPOSE -f "docker-compose.local.yml" --env-file ".env.local" logs -f --tail=50
}

# 显示状态
show_status() {
    log_info "服务状态:"
    $DOCKER_COMPOSE -f "docker-compose.local.yml" --env-file ".env.local" ps
    
    echo ""
    log_info "系统资源使用:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" \
        $(docker ps --format "{{.Names}}" | grep "${PROJECT_NAME}" | head -5)
}

# 停止服务
stop_services() {
    log_step "停止服务..."
    $DOCKER_COMPOSE -f "docker-compose.local.yml" --env-file ".env.local" down
    log_success "服务已停止"
}

# 重启服务
restart_services() {
    log_step "重启服务..."
    stop_services
    sleep 3
    deploy_services
}

# 清理资源
clean_resources() {
    log_step "清理资源..."
    
    # 停止服务
    if [ -f "docker-compose.local.yml" ]; then
        $DOCKER_COMPOSE -f "docker-compose.local.yml" --env-file ".env.local" down -v 2>/dev/null || true
    fi
    
    # 清理镜像
    log_info "清理本地构建的镜像..."
    docker images | grep "${LOCAL_REGISTRY}/${PROJECT_NAME}" | awk '{print $3}' | xargs docker rmi -f 2>/dev/null || true
    
    # 清理构建缓存
    log_info "清理构建缓存..."
    rm -rf ./build-logs ./build-cache ./build-config.env
    
    # 清理配置文件
    rm -f .env.local docker-compose.local.yml
    
    # 清理Docker资源
    docker system prune -f
    
    log_success "资源清理完成"
}

# 主函数
main() {
    local action="build"
    local clean_before_build=false
    local run_tests=false
    local production=false
    
    # 显示banner
    show_banner
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -v|--version)
                VERSION="$2"
                shift 2
                ;;
            -r|--registry)
                LOCAL_REGISTRY="$2"
                shift 2
                ;;
            -b|--build-only)
                BUILD_ONLY=true
                shift
                ;;
            -c|--clean)
                clean_before_build=true
                shift
                ;;
            -t|--test)
                run_tests=true
                shift
                ;;
            -p|--production)
                production=true
                ENVIRONMENT="production"
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            build|deploy|start|stop|restart|clean|test|logs|status)
                action="$1"
                shift
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 显示配置信息
    echo "🔧 构建配置:"
    echo "  项目名称: $PROJECT_NAME"
    echo "  版本标签: $VERSION"
    echo "  镜像前缀: $LOCAL_REGISTRY"
    echo "  环境类型: ${ENVIRONMENT:-development}"
    echo "  仅构建:   $BUILD_ONLY"
    echo ""
    
    # 检查环境
    check_environment
    
    # 执行动作
    case $action in
        build)
            if [ "$clean_before_build" = true ]; then
                clean_resources
            fi
            setup_build_environment
            build_backend
            build_frontend
            if [ "$run_tests" = true ]; then
                test_images
            fi
            log_success "镜像构建完成！"
            echo ""
            echo "下一步: $0 deploy  # 部署服务"
            ;;
        deploy)
            if [ "$clean_before_build" = true ]; then
                clean_resources
            fi
            setup_build_environment
            build_backend
            build_frontend
            if [ "$run_tests" = true ]; then
                test_images
            fi
            if [ "$BUILD_ONLY" = false ]; then
                create_deployment_config
                deploy_services
            fi
            ;;
        start)
            if [ ! -f "docker-compose.local.yml" ]; then
                log_error "找不到部署配置，请先运行: $0 deploy"
                exit 1
            fi
            create_deployment_config
            deploy_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        clean)
            clean_resources
            ;;
        test)
            test_images
            ;;
        logs)
            show_logs
            ;;
        status)
            show_status
            ;;
        *)
            log_error "未知动作: $action"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"