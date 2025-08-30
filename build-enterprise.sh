#!/bin/bash

# AI文档测试系统 - 企业级构建脚本
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
NC='\033[0m'

print_info() { echo -e "${BLUE}ℹ️ $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_header() { echo -e "${BLUE}🏗️ $1${NC}"; }

show_help() {
    cat << EOF
AI文档测试系统 - 企业级构建脚本

用法: $0 [选项] <component>

组件:
  backend     构建后端服务镜像
  frontend    构建前端服务镜像
  all         构建所有组件

选项:
  -r, --registry REGISTRY    镜像仓库地址 (默认: ghcr.io/wantiantian/ai_docs2)
  -v, --version VERSION      镜像版本标签 (默认: latest)
  -p, --platform PLATFORM   目标平台 (默认: linux/amd64)
  --push                     推送到镜像仓库
  --ci                       CI环境模式 (启用缓存优化)
  --multi-arch               多架构构建 (linux/amd64,linux/arm64)
  --test                     运行基础API测试 (推荐)
  --full-tests               运行完整测试套件
  --quality-check            运行代码质量检查
  --fail-on-test-false       测试失败不阻断构建 (默认阻断)
  --no-cache                 禁用构建缓存
  -h, --help                 显示帮助信息

环境变量:
  REGISTRY                   镜像仓库地址
  VERSION                    版本标签
  DOCKER_BUILDKIT            启用BuildKit (推荐设置为1)
  
示例:
  # 本地构建
  $0 backend --test                    # 构建后端并运行API测试
  $0 frontend -v v2.0.0 --quality-check  # 构建前端并检查代码质量
  $0 all --test --full-tests              # 构建所有组件并运行完整测试
  
  # CI环境构建 (推荐配置)
  $0 all --ci --push --multi-arch -v \$VERSION --test --quality-check
  
  # 生产构建 (严格质量控制)
  REGISTRY=myregistry.com/aidd $0 all --push -v v1.0.0 --test --quality-check
  
  # 快速构建 (跳过测试)
  $0 all --fail-on-test-false --no-cache

构建产物:
  - 后端镜像: \$REGISTRY/backend:\$VERSION
  - 前端镜像: \$REGISTRY/frontend:\$VERSION
  - 镜像清单: build-manifest.json
  - 部署配置: release/docker-compose.yml
EOF
}

# 检查构建环境
check_environment() {
    print_info "检查构建环境..."
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装"
        exit 1
    fi
    
    # 检查Docker Buildx
    if ! docker buildx version &> /dev/null; then
        print_error "Docker Buildx 未安装"
        exit 1
    fi
    
    # 启用BuildKit
    if [[ "${DOCKER_BUILDKIT:-1}" == "1" ]]; then
        export DOCKER_BUILDKIT=1
        print_info "已启用Docker BuildKit"
    fi
    
    print_success "构建环境检查完成"
}

# 设置构建参数
setup_build_args() {
    local component="$1"
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    local git_commit=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    local git_branch=$(git branch --show-current 2>/dev/null || echo "unknown")
    
    BUILD_ARGS="--build-arg BUILDTIME=${timestamp}"
    BUILD_ARGS="${BUILD_ARGS} --build-arg VERSION=${VERSION}"
    BUILD_ARGS="${BUILD_ARGS} --build-arg GIT_COMMIT=${git_commit}"
    BUILD_ARGS="${BUILD_ARGS} --build-arg GIT_BRANCH=${git_branch}"
    
    # 组件特定的构建参数
    case "$component" in
        "frontend")
            BUILD_ARGS="${BUILD_ARGS} --build-arg VITE_APP_VERSION=${VERSION}"
            ;;
    esac
}

# 设置缓存参数
setup_cache() {
    local component="$1"
    
    if [[ "$CI_MODE" == "true" ]]; then
        CACHE_FROM="--cache-from type=gha,scope=${component}"
        CACHE_TO="--cache-to type=gha,mode=max,scope=${component}"
    else
        # 本地缓存
        CACHE_FROM="--cache-from type=local,src=.cache/${component}"
        CACHE_TO="--cache-to type=local,dest=.cache/${component},mode=max"
        mkdir -p .cache/${component}
    fi
}

# 构建单个组件
build_component() {
    local component="$1"
    local context_dir="$1"
    local image_name="${REGISTRY}/${component}:${VERSION}"
    
    print_header "构建 ${component} 镜像..."
    
    # 检查构建上下文
    if [[ ! -d "$context_dir" ]]; then
        print_error "构建上下文目录不存在: $context_dir"
        exit 1
    fi
    
    if [[ ! -f "$context_dir/Dockerfile" ]]; then
        print_error "Dockerfile不存在: $context_dir/Dockerfile"
        exit 1
    fi
    
    # 设置构建和缓存参数
    setup_build_args "$component"
    setup_cache "$component"
    
    # 构建命令
    local build_cmd="docker buildx build"
    build_cmd="${build_cmd} --platform ${PLATFORM}"
    build_cmd="${build_cmd} ${BUILD_ARGS}"
    
    if [[ "$NO_CACHE" != "true" ]]; then
        build_cmd="${build_cmd} ${CACHE_FROM} ${CACHE_TO}"
    else
        build_cmd="${build_cmd} --no-cache"
    fi
    
    build_cmd="${build_cmd} --tag ${image_name}"
    
    if [[ "$PUSH" == "true" ]]; then
        build_cmd="${build_cmd} --push"
    else
        build_cmd="${build_cmd} --load"
    fi
    
    build_cmd="${build_cmd} ${context_dir}"
    
    print_info "构建命令: $build_cmd"
    
    # 执行构建
    if eval "$build_cmd"; then
        print_success "${component} 镜像构建完成"
        
        # 记录构建信息
        echo "{" >> build-info.json
        echo "  \"component\": \"${component}\"," >> build-info.json
        echo "  \"image\": \"${image_name}\"," >> build-info.json
        echo "  \"version\": \"${VERSION}\"," >> build-info.json
        echo "  \"platform\": \"${PLATFORM}\"," >> build-info.json
        echo "  \"timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"" >> build-info.json
        echo "}," >> build-info.json
        
        return 0
    else
        print_error "${component} 镜像构建失败"
        return 1
    fi
}

# 运行测试
run_tests() {
    local component="$1"
    
    print_info "运行 ${component} 测试..."
    
    case "$component" in
        "backend")
            # 后端API基础测试 - 关键质量保障
            if [[ -f "backend/requirements.txt" ]]; then
                print_info "执行后端API基础测试..."
                
                # 创建临时测试容器
                local test_container="aidd-backend-test-$$"
                
                # 运行API测试，排除批量和并发测试，快速验证核心功能
                if docker run --name "$test_container" --rm \
                    -v "$(pwd)/backend:/app" \
                    -w /app \
                    python:3.12-slim \
                    bash -c "
                        echo '🔧 安装测试依赖...'
                        pip install -r requirements.txt > /dev/null 2>&1
                        
                        echo '🧪 运行API基础测试...'
                        python -m pytest tests/api \
                            --tb=no \
                            -v \
                            -k 'not (batch or concurrency or concurrent)' \
                            --maxfail=1 \
                            --disable-warnings
                    "; then
                    print_success "后端API测试通过"
                    
                    # 可选：运行单元测试
                    if [[ "$FULL_TESTS" == "true" ]]; then
                        print_info "运行后端单元测试..."
                        docker run --rm \
                            -v "$(pwd)/backend:/app" \
                            -w /app \
                            python:3.12-slim \
                            bash -c "python -m pytest tests/unit -v --disable-warnings" || {
                            print_warning "单元测试失败，但继续构建..."
                        }
                    fi
                else
                    print_error "后端API测试失败，这是构建的阻断条件"
                    if [[ "$FAIL_ON_TEST" != "false" ]]; then
                        exit 1
                    else
                        print_warning "忽略测试失败，继续构建..."
                    fi
                fi
            else
                print_warning "未找到 backend/requirements.txt，跳过后端测试"
            fi
            ;;
        "frontend")
            # 前端基础测试
            if [[ -f "frontend/package.json" ]]; then
                print_info "执行前端基础测试..."
                
                if docker run --rm \
                    -v "$(pwd)/frontend:/app" \
                    -w /app \
                    node:22-alpine \
                    sh -c "
                        echo '🔧 安装依赖...'
                        npm ci --silent
                        
                        echo '🧪 运行单元测试...'
                        npm run test:unit 2>/dev/null || npm test 2>/dev/null
                    "; then
                    print_success "前端测试通过"
                else
                    print_warning "前端测试失败"
                    if [[ "$FAIL_ON_TEST" != "false" ]]; then
                        print_error "前端测试失败是构建的阻断条件"
                        exit 1
                    else
                        print_warning "忽略测试失败，继续构建..."
                    fi
                fi
            else
                print_warning "未找到 frontend/package.json，跳过前端测试"
            fi
            ;;
    esac
}

# 运行代码质量检查
run_quality_checks() {
    local component="$1"
    
    print_info "运行 ${component} 代码质量检查..."
    
    case "$component" in
        "backend")
            # Python代码质量检查
            if [[ -f "backend/requirements.txt" ]]; then
                print_info "检查Python代码质量..."
                docker run --rm \
                    -v "$(pwd)/backend:/app" \
                    -w /app \
                    python:3.12-slim \
                    bash -c "
                        pip install flake8 > /dev/null 2>&1
                        echo '📏 运行代码风格检查...'
                        flake8 app/ --max-line-length=100 --ignore=E501,W503 || true
                    " || print_warning "Python代码质量检查失败"
            fi
            ;;
        "frontend")
            # TypeScript代码质量检查
            if [[ -f "frontend/package.json" ]]; then
                print_info "检查TypeScript代码质量..."
                docker run --rm \
                    -v "$(pwd)/frontend:/app" \
                    -w /app \
                    node:22-alpine \
                    sh -c "
                        npm ci --silent
                        echo '📏 运行ESLint检查...'
                        npm run lint 2>/dev/null || npx eslint src/ --max-warnings=10 || true
                    " || print_warning "TypeScript代码质量检查失败"
            fi
            ;;
    esac
}

# 生成部署清单
generate_manifest() {
    print_info "生成构建清单..."
    
    cat > build-manifest.json << EOF
{
  "version": "${VERSION}",
  "registry": "${REGISTRY}",
  "platform": "${PLATFORM}",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "git_commit": "$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")",
  "git_branch": "$(git branch --show-current 2>/dev/null || echo "unknown")",
  "images": {
    "backend": "${REGISTRY}/backend:${VERSION}",
    "frontend": "${REGISTRY}/frontend:${VERSION}"
  },
  "deployment": {
    "compose_file": "release/docker-compose.yml",
    "config_template": "release/config-template.yaml"
  }
}
EOF
    
    print_success "构建清单已生成: build-manifest.json"
}

# 生成部署包
generate_deployment_package() {
    print_info "生成部署包..."
    
    # 创建release目录
    mkdir -p release
    
    # 生成生产环境docker-compose.yml
    cat > release/docker-compose.yml << EOF
version: '3.8'

services:
  backend:
    image: ${REGISTRY}/backend:${VERSION}
    container_name: aidd-backend
    restart: unless-stopped
    ports:
      - "\${BACKEND_PORT:-8080}:8000"
    environment:
      - CONFIG_FILE=\${CONFIG_FILE:-config.yaml}
    env_file:
      - .env
    volumes:
      - \${CONFIG_PATH:-./config.yaml}:/app/config.yaml:ro
      - \${DATA_PATH:-./data}:/app/data
      - \${LOG_PATH:-./logs}:/app/logs
    depends_on:
      - redis
    networks:
      - aidd-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    image: ${REGISTRY}/frontend:${VERSION}
    container_name: aidd-frontend
    restart: unless-stopped
    ports:
      - "\${FRONTEND_PORT:-3000}:80"
    depends_on:
      - backend
    networks:
      - aidd-network

  redis:
    image: redis:7-alpine
    container_name: aidd-redis
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - aidd-network

volumes:
  redis_data:

networks:
  aidd-network:
    driver: bridge
EOF

    # 生成配置模板
    cat > release/config-template.yaml << EOF
# AI文档测试系统 - 生产环境配置模板
# 复制此文件为 config.yaml 并根据环境修改

# 服务器配置
server:
  host: "0.0.0.0"
  port: 8000
  debug: false
  workers: 4

# 数据库配置 - 使用环境变量
database:
  type: "\${DATABASE_TYPE}"
  postgresql:
    host: "\${POSTGRES_HOST}"
    port: "\${POSTGRES_PORT}"
    username: "\${POSTGRES_USER}"
    password: "\${POSTGRES_PASSWORD}"
    database: "\${POSTGRES_DB}"

# Redis缓存配置
cache:
  strategy: "redis"
  redis:
    host: "\${REDIS_HOST:-redis}"
    port: "\${REDIS_PORT:-6379}"
    database: "\${REDIS_DATABASE:-0}"

# AI服务配置
ai_models:
  default_index: 0
  models:
    - label: "GPT-4o Mini"
      provider: "openai"
      config:
        api_key: "\${OPENAI_API_KEY}"
        model: "gpt-4o-mini"

# 安全配置
jwt:
  secret_key: "\${JWT_SECRET_KEY}"

# 第三方登录配置
third_party_auth:
  client_id: "\${OAUTH_CLIENT_ID}"
  client_secret: "\${OAUTH_CLIENT_SECRET}"
  frontend_domain: "\${FRONTEND_DOMAIN}"
EOF

    # 生成环境变量模板
    cat > release/.env.template << EOF
# AI文档测试系统 - 环境变量模板
# 复制此文件为 .env 并填写实际值

# 应用配置
VERSION=${VERSION}
ENVIRONMENT=production

# 端口配置
FRONTEND_PORT=3000
BACKEND_PORT=8080

# 数据库配置
DATABASE_TYPE=postgresql
POSTGRES_HOST=your-db-host
POSTGRES_PORT=5432
POSTGRES_USER=your-db-user
POSTGRES_PASSWORD=your-db-password
POSTGRES_DB=your-db-name

# Redis配置
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DATABASE=0

# AI服务配置
OPENAI_API_KEY=your-openai-api-key

# OAuth配置
OAUTH_CLIENT_ID=your-oauth-client-id
OAUTH_CLIENT_SECRET=your-oauth-client-secret
FRONTEND_DOMAIN=https://your-domain.com

# 安全配置
JWT_SECRET_KEY=your-jwt-secret-key

# 数据路径配置
CONFIG_PATH=./config.yaml
DATA_PATH=./data
LOG_PATH=./logs
EOF

    # 生成部署脚本
    cat > release/deploy.sh << 'EOF'
#!/bin/bash
# 生产环境部署脚本

set -e

if [[ ! -f ".env" ]]; then
    echo "❌ 环境变量文件 .env 不存在，请从 .env.template 复制并配置"
    exit 1
fi

if [[ ! -f "config.yaml" ]]; then
    echo "❌ 配置文件 config.yaml 不存在，请从 config-template.yaml 复制并配置"
    exit 1
fi

echo "🚀 开始部署..."
docker-compose up -d

echo "⏳ 等待服务启动..."
sleep 10

echo "🔍 检查服务状态..."
docker-compose ps

echo "✅ 部署完成！"
echo "🌐 前端访问: http://localhost:${FRONTEND_PORT:-3000}"
echo "🔧 后端API: http://localhost:${BACKEND_PORT:-8080}"
EOF

    chmod +x release/deploy.sh
    
    print_success "部署包已生成到 release/ 目录"
}

# 主函数
main() {
    local component=""
    local components=()
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -r|--registry)
                REGISTRY="$2"
                shift 2
                ;;
            -v|--version)
                VERSION="$2"
                shift 2
                ;;
            -p|--platform)
                PLATFORM="$2"
                shift 2
                ;;
            --push)
                PUSH="true"
                shift
                ;;
            --ci)
                CI_MODE="true"
                shift
                ;;
            --multi-arch)
                PLATFORM="linux/amd64,linux/arm64"
                shift
                ;;
            --test)
                RUN_TESTS="true"
                shift
                ;;
            --full-tests)
                RUN_TESTS="true"
                FULL_TESTS="true"
                shift
                ;;
            --quality-check)
                RUN_QUALITY_CHECK="true"
                shift
                ;;
            --fail-on-test-false)
                FAIL_ON_TEST="false"
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
            backend|frontend|all)
                component="$1"
                shift
                ;;
            *)
                print_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    if [[ -z "$component" ]]; then
        print_error "请指定构建组件"
        show_help
        exit 1
    fi
    
    # 确定要构建的组件
    case "$component" in
        "backend")
            components=("backend")
            ;;
        "frontend") 
            components=("frontend")
            ;;
        "all")
            components=("backend" "frontend")
            ;;
    esac
    
    print_header "开始构建 AI文档测试系统"
    echo "📋 构建信息:"
    echo "  仓库: $REGISTRY"
    echo "  版本: $VERSION"
    echo "  平台: $PLATFORM"
    echo "  推送: $PUSH"
    echo "  组件: ${components[*]}"
    echo ""
    
    # 检查环境
    check_environment
    
    # 初始化构建信息
    echo "[" > build-info.json
    
    # 构建各个组件
    local success=true
    for comp in "${components[@]}"; do
        # 运行测试
        if [[ "$RUN_TESTS" == "true" ]]; then
            run_tests "$comp"
        fi
        
        # 运行代码质量检查
        if [[ "$RUN_QUALITY_CHECK" == "true" ]]; then
            run_quality_checks "$comp"
        fi
        
        # 构建镜像
        if ! build_component "$comp"; then
            success=false
        fi
    done
    
    # 完成构建信息
    sed -i '$ s/,$//' build-info.json 2>/dev/null || true
    echo "]" >> build-info.json
    
    if [[ "$success" == "true" ]]; then
        generate_manifest
        generate_deployment_package
        
        print_success "🎉 所有组件构建完成！"
        echo ""
        echo "📦 构建产物:"
        for comp in "${components[@]}"; do
            echo "  ${REGISTRY}/${comp}:${VERSION}"
        done
        echo ""
        echo "📁 部署文件: release/"
        echo "📋 构建清单: build-manifest.json"
    else
        print_error "构建过程中出现错误"
        exit 1
    fi
}

# 检查是否直接运行脚本
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi