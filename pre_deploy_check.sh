#!/bin/bash

# 部署前环境检查脚本
# 用于验证生产环境是否准备好进行更新

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✅]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[⚠️]${NC} $1"
}

log_error() {
    echo -e "${RED}[❌]${NC} $1"
}

# 检查计数器
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNING=0

check_item() {
    local description=$1
    local command=$2
    local warning_only=${3:-false}
    
    echo -n "检查 $description... "
    
    if eval "$command" &>/dev/null; then
        log_success "$description"
        ((CHECKS_PASSED++))
        return 0
    else
        if [[ "$warning_only" == true ]]; then
            log_warning "$description (可选)"
            ((CHECKS_WARNING++))
            return 1
        else
            log_error "$description"
            ((CHECKS_FAILED++))
            return 1
        fi
    fi
}

print_header() {
    echo "=================================================="
    echo "🔍 生产环境部署前检查"
    echo "=================================================="
    echo "检查时间: $(date)"
    echo
}

# 1. 系统环境检查
check_system() {
    echo "📋 1. 系统环境检查"
    echo "----------------------------------------"
    
    check_item "操作系统类型" "uname -s"
    check_item "系统架构" "uname -m"
    
    # 检查磁盘空间（至少2GB）
    local available_kb=$(df . | awk 'NR==2 {print $4}')
    if [[ $available_kb -gt 2097152 ]]; then
        log_success "磁盘空间充足 ($(( available_kb / 1024 / 1024 ))GB可用)"
        ((CHECKS_PASSED++))
    else
        log_warning "磁盘空间不足2GB ($(( available_kb / 1024 ))MB可用)"
        ((CHECKS_WARNING++))
    fi
    
    # 检查内存
    if command -v free &>/dev/null; then
        local mem_available=$(free -m | awk '/^Mem:/ {print $7}')
        if [[ $mem_available -gt 512 ]]; then
            log_success "内存充足 (${mem_available}MB可用)"
            ((CHECKS_PASSED++))
        else
            log_warning "可用内存较少 (${mem_available}MB)"
            ((CHECKS_WARNING++))
        fi
    fi
    
    echo
}

# 2. 必要命令检查
check_commands() {
    echo "💻 2. 必要命令检查"
    echo "----------------------------------------"
    
    local required_commands=("git" "python3" "pip3" "mysql" "mysqldump" "npm" "node" "curl")
    
    for cmd in "${required_commands[@]}"; do
        if command -v "$cmd" &>/dev/null; then
            local version=""
            case $cmd in
                python3) version="($(python3 --version 2>&1))" ;;
                node) version="($(node --version))" ;;
                npm) version="($(npm --version))" ;;
                mysql) version="($(mysql --version | cut -d' ' -f3))" ;;
                git) version="($(git --version | cut -d' ' -f3))" ;;
            esac
            log_success "$cmd $version"
            ((CHECKS_PASSED++))
        else
            log_error "缺少命令: $cmd"
            ((CHECKS_FAILED++))
        fi
    done
    
    echo
}

# 3. Python环境检查
check_python() {
    echo "🐍 3. Python环境检查"
    echo "----------------------------------------"
    
    check_item "Python版本 >= 3.8" "python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)'"
    check_item "pip可用" "pip3 --version"
    
    # 检查关键Python包
    local python_packages=("sqlalchemy" "fastapi" "uvicorn" "pydantic")
    for pkg in "${python_packages[@]}"; do
        check_item "Python包: $pkg" "python3 -c 'import $pkg'" true
    done
    
    echo
}

# 4. Node.js环境检查
check_nodejs() {
    echo "📦 4. Node.js环境检查"
    echo "----------------------------------------"
    
    check_item "Node.js版本 >= 14" "node -e 'process.exit(parseInt(process.version.slice(1)) >= 14 ? 0 : 1)'"
    check_item "npm可用" "npm --version"
    
    # 检查全局包
    check_item "全局包: pm2" "npm list -g pm2" true
    
    echo
}

# 5. 数据库连接检查
check_database() {
    echo "🗄️  5. 数据库连接检查"
    echo "----------------------------------------"
    
    # 检查MySQL服务
    if systemctl is-active --quiet mysql 2>/dev/null; then
        log_success "MySQL服务运行中"
        ((CHECKS_PASSED++))
    elif service mysql status &>/dev/null; then
        log_success "MySQL服务运行中"
        ((CHECKS_PASSED++))
    else
        log_error "MySQL服务未运行"
        ((CHECKS_FAILED++))
    fi
    
    # 测试数据库连接（需要用户输入）
    echo -n "测试数据库连接 (输入数据库密码): "
    read -s db_pass
    echo
    
    if mysql -u root -p"$db_pass" -e "SELECT 1" &>/dev/null; then
        log_success "数据库连接正常"
        ((CHECKS_PASSED++))
        
        # 检查目标数据库
        if mysql -u root -p"$db_pass" -e "USE ai_doc_test; SELECT 1" &>/dev/null; then
            log_success "目标数据库 ai_doc_test 存在"
            ((CHECKS_PASSED++))
        else
            log_error "目标数据库 ai_doc_test 不存在"
            ((CHECKS_FAILED++))
        fi
    else
        log_error "数据库连接失败"
        ((CHECKS_FAILED++))
    fi
    
    echo
}

# 6. 项目结构检查
check_project() {
    echo "📁 6. 项目结构检查"
    echo "----------------------------------------"
    
    # 检查关键目录
    local required_dirs=("backend" "frontend" "backend/app" "frontend/src")
    for dir in "${required_dirs[@]}"; do
        check_item "目录: $dir" "test -d '$dir'"
    done
    
    # 检查关键文件
    local required_files=(
        "backend/app/main.py"
        "backend/requirements.txt"
        "backend/config.yaml"
        "frontend/package.json"
        "backend/migrate_user_concurrency.py"
        "backend/fix_foreign_key_constraints.py"
    )
    
    for file in "${required_files[@]}"; do
        check_item "文件: $file" "test -f '$file'"
    done
    
    echo
}

# 7. 服务状态检查
check_services() {
    echo "🔧 7. 服务状态检查"
    echo "----------------------------------------"
    
    # 检查后端服务
    local backend_services=("ai-doc-backend" "ai_doc_backend" "python")
    local backend_running=false
    
    for service in "${backend_services[@]}"; do
        if systemctl is-active --quiet "$service" 2>/dev/null; then
            log_success "后端服务运行中: $service"
            ((CHECKS_PASSED++))
            backend_running=true
            break
        fi
    done
    
    if [[ "$backend_running" == false ]]; then
        # 检查是否有Python进程在运行
        if pgrep -f "python.*main.py" &>/dev/null; then
            log_success "Python后端进程运行中"
            ((CHECKS_PASSED++))
        else
            log_warning "未检测到后端服务运行"
            ((CHECKS_WARNING++))
        fi
    fi
    
    # 检查Web服务器
    local web_services=("nginx" "apache2" "httpd")
    local web_running=false
    
    for service in "${web_services[@]}"; do
        if systemctl is-active --quiet "$service" 2>/dev/null; then
            log_success "Web服务器运行中: $service"
            ((CHECKS_PASSED++))
            web_running=true
            break
        fi
    done
    
    if [[ "$web_running" == false ]]; then
        log_warning "未检测到Web服务器运行"
        ((CHECKS_WARNING++))
    fi
    
    echo
}

# 8. 网络连接检查
check_network() {
    echo "🌐 8. 网络连接检查"
    echo "----------------------------------------"
    
    # 检查本地端口
    local ports=("8080" "3000" "80" "443")
    for port in "${ports[@]}"; do
        if netstat -tuln 2>/dev/null | grep ":$port " &>/dev/null; then
            log_success "端口 $port 正在监听"
            ((CHECKS_PASSED++))
        else
            check_item "端口 $port" "false" true
        fi
    done
    
    # 检查网络连通性
    check_item "互联网连接" "curl -s --max-time 5 http://www.google.com" true
    
    echo
}

# 9. Git状态检查
check_git() {
    echo "📝 9. Git状态检查"
    echo "----------------------------------------"
    
    if [[ -d ".git" ]]; then
        log_success "Git仓库"
        ((CHECKS_PASSED++))
        
        # 检查当前分支
        local current_branch=$(git branch --show-current)
        if [[ "$current_branch" == "main" ]] || [[ "$current_branch" == "master" ]]; then
            log_success "当前分支: $current_branch"
            ((CHECKS_PASSED++))
        else
            log_warning "当前分支: $current_branch (建议使用main分支)"
            ((CHECKS_WARNING++))
        fi
        
        # 检查是否有未提交的更改
        if git diff-index --quiet HEAD --; then
            log_success "工作区干净"
            ((CHECKS_PASSED++))
        else
            log_warning "工作区有未提交的更改"
            ((CHECKS_WARNING++))
        fi
        
        # 检查远程连接
        if git remote get-url origin &>/dev/null; then
            log_success "Git远程仓库配置"
            ((CHECKS_PASSED++))
        else
            log_warning "Git远程仓库未配置"
            ((CHECKS_WARNING++))
        fi
    else
        log_error "不是Git仓库"
        ((CHECKS_FAILED++))
    fi
    
    echo
}

# 10. 权限检查
check_permissions() {
    echo "🔐 10. 权限检查"
    echo "----------------------------------------"
    
    # 检查sudo权限
    if sudo -n true 2>/dev/null; then
        log_success "sudo权限可用"
        ((CHECKS_PASSED++))
    else
        log_warning "需要sudo权限来重启服务"
        ((CHECKS_WARNING++))
    fi
    
    # 检查文件权限
    check_item "项目目录可写" "test -w ."
    check_item "后端目录可写" "test -w backend"
    check_item "前端目录可写" "test -w frontend"
    
    echo
}

print_summary() {
    echo "=================================================="
    echo "📊 检查结果总结"
    echo "=================================================="
    echo -e "✅ 通过: ${GREEN}$CHECKS_PASSED${NC} 项"
    echo -e "⚠️  警告: ${YELLOW}$CHECKS_WARNING${NC} 项"
    echo -e "❌ 失败: ${RED}$CHECKS_FAILED${NC} 项"
    echo
    
    if [[ $CHECKS_FAILED -eq 0 ]]; then
        if [[ $CHECKS_WARNING -eq 0 ]]; then
            echo -e "${GREEN}🎉 环境检查完全通过，可以开始部署！${NC}"
            exit 0
        else
            echo -e "${YELLOW}⚠️  环境基本满足条件，但有一些警告项需要注意${NC}"
            echo "建议在部署时密切关注这些警告项"
            exit 0
        fi
    else
        echo -e "${RED}❌ 环境检查未通过，请解决失败项后再进行部署${NC}"
        echo
        echo "建议处理步骤："
        echo "1. 安装缺失的命令和依赖"
        echo "2. 检查数据库连接和配置"
        echo "3. 确保必要的服务正在运行"
        echo "4. 验证项目结构完整性"
        exit 1
    fi
}

main() {
    print_header
    
    check_system
    check_commands
    check_python
    check_nodejs
    check_database
    check_project
    check_services
    check_network
    check_git
    check_permissions
    
    print_summary
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            echo "用法: $0 [选项]"
            echo "选项:"
            echo "  -h, --help      显示此帮助信息"
            echo
            echo "此脚本会检查生产环境是否准备好进行更新部署"
            exit 0
            ;;
        *)
            echo "未知参数: $1"
            echo "使用 -h 或 --help 查看帮助"
            exit 1
            ;;
    esac
done

main