#!/bin/bash

# ============================================================================
# AI Document Testing System - 本地一键部署脚本
# ============================================================================
# 功能：本地环境下一键部署和启动应用
# 作者：Claude Code Assistant
# 版本：v1.0.0
# ============================================================================

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="ai-document-testing-system"
DEPLOY_MODE="dev"
USE_DOCKER=false
AUTO_BUILD=true
SKIP_HEALTH_CHECK=false
FRONTEND_PORT=3000
BACKEND_PORT=8080
REDIS_PORT=6379
LOG_LEVEL="INFO"
CONFIG_FILE="config.yaml"

# PID文件目录
PID_DIR="$SCRIPT_DIR/pids"
mkdir -p "$PID_DIR"

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

log_header() {
    echo -e "${PURPLE}╔════════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║${NC} $1"
    echo -e "${PURPLE}╚════════════════════════════════════════════════════════════════════════════════╝${NC}"
}

# 显示使用方法
show_help() {
    echo "AI Document Testing System - 本地部署脚本"
    echo ""
    echo "使用方法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help              显示此帮助信息"
    echo "  -m, --mode MODE         部署模式 (dev|prod|test) [默认: dev]"
    echo "  -d, --docker            使用Docker部署"
    echo "  --no-build              跳过构建步骤"
    echo "  --skip-health-check     跳过健康检查"
    echo "  --frontend-port PORT    前端端口 [默认: 3000]"
    echo "  --backend-port PORT     后端端口 [默认: 8080]"
    echo "  --redis-port PORT       Redis端口 [默认: 6379]"
    echo "  --config FILE           配置文件 [默认: config.yaml]"
    echo "  --log-level LEVEL       日志级别 (DEBUG|INFO|WARNING|ERROR) [默认: INFO]"
    echo ""
    echo "部署模式:"
    echo "  dev                     开发模式（热重载、详细日志）"
    echo "  prod                    生产模式（优化性能、简化日志）"
    echo "  test                    测试模式（使用测试配置）"
    echo ""
    echo "示例:"
    echo "  $0                      # 开发模式部署"
    echo "  $0 --mode prod          # 生产模式部署"
    echo "  $0 --docker             # 使用Docker部署"
    echo "  $0 --no-build           # 跳过构建直接部署"
    echo ""
    echo "管理命令:"
    echo "  $0 stop                 # 停止所有服务"
    echo "  $0 restart              # 重启所有服务"
    echo "  $0 status               # 查看服务状态"
    echo "  $0 logs                 # 查看服务日志"
    echo ""
}

# 解析命令行参数
parse_args() {
    # 处理管理命令
    if [[ $# -gt 0 ]] && [[ "$1" =~ ^(stop|restart|status|logs)$ ]]; then
        case "$1" in
            stop)
                stop_services
                exit 0
                ;;
            restart)
                stop_services
                sleep 2
                shift
                parse_args "$@"  # 解析剩余参数然后继续部署
                ;;
            status)
                show_status
                exit 0
                ;;
            logs)
                show_logs
                exit 0
                ;;
        esac
    fi
    
    # 解析选项参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -m|--mode)
                DEPLOY_MODE="$2"
                shift 2
                ;;
            -d|--docker)
                USE_DOCKER=true
                shift
                ;;
            --no-build)
                AUTO_BUILD=false
                shift
                ;;
            --skip-health-check)
                SKIP_HEALTH_CHECK=true
                shift
                ;;
            --frontend-port)
                FRONTEND_PORT="$2"
                shift 2
                ;;
            --backend-port)
                BACKEND_PORT="$2"
                shift 2
                ;;
            --redis-port)
                REDIS_PORT="$2"
                shift 2
                ;;
            --config)
                CONFIG_FILE="$2"
                shift 2
                ;;
            --log-level)
                LOG_LEVEL="$2"
                shift 2
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# 检查端口占用
check_port() {
    local port=$1
    local service_name=$2
    
    if command -v lsof &> /dev/null; then
        if lsof -i :$port &> /dev/null; then
            log_warning "端口 $port 已被占用 ($service_name)"
            local pid=$(lsof -ti :$port)
            log_info "占用进程 PID: $pid"
            return 1
        fi
    elif command -v netstat &> /dev/null; then
        if netstat -tuln | grep ":$port " &> /dev/null; then
            log_warning "端口 $port 已被占用 ($service_name)"
            return 1
        fi
    fi
    
    return 0
}

# 检查必需服务
check_prerequisites() {
    log_header "检查部署前置条件"
    
    # 检查Redis（如果不使用Docker）
    if [[ "$USE_DOCKER" == "false" ]]; then
        if ! command -v redis-server &> /dev/null; then
            log_warning "Redis未安装，将尝试启动Docker Redis容器"
            
            if command -v docker &> /dev/null; then
                if ! docker ps --format 'table {{.Names}}' | grep -q "redis"; then
                    log_info "启动Redis Docker容器..."
                    if docker run -d --name redis -p $REDIS_PORT:6379 redis:7-alpine; then
                        log_success "Redis容器启动成功"
                    else
                        log_error "Redis容器启动失败"
                        return 1
                    fi
                else
                    log_success "Redis容器已在运行"
                fi
            else
                log_error "需要安装Redis或Docker"
                return 1
            fi
        else
            log_success "Redis已安装"
        fi
    fi
    
    # 检查端口
    local ports_to_check=(
        "$FRONTEND_PORT:前端服务"
        "$BACKEND_PORT:后端服务"
    )
    
    if [[ "$USE_DOCKER" == "false" ]]; then
        ports_to_check+=("$REDIS_PORT:Redis服务")
    fi
    
    for port_info in "${ports_to_check[@]}"; do
        local port=$(echo $port_info | cut -d: -f1)
        local service=$(echo $port_info | cut -d: -f2)
        
        if ! check_port $port "$service"; then
            log_error "端口冲突，请检查或更改端口配置"
            return 1
        fi
    done
    
    log_success "前置条件检查通过"
}

# 准备配置文件
prepare_config() {
    log_header "准备配置文件"
    
    # 根据部署模式选择配置文件
    case "$DEPLOY_MODE" in
        dev)
            CONFIG_FILE="config.yaml"
            ;;
        prod)
            CONFIG_FILE="config.prod.yaml"
            ;;
        test)
            CONFIG_FILE="config.test.yaml"
            ;;
    esac
    
    log_info "使用配置文件: $CONFIG_FILE"
    
    # 检查配置文件是否存在
    if [[ -f "backend/$CONFIG_FILE" ]]; then
        log_success "配置文件存在: backend/$CONFIG_FILE"
    else
        log_warning "配置文件不存在，从模板创建..."
        
        if [[ -f "backend/config.yaml" ]]; then
            cp "backend/config.yaml" "backend/$CONFIG_FILE"
            log_success "从默认配置创建: $CONFIG_FILE"
        else
            log_error "找不到配置模板文件"
            return 1
        fi
    fi
    
    # 创建环境变量文件
    cat > .env.local << EOF
# AI Document Testing System - 本地部署环境变量
NODE_ENV=$DEPLOY_MODE
VITE_API_BASE_URL=http://localhost:$BACKEND_PORT
VITE_HOST=localhost
VITE_PORT=$FRONTEND_PORT

PYTHONPATH=.
CONFIG_FILE=$CONFIG_FILE
LOG_LEVEL=$LOG_LEVEL
REDIS_URL=redis://localhost:$REDIS_PORT/0

# 服务端口配置
FRONTEND_PORT=$FRONTEND_PORT
BACKEND_PORT=$BACKEND_PORT
REDIS_PORT=$REDIS_PORT
EOF
    
    log_success "环境变量文件已创建: .env.local"
}

# 构建应用
build_application() {
    if [[ "$AUTO_BUILD" == "true" ]]; then
        log_header "构建应用"
        
        local build_args=""
        if [[ "$DEPLOY_MODE" == "prod" ]]; then
            build_args="--type production"
        fi
        
        if [[ -f "./build-local.sh" ]]; then
            if ! chmod +x ./build-local.sh; then
                log_warning "无法设置构建脚本权限"
            fi
            
            log_info "运行构建脚本..."
            if ! ./build-local.sh $build_args; then
                log_error "应用构建失败"
                return 1
            fi
            log_success "应用构建完成"
        else
            log_error "构建脚本不存在: ./build-local.sh"
            return 1
        fi
    else
        log_info "跳过构建步骤"
    fi
}

# Docker部署
deploy_with_docker() {
    log_header "使用Docker部署"
    
    # 选择docker-compose文件
    local compose_file="docker-compose.yml"
    if [[ "$DEPLOY_MODE" == "prod" ]]; then
        compose_file="docker-compose.prod.yml"
    fi
    
    if [[ ! -f "$compose_file" ]]; then
        log_error "Docker Compose文件不存在: $compose_file"
        return 1
    fi
    
    # 设置环境变量
    export FRONTEND_PORT BACKEND_PORT REDIS_PORT
    
    log_info "启动Docker容器..."
    if docker-compose -f "$compose_file" up -d; then
        log_success "Docker容器启动成功"
        
        # 等待服务启动
        log_info "等待服务启动..."
        sleep 10
        
        return 0
    else
        log_error "Docker部署失败"
        return 1
    fi
}

# 本地部署
deploy_locally() {
    log_header "本地部署应用"
    
    # 启动Redis（如果需要）
    start_redis
    
    # 启动后端
    start_backend
    
    # 启动前端
    start_frontend
    
    log_success "所有服务已启动"
}

# 启动Redis
start_redis() {
    if command -v redis-server &> /dev/null; then
        if ! pgrep redis-server > /dev/null; then
            log_info "启动Redis服务..."
            redis-server --port $REDIS_PORT --daemonize yes --pidfile "$PID_DIR/redis.pid"
            
            if [[ -f "$PID_DIR/redis.pid" ]]; then
                log_success "Redis启动成功 (PID: $(cat $PID_DIR/redis.pid))"
            else
                log_error "Redis启动失败"
                return 1
            fi
        else
            log_success "Redis已在运行"
        fi
    else
        log_info "Redis服务由Docker提供"
    fi
}

# 启动后端
start_backend() {
    log_info "启动后端服务..."
    
    cd backend
    
    # 激活虚拟环境
    if [[ -d "venv" ]]; then
        source venv/bin/activate || source venv/Scripts/activate
    else
        log_error "Python虚拟环境不存在，请先运行构建"
        return 1
    fi
    
    # 设置环境变量
    export PYTHONPATH="."
    export CONFIG_FILE="$CONFIG_FILE"
    export LOG_LEVEL="$LOG_LEVEL"
    
    # 启动后端应用
    nohup python app/main.py > "../logs/backend.log" 2>&1 &
    local backend_pid=$!
    echo $backend_pid > "../$PID_DIR/backend.pid"
    
    cd ..
    
    # 等待启动
    sleep 3
    
    if kill -0 $backend_pid 2>/dev/null; then
        log_success "后端服务启动成功 (PID: $backend_pid, Port: $BACKEND_PORT)"
    else
        log_error "后端服务启动失败"
        return 1
    fi
}

# 启动前端
start_frontend() {
    log_info "启动前端服务..."
    
    cd frontend
    
    # 设置环境变量
    export NODE_ENV="$DEPLOY_MODE"
    export VITE_API_BASE_URL="http://localhost:$BACKEND_PORT"
    export PORT="$FRONTEND_PORT"
    
    if [[ "$DEPLOY_MODE" == "dev" ]]; then
        # 开发模式
        nohup npm run dev -- --port $FRONTEND_PORT > "../logs/frontend.log" 2>&1 &
    else
        # 生产模式
        if [[ -d "dist" ]]; then
            # 使用简单HTTP服务器
            if command -v python3 &> /dev/null; then
                nohup python3 -m http.server $FRONTEND_PORT --directory dist > "../logs/frontend.log" 2>&1 &
            elif command -v python &> /dev/null; then
                nohup python -m http.server $FRONTEND_PORT --directory dist > "../logs/frontend.log" 2>&1 &
            else
                log_error "需要Python来提供静态文件服务"
                return 1
            fi
        else
            log_error "前端构建文件不存在，请先构建应用"
            return 1
        fi
    fi
    
    local frontend_pid=$!
    echo $frontend_pid > "../$PID_DIR/frontend.pid"
    
    cd ..
    
    # 等待启动
    sleep 3
    
    if kill -0 $frontend_pid 2>/dev/null; then
        log_success "前端服务启动成功 (PID: $frontend_pid, Port: $FRONTEND_PORT)"
    else
        log_error "前端服务启动失败"
        return 1
    fi
}

# 健康检查
health_check() {
    if [[ "$SKIP_HEALTH_CHECK" == "true" ]]; then
        log_info "跳过健康检查"
        return 0
    fi
    
    log_header "服务健康检查"
    
    local check_attempts=12
    local check_interval=5
    
    # 检查后端健康
    log_info "检查后端服务健康状态..."
    for ((i=1; i<=check_attempts; i++)); do
        if curl -f -s "http://localhost:$BACKEND_PORT/api/system/health" > /dev/null; then
            log_success "后端服务健康检查通过"
            break
        elif [[ $i -eq $check_attempts ]]; then
            log_error "后端服务健康检查失败"
            return 1
        else
            log_info "等待后端服务启动... ($i/$check_attempts)"
            sleep $check_interval
        fi
    done
    
    # 检查前端访问
    log_info "检查前端服务访问性..."
    for ((i=1; i<=check_attempts; i++)); do
        if curl -f -s "http://localhost:$FRONTEND_PORT" > /dev/null; then
            log_success "前端服务访问检查通过"
            break
        elif [[ $i -eq $check_attempts ]]; then
            log_warning "前端服务访问检查失败，但可能正常"
            break
        else
            log_info "等待前端服务启动... ($i/$check_attempts)"
            sleep $check_interval
        fi
    done
    
    log_success "健康检查完成"
}

# 停止服务
stop_services() {
    log_header "停止所有服务"
    
    local stopped_services=0
    
    # 停止前端
    if [[ -f "$PID_DIR/frontend.pid" ]]; then
        local frontend_pid=$(cat "$PID_DIR/frontend.pid")
        if kill -0 $frontend_pid 2>/dev/null; then
            if kill $frontend_pid 2>/dev/null; then
                log_success "前端服务已停止 (PID: $frontend_pid)"
                stopped_services=$((stopped_services + 1))
            fi
        fi
        rm -f "$PID_DIR/frontend.pid"
    fi
    
    # 停止后端
    if [[ -f "$PID_DIR/backend.pid" ]]; then
        local backend_pid=$(cat "$PID_DIR/backend.pid")
        if kill -0 $backend_pid 2>/dev/null; then
            if kill $backend_pid 2>/dev/null; then
                log_success "后端服务已停止 (PID: $backend_pid)"
                stopped_services=$((stopped_services + 1))
            fi
        fi
        rm -f "$PID_DIR/backend.pid"
    fi
    
    # 停止Redis（如果由脚本启动）
    if [[ -f "$PID_DIR/redis.pid" ]]; then
        local redis_pid=$(cat "$PID_DIR/redis.pid")
        if kill -0 $redis_pid 2>/dev/null; then
            if kill $redis_pid 2>/dev/null; then
                log_success "Redis服务已停止 (PID: $redis_pid)"
                stopped_services=$((stopped_services + 1))
            fi
        fi
        rm -f "$PID_DIR/redis.pid"
    fi
    
    # 停止Docker服务
    if [[ "$USE_DOCKER" == "true" ]]; then
        if docker-compose down > /dev/null 2>&1; then
            log_success "Docker服务已停止"
            stopped_services=$((stopped_services + 1))
        fi
    fi
    
    if [[ $stopped_services -eq 0 ]]; then
        log_info "没有正在运行的服务"
    else
        log_success "已停止 $stopped_services 个服务"
    fi
}

# 显示服务状态
show_status() {
    log_header "服务运行状态"
    
    # 检查前端状态
    if [[ -f "$PID_DIR/frontend.pid" ]]; then
        local frontend_pid=$(cat "$PID_DIR/frontend.pid")
        if kill -0 $frontend_pid 2>/dev/null; then
            log_success "前端服务: 运行中 (PID: $frontend_pid, Port: $FRONTEND_PORT)"
        else
            log_warning "前端服务: PID文件存在但进程未运行"
        fi
    else
        log_info "前端服务: 未启动"
    fi
    
    # 检查后端状态
    if [[ -f "$PID_DIR/backend.pid" ]]; then
        local backend_pid=$(cat "$PID_DIR/backend.pid")
        if kill -0 $backend_pid 2>/dev/null; then
            log_success "后端服务: 运行中 (PID: $backend_pid, Port: $BACKEND_PORT)"
        else
            log_warning "后端服务: PID文件存在但进程未运行"
        fi
    else
        log_info "后端服务: 未启动"
    fi
    
    # 检查Redis状态
    if [[ -f "$PID_DIR/redis.pid" ]]; then
        local redis_pid=$(cat "$PID_DIR/redis.pid")
        if kill -0 $redis_pid 2>/dev/null; then
            log_success "Redis服务: 运行中 (PID: $redis_pid, Port: $REDIS_PORT)"
        else
            log_warning "Redis服务: PID文件存在但进程未运行"
        fi
    else
        if pgrep redis-server > /dev/null; then
            log_success "Redis服务: 运行中 (系统服务)"
        else
            log_info "Redis服务: 未启动"
        fi
    fi
    
    # Docker状态
    if docker-compose ps 2>/dev/null | grep -q "Up"; then
        log_success "Docker服务: 运行中"
        docker-compose ps
    fi
}

# 显示服务日志
show_logs() {
    log_header "查看服务日志"
    
    echo -e "${CYAN}选择要查看的日志:${NC}"
    echo "1) 前端日志"
    echo "2) 后端日志"
    echo "3) 所有日志"
    echo "4) 实时跟踪所有日志"
    
    read -p "请选择 [1-4]: " choice
    
    case $choice in
        1)
            if [[ -f "logs/frontend.log" ]]; then
                tail -n 50 logs/frontend.log
            else
                log_warning "前端日志文件不存在"
            fi
            ;;
        2)
            if [[ -f "logs/backend.log" ]]; then
                tail -n 50 logs/backend.log
            else
                log_warning "后端日志文件不存在"
            fi
            ;;
        3)
            echo -e "${YELLOW}=== 前端日志 ===${NC}"
            if [[ -f "logs/frontend.log" ]]; then
                tail -n 25 logs/frontend.log
            else
                log_warning "前端日志文件不存在"
            fi
            
            echo -e "\n${YELLOW}=== 后端日志 ===${NC}"
            if [[ -f "logs/backend.log" ]]; then
                tail -n 25 logs/backend.log
            else
                log_warning "后端日志文件不存在"
            fi
            ;;
        4)
            log_info "按 Ctrl+C 退出日志跟踪"
            if [[ -f "logs/frontend.log" && -f "logs/backend.log" ]]; then
                tail -f logs/frontend.log logs/backend.log
            else
                log_warning "日志文件不存在"
            fi
            ;;
        *)
            log_error "无效选择"
            ;;
    esac
}

# 主函数
main() {
    # 显示标题
    echo -e "${CYAN}"
    echo "┌─────────────────────────────────────────────────────────────────┐"
    echo "│                                                                 │"
    echo "│     AI Document Testing System - 本地部署脚本 v1.0.0           │"
    echo "│                                                                 │"
    echo "└─────────────────────────────────────────────────────────────────┘"
    echo -e "${NC}"
    
    # 创建必要目录
    mkdir -p logs pids
    
    # 记录开始时间
    local start_time=$(date +%s)
    
    # 解析参数
    parse_args "$@"
    
    # 进入项目目录
    cd "$SCRIPT_DIR"
    
    log_info "项目目录: $SCRIPT_DIR"
    log_info "部署模式: $DEPLOY_MODE"
    log_info "使用Docker: $USE_DOCKER"
    
    # 执行部署步骤
    check_prerequisites
    prepare_config
    
    # 如果需要构建
    if [[ "$AUTO_BUILD" == "true" ]]; then
        build_application
    fi
    
    # 选择部署方式
    if [[ "$USE_DOCKER" == "true" ]]; then
        deploy_with_docker
    else
        deploy_locally
    fi
    
    # 健康检查
    health_check
    
    # 计算部署时间
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))
    
    # 显示最终结果
    log_header "部署完成"
    log_success "🎉 应用部署成功！"
    log_info "部署耗时: ${minutes}分${seconds}秒"
    
    echo -e "\n${GREEN}访问地址:${NC}"
    echo "  前端应用: http://localhost:$FRONTEND_PORT"
    echo "  后端API: http://localhost:$BACKEND_PORT"
    echo "  API文档: http://localhost:$BACKEND_PORT/docs"
    
    echo -e "\n${CYAN}管理命令:${NC}"
    echo "  查看状态: $0 status"
    echo "  查看日志: $0 logs"
    echo "  停止服务: $0 stop"
    echo "  重启服务: $0 restart"
    
    echo -e "\n${YELLOW}注意事项:${NC}"
    echo "  - 服务运行在后台，可以通过管理命令监控"
    echo "  - 日志文件位于 logs/ 目录"
    echo "  - PID文件位于 pids/ 目录"
    
    if [[ "$DEPLOY_MODE" == "dev" ]]; then
        echo -e "  - 开发模式支持热重载"
    fi
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi