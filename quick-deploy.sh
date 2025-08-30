#!/bin/bash

# AIDD 快速本机部署脚本
# 最简单的本机构建和部署方案，支持多种数据库

set -e

# 默认配置
DATABASE_TYPE=${DATABASE_TYPE:-"sqlite"}
DB_PORT_MYSQL=3306
DB_PORT_POSTGRES=5432

echo "🚀 AIDD 快速部署 - 开始..."

# 显示数据库选择帮助
show_db_help() {
    echo "📂 支持的数据库类型:"
    echo "  sqlite     - SQLite (默认，无需额外配置)"
    echo "  mysql      - MySQL 8.0"
    echo "  postgresql - PostgreSQL 15"
    echo ""
    echo "💡 使用方法:"
    echo "  DATABASE_TYPE=sqlite ./quick-deploy.sh      # SQLite"
    echo "  DATABASE_TYPE=mysql ./quick-deploy.sh       # MySQL"
    echo "  DATABASE_TYPE=postgresql ./quick-deploy.sh  # PostgreSQL"
    echo ""
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --db)
            DATABASE_TYPE="$2"
            shift 2
            ;;
        --help|-h)
            show_db_help
            exit 0
            ;;
        *)
            echo "未知参数: $1"
            show_db_help
            exit 1
            ;;
    esac
done

echo "🗄️  数据库类型: $DATABASE_TYPE"

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo "❌ 请先安装Docker"
    exit 1
fi

# 检查Docker Compose
if docker compose version &> /dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    echo "❌ 请先安装Docker Compose"
    exit 1
fi

echo "✅ Docker环境检查通过"

# 生成数据库配置
generate_db_config() {
    case $DATABASE_TYPE in
        sqlite)
            cat << EOF
# SQLite配置 (默认)
DATABASE_TYPE=sqlite
DATABASE_URL=sqlite:///app/data/app.db
EOF
            ;;
        mysql)
            local mysql_password=$(openssl rand -base64 12 | tr -d "=+/" | cut -c1-12)
            cat << EOF
# MySQL配置
DATABASE_TYPE=mysql
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_USERNAME=aidd
MYSQL_PASSWORD=$mysql_password
MYSQL_DATABASE=aidd_db
DATABASE_URL=mysql://aidd:$mysql_password@mysql:3306/aidd_db
EOF
            ;;
        postgresql)
            local pg_password=$(openssl rand -base64 12 | tr -d "=+/" | cut -c1-12)
            cat << EOF
# PostgreSQL配置
DATABASE_TYPE=postgresql
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=aidd
POSTGRES_PASSWORD=$pg_password
POSTGRES_DB=aidd_db
DATABASE_URL=postgresql://aidd:$pg_password@postgres:5432/aidd_db
EOF
            ;;
        *)
            echo "❌ 不支持的数据库类型: $DATABASE_TYPE"
            exit 1
            ;;
    esac
}

# 创建环境配置
echo "📝 创建配置文件..."
cat > .env.quick << EOF
# AIDD 快速部署配置
PROJECT_NAME=aidd
ENVIRONMENT=development
$(generate_db_config)
REDIS_URL=redis://redis:6379/0
DEBUG=true
LOG_LEVEL=INFO
BACKEND_PORT=8080
FRONTEND_PORT=3000
JWT_SECRET_KEY=quick-deploy-secret-key
OAUTH_CLIENT_SECRET=quick-deploy-oauth
OPENAI_API_KEY=your-openai-api-key-here
EOF

# 生成数据库服务配置
generate_db_service() {
    case $DATABASE_TYPE in
        mysql)
            cat << 'EOF'
  # MySQL数据库
  mysql:
    image: mysql:8.0
    container_name: aidd-mysql-quick
    restart: unless-stopped
    environment:
      - MYSQL_ROOT_PASSWORD=root123456
      - MYSQL_DATABASE=${MYSQL_DATABASE:-aidd_db}
      - MYSQL_USER=${MYSQL_USERNAME:-aidd}
      - MYSQL_PASSWORD=${MYSQL_PASSWORD}
    volumes:
      - mysql_data:/var/lib/mysql
    ports:
      - "3306:3306"
    networks:
      - aidd-quick-network
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

EOF
            ;;
        postgresql)
            cat << 'EOF'
  # PostgreSQL数据库
  postgres:
    image: postgres:15-alpine
    container_name: aidd-postgres-quick
    restart: unless-stopped
    environment:
      - POSTGRES_DB=${POSTGRES_DB:-aidd_db}
      - POSTGRES_USER=${POSTGRES_USER:-aidd}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - aidd-quick-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-aidd} -d ${POSTGRES_DB:-aidd_db}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

EOF
            ;;
        sqlite)
            # SQLite不需要额外的数据库服务
            echo ""
            ;;
    esac
}

# 生成数据库卷配置
generate_db_volumes() {
    case $DATABASE_TYPE in
        mysql)
            echo "  mysql_data:"
            ;;
        postgresql)
            echo "  postgres_data:"
            ;;
        sqlite)
            # SQLite使用文件存储，不需要额外卷
            echo ""
            ;;
    esac
}

# 生成后端依赖配置
generate_backend_depends() {
    case $DATABASE_TYPE in
        mysql)
            echo "      - mysql"
            ;;
        postgresql)
            echo "      - postgres"
            ;;
        sqlite)
            # SQLite不需要依赖外部数据库
            echo ""
            ;;
    esac
}

# 创建快速部署Docker Compose文件
echo "📦 创建部署配置..."
cat > docker-compose.quick.yml << EOF
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: aidd-backend-quick
    restart: unless-stopped
    ports:
      - "${BACKEND_PORT:-8080}:8000"
    environment:
      - ENVIRONMENT=${ENVIRONMENT:-development}
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - PYTHONPATH=/app
      - DEBUG=${DEBUG:-true}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - backend_data:/app/data
      - backend_logs:/app/logs
    depends_on:
      - redis
$(generate_backend_depends)
    networks:
      - aidd-quick-network

$(generate_db_service)  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: aidd-frontend-quick
    restart: unless-stopped
    ports:
      - "${FRONTEND_PORT:-3000}:80"
    depends_on:
      - backend
    networks:
      - aidd-quick-network

  redis:
    image: redis:7-alpine
    container_name: aidd-redis-quick
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - aidd-quick-network

volumes:
  backend_data:
  backend_logs:
  redis_data:
$(generate_db_volumes)

networks:
  aidd-quick-network:
    driver: bridge
EOF

# 构建和启动
echo "🏗️ 构建和启动服务..."
echo "这可能需要几分钟时间，请耐心等待..."

$DOCKER_COMPOSE -f docker-compose.quick.yml --env-file .env.quick up -d --build

# 等待服务启动（数据库需要更长时间）
echo "⏳ 等待服务启动..."
if [[ "$DATABASE_TYPE" == "mysql" || "$DATABASE_TYPE" == "postgresql" ]]; then
    echo "  数据库初始化中，请耐心等待..."
    sleep 45
else
    sleep 20
fi

# 检查服务状态
echo "🔍 检查服务状态..."
$DOCKER_COMPOSE -f docker-compose.quick.yml --env-file .env.quick ps

# 健康检查
echo "💊 运行健康检查..."
max_attempts=15
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if curl -s -f "http://localhost:8080/health" >/dev/null 2>&1; then
        break
    fi
    echo "  等待后端服务启动... ($((attempt+1))/$max_attempts)"
    sleep 5
    ((attempt++))
done

if [ $attempt -eq $max_attempts ]; then
    echo "⚠️  后端服务启动超时，但容器可能仍在初始化"
    echo "📋 请稍后访问服务地址检查状态"
else
    echo "✅ 后端服务已就绪"
fi

# 显示访问信息
echo ""
echo "🎉 AIDD 快速部署完成！"
echo ""
echo "📋 访问地址:"
echo "  🌐 前端界面: http://localhost:3000"
echo "  🔧 后端API:  http://localhost:8080"
echo "  📚 API文档:  http://localhost:8080/docs"
echo ""
echo "🛠️ 管理命令:"
echo "  查看日志: $DOCKER_COMPOSE -f docker-compose.quick.yml logs -f"
echo "  停止服务: $DOCKER_COMPOSE -f docker-compose.quick.yml down"
echo "  重启服务: $DOCKER_COMPOSE -f docker-compose.quick.yml restart"
echo ""
echo "💡 提示:"
echo "  - 数据会自动保存到Docker卷中"
echo "  - 请编辑 .env.quick 文件配置OpenAI API Key"
case $DATABASE_TYPE in
    mysql)
        echo "  - MySQL数据库端口: 3306 (用户: aidd)"
        echo "  - 数据库连接: mysql://aidd:PASSWORD@localhost:3306/aidd_db"
        ;;
    postgresql)
        echo "  - PostgreSQL数据库端口: 5432 (用户: aidd)"
        echo "  - 数据库连接: postgresql://aidd:PASSWORD@localhost:5432/aidd_db"
        ;;
    sqlite)
        echo "  - SQLite数据库文件: ./data/app.db"
        ;;
esac
echo "  - 首次启动可能需要几分钟初始化数据库"
echo ""
echo "🗄️ 数据库类型: $DATABASE_TYPE"
echo "✨ 开始使用AIDD吧！"