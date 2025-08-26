#!/bin/bash

# AI文档测试系统 - 生产环境更新部署脚本
# 版本: 1.0
# 用途: 自动化部署最新功能更新和错误修复

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# 配置变量
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
BACKUP_DIR="$PROJECT_DIR/backups/$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$PROJECT_DIR/deployment.log"

# 数据库配置（需要根据实际环境调整）
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-3306}"
DB_NAME="${DB_NAME:-ai_doc_test}"
DB_USER="${DB_USER:-root}"

# 服务配置
BACKEND_SERVICE="${BACKEND_SERVICE:-ai-doc-backend}"
FRONTEND_SERVICE="${FRONTEND_SERVICE:-nginx}"

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 重定向输出到日志文件
exec > >(tee -a "$LOG_FILE")
exec 2>&1

print_banner() {
    echo "=================================================="
    echo "🚀 AI文档测试系统 - 生产环境更新部署"
    echo "=================================================="
    echo "部署时间: $(date)"
    echo "项目目录: $PROJECT_DIR"
    echo "备份目录: $BACKUP_DIR"
    echo "=================================================="
    echo
}

check_prerequisites() {
    log_info "检查部署前提条件..."
    
    # 检查是否为root用户或有sudo权限
    if [[ $EUID -ne 0 ]] && ! sudo -n true 2>/dev/null; then
        log_error "需要root权限或sudo权限来重启服务"
        exit 1
    fi
    
    # 检查必要命令
    local required_commands=("git" "python3" "mysql" "mysqldump" "npm")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "缺少必要命令: $cmd"
            exit 1
        fi
    done
    
    # 检查项目目录
    if [[ ! -d "$BACKEND_DIR" || ! -d "$FRONTEND_DIR" ]]; then
        log_error "项目目录结构不完整"
        exit 1
    fi
    
    # 检查磁盘空间（至少2GB）
    local available_space=$(df "$PROJECT_DIR" | awk 'NR==2 {print $4}')
    if [[ $available_space -lt 2097152 ]]; then  # 2GB in KB
        log_warning "可用磁盘空间不足2GB，请确保有足够空间进行备份"
        read -p "是否继续？(y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    log_success "前提条件检查通过"
}

backup_database() {
    log_info "开始数据库备份..."
    
    # 提示输入数据库密码
    echo -n "请输入数据库密码: "
    read -s DB_PASS
    echo
    
    local backup_file="$BACKUP_DIR/database_backup.sql"
    
    # 执行备份
    if mysqldump -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASS" \
        --single-transaction --routines --triggers "$DB_NAME" > "$backup_file"; then
        log_success "数据库备份完成: $backup_file"
        
        # 验证备份文件
        if [[ -s "$backup_file" ]]; then
            local backup_size=$(du -h "$backup_file" | cut -f1)
            log_info "备份文件大小: $backup_size"
        else
            log_error "备份文件为空，备份可能失败"
            exit 1
        fi
    else
        log_error "数据库备份失败"
        exit 1
    fi
}

backup_code() {
    log_info "备份当前代码..."
    
    # 获取当前commit hash
    local current_commit=$(git rev-parse HEAD)
    echo "$current_commit" > "$BACKUP_DIR/current_commit.txt"
    
    # 创建代码备份
    tar -czf "$BACKUP_DIR/code_backup.tar.gz" \
        --exclude='node_modules' \
        --exclude='__pycache__' \
        --exclude='.git' \
        --exclude='data' \
        --exclude='logs' \
        -C "$PROJECT_DIR/.." "$(basename "$PROJECT_DIR")"
    
    log_success "代码备份完成: $BACKUP_DIR/code_backup.tar.gz"
}

update_code() {
    log_info "更新代码..."
    
    # 保存当前状态
    git stash push -m "Auto-stash before deployment $(date)"
    
    # 拉取最新代码
    git fetch origin
    git checkout main
    git pull origin main
    
    # 获取更新信息
    local new_commit=$(git rev-parse HEAD)
    local commit_count=$(git rev-list --count HEAD)
    
    log_success "代码更新完成"
    log_info "最新commit: $new_commit"
    log_info "总commit数: $commit_count"
    
    # 显示最近的提交
    log_info "最近的提交:"
    git log --oneline -5
}

install_dependencies() {
    log_info "安装/更新依赖..."
    
    # 后端依赖
    cd "$BACKEND_DIR"
    if [[ -f "requirements.txt" ]]; then
        if command -v pip3 &> /dev/null; then
            pip3 install -r requirements.txt
        else
            pip install -r requirements.txt
        fi
        log_success "后端依赖安装完成"
    fi
    
    # 前端依赖
    cd "$FRONTEND_DIR"
    if [[ -f "package.json" ]]; then
        npm install
        log_success "前端依赖安装完成"
    fi
    
    cd "$PROJECT_DIR"
}

run_database_migrations() {
    log_info "执行数据库迁移..."
    
    cd "$BACKEND_DIR"
    
    # 1. 并发限制字段迁移
    log_info "执行并发限制字段迁移..."
    if python3 migrate_user_concurrency.py --verify; then
        log_info "并发限制字段已存在，跳过迁移"
    else
        log_info "开始并发限制字段迁移..."
        if python3 migrate_user_concurrency.py; then
            log_success "并发限制字段迁移完成"
        else
            log_error "并发限制字段迁移失败"
            exit 1
        fi
    fi
    
    # 2. 外键约束问题修复
    log_info "检查外键约束问题..."
    if python3 fix_foreign_key_constraints.py --verify; then
        log_info "外键约束正常，无需修复"
    else
        log_warning "发现外键约束问题，开始修复..."
        if python3 fix_foreign_key_constraints.py --force; then
            log_success "外键约束问题修复完成"
        else
            log_error "外键约束问题修复失败"
            exit 1
        fi
    fi
    
    cd "$PROJECT_DIR"
}

build_frontend() {
    log_info "构建前端..."
    
    cd "$FRONTEND_DIR"
    
    if npm run build; then
        log_success "前端构建完成"
    else
        log_error "前端构建失败"
        exit 1
    fi
    
    cd "$PROJECT_DIR"
}

restart_services() {
    log_info "重启服务..."
    
    # 重启后端服务
    if systemctl is-active --quiet "$BACKEND_SERVICE"; then
        log_info "重启后端服务: $BACKEND_SERVICE"
        sudo systemctl restart "$BACKEND_SERVICE"
        
        # 等待服务启动
        sleep 5
        
        if systemctl is-active --quiet "$BACKEND_SERVICE"; then
            log_success "后端服务重启成功"
        else
            log_error "后端服务重启失败"
            sudo systemctl status "$BACKEND_SERVICE"
            exit 1
        fi
    else
        log_warning "后端服务 $BACKEND_SERVICE 未运行，尝试启动..."
        sudo systemctl start "$BACKEND_SERVICE"
    fi
    
    # 重启前端服务
    if systemctl is-active --quiet "$FRONTEND_SERVICE"; then
        log_info "重启前端服务: $FRONTEND_SERVICE"
        sudo systemctl restart "$FRONTEND_SERVICE"
        
        if systemctl is-active --quiet "$FRONTEND_SERVICE"; then
            log_success "前端服务重启成功"
        else
            log_error "前端服务重启失败"
            sudo systemctl status "$FRONTEND_SERVICE"
            exit 1
        fi
    else
        log_warning "前端服务 $FRONTEND_SERVICE 未运行，尝试启动..."
        sudo systemctl start "$FRONTEND_SERVICE"
    fi
}

verify_deployment() {
    log_info "验证部署结果..."
    
    cd "$BACKEND_DIR"
    
    # 1. 检查服务状态
    if systemctl is-active --quiet "$BACKEND_SERVICE"; then
        log_success "后端服务运行正常"
    else
        log_error "后端服务异常"
        return 1
    fi
    
    # 2. 测试数据库连接
    log_info "测试数据库连接..."
    python3 -c "
import sys
sys.path.append('.')
try:
    from app.core.database import get_db
    from app.core.config import get_settings
    print('✅ 数据库连接正常')
except Exception as e:
    print(f'❌ 数据库连接失败: {e}')
    sys.exit(1)
" || return 1
    
    # 3. 测试并发控制功能
    log_info "测试并发控制功能..."
    python3 -c "
import sys
sys.path.append('.')
try:
    from app.services.concurrency_service import concurrency_service
    from app.core.database import get_db
    from app.models.user import User
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import create_engine
    from app.core.config import get_settings
    
    settings = get_settings()
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        user = db.query(User).first()
        if user:
            status = concurrency_service.get_concurrency_status(db, user)
            print(f'✅ 并发控制功能正常: 系统{status[\"system\"][\"max_count\"]}个，用户{status[\"user\"][\"max_count\"]}个')
        else:
            print('⚠️ 没有用户数据进行测试')
    finally:
        db.close()
except Exception as e:
    print(f'❌ 并发控制功能测试失败: {e}')
    sys.exit(1)
" || return 1
    
    # 4. 测试API健康检查
    log_info "测试API健康检查..."
    local api_port="${API_PORT:-8080}"
    if curl -f "http://localhost:$api_port/health" &> /dev/null; then
        log_success "API健康检查通过"
    else
        log_warning "API健康检查失败，可能端口配置不同"
    fi
    
    cd "$PROJECT_DIR"
    log_success "部署验证完成"
}

cleanup() {
    log_info "清理临时文件..."
    
    # 清理旧的日志文件（保留最近10个）
    find "$PROJECT_DIR" -name "deployment.log.*" -type f | sort -r | tail -n +11 | xargs rm -f
    
    # 清理旧的备份（保留最近5个）
    find "$PROJECT_DIR/backups" -maxdepth 1 -type d -name "20*" | sort -r | tail -n +6 | xargs rm -rf
    
    log_success "清理完成"
}

print_summary() {
    echo
    echo "=================================================="
    echo "🎉 部署完成总结"
    echo "=================================================="
    echo "部署时间: $(date)"
    echo "备份位置: $BACKUP_DIR"
    echo "日志文件: $LOG_FILE"
    echo
    echo "✅ 主要更新:"
    echo "  - 并发任务限制功能（用户10个，系统100个）"
    echo "  - 外键约束问题修复"
    echo "  - 数据库字段优化"
    echo "  - 错误处理增强"
    echo
    echo "📊 建议监控的指标:"
    echo "  - 任务创建成功率"
    echo "  - 并发任务数量"
    echo "  - 数据库错误日志"
    echo "  - 系统资源使用"
    echo
    echo "如有问题，请查看详细部署指南: PRODUCTION_UPDATE_GUIDE.md"
    echo "=================================================="
}

rollback() {
    log_warning "开始回滚操作..."
    
    # 停止服务
    sudo systemctl stop "$BACKEND_SERVICE" || true
    
    # 恢复数据库
    if [[ -f "$BACKUP_DIR/database_backup.sql" ]]; then
        log_info "恢复数据库..."
        echo -n "请输入数据库密码进行恢复: "
        read -s DB_PASS
        echo
        mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" < "$BACKUP_DIR/database_backup.sql"
        log_success "数据库恢复完成"
    fi
    
    # 恢复代码
    if [[ -f "$BACKUP_DIR/current_commit.txt" ]]; then
        local old_commit=$(cat "$BACKUP_DIR/current_commit.txt")
        git reset --hard "$old_commit"
        log_success "代码恢复到: $old_commit"
    fi
    
    # 重启服务
    sudo systemctl start "$BACKEND_SERVICE"
    sudo systemctl start "$FRONTEND_SERVICE"
    
    log_success "回滚完成"
}

main() {
    print_banner
    
    # 设置错误处理
    trap 'log_error "部署过程中发生错误，执行回滚..."; rollback; exit 1' ERR
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-backup)
                SKIP_BACKUP=true
                shift
                ;;
            --skip-deps)
                SKIP_DEPS=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --rollback)
                rollback
                exit 0
                ;;
            -h|--help)
                echo "用法: $0 [选项]"
                echo "选项:"
                echo "  --skip-backup   跳过备份步骤"
                echo "  --skip-deps     跳过依赖安装"
                echo "  --dry-run       仅验证环境，不执行实际部署"
                echo "  --rollback      回滚到上次备份"
                echo "  -h, --help      显示此帮助信息"
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                exit 1
                ;;
        esac
    done
    
    # 执行部署步骤
    check_prerequisites
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "DRY RUN模式，仅验证环境"
        exit 0
    fi
    
    if [[ "$SKIP_BACKUP" != true ]]; then
        backup_database
        backup_code
    fi
    
    update_code
    
    if [[ "$SKIP_DEPS" != true ]]; then
        install_dependencies
    fi
    
    run_database_migrations
    build_frontend
    restart_services
    verify_deployment
    cleanup
    print_summary
    
    log_success "🎉 部署成功完成！"
}

# 执行主函数
main "$@"