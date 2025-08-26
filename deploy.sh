#!/bin/bash

# AI文档测试系统 Docker部署脚本
# 使用方法: ./deploy.sh [命令]
# 命令: build, up, down, restart, logs, status

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 函数定义
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

# 检查Docker和Docker Compose
check_requirements() {
    log_info "检查环境要求..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
    
    log_success "环境检查通过"
}

# 初始化环境文件
init_env() {
    if [ ! -f .env ]; then
        log_info "创建环境配置文件..."
        cp .env.example .env
        log_warning "请编辑 .env 文件配置相关参数"
    fi
    
    # 确保数据目录存在
    mkdir -p data/uploads data/reports
    log_info "数据目录初始化完成"
}

# 构建镜像
build() {
    log_info "开始构建Docker镜像..."
    docker-compose build --no-cache
    log_success "镜像构建完成"
}

# 启动服务
up() {
    log_info "启动所有服务..."
    init_env
    docker-compose up -d
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 10
    
    # 检查服务状态
    if docker-compose ps | grep -q "Up"; then
        log_success "服务启动成功！"
        echo ""
        log_info "服务访问地址:"
        echo "  前端: http://localhost"
        echo "  后端API: http://localhost/api"
        echo ""
        log_info "查看日志: ./deploy.sh logs"
        log_info "停止服务: ./deploy.sh down"
    else
        log_error "服务启动失败，请查看日志"
        docker-compose logs
    fi
}

# 停止服务
down() {
    log_info "停止所有服务..."
    docker-compose down
    log_success "服务已停止"
}

# 重启服务
restart() {
    log_info "重启服务..."
    down
    sleep 2
    up
}

# 查看日志
logs() {
    if [ -n "$2" ]; then
        # 查看指定服务日志
        docker-compose logs -f "$2"
    else
        # 查看所有服务日志
        docker-compose logs -f
    fi
}

# 查看状态
status() {
    log_info "服务状态:"
    docker-compose ps
    
    echo ""
    log_info "健康检查:"
    
    # 检查后端健康状态
    if curl -s http://localhost/api/health > /dev/null 2>&1; then
        log_success "后端服务: 正常"
    else
        log_error "后端服务: 异常"
    fi
    
    # 检查前端
    if curl -s http://localhost > /dev/null 2>&1; then
        log_success "前端服务: 正常"
    else
        log_error "前端服务: 异常"
    fi
    
    # 检查Redis
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        log_success "Redis服务: 正常"
    else
        log_error "Redis服务: 异常"
    fi
}

# 更新服务
update() {
    log_info "更新服务..."
    
    # 拉取最新代码
    log_info "拉取最新代码..."
    git pull
    
    # 重新构建并启动
    build
    restart
    
    log_success "服务更新完成"
}

# 清理数据
clean() {
    log_warning "这将删除所有容器、镜像和数据，确定要继续吗？(y/N)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        log_info "清理Docker资源..."
        docker-compose down -v --rmi all
        docker system prune -f
        log_success "清理完成"
    else
        log_info "取消清理操作"
    fi
}

# 备份数据
backup() {
    backup_dir="backup/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    log_info "备份数据到 $backup_dir..."
    
    # 备份数据库和文件
    cp -r data "$backup_dir/"
    
    # 备份配置文件
    cp .env "$backup_dir/" 2>/dev/null || true
    cp backend/config.yaml "$backup_dir/" 2>/dev/null || true
    
    log_success "数据备份完成: $backup_dir"
}

# 显示帮助
help() {
    echo "AI文档测试系统 Docker部署脚本"
    echo ""
    echo "使用方法: ./deploy.sh [命令]"
    echo ""
    echo "可用命令:"
    echo "  build     构建Docker镜像"
    echo "  up        启动所有服务"
    echo "  down      停止所有服务"
    echo "  restart   重启服务"
    echo "  logs      查看日志 (可指定服务名)"
    echo "  status    查看服务状态"
    echo "  update    更新服务"
    echo "  backup    备份数据"
    echo "  clean     清理所有Docker资源"
    echo "  help      显示帮助信息"
    echo ""
    echo "示例:"
    echo "  ./deploy.sh up                启动服务"
    echo "  ./deploy.sh logs backend      查看后端日志"
    echo "  ./deploy.sh status            查看状态"
}

# 主逻辑
main() {
    case "$1" in
        build)
            check_requirements
            build
            ;;
        up)
            check_requirements
            up
            ;;
        down)
            down
            ;;
        restart)
            check_requirements
            restart
            ;;
        logs)
            logs "$@"
            ;;
        status)
            status
            ;;
        update)
            check_requirements
            update
            ;;
        backup)
            backup
            ;;
        clean)
            clean
            ;;
        help|--help|-h)
            help
            ;;
        "")
            log_error "请指定命令，使用 ./deploy.sh help 查看帮助"
            exit 1
            ;;
        *)
            log_error "未知命令: $1"
            help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"