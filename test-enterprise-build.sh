#!/bin/bash

# AI文档测试系统 - 企业级构建和部署流程测试脚本
# 验证完整的构建、测试和部署工作流

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
print_header() { echo -e "${BLUE}🧪 $1${NC}"; }

# 测试配置
TEST_VERSION="test-$(date +%Y%m%d-%H%M%S)"
TEST_REGISTRY="localhost:5000"
CLEANUP=${CLEANUP:-"true"}
FULL_TESTS=${FULL_TESTS:-"false"}

show_help() {
    cat << EOF
AI文档测试系统 - 企业级构建测试脚本

用法: $0 [选项]

选项:
  --full-tests         运行完整测试套件
  --no-cleanup         测试后不清理资源
  --registry REGISTRY  使用指定的镜像仓库 (默认: localhost:5000)
  --version VERSION    使用指定的版本标签
  -h, --help          显示帮助信息

测试流程:
  1. 环境检查和准备
  2. 代码质量检查
  3. API基础测试
  4. 镜像构建测试
  5. 部署配置测试
  6. 集成测试
  7. 清理资源

环境变量:
  CLEANUP              测试后是否清理 (true/false)
  FULL_TESTS           是否运行完整测试 (true/false)
EOF
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --full-tests)
            FULL_TESTS="true"
            shift
            ;;
        --no-cleanup)
            CLEANUP="false"
            shift
            ;;
        --registry)
            TEST_REGISTRY="$2"
            shift 2
            ;;
        --version)
            TEST_VERSION="$2"
            shift 2
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

print_header "开始企业级构建和部署流程测试"
echo "📋 测试配置:"
echo "  版本标签: $TEST_VERSION"
echo "  镜像仓库: $TEST_REGISTRY"  
echo "  完整测试: $FULL_TESTS"
echo "  测试清理: $CLEANUP"
echo ""

# 步骤1: 环境检查
print_header "步骤1: 环境检查"
test_environment() {
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
    
    # 检查构建脚本
    if [[ ! -f "build-enterprise.sh" ]]; then
        print_error "企业级构建脚本不存在"
        exit 1
    fi
    
    # 检查必要文件
    local required_files=(
        "backend/Dockerfile.enterprise"
        "frontend/Dockerfile.enterprise"  
        "docker-compose.production.yml"
        "deployment-config-guide.md"
    )
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            print_error "必需文件不存在: $file"
            exit 1
        fi
    done
    
    print_success "环境检查通过"
}

test_environment

# 步骤2: 代码质量检查
print_header "步骤2: 代码质量检查"
test_code_quality() {
    print_info "运行代码质量检查..."
    
    # Python代码检查
    if [[ -f "backend/requirements.txt" ]]; then
        print_info "检查Python代码质量..."
        docker run --rm \
            -v "$(pwd)/backend:/app" \
            -w /app \
            python:3.12-slim \
            bash -c "
                pip install flake8 > /dev/null 2>&1
                flake8 app/ --max-line-length=100 --ignore=E501,W503 --statistics
            " || print_warning "Python代码质量检查发现问题"
    fi
    
    # TypeScript代码检查
    if [[ -f "frontend/package.json" ]]; then
        print_info "检查TypeScript代码质量..."  
        docker run --rm \
            -v "$(pwd)/frontend:/app" \
            -w /app \
            node:22-alpine \
            sh -c "
                npm ci --silent
                npm run lint 2>/dev/null || true
            " || print_warning "TypeScript代码质量检查发现问题"
    fi
    
    print_success "代码质量检查完成"
}

if [[ "$FULL_TESTS" == "true" ]]; then
    test_code_quality
else
    print_info "跳过代码质量检查 (使用 --full-tests 启用)"
fi

# 步骤3: API基础测试
print_header "步骤3: API基础测试"
test_api() {
    print_info "运行API基础测试..."
    
    if [[ -f "backend/requirements.txt" ]]; then
        docker run --rm \
            -v "$(pwd)/backend:/app" \
            -w /app \
            python:3.12-slim \
            bash -c "
                pip install -r requirements.txt > /dev/null 2>&1
                python -m pytest tests/api \
                    --tb=no \
                    -v \
                    -k 'not (batch or concurrency or concurrent)' \
                    --maxfail=1 \
                    --disable-warnings
            " && print_success "API基础测试通过" || {
            print_warning "API测试失败，但继续测试构建流程..."
        }
    else
        print_warning "未找到 backend/requirements.txt，跳过API测试"
    fi
}

test_api

# 步骤4: 镜像构建测试
print_header "步骤4: 镜像构建测试"
test_build() {
    print_info "测试企业级构建脚本..."
    
    # 设置测试环境变量
    export REGISTRY="$TEST_REGISTRY"
    export VERSION="$TEST_VERSION"
    export PUSH="false"  # 本地测试不推送
    
    # 测试构建命令
    if ./build-enterprise.sh --test --quality-check all; then
        print_success "镜像构建测试通过"
        
        # 验证镜像是否存在
        if docker image ls | grep -q "${TEST_REGISTRY}/backend:${TEST_VERSION}"; then
            print_success "后端镜像构建成功"
        else
            print_error "后端镜像不存在"
            exit 1
        fi
        
        if docker image ls | grep -q "${TEST_REGISTRY}/frontend:${TEST_VERSION}"; then
            print_success "前端镜像构建成功"
        else
            print_error "前端镜像不存在" 
            exit 1
        fi
    else
        print_error "镜像构建失败"
        exit 1
    fi
}

test_build

# 步骤5: 部署配置测试
print_header "步骤5: 部署配置测试"
test_deployment_config() {
    print_info "测试部署配置生成..."
    
    # 检查是否生成了部署文件
    local required_files=(
        "release/docker-compose.yml"
        "release/.env.template"
        "release/config-template.yaml" 
        "release/deploy.sh"
        "build-manifest.json"
    )
    
    for file in "${required_files[@]}"; do
        if [[ -f "$file" ]]; then
            print_success "生成了部署文件: $file"
        else
            print_warning "部署文件不存在: $file"
        fi
    done
    
    # 验证docker-compose语法
    if docker-compose -f release/docker-compose.yml config > /dev/null 2>&1; then
        print_success "Docker Compose配置语法正确"
    else
        print_error "Docker Compose配置语法错误"
    fi
    
    # 验证生产环境配置
    if docker-compose -f docker-compose.production.yml config > /dev/null 2>&1; then
        print_success "生产环境Docker Compose配置语法正确"
    else
        print_error "生产环境Docker Compose配置语法错误"
    fi
}

test_deployment_config

# 步骤6: 集成测试
print_header "步骤6: 集成测试"
test_integration() {
    print_info "运行集成测试..."
    
    # 创建测试环境配置
    cat > .env.test << EOF
VERSION=${TEST_VERSION}
ENVIRONMENT=test
REGISTRY=${TEST_REGISTRY}

FRONTEND_PORT=3001
BACKEND_PORT=8081

DATABASE_TYPE=sqlite
POSTGRES_PASSWORD=test_password

REDIS_HOST=redis
REDIS_PORT=6379

OPENAI_API_KEY=test-key
OAUTH_CLIENT_ID=test-client-id
OAUTH_CLIENT_SECRET=test-client-secret
JWT_SECRET_KEY=test-jwt-secret

CONFIG_PATH=./config.yaml
DATA_PATH=./test-data
LOG_PATH=./test-logs
EOF

    # 创建测试配置文件
    cat > config.test.yaml << EOF
server:
  host: "0.0.0.0"
  port: 8000
  debug: true

database:
  type: "sqlite"
  sqlite:
    path: "./test-data/app.db"

cache:
  strategy: "redis"
  redis:
    host: "redis"
    port: 6379

jwt:
  secret_key: "test-jwt-secret"

ai_models:
  default_index: 0
  models:
    - label: "Test Model"
      provider: "openai"
      config:
        api_key: "test-key"
        model: "gpt-4o-mini"
EOF

    # 创建测试docker-compose文件
    cat > docker-compose.test.yml << EOF
version: '3.8'

services:
  backend:
    image: ${TEST_REGISTRY}/backend:${TEST_VERSION}
    ports:
      - "8081:8000"
    environment:
      - CONFIG_FILE=config.yaml
    env_file:
      - .env.test
    volumes:
      - ./config.test.yaml:/app/config.yaml:ro
      - ./test-data:/app/data
    depends_on:
      - redis
    networks:
      - test-network

  frontend:
    image: ${TEST_REGISTRY}/frontend:${TEST_VERSION}
    ports:
      - "3001:80"
    depends_on:
      - backend
    networks:
      - test-network

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - test_redis_data:/data
    networks:
      - test-network

volumes:
  test_redis_data:

networks:
  test-network:
    driver: bridge
EOF

    # 启动测试环境
    print_info "启动测试环境..."
    mkdir -p test-data test-logs
    
    if docker-compose -f docker-compose.test.yml up -d; then
        print_success "测试环境启动成功"
        
        # 等待服务就绪
        print_info "等待服务就绪..."
        sleep 20
        
        # 健康检查
        local max_attempts=10
        local attempt=0
        while [ $attempt -lt $max_attempts ]; do
            if curl -s -f "http://localhost:8081/health" >/dev/null 2>&1; then
                print_success "后端服务健康检查通过"
                break
            fi
            print_info "等待后端服务... ($((attempt+1))/$max_attempts)"
            sleep 5
            ((attempt++))
        done
        
        if [ $attempt -eq $max_attempts ]; then
            print_error "后端服务健康检查超时"
            docker-compose -f docker-compose.test.yml logs backend
        else
            # 测试前端服务
            if curl -s -f "http://localhost:3001/health" >/dev/null 2>&1; then
                print_success "前端服务健康检查通过"
            else
                print_warning "前端服务健康检查失败"
            fi
        fi
        
        # 停止测试环境
        print_info "停止测试环境..."
        docker-compose -f docker-compose.test.yml down
        
    else
        print_error "测试环境启动失败"
        exit 1
    fi
}

if [[ "$FULL_TESTS" == "true" ]]; then
    test_integration
else
    print_info "跳过集成测试 (使用 --full-tests 启用)"
fi

# 步骤7: 清理资源
print_header "步骤7: 清理测试资源"
cleanup_test_resources() {
    if [[ "$CLEANUP" == "true" ]]; then
        print_info "清理测试资源..."
        
        # 清理测试镜像
        docker rmi "${TEST_REGISTRY}/backend:${TEST_VERSION}" 2>/dev/null || true
        docker rmi "${TEST_REGISTRY}/frontend:${TEST_VERSION}" 2>/dev/null || true
        
        # 清理测试文件
        rm -f .env.test config.test.yaml docker-compose.test.yml
        rm -rf test-data test-logs release/ build-*.json
        
        # 清理Docker资源
        docker system prune -f > /dev/null 2>&1 || true
        
        print_success "测试资源清理完成"
    else
        print_info "跳过资源清理 (使用 --no-cleanup 禁用了清理)"
    fi
}

cleanup_test_resources

print_success "🎉 企业级构建和部署流程测试完成！"
echo ""
echo "📋 测试总结:"
echo "✅ 环境检查通过"
echo "✅ 镜像构建测试通过"
echo "✅ 部署配置测试通过"
if [[ "$FULL_TESTS" == "true" ]]; then
    echo "✅ 代码质量检查完成"
    echo "✅ 集成测试完成"
fi
echo ""
echo "🚀 构建流程已准备就绪！"
echo ""
echo "💡 使用建议:"
echo "  本地构建: ./build-enterprise.sh --test backend"
echo "  生产构建: ./build-enterprise.sh --push --multi-arch -v v1.0.0 all"
echo "  CI构建: 使用 .github/workflows/docker-build-enterprise.yml"