#!/bin/bash

# AI文档测试系统 - 一键部署脚本
# 支持开发环境和生产环境部署

set -e

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV=${ENV:-"dev"}
COMPOSE_FILE=""
ENV_FILE=""

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# 显示帮助信息
show_help() {
    cat << EOF
AI文档测试系统 - 一键部署脚本

用法: $0 [选项] [动作]

选项:
  -e, --env ENV           指定环境 (dev|prod) (默认: dev)
  -f, --file FILE         指定docker-compose文件
  --build                 强制重新构建镜像
  --pull                  拉取最新镜像
  -h, --help              显示此帮助信息

动作:
  up                      启动所有服务 (默认)
  down                    停止所有服务
  restart                 重启所有服务
  logs                    查看日志
  status                  查看服务状态
  clean                   清理资源
  backup                  备份数据
  restore [file]          恢复数据

环境说明:
  dev                     开发环境，使用SQLite，本地构建
  prod                    生产环境，使用PostgreSQL，预构建镜像

示例:
  $0                      # 启动开发环境
  $0 -e prod up           # 启动生产环境
  $0 --build up           # 重新构建并启动
  $0 logs                 # 查看日志
  $0 down                 # 停止服务
  $0 clean                # 清理资源
EOF
}

# 检查依赖
check_dependencies() {
    log_info "检查系统依赖..."
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
    
    # 统一使用docker compose命令
    if docker compose version &> /dev/null; then
        DOCKER_COMPOSE="docker compose"
    else
        DOCKER_COMPOSE="docker-compose"
    fi
    
    log_success "依赖检查通过"
}

# 设置环境配置
setup_environment() {
    log_info "设置环境配置: $ENV"
    
    case $ENV in
        dev)
            COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
            ENV_FILE="$SCRIPT_DIR/.env"
            ;;
        prod)
            COMPOSE_FILE="$SCRIPT_DIR/docker-compose.prod.yml"
            ENV_FILE="$SCRIPT_DIR/.env.production"
            ;;
        *)
            log_error "不支持的环境: $ENV (支持: dev, prod)"
            exit 1
            ;;
    esac
    
    # 检查compose文件
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        log_error "Docker Compose文件不存在: $COMPOSE_FILE"
        exit 1
    fi
    
    # 创建环境文件
    if [[ ! -f "$ENV_FILE" ]]; then
        log_warning "环境文件不存在，创建默认配置: $ENV_FILE"
        create_env_file
    fi
    
    log_success "环境配置完成"
}

# 创建环境文件
create_env_file() {
    case $ENV in
        dev)
            cat > "$ENV_FILE" << EOF
# 开发环境配置
DATABASE_TYPE=sqlite
DATABASE_URL=sqlite:///app/data/app.db

# Redis配置
REDIS_URL=redis://redis:6379/0

# 应用配置
DEBUG=true
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# 端口配置
BACKEND_PORT=8000
FRONTEND_PORT=3000

# 安全配置 (开发环境使用默认值)
JWT_SECRET_KEY=dev-secret-key-change-in-production
OAUTH_CLIENT_SECRET=dev-oauth-secret

# AI服务配置
OPENAI_API_KEY=your-openai-api-key-here
EOF
            ;;
        prod)
            cat > "$ENV_FILE" << EOF
# 生产环境配置
DATABASE_TYPE=postgresql
POSTGRES_DB=ai_docs_db
POSTGRES_USER=ai_docs
POSTGRES_PASSWORD=$(openssl rand -base64 32)
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Redis配置
REDIS_URL=redis://redis:6379/0

# 应用配置
DEBUG=false
ENVIRONMENT=production
LOG_LEVEL=INFO

# 端口配置
BACKEND_PORT=8000
FRONTEND_PORT=80

# 安全配置 (请修改为安全的值)
JWT_SECRET_KEY=$(openssl rand -base64 32)
OAUTH_CLIENT_SECRET=your-oauth-client-secret-here

# AI服务配置
OPENAI_API_KEY=your-openai-api-key-here

# 外部域名配置
EXTERNAL_HOST=localhost
EXTERNAL_PORT=80
EXTERNAL_PROTOCOL=http
FRONTEND_DOMAIN=http://localhost
EOF
            ;;
    esac
    
    log_info "已创建环境文件，请编辑 $ENV_FILE 修改配置"
}

# 启动服务
start_services() {
    log_info "启动AI文档测试系统..."
    
    local compose_args=""
    
    if [[ "$BUILD" == "true" ]]; then
        compose_args="--build"
        log_info "将重新构建镜像"
    fi
    
    if [[ "$PULL" == "true" ]]; then
        log_info "拉取最新镜像..."
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull
    fi
    
    # 启动服务
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d $compose_args
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 10
    
    # 检查服务状态
    check_services_health
    
    log_success "系统启动完成!"
    show_access_info
}

# 停止服务
stop_services() {
    log_info "停止AI文档测试系统..."
    
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down
    
    log_success "系统已停止"
}

# 重启服务
restart_services() {
    log_info "重启AI文档测试系统..."
    
    stop_services
    sleep 5
    start_services
}

# 查看日志
show_logs() {
    log_info "显示系统日志..."
    
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs -f --tail=100
}

# 检查服务健康状态
check_services_health() {
    log_info "检查服务健康状态..."
    
    local max_attempts=30
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        local healthy_count=0
        local total_services=0
        
        # 检查各个服务
        if $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps | grep -q "Up.*healthy"; then
            healthy_count=$($DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps | grep -c "Up.*healthy" || echo "0")
        fi
        
        total_services=$($DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps | grep -c "Up" || echo "0")
        
        if [[ $healthy_count -eq $total_services ]] && [[ $total_services -gt 0 ]]; then
            log_success "所有服务健康运行"
            return 0
        fi
        
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    log_warning "部分服务可能未正常启动，请检查日志"
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps
}

# 显示服务状态
show_status() {
    log_info "AI文档测试系统状态:"
    
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps
    
    echo ""
    log_info "系统资源使用情况:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" \
        $(docker ps --format "{{.Names}}" | grep -E "(aidd|postgres|redis)")
}

# 显示访问信息
show_access_info() {
    local frontend_port="80"
    local backend_port="8000"
    
    if [[ "$ENV" == "dev" ]]; then
        frontend_port="3000"
    fi
    
    cat << EOF

${GREEN}✅ AI文档测试系统部署完成！${NC}

访问地址:
  前端界面: http://localhost:${frontend_port}
  后端API:  http://localhost:${backend_port}
  API文档:  http://localhost:${backend_port}/docs

管理命令:
  查看日志:   $0 logs
  重启系统:   $0 restart
  停止系统:   $0 down
  系统状态:   $0 status

配置文件:
  环境配置:   $ENV_FILE
  Compose:   $COMPOSE_FILE

${YELLOW}注意事项:${NC}
  - 首次启动需要等待镜像下载和服务初始化
  - 生产环境请修改环境文件中的安全配置
  - 建议定期备份数据: $0 backup

EOF
}

# 清理资源
clean_resources() {
    log_info "清理系统资源..."
    
    # 停止服务
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down -v
    
    # 清理镜像
    docker image prune -f
    
    # 清理网络
    docker network prune -f
    
    log_success "资源清理完成"
}

# 备份数据
backup_data() {
    log_info "备份系统数据..."
    
    local backup_dir="$SCRIPT_DIR/backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    # 备份数据库
    if [[ "$ENV" == "prod" ]]; then
        # PostgreSQL备份
        docker exec aidd-postgres pg_dump -U ai_docs ai_docs_db > "$backup_dir/database.sql"
    else
        # SQLite备份
        docker cp aidd-backend:/app/data/app.db "$backup_dir/app.db" 2>/dev/null || true
    fi
    
    # 备份上传文件
    docker cp aidd-backend:/app/data/uploads "$backup_dir/" 2>/dev/null || true
    
    # 备份配置文件
    cp "$ENV_FILE" "$backup_dir/env_config" 2>/dev/null || true
    
    log_success "数据备份完成: $backup_dir"
}

# 恢复数据
restore_data() {
    local backup_file="$1"
    
    if [[ -z "$backup_file" ]]; then
        log_error "请指定备份文件路径"
        exit 1
    fi
    
    if [[ ! -f "$backup_file" ]]; then
        log_error "备份文件不存在: $backup_file"
        exit 1
    fi
    
    log_info "恢复系统数据..."
    
    # TODO: 实现数据恢复逻辑
    log_warning "数据恢复功能开发中..."
}

# 主函数
main() {
    local action="up"
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--env)
                ENV="$2"
                shift 2
                ;;
            -f|--file)
                COMPOSE_FILE="$2"
                shift 2
                ;;
            --build)
                BUILD="true"
                shift
                ;;
            --pull)
                PULL="true"
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            up|down|restart|logs|status|clean|backup)
                action="$1"
                shift
                ;;
            restore)
                action="restore"
                backup_file="$2"
                shift 2
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 检查依赖
    check_dependencies
    
    # 设置环境
    setup_environment
    
    # 执行对应动作
    case $action in
        up)
            start_services
            ;;
        down)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        logs)
            show_logs
            ;;
        status)
            show_status
            ;;
        clean)
            clean_resources
            ;;
        backup)
            backup_data
            ;;
        restore)
            restore_data "$backup_file"
            ;;
        *)
            log_error "未知动作: $action"
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"