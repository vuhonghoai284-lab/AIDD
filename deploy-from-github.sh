#!/bin/bash

# AI文档测试系统 - 从GitHub一键部署脚本
# 自动从GitHub Container Registry获取预构建镜像并完成部署

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${BLUE}ℹ️ $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_header() { echo -e "${BLUE}🚀 $1${NC}"; }

# 默认配置
DEFAULT_VERSION="latest"
DEFAULT_REGISTRY="ghcr.io/wantiantian/ai_docs2"
DEFAULT_FRONTEND_PORT=3000
DEFAULT_BACKEND_PORT=8080
DEFAULT_POSTGRES_PORT=5432
DEFAULT_REDIS_PORT=6379

# 配置变量
VERSION=${VERSION:-$DEFAULT_VERSION}
REGISTRY=${REGISTRY:-$DEFAULT_REGISTRY}
FRONTEND_PORT=${FRONTEND_PORT:-$DEFAULT_FRONTEND_PORT}
BACKEND_PORT=${BACKEND_PORT:-$DEFAULT_BACKEND_PORT}
POSTGRES_PORT=${POSTGRES_PORT:-$DEFAULT_POSTGRES_PORT}
REDIS_PORT=${REDIS_PORT:-$DEFAULT_REDIS_PORT}
ENVIRONMENT=${ENVIRONMENT:-production}
DATA_PATH=${DATA_PATH:-./data}
LOG_PATH=${LOG_PATH:-./logs}
CONFIG_PATH=${CONFIG_PATH:-./config.yaml}

show_help() {
    cat << EOF
AI文档测试系统 - 从GitHub一键部署脚本

用法: $0 [选项]

选项:
  --version VERSION        指定镜像版本 (默认: latest)
  --registry REGISTRY      指定镜像仓库 (默认: ghcr.io/wantiantian/ai_docs2)
  --frontend-port PORT     前端服务端口 (默认: 3000)
  --backend-port PORT      后端服务端口 (默认: 8080)
  --postgres-port PORT     PostgreSQL端口 (默认: 5432)
  --redis-port PORT        Redis端口 (默认: 6379)
  --data-path PATH         数据存储路径 (默认: ./data)
  --log-path PATH          日志存储路径 (默认: ./logs)
  --config-path PATH       配置文件路径 (默认: ./config.yaml)
  --skip-config            跳过配置文件生成，使用现有配置
  --stop                   停止并删除所有服务
  --restart                重启所有服务
  --status                 查看服务状态
  --logs [SERVICE]         查看服务日志 (可选指定服务名)
  --update                 更新到最新版本
  -h, --help              显示帮助信息

环境变量:
  VERSION                  镜像版本
  REGISTRY                 镜像仓库地址
  ENVIRONMENT              运行环境 (production/staging)
  FRONTEND_PORT            前端端口
  BACKEND_PORT             后端端口
  DATA_PATH                数据路径
  LOG_PATH                 日志路径
  CONFIG_PATH              配置文件路径

示例:
  # 默认部署
  $0

  # 指定版本部署
  $0 --version v2.0.0

  # 自定义端口部署
  $0 --frontend-port 8080 --backend-port 9000

  # 查看服务状态
  $0 --status

  # 查看后端日志
  $0 --logs backend

  # 更新服务
  $0 --update

  # 停止服务
  $0 --stop
EOF
}

# 解析命令行参数
SKIP_CONFIG=false
ACTION="deploy"

while [[ $# -gt 0 ]]; do
    case $1 in
        --version)
            VERSION="$2"
            shift 2
            ;;
        --registry)
            REGISTRY="$2"
            shift 2
            ;;
        --frontend-port)
            FRONTEND_PORT="$2"
            shift 2
            ;;
        --backend-port)
            BACKEND_PORT="$2"
            shift 2
            ;;
        --postgres-port)
            POSTGRES_PORT="$2"
            shift 2
            ;;
        --redis-port)
            REDIS_PORT="$2"
            shift 2
            ;;
        --data-path)
            DATA_PATH="$2"
            shift 2
            ;;
        --log-path)
            LOG_PATH="$2"
            shift 2
            ;;
        --config-path)
            CONFIG_PATH="$2"
            shift 2
            ;;
        --skip-config)
            SKIP_CONFIG=true
            shift
            ;;
        --stop)
            ACTION="stop"
            shift
            ;;
        --restart)
            ACTION="restart"
            shift
            ;;
        --status)
            ACTION="status"
            shift
            ;;
        --logs)
            ACTION="logs"
            SERVICE="$2"
            if [[ "$SERVICE" != "--"* && -n "$SERVICE" ]]; then
                shift 2
            else
                SERVICE=""
                shift
            fi
            ;;
        --update)
            ACTION="update"
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            print_error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

# 检查Docker环境
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi

    # 检查Docker是否运行
    if ! docker info &> /dev/null; then
        print_error "Docker 服务未运行，请先启动 Docker 服务"
        exit 1
    fi
}

# 创建必要目录
create_directories() {
    print_info "创建必要的目录..."
    
    mkdir -p "$DATA_PATH"/{postgres,redis,uploads,reports}
    mkdir -p "$LOG_PATH"
    
    # 设置目录权限
    chmod 755 "$DATA_PATH"
    chmod 755 "$LOG_PATH"
    
    print_success "目录创建完成"
}

# 生成环境变量文件
generate_env_file() {
    if [[ "$SKIP_CONFIG" == "true" && -f ".env" ]]; then
        print_info "跳过环境变量文件生成，使用现有 .env 文件"
        return
    fi

    print_info "生成环境变量文件..."
    
    # 生成随机密码
    POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    JWT_SECRET_KEY=$(openssl rand -base64 64 | tr -d "=+/" | cut -c1-50)
    
    cat > .env << EOF
# AI文档测试系统 - 部署配置
# 自动生成于: $(date)

# 应用版本和镜像
VERSION=$VERSION
REGISTRY=$REGISTRY
ENVIRONMENT=$ENVIRONMENT

# 服务端口配置
FRONTEND_PORT=$FRONTEND_PORT
BACKEND_PORT=$BACKEND_PORT
POSTGRES_PORT=$POSTGRES_PORT
REDIS_PORT=$REDIS_PORT

# 数据库配置
DATABASE_TYPE=postgresql
POSTGRES_HOST=postgres
POSTGRES_USER=aidd_user
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
POSTGRES_DB=aidd_db

# Redis配置
REDIS_HOST=redis
REDIS_PASSWORD=

# 路径配置
DATA_PATH=$DATA_PATH
LOG_PATH=$LOG_PATH
CONFIG_PATH=$CONFIG_PATH

# 安全配置
JWT_SECRET_KEY=$JWT_SECRET_KEY

# AI服务配置 (请根据需要填入)
OPENAI_API_KEY=sk-your-openai-api-key-here
BAIDU_API_KEY=your-baidu-api-key-here

# OAuth配置 (请根据需要填入)
OAUTH_CLIENT_ID=your-oauth-client-id
OAUTH_CLIENT_SECRET=your-oauth-client-secret
FRONTEND_DOMAIN=http://localhost:$FRONTEND_PORT

# Docker资源限制
BACKEND_MEMORY_LIMIT=2G
BACKEND_CPU_LIMIT=2
FRONTEND_MEMORY_LIMIT=512M
FRONTEND_CPU_LIMIT=1
POSTGRES_MEMORY_LIMIT=1G
POSTGRES_CPU_LIMIT=2
REDIS_MEMORY_LIMIT=512M
REDIS_CPU_LIMIT=1
EOF

    print_success "环境变量文件已生成: .env"
    print_warning "请编辑 .env 文件，填入正确的 API 密钥和 OAuth 配置"
}

# 生成配置文件
generate_config_file() {
    if [[ "$SKIP_CONFIG" == "true" && -f "$CONFIG_PATH" ]]; then
        print_info "跳过配置文件生成，使用现有配置文件: $CONFIG_PATH"
        return
    fi

    print_info "生成应用配置文件..."
    
    cat > "$CONFIG_PATH" << EOF
# AI文档测试系统 - 应用配置文件
# 自动生成于: $(date)

server:
  host: "0.0.0.0"
  port: 8000
  debug: \${DEBUG:false}
  workers: \${WORKERS:4}
  external_host: \${EXTERNAL_HOST:localhost}
  external_port: \${EXTERNAL_PORT:$BACKEND_PORT}
  external_protocol: \${EXTERNAL_PROTOCOL:http}

database:
  type: \${DATABASE_TYPE:postgresql}
  postgresql:
    host: \${POSTGRES_HOST:postgres}
    port: \${POSTGRES_PORT:5432}
    username: \${POSTGRES_USER:aidd_user}
    password: \${POSTGRES_PASSWORD}
    database: \${POSTGRES_DB:aidd_db}
    pool_size: \${DB_POOL_SIZE:20}
    max_overflow: \${DB_MAX_OVERFLOW:10}

cache:
  strategy: \${CACHE_STRATEGY:redis}
  redis:
    host: \${REDIS_HOST:redis}
    port: \${REDIS_PORT:6379}
    password: \${REDIS_PASSWORD:}
    database: \${REDIS_DATABASE:0}
    max_connections: \${REDIS_MAX_CONNECTIONS:50}

ai_models:
  default_index: 0
  models:
    - label: "GPT-4o Mini (快速)"
      provider: "openai"
      config:
        api_key: \${OPENAI_API_KEY}
        base_url: "https://api.openai.com/v1"
        model: "gpt-4o-mini"
        timeout: 60
        max_retries: 3
    - label: "Baidu Ernie (官方)"
      provider: "baidu"
      config:
        api_key: \${BAIDU_API_KEY}
        model: "ernie-speed-pro-128k"
        timeout: 60
        max_retries: 3

jwt:
  secret_key: \${JWT_SECRET_KEY}
  algorithm: "HS256"
  access_token_expire_minutes: 30
  refresh_token_expire_days: 7

third_party_auth:
  provider_type: "gitee"
  client_id: \${OAUTH_CLIENT_ID}
  client_secret: \${OAUTH_CLIENT_SECRET}
  frontend_domain: \${FRONTEND_DOMAIN}
  scope: "user_info"

file_upload:
  max_file_size: 10485760  # 10MB
  allowed_extensions: [".pdf", ".docx", ".md", ".txt"]
  upload_path: "./data/uploads"

logging:
  level: \${LOG_LEVEL:INFO}
  file: \${LOG_FILE:./logs/app.log}
  max_file_size: 10485760  # 10MB
  backup_count: 5

monitoring:
  enable_metrics: \${ENABLE_METRICS:true}
  metrics_port: \${METRICS_PORT:9090}
EOF

    print_success "应用配置文件已生成: $CONFIG_PATH"
}

# 生成Docker Compose文件
generate_docker_compose() {
    print_info "生成Docker Compose配置文件..."
    
    cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  # 后端服务
  backend:
    image: ${REGISTRY}/backend:${VERSION}
    container_name: aidd-backend
    restart: unless-stopped
    ports:
      - "${BACKEND_PORT}:8000"
    environment:
      - CONFIG_FILE=${CONFIG_PATH}
      - PYTHONPATH=/app
      - WAIT_FOR_DB=true
      - RUN_MIGRATIONS=true
      - VERSION=${VERSION}
      - ENVIRONMENT=${ENVIRONMENT}
    env_file:
      - .env
    volumes:
      - ${CONFIG_PATH}:/app/config.yaml:ro
      - ${DATA_PATH}:/app/data
      - ${LOG_PATH}:/app/logs
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - aidd-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    deploy:
      resources:
        limits:
          memory: ${BACKEND_MEMORY_LIMIT}
          cpus: '${BACKEND_CPU_LIMIT}'
        reservations:
          memory: 512M
          cpus: '0.5'

  # 前端服务
  frontend:
    image: ${REGISTRY}/frontend:${VERSION}
    container_name: aidd-frontend
    restart: unless-stopped
    ports:
      - "${FRONTEND_PORT}:80"
    environment:
      - VERSION=${VERSION}
      - ENVIRONMENT=${ENVIRONMENT}
      - BACKEND_URL=http://localhost:${BACKEND_PORT}
    depends_on:
      backend:
        condition: service_healthy
    networks:
      - aidd-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/health"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 30s
    deploy:
      resources:
        limits:
          memory: ${FRONTEND_MEMORY_LIMIT}
          cpus: '${FRONTEND_CPU_LIMIT}'
        reservations:
          memory: 128M
          cpus: '0.1'

  # PostgreSQL数据库
  postgres:
    image: postgres:15-alpine
    container_name: aidd-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_INITDB_ARGS=--auth-host=md5
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "${POSTGRES_PORT}:5432"
    networks:
      - aidd-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    deploy:
      resources:
        limits:
          memory: ${POSTGRES_MEMORY_LIMIT}
          cpus: '${POSTGRES_CPU_LIMIT}'
        reservations:
          memory: 256M
          cpus: '0.25'

  # Redis缓存
  redis:
    image: redis:7-alpine
    container_name: aidd-redis
    restart: unless-stopped
    command: >
      redis-server
      --appendonly yes
      --appendfsync everysec
      --maxmemory ${REDIS_MEMORY_LIMIT:-512mb}
      --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    ports:
      - "${REDIS_PORT}:6379"
    networks:
      - aidd-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3
      start_period: 10s
    deploy:
      resources:
        limits:
          memory: ${REDIS_MEMORY_LIMIT}
          cpus: '${REDIS_CPU_LIMIT}'
        reservations:
          memory: 64M
          cpus: '0.1'

# 数据卷
volumes:
  postgres_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: ${DATA_PATH}/postgres

  redis_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: ${DATA_PATH}/redis

# 网络
networks:
  aidd-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
EOF

    print_success "Docker Compose配置文件已生成: docker-compose.yml"
}

# 拉取最新镜像
pull_images() {
    print_info "从GitHub Container Registry拉取镜像..."
    
    # 拉取后端镜像
    print_info "拉取后端镜像: $REGISTRY/backend:$VERSION"
    if docker pull "$REGISTRY/backend:$VERSION"; then
        print_success "后端镜像拉取成功"
    else
        print_error "后端镜像拉取失败，请检查镜像是否存在"
        print_info "可用的镜像版本可以在 GitHub Packages 中查看"
        exit 1
    fi
    
    # 拉取前端镜像
    print_info "拉取前端镜像: $REGISTRY/frontend:$VERSION"
    if docker pull "$REGISTRY/frontend:$VERSION"; then
        print_success "前端镜像拉取成功"
    else
        print_error "前端镜像拉取失败，请检查镜像是否存在"
        exit 1
    fi
    
    # 拉取依赖镜像
    print_info "拉取依赖镜像..."
    docker pull postgres:15-alpine
    docker pull redis:7-alpine
    
    print_success "所有镜像拉取完成"
}

# 启动服务
start_services() {
    print_info "启动所有服务..."
    
    # 启动服务
    docker-compose up -d
    
    print_success "服务启动命令已执行"
    print_info "等待服务就绪..."
    
    # 等待服务启动
    local max_wait=180
    local wait_time=0
    
    while [ $wait_time -lt $max_wait ]; do
        if docker-compose ps | grep -q "Up.*healthy.*aidd-backend"; then
            print_success "后端服务已就绪"
            break
        fi
        
        echo -n "."
        sleep 5
        wait_time=$((wait_time + 5))
    done
    
    if [ $wait_time -ge $max_wait ]; then
        print_warning "服务启动时间较长，请检查日志"
        print_info "运行 '$0 --logs' 查看详细日志"
    fi
}

# 健康检查
health_check() {
    print_info "进行服务健康检查..."
    
    # 检查后端健康状态
    if curl -f "http://localhost:$BACKEND_PORT/health" >/dev/null 2>&1; then
        print_success "✅ 后端服务健康检查通过"
    else
        print_error "❌ 后端服务健康检查失败"
        print_info "请检查服务日志: $0 --logs backend"
    fi
    
    # 检查前端健康状态
    if curl -f "http://localhost:$FRONTEND_PORT/health" >/dev/null 2>&1; then
        print_success "✅ 前端服务健康检查通过"
    else
        # 前端可能没有health端点，检查主页
        if curl -f "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1; then
            print_success "✅ 前端服务可访问"
        else
            print_error "❌ 前端服务健康检查失败"
            print_info "请检查服务日志: $0 --logs frontend"
        fi
    fi
    
    # 检查数据库连接
    if docker-compose exec -T postgres pg_isready -U aidd_user >/dev/null 2>&1; then
        print_success "✅ PostgreSQL数据库连接正常"
    else
        print_error "❌ PostgreSQL数据库连接失败"
    fi
    
    # 检查Redis连接
    if docker-compose exec -T redis redis-cli ping >/dev/null 2>&1; then
        print_success "✅ Redis缓存连接正常"
    else
        print_error "❌ Redis缓存连接失败"
    fi
}

# 显示服务状态
show_status() {
    print_header "AI文档测试系统 - 服务状态"
    echo ""
    
    print_info "Docker Compose 服务状态:"
    docker-compose ps
    
    echo ""
    print_info "服务访问地址:"
    echo "🌐 前端地址: http://localhost:$FRONTEND_PORT"
    echo "🔧 后端API: http://localhost:$BACKEND_PORT"
    echo "🗄️ PostgreSQL: localhost:$POSTGRES_PORT"
    echo "💾 Redis: localhost:$REDIS_PORT"
    
    echo ""
    print_info "数据存储位置:"
    echo "📁 数据目录: $(realpath "$DATA_PATH")"
    echo "📋 日志目录: $(realpath "$LOG_PATH")"
    echo "⚙️ 配置文件: $(realpath "$CONFIG_PATH")"
}

# 显示日志
show_logs() {
    if [[ -n "$SERVICE" ]]; then
        print_info "显示 $SERVICE 服务日志:"
        docker-compose logs -f "$SERVICE"
    else
        print_info "显示所有服务日志:"
        docker-compose logs -f
    fi
}

# 停止服务
stop_services() {
    print_info "停止并删除所有服务..."
    docker-compose down -v
    print_success "服务已停止"
}

# 重启服务
restart_services() {
    print_info "重启所有服务..."
    docker-compose restart
    print_success "服务已重启"
    
    # 等待服务就绪
    sleep 10
    health_check
}

# 更新服务
update_services() {
    print_info "更新服务到最新版本..."
    
    # 拉取最新镜像
    pull_images
    
    # 重新创建服务
    docker-compose up -d --force-recreate
    
    print_success "服务更新完成"
    
    # 等待服务就绪
    sleep 15
    health_check
}

# 部署完成信息
show_completion_info() {
    echo ""
    print_success "🎉 AI文档测试系统部署完成！"
    echo ""
    echo "📋 访问信息："
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🌐 前端应用: http://localhost:$FRONTEND_PORT"
    echo "🔧 后端API: http://localhost:$BACKEND_PORT"
    echo "📚 API文档: http://localhost:$BACKEND_PORT/docs"
    echo ""
    echo "📂 数据存储："
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📁 数据目录: $(realpath "$DATA_PATH")"
    echo "📋 日志目录: $(realpath "$LOG_PATH")"
    echo "⚙️ 配置文件: $(realpath "$CONFIG_PATH")"
    echo ""
    echo "🛠️ 常用命令："
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "查看状态: $0 --status"
    echo "查看日志: $0 --logs"
    echo "重启服务: $0 --restart"
    echo "更新服务: $0 --update"
    echo "停止服务: $0 --stop"
    echo ""
    echo "⚠️ 重要提醒："
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "请编辑 .env 文件，填入正确的 API 密钥和 OAuth 配置"
    echo "首次运行可能需要几分钟时间进行数据库初始化"
}

# 主要执行逻辑
main() {
    print_header "AI文档测试系统 - GitHub镜像一键部署"
    echo "版本: $VERSION | 镜像仓库: $REGISTRY"
    echo ""
    
    case $ACTION in
        "deploy")
            check_docker
            create_directories
            generate_env_file
            generate_config_file
            generate_docker_compose
            pull_images
            start_services
            health_check
            show_completion_info
            ;;
        "stop")
            stop_services
            ;;
        "restart")
            restart_services
            ;;
        "status")
            show_status
            ;;
        "logs")
            show_logs
            ;;
        "update")
            update_services
            ;;
        *)
            print_error "未知操作: $ACTION"
            show_help
            exit 1
            ;;
    esac
}

# 脚本入口
main "$@"