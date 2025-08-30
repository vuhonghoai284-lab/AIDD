#!/bin/bash

# AI文档测试系统 - 统一构建脚本
# 支持本地构建和CI环境，构建标准化的Docker镜像

set -e

# 默认配置
REGISTRY=${REGISTRY:-"ghcr.io/wantiantian/ai_docs2"}
VERSION=${VERSION:-"latest"}
PLATFORM=${PLATFORM:-"linux/amd64"}
PUSH=${PUSH:-"false"}
BUILD_ARGS=""
CACHE_FROM=""
CACHE_TO=""

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
AI文档测试系统 - 自动构建脚本

用法: $0 [选项] [动作]

选项:
  -v, --version VERSION    指定版本标签 (默认: latest)
  -r, --registry REGISTRY  指定镜像仓库 (默认: ghcr.io/wantiantian)
  -p, --platforms PLATFORMS 指定构建平台 (默认: linux/amd64,linux/arm64)
  --push                   构建后推送到仓库
  --no-cache               不使用构建缓存
  -h, --help               显示此帮助信息

动作:
  build                    构建所有镜像 (默认)
  backend                  仅构建后端镜像
  frontend                 仅构建前端镜像
  push                     推送所有镜像
  clean                    清理本地镜像

环境变量:
  DOCKER_BUILDKIT=1        启用BuildKit (推荐)
  VERSION                  镜像版本标签
  REGISTRY                 镜像仓库地址
  PLATFORMS                构建平台列表

示例:
  $0 build                 # 构建所有镜像
  $0 --version v1.0.0 --push build  # 构建并推送v1.0.0版本
  $0 backend               # 仅构建后端镜像
  $0 clean                 # 清理本地镜像
EOF
}

# 检查Docker环境
check_docker() {
    log_info "检查Docker环境..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker服务未启动，请启动Docker服务"
        exit 1
    fi
    
    # 启用BuildKit
    export DOCKER_BUILDKIT=1
    export DOCKER_CLI_EXPERIMENTAL=enabled
    
    log_success "Docker环境检查通过"
}

# 检查buildx支持
check_buildx() {
    log_info "检查Docker Buildx支持..."
    
    if ! docker buildx version &> /dev/null; then
        log_error "Docker Buildx未安装，无法进行多平台构建"
        exit 1
    fi
    
    # 创建并使用buildx实例
    if ! docker buildx inspect ai-docs-builder &> /dev/null; then
        log_info "创建buildx实例..."
        docker buildx create --name ai-docs-builder --use
        docker buildx bootstrap
    else
        docker buildx use ai-docs-builder
    fi
    
    log_success "Docker Buildx准备就绪"
}

# 构建后端镜像
build_backend() {
    log_info "开始构建后端镜像..."
    
    local image_name="${REGISTRY}/${PROJECT_NAME}/backend:${VERSION}"
    local build_args=""
    
    if [[ "$PUSH" == "true" ]]; then
        build_args="--push"
    else
        build_args="--load"
    fi
    
    if [[ "$NO_CACHE" == "true" ]]; then
        build_args="$build_args --no-cache"
    fi
    
    docker buildx build \
        --platform $PLATFORMS \
        --tag $image_name \
        --tag "${REGISTRY}/${PROJECT_NAME}/backend:latest" \
        $build_args \
        --file ./backend/Dockerfile \
        ./backend/
    
    log_success "后端镜像构建完成: $image_name"
}

# 构建前端镜像
build_frontend() {
    log_info "开始构建前端镜像..."
    
    local image_name="${REGISTRY}/${PROJECT_NAME}/frontend:${VERSION}"
    local build_args=""
    
    if [[ "$PUSH" == "true" ]]; then
        build_args="--push"
    else
        build_args="--load"
    fi
    
    if [[ "$NO_CACHE" == "true" ]]; then
        build_args="$build_args --no-cache"
    fi
    
    docker buildx build \
        --platform $PLATFORMS \
        --tag $image_name \
        --tag "${REGISTRY}/${PROJECT_NAME}/frontend:latest" \
        $build_args \
        --file ./frontend/Dockerfile \
        ./frontend/
    
    log_success "前端镜像构建完成: $image_name"
}

# 推送镜像
push_images() {
    log_info "推送镜像到仓库..."
    
    docker push "${REGISTRY}/${PROJECT_NAME}/backend:${VERSION}"
    docker push "${REGISTRY}/${PROJECT_NAME}/backend:latest"
    docker push "${REGISTRY}/${PROJECT_NAME}/frontend:${VERSION}"
    docker push "${REGISTRY}/${PROJECT_NAME}/frontend:latest"
    
    log_success "镜像推送完成"
}

# 清理镜像
clean_images() {
    log_info "清理本地镜像..."
    
    # 清理指定项目的镜像
    docker images "${REGISTRY}/${PROJECT_NAME}/*" --quiet | xargs -r docker rmi -f
    
    # 清理悬挂镜像
    docker image prune -f
    
    log_success "镜像清理完成"
}

# 显示构建信息
show_build_info() {
    log_info "构建信息:"
    echo "  项目名称: $PROJECT_NAME"
    echo "  版本标签: $VERSION"
    echo "  镜像仓库: $REGISTRY"
    echo "  构建平台: $PLATFORMS"
    echo "  推送镜像: ${PUSH:-false}"
    echo "  使用缓存: ${NO_CACHE:-false}"
    echo ""
}

# 主函数
main() {
    local action="build"
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -v|--version)
                VERSION="$2"
                shift 2
                ;;
            -r|--registry)
                REGISTRY="$2"
                shift 2
                ;;
            -p|--platforms)
                PLATFORMS="$2"
                shift 2
                ;;
            --push)
                PUSH="true"
                shift
                ;;
            --no-cache)
                NO_CACHE="true"
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            build|backend|frontend|push|clean)
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
    
    # 显示构建信息
    show_build_info
    
    # 检查环境
    check_docker
    
    # 执行对应动作
    case $action in
        build)
            check_buildx
            build_backend
            build_frontend
            ;;
        backend)
            check_buildx
            build_backend
            ;;
        frontend)
            check_buildx
            build_frontend
            ;;
        push)
            push_images
            ;;
        clean)
            clean_images
            ;;
        *)
            log_error "未知动作: $action"
            show_help
            exit 1
            ;;
    esac
    
    log_success "操作完成!"
}

# 运行主函数
main "$@"