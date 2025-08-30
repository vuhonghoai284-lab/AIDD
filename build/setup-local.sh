#!/bin/bash

# ============================================================================
# AI Document Testing System - 本地环境快速设置脚本
# ============================================================================
# 功能：一键完成本地开发环境的初始化、构建和部署
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
QUICK_SETUP=false
SKIP_DEPENDENCIES=false
USE_DOCKER=false
FRONTEND_PORT=3000
BACKEND_PORT=8080

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

# 显示欢迎信息
show_welcome() {
    echo -e "${CYAN}"
    cat << "EOF"
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   🚀 AI Document Testing System - 本地环境快速设置                      ║
║                                                                          ║
║   这个脚本将帮助您快速设置完整的本地开发环境                           ║
║   包括：环境检查、配置初始化、应用构建、服务部署                       ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

# 显示使用方法
show_help() {
    echo "AI Document Testing System - 本地环境快速设置脚本"
    echo ""
    echo "使用方法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help              显示此帮助信息"
    echo "  -q, --quick             快速设置模式（跳过交互确认）"
    echo "  -d, --docker            使用Docker进行设置"
    echo "  --skip-deps             跳过依赖检查和安装"
    echo "  --frontend-port PORT    前端端口 [默认: 3000]"
    echo "  --backend-port PORT     后端端口 [默认: 8080]"
    echo ""
    echo "模式:"
    echo "  默认模式                完整的交互式设置流程"
    echo "  快速模式 (-q)           自动选择默认选项，无需交互"
    echo "  Docker模式 (-d)         使用Docker容器化部署"
    echo ""
    echo "示例:"
    echo "  $0                      # 完整交互式设置"
    echo "  $0 --quick              # 快速自动设置"
    echo "  $0 --docker             # 使用Docker设置"
    echo ""
}

# 解析命令行参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -q|--quick)
                QUICK_SETUP=true
                shift
                ;;
            -d|--docker)
                USE_DOCKER=true
                shift
                ;;
            --skip-deps)
                SKIP_DEPENDENCIES=true
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
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# 交互式确认
confirm_action() {
    local message="$1"
    local default="${2:-y}"
    
    if [[ "$QUICK_SETUP" == "true" ]]; then
        log_info "$message (快速模式: 自动选择)"
        return 0
    fi
    
    while true; do
        if [[ "$default" == "y" ]]; then
            read -p "$(echo -e ${YELLOW}[CONFIRM]${NC} $message [Y/n]: )" yn
            yn=${yn:-y}
        else
            read -p "$(echo -e ${YELLOW}[CONFIRM]${NC} $message [y/N]: )" yn
            yn=${yn:-n}
        fi
        
        case $yn in
            [Yy]* ) return 0;;
            [Nn]* ) return 1;;
            * ) echo "请输入 yes 或 no";;
        esac
    done
}

# 系统环境检查
check_system_requirements() {
    log_header "检查系统环境"
    
    local missing_tools=()
    local optional_tools=()
    
    # 检查必需工具
    if ! command -v node &> /dev/null; then
        missing_tools+=("Node.js (https://nodejs.org)")
    else
        local node_version=$(node --version)
        log_success "Node.js: $node_version"
    fi
    
    if ! command -v npm &> /dev/null; then
        missing_tools+=("npm (Node.js包管理器)")
    else
        local npm_version=$(npm --version)
        log_success "npm: $npm_version"
    fi
    
    if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
        missing_tools+=("Python 3.8+ (https://python.org)")
    else
        local python_cmd="python3"
        if ! command -v python3 &> /dev/null; then
            python_cmd="python"
        fi
        local python_version=$($python_cmd --version 2>&1)
        log_success "Python: $python_version"
    fi
    
    if ! command -v pip3 &> /dev/null && ! command -v pip &> /dev/null; then
        missing_tools+=("pip (Python包管理器)")
    else
        local pip_cmd="pip3"
        if ! command -v pip3 &> /dev/null; then
            pip_cmd="pip"
        fi
        local pip_version=$($pip_cmd --version | cut -d' ' -f2)
        log_success "pip: $pip_version"
    fi
    
    # 检查可选工具
    if ! command -v git &> /dev/null; then
        optional_tools+=("Git")
    else
        log_success "Git: $(git --version | cut -d' ' -f3)"
    fi
    
    if ! command -v docker &> /dev/null; then
        optional_tools+=("Docker")
        if [[ "$USE_DOCKER" == "true" ]]; then
            missing_tools+=("Docker (Docker模式必需)")
        fi
    else
        log_success "Docker: $(docker --version | cut -d' ' -f3 | tr -d ',')"
    fi
    
    # 报告检查结果
    if [[ ${#missing_tools[@]} -ne 0 ]]; then
        log_error "缺少必需工具："
        for tool in "${missing_tools[@]}"; do
            echo "  ❌ $tool"
        done
        echo ""
        echo -e "${YELLOW}请安装以上工具后重新运行此脚本${NC}"
        echo -e "${BLUE}安装指南：查看 LOCAL_DEPLOYMENT_GUIDE.md${NC}"
        exit 1
    fi
    
    if [[ ${#optional_tools[@]} -ne 0 ]]; then
        log_warning "可选工具未安装："
        for tool in "${optional_tools[@]}"; do
            echo "  ⚠️  $tool"
        done
    fi
    
    log_success "系统环境检查通过"
}

# 初始化配置文件
initialize_config() {
    log_header "初始化配置文件"
    
    # 创建必要目录
    mkdir -p data/{uploads,temp,reports} logs pids
    
    # 设置环境变量文件
    if [[ ! -f ".env" ]]; then
        if [[ -f ".env.template" ]]; then
            log_info "创建环境变量文件..."
            cp .env.template .env
            
            # 更新端口配置
            sed -i "s/FRONTEND_PORT=.*/FRONTEND_PORT=$FRONTEND_PORT/" .env
            sed -i "s/BACKEND_PORT=.*/BACKEND_PORT=$BACKEND_PORT/" .env
            
            log_success "环境变量文件已创建: .env"
            
            if ! confirm_action "是否需要编辑环境变量文件？"; then
                log_info "使用默认配置继续..."
            else
                echo -e "${CYAN}请编辑 .env 文件，配置以下重要项目：${NC}"
                echo "  - OPENAI_API_KEY (如有AI服务密钥)"
                echo "  - GITEE_CLIENT_ID/SECRET (如需第三方登录)"
                echo "  - 其他自定义配置"
                echo ""
                read -p "编辑完成后按回车继续..."
            fi
        else
            log_error ".env.template 文件不存在"
            return 1
        fi
    else
        log_success "环境变量文件已存在: .env"
    fi
    
    # 设置后端配置
    if [[ ! -f "backend/config.local.yaml" ]]; then
        if [[ -f "config.local.yaml" ]]; then
            log_info "复制本地配置文件..."
            cp config.local.yaml backend/config.local.yaml
            log_success "本地配置文件已创建: backend/config.local.yaml"
        elif [[ -f "backend/config.yaml" ]]; then
            log_info "从默认配置创建本地配置..."
            cp backend/config.yaml backend/config.local.yaml
            log_success "本地配置文件已创建: backend/config.local.yaml"
        else
            log_error "找不到配置模板文件"
            return 1
        fi
    else
        log_success "本地配置文件已存在: backend/config.local.yaml"
    fi
    
    log_success "配置文件初始化完成"
}

# 构建应用
build_application() {
    log_header "构建应用"
    
    # 检查构建脚本
    if [[ ! -f "./build-local.sh" ]]; then
        log_error "构建脚本不存在: ./build-local.sh"
        return 1
    fi
    
    # 设置执行权限
    chmod +x ./build-local.sh
    
    # 选择构建选项
    local build_args=""
    
    if [[ "$QUICK_SETUP" == "false" ]]; then
        echo -e "${CYAN}构建选项：${NC}"
        echo "1. 完整构建（包含测试）"
        echo "2. 快速构建（跳过测试）"
        echo "3. 自定义构建选项"
        
        read -p "请选择 [1-3]: " build_choice
        
        case $build_choice in
            1)
                build_args=""
                ;;
            2)
                build_args="--skip-tests"
                ;;
            3)
                echo "可用选项："
                echo "  --skip-tests      跳过测试"
                echo "  --skip-frontend   跳过前端构建"
                echo "  --skip-backend    跳过后端构建"
                echo "  --verbose         详细输出"
                echo "  --clean           清理重新构建"
                read -p "请输入构建参数: " build_args
                ;;
            *)
                log_warning "无效选择，使用默认构建"
                build_args=""
                ;;
        esac
    else
        build_args="--skip-tests"  # 快速模式默认跳过测试
    fi
    
    log_info "开始构建应用..."
    log_info "构建参数: $build_args"
    
    if ./build-local.sh $build_args; then
        log_success "应用构建完成"
    else
        log_error "应用构建失败"
        return 1
    fi
}

# 部署应用
deploy_application() {
    log_header "部署应用"
    
    # 检查部署脚本
    if [[ ! -f "./deploy-local.sh" ]]; then
        log_error "部署脚本不存在: ./deploy-local.sh"
        return 1
    fi
    
    # 设置执行权限
    chmod +x ./deploy-local.sh
    
    # 选择部署选项
    local deploy_args="--frontend-port $FRONTEND_PORT --backend-port $BACKEND_PORT"
    
    if [[ "$USE_DOCKER" == "true" ]]; then
        deploy_args="$deploy_args --docker"
    fi
    
    if [[ "$QUICK_SETUP" == "false" ]]; then
        echo -e "${CYAN}部署模式：${NC}"
        echo "1. 开发模式（热重载、详细日志）"
        echo "2. 生产模式（优化性能）"
        echo "3. 测试模式（测试配置）"
        
        read -p "请选择 [1-3]: " deploy_choice
        
        case $deploy_choice in
            1)
                deploy_args="$deploy_args --mode dev"
                ;;
            2)
                deploy_args="$deploy_args --mode prod"
                ;;
            3)
                deploy_args="$deploy_args --mode test"
                ;;
            *)
                log_warning "无效选择，使用开发模式"
                deploy_args="$deploy_args --mode dev"
                ;;
        esac
    else
        deploy_args="$deploy_args --mode dev"  # 快速模式默认开发模式
    fi
    
    log_info "开始部署应用..."
    log_info "部署参数: $deploy_args"
    
    if ./deploy-local.sh $deploy_args; then
        log_success "应用部署完成"
        return 0
    else
        log_error "应用部署失败"
        return 1
    fi
}

# 显示设置结果
show_setup_result() {
    log_header "设置完成"
    
    echo -e "${GREEN}🎉 本地环境设置成功！${NC}"
    echo ""
    echo -e "${CYAN}访问地址：${NC}"
    echo "  🌐 前端应用: http://localhost:$FRONTEND_PORT"
    echo "  🔧 后端API: http://localhost:$BACKEND_PORT"
    echo "  📚 API文档: http://localhost:$BACKEND_PORT/docs"
    echo ""
    echo -e "${CYAN}常用命令：${NC}"
    echo "  📊 查看状态: ./deploy-local.sh status"
    echo "  📝 查看日志: ./deploy-local.sh logs"
    echo "  🔄 重启服务: ./deploy-local.sh restart"
    echo "  ⏹️  停止服务: ./deploy-local.sh stop"
    echo ""
    echo -e "${CYAN}开发建议：${NC}"
    echo "  1. 前端代码修改会自动重载"
    echo "  2. 后端代码修改需要重启服务"
    echo "  3. 查看 LOCAL_DEPLOYMENT_GUIDE.md 了解更多"
    echo ""
    echo -e "${YELLOW}注意事项：${NC}"
    echo "  - 服务运行在后台，可以关闭终端"
    echo "  - 重启电脑后需要重新运行部署命令"
    echo "  - 定期更新依赖包以获得最新功能"
    echo ""
    
    # 显示下一步操作
    if [[ "$QUICK_SETUP" == "false" ]]; then
        echo -e "${CYAN}下一步操作建议：${NC}"
        echo "1. 🌐 在浏览器中访问 http://localhost:$FRONTEND_PORT"
        echo "2. 📖 查看用户指南了解功能使用"
        echo "3. 🔧 根据需要修改配置文件"
        echo "4. 🧪 尝试上传文档进行测试"
        echo ""
        
        if confirm_action "是否现在打开前端应用？"; then
            if command -v xdg-open &> /dev/null; then
                xdg-open "http://localhost:$FRONTEND_PORT"
            elif command -v open &> /dev/null; then
                open "http://localhost:$FRONTEND_PORT"
            elif command -v start &> /dev/null; then
                start "http://localhost:$FRONTEND_PORT"
            else
                log_info "请手动在浏览器中打开: http://localhost:$FRONTEND_PORT"
            fi
        fi
    fi
}

# 错误处理
handle_error() {
    local exit_code=$?
    log_error "设置过程中出现错误 (退出码: $exit_code)"
    echo ""
    echo -e "${YELLOW}故障排除建议：${NC}"
    echo "1. 检查系统要求是否满足"
    echo "2. 查看错误日志获取详细信息"
    echo "3. 尝试清理后重新设置："
    echo "   ./build-local.sh --clean"
    echo "4. 查看故障排除文档："
    echo "   LOCAL_DEPLOYMENT_GUIDE.md"
    echo ""
    echo -e "${BLUE}获取帮助：${NC}"
    echo "- 查看项目文档"
    echo "- 提交GitHub Issue"
    echo "- 查看日志文件: logs/"
    
    exit $exit_code
}

# 主函数
main() {
    # 设置错误处理
    trap handle_error ERR
    
    # 显示欢迎信息
    show_welcome
    
    # 记录开始时间
    local start_time=$(date +%s)
    
    # 解析参数
    parse_args "$@"
    
    # 进入项目目录
    cd "$SCRIPT_DIR"
    
    log_info "项目目录: $SCRIPT_DIR"
    log_info "快速模式: $QUICK_SETUP"
    log_info "使用Docker: $USE_DOCKER"
    log_info "前端端口: $FRONTEND_PORT"
    log_info "后端端口: $BACKEND_PORT"
    
    # 执行设置步骤
    if [[ "$SKIP_DEPENDENCIES" == "false" ]]; then
        check_system_requirements
    fi
    
    initialize_config
    build_application
    deploy_application
    
    # 计算设置时间
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))
    
    log_success "环境设置完成，总耗时: ${minutes}分${seconds}秒"
    
    # 显示结果
    show_setup_result
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi