#!/bin/bash

# AI文档测试系统 - 本地Docker构建部署脚本
# 基于用户配置文件一键构建和部署

set -e

# 默认配置文件
CONFIG_FILE="deploy-config.yaml"
DOCKER_COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo -e "${BLUE}🚀 $1${NC}"
}

# 显示帮助信息
show_help() {
    cat << EOF
AI文档测试系统 - Docker部署工具

用法:
  $0 [选项]

选项:
  -c, --config FILE     指定配置文件 (默认: deploy-config.yaml)
  -f, --force          强制重新构建镜像
  -d, --down           停止并删除所有服务
  --logs               查看服务日志
  --status             查看服务状态
  -h, --help           显示此帮助信息

示例:
  $0                   # 使用默认配置部署
  $0 -c my-config.yaml # 使用自定义配置部署
  $0 --force           # 强制重新构建部署
  $0 --down            # 停止所有服务
  $0 --logs            # 查看日志
EOF
}

# 检查依赖
check_dependencies() {
    print_info "检查依赖..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    if ! command -v docker compose &> /dev/null; then
        if ! command -v docker-compose &> /dev/null; then
            print_error "Docker Compose 未安装，请先安装 Docker Compose"
            exit 1
        else
            DOCKER_COMPOSE_CMD="docker-compose"
        fi
    else
        DOCKER_COMPOSE_CMD="docker compose"
    fi
    
    if ! command -v yq &> /dev/null; then
        print_warning "yq 未安装，将使用简化的配置解析"
        USE_YQ=false
    else
        USE_YQ=true
    fi
    
    print_success "依赖检查完成"
}

# 解析YAML配置（简化版）
parse_config_simple() {
    local config_file="$1"
    
    if [[ ! -f "$config_file" ]]; then
        print_error "配置文件不存在: $config_file"
        exit 1
    fi
    
    print_info "解析配置文件: $config_file"
    
    # 提取主要配置项（简化版）
    APP_NAME=$(grep -A 1 "^app:" "$config_file" | grep "name:" | sed 's/.*name: *"\?\([^"]*\)"\?.*/\1/' || echo "aidd")
    APP_VERSION=$(grep -A 2 "^app:" "$config_file" | grep "version:" | sed 's/.*version: *"\?\([^"]*\)"\?.*/\1/' || echo "2.0.0")
    
    DATABASE_TYPE=$(grep -A 1 "^database:" "$config_file" | grep "type:" | sed 's/.*type: *"\?\([^"]*\)"\?.*/\1/' || echo "postgresql")
    
    FRONTEND_PORT=$(grep -A 2 "^ports:" "$config_file" | grep "frontend:" | sed 's/.*frontend: *\([0-9]*\).*/\1/' || echo "3000")
    BACKEND_PORT=$(grep -A 2 "^ports:" "$config_file" | grep "backend:" | sed 's/.*backend: *\([0-9]*\).*/\1/' || echo "8080")
    
    EXTERNAL_HOST=$(grep -A 3 "^external:" "$config_file" | grep "host:" | sed 's/.*host: *"\?\([^"]*\)"\?.*/\1/' || echo "localhost")
    EXTERNAL_PROTOCOL=$(grep -A 3 "^external:" "$config_file" | grep "protocol:" | sed 's/.*protocol: *"\?\([^"]*\)"\?.*/\1/' || echo "http")
    
    # 数据库配置
    if [[ "$DATABASE_TYPE" == "mysql" ]]; then
        DB_PASSWORD=$(grep -A 5 "mysql:" "$config_file" | grep "password:" | sed 's/.*password: *"\?\([^"]*\)"\?.*/\1/' || echo "change_me_mysql_password")
        DB_ROOT_PASSWORD=$(grep -A 5 "mysql:" "$config_file" | grep "root_password:" | sed 's/.*root_password: *"\?\([^"]*\)"\?.*/\1/' || echo "change_me_root_password")
    elif [[ "$DATABASE_TYPE" == "postgresql" ]]; then
        DB_PASSWORD=$(grep -A 5 "postgresql:" "$config_file" | grep "password:" | sed 's/.*password: *"\?\([^"]*\)"\?.*/\1/' || echo "change_me_pg_password")
    fi
    
    # AI服务配置
    OPENAI_API_KEY=$(grep -A 2 "openai:" "$config_file" | grep "api_key:" | sed 's/.*api_key: *"\?\([^"]*\)"\?.*/\1/' || echo "your-openai-api-key-here")
    BAIDU_API_KEY=$(grep -A 2 "baidu:" "$config_file" | grep "api_key:" | sed 's/.*api_key: *"\?\([^"]*\)"\?.*/\1/' || echo "")
    DEEPSEEK_API_KEY=$(grep -A 2 "deepseek:" "$config_file" | grep "api_key:" | sed 's/.*api_key: *"\?\([^"]*\)"\?.*/\1/' || echo "")
    
    # OAuth配置
    OAUTH_CLIENT_ID=$(grep -A 4 "^oauth:" "$config_file" | grep "client_id:" | sed 's/.*client_id: *"\?\([^"]*\)"\?.*/\1/' || echo "your-oauth-client-id")
    OAUTH_CLIENT_SECRET=$(grep -A 4 "^oauth:" "$config_file" | grep "client_secret:" | sed 's/.*client_secret: *"\?\([^"]*\)"\?.*/\1/' || echo "your-oauth-client-secret")
    
    # 安全配置
    JWT_SECRET=$(grep -A 2 "^security:" "$config_file" | grep "jwt_secret:" | sed 's/.*jwt_secret: *"\?\([^"]*\)"\?.*/\1/' || echo "change_me_jwt_secret_key")
    
    # 环境配置
    DEPLOY_MODE=$(grep -A 3 "^environment:" "$config_file" | grep "mode:" | sed 's/.*mode: *"\?\([^"]*\)"\?.*/\1/' || echo "production")
    DEBUG=$(grep -A 3 "^environment:" "$config_file" | grep "debug:" | sed 's/.*debug: *\([^[:space:]]*\).*/\1/' || echo "false")
    LOG_LEVEL=$(grep -A 3 "^environment:" "$config_file" | grep "log_level:" | sed 's/.*log_level: *"\?\([^"]*\)"\?.*/\1/' || echo "INFO")
}

# 生成环境变量文件
generate_env_file() {
    print_info "生成环境变量文件..."
    
    cat > "$ENV_FILE" << EOF
# AI文档测试系统部署环境变量
# 自动生成于 $(date)

# 应用配置
APP_NAME=${APP_NAME}
APP_VERSION=${APP_VERSION}
ENVIRONMENT=${DEPLOY_MODE}
DEBUG=${DEBUG}
LOG_LEVEL=${LOG_LEVEL}

# 端口配置
FRONTEND_PORT=${FRONTEND_PORT}
BACKEND_PORT=${BACKEND_PORT}

# 数据库配置
DATABASE_TYPE=${DATABASE_TYPE}
EOF

    # 根据数据库类型添加对应配置
    case "$DATABASE_TYPE" in
        "mysql")
            cat >> "$ENV_FILE" << EOF
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_USERNAME=aidd
MYSQL_PASSWORD=${DB_PASSWORD}
MYSQL_DATABASE=aidd_db
MYSQL_ROOT_PASSWORD=${DB_ROOT_PASSWORD}
DATABASE_URL=mysql://aidd:${DB_PASSWORD}@mysql:3306/aidd_db
EOF
            ;;
        "postgresql")
            cat >> "$ENV_FILE" << EOF
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=aidd
POSTGRES_PASSWORD=${DB_PASSWORD}
POSTGRES_DB=aidd_db
DATABASE_URL=postgresql://aidd:${DB_PASSWORD}@postgres:5432/aidd_db
EOF
            ;;
        "sqlite")
            cat >> "$ENV_FILE" << EOF
DATABASE_URL=sqlite:///app/data/app.db
EOF
            ;;
    esac
    
    cat >> "$ENV_FILE" << EOF

# Redis配置
REDIS_URL=redis://redis:6379/0

# 外部访问配置
EXTERNAL_HOST=${EXTERNAL_HOST}
EXTERNAL_PORT=${BACKEND_PORT}
EXTERNAL_PROTOCOL=${EXTERNAL_PROTOCOL}
FRONTEND_DOMAIN=${EXTERNAL_PROTOCOL}://${EXTERNAL_HOST}:${FRONTEND_PORT}

# AI服务配置
OPENAI_API_KEY=${OPENAI_API_KEY}
BAIDU_API_KEY=${BAIDU_API_KEY}
DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}

# OAuth配置
OAUTH_CLIENT_ID=${OAUTH_CLIENT_ID}
OAUTH_CLIENT_SECRET=${OAUTH_CLIENT_SECRET}

# 安全配置
JWT_SECRET_KEY=${JWT_SECRET}

# 前端构建配置
FRONTEND_API_BASE_URL=${EXTERNAL_PROTOCOL}://${EXTERNAL_HOST}:${BACKEND_PORT}/api
FRONTEND_APP_TITLE=AI文档测试系统
EOF

    # 设置Redis密码命令
    if [[ -n "$REDIS_PASSWORD" ]]; then
        echo "REDIS_PASSWORD_CMD=--requirepass ${REDIS_PASSWORD}" >> "$ENV_FILE"
    else
        echo "REDIS_PASSWORD_CMD=" >> "$ENV_FILE"
    fi
    
    print_success "环境变量文件已生成: $ENV_FILE"
}

# 生成Docker Compose文件
generate_docker_compose() {
    print_info "生成Docker Compose配置..."
    
    cp docker-compose.template.yml "$DOCKER_COMPOSE_FILE"
    
    # 根据数据库类型添加对应服务
    case "$DATABASE_TYPE" in
        "mysql")
            # 添加MySQL依赖
            sed -i 's/# DATABASE_DEPENDS_ON_PLACEHOLDER/      - mysql/' "$DOCKER_COMPOSE_FILE"
            
            # 添加MySQL服务
            cat >> "$DOCKER_COMPOSE_FILE" << 'EOF'

  mysql:
    image: mysql:8.0
    container_name: ${APP_NAME:-aidd}-mysql
    restart: unless-stopped
    environment:
      - MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD}
      - MYSQL_DATABASE=${MYSQL_DATABASE:-aidd_db}
      - MYSQL_USER=${MYSQL_USERNAME:-aidd}
      - MYSQL_PASSWORD=${MYSQL_PASSWORD}
    volumes:
      - mysql_data:/var/lib/mysql
    networks:
      - aidd-network
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
EOF
            # 添加MySQL数据卷
            sed -i 's/# DATABASE_VOLUMES_PLACEHOLDER/  mysql_data:/' "$DOCKER_COMPOSE_FILE"
            ;;
            
        "postgresql")
            # 添加PostgreSQL依赖
            sed -i 's/# DATABASE_DEPENDS_ON_PLACEHOLDER/      - postgres/' "$DOCKER_COMPOSE_FILE"
            
            # 添加PostgreSQL服务
            cat >> "$DOCKER_COMPOSE_FILE" << 'EOF'

  postgres:
    image: postgres:15-alpine
    container_name: ${APP_NAME:-aidd}-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_DB=${POSTGRES_DB:-aidd_db}
      - POSTGRES_USER=${POSTGRES_USER:-aidd}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - aidd-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-aidd} -d ${POSTGRES_DB:-aidd_db}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
EOF
            # 添加PostgreSQL数据卷
            sed -i 's/# DATABASE_VOLUMES_PLACEHOLDER/  postgres_data:/' "$DOCKER_COMPOSE_FILE"
            ;;
            
        "sqlite")
            # SQLite不需要额外服务，清理占位符
            sed -i 's/# DATABASE_DEPENDS_ON_PLACEHOLDER//' "$DOCKER_COMPOSE_FILE"
            sed -i 's/# DATABASE_VOLUMES_PLACEHOLDER//' "$DOCKER_COMPOSE_FILE"
            ;;
    esac
    
    # 清理剩余的占位符
    sed -i '/# DATABASE_SERVICES_PLACEHOLDER/d' "$DOCKER_COMPOSE_FILE"
    
    print_success "Docker Compose配置已生成: $DOCKER_COMPOSE_FILE"
}

# 构建和启动服务
deploy_services() {
    local force_build="$1"
    
    print_header "开始部署AI文档测试系统..."
    
    # 构建参数
    local build_args=""
    if [[ "$force_build" == "true" ]]; then
        build_args="--build --force-recreate"
        print_info "强制重新构建镜像..."
    fi
    
    # 启动服务
    print_info "启动Docker服务..."
    $DOCKER_COMPOSE_CMD -f "$DOCKER_COMPOSE_FILE" --env-file "$ENV_FILE" up -d $build_args
    
    # 等待服务启动
    print_info "等待服务启动..."
    sleep 10
    
    # 数据库需要更长时间初始化
    if [[ "$DATABASE_TYPE" == "mysql" || "$DATABASE_TYPE" == "postgresql" ]]; then
        print_info "等待数据库初始化完成..."
        sleep 30
    fi
    
    # 检查服务状态
    print_info "检查服务状态..."
    $DOCKER_COMPOSE_CMD -f "$DOCKER_COMPOSE_FILE" ps
    
    # 健康检查
    print_info "执行健康检查..."
    local max_attempts=15
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s -f "http://localhost:${BACKEND_PORT}/health" >/dev/null 2>&1; then
            break
        fi
        echo "  等待后端服务启动... ($((attempt+1))/$max_attempts)"
        sleep 5
        ((attempt++))
    done
    
    if [ $attempt -eq $max_attempts ]; then
        print_warning "后端服务启动超时，但容器可能仍在初始化"
        print_info "请稍后检查服务状态"
    else
        print_success "后端服务已就绪"
    fi
    
    # 显示部署结果
    show_deployment_info
}

# 显示部署信息
show_deployment_info() {
    print_header "🎉 AI文档测试系统部署完成！"
    echo
    print_info "📋 访问地址:"
    echo "  🌐 前端界面: ${EXTERNAL_PROTOCOL}://${EXTERNAL_HOST}:${FRONTEND_PORT}"
    echo "  🔧 后端API:  ${EXTERNAL_PROTOCOL}://${EXTERNAL_HOST}:${BACKEND_PORT}"
    echo "  📚 API文档:  ${EXTERNAL_PROTOCOL}://${EXTERNAL_HOST}:${BACKEND_PORT}/docs"
    echo
    print_info "🛠️ 管理命令:"
    echo "  查看日志: $DOCKER_COMPOSE_CMD -f $DOCKER_COMPOSE_FILE logs -f"
    echo "  停止服务: $DOCKER_COMPOSE_CMD -f $DOCKER_COMPOSE_FILE down"
    echo "  重启服务: $DOCKER_COMPOSE_CMD -f $DOCKER_COMPOSE_FILE restart"
    echo "  查看状态: $DOCKER_COMPOSE_CMD -f $DOCKER_COMPOSE_FILE ps"
    echo
    print_info "💡 提示:"
    echo "  - 数据会自动保存到Docker卷中"
    echo "  - 配置文件: $CONFIG_FILE"
    echo "  - 环境变量: $ENV_FILE"
    case "$DATABASE_TYPE" in
        "mysql")
            echo "  - MySQL数据库: localhost:3306 (用户: aidd)"
            ;;
        "postgresql")
            echo "  - PostgreSQL数据库: localhost:5432 (用户: aidd)"
            ;;
        "sqlite")
            echo "  - SQLite数据库文件: ./data/app.db"
            ;;
    esac
    echo "  - 首次启动可能需要几分钟初始化"
    echo
    print_success "✨ 开始使用AI文档测试系统吧！"
}

# 停止服务
stop_services() {
    print_info "停止所有服务..."
    if [[ -f "$DOCKER_COMPOSE_FILE" ]]; then
        $DOCKER_COMPOSE_CMD -f "$DOCKER_COMPOSE_FILE" down
        print_success "服务已停止"
    else
        print_warning "Docker Compose文件不存在"
    fi
}

# 查看日志
show_logs() {
    if [[ -f "$DOCKER_COMPOSE_FILE" ]]; then
        $DOCKER_COMPOSE_CMD -f "$DOCKER_COMPOSE_FILE" logs -f
    else
        print_error "Docker Compose文件不存在"
    fi
}

# 查看状态
show_status() {
    if [[ -f "$DOCKER_COMPOSE_FILE" ]]; then
        print_info "服务状态:"
        $DOCKER_COMPOSE_CMD -f "$DOCKER_COMPOSE_FILE" ps
    else
        print_error "Docker Compose文件不存在"
    fi
}

# 主函数
main() {
    local force_build=false
    local action="deploy"
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -c|--config)
                CONFIG_FILE="$2"
                shift 2
                ;;
            -f|--force)
                force_build=true
                shift
                ;;
            -d|--down)
                action="stop"
                shift
                ;;
            --logs)
                action="logs"
                shift
                ;;
            --status)
                action="status"
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
    
    # 执行相应操作
    case "$action" in
        "deploy")
            check_dependencies
            parse_config_simple "$CONFIG_FILE"
            generate_env_file
            generate_docker_compose
            deploy_services "$force_build"
            ;;
        "stop")
            check_dependencies
            stop_services
            ;;
        "logs")
            check_dependencies
            show_logs
            ;;
        "status")
            check_dependencies
            show_status
            ;;
    esac
}

# 检查是否直接运行脚本
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi