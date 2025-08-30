# AIDD (AI Document Detector) Makefile
# 统一管理本机构建、测试和部署命令

.PHONY: help quick deploy build start stop restart clean test logs status
.DEFAULT_GOAL := help

# 颜色定义
BLUE := \033[34m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
RESET := \033[0m

# 项目配置
PROJECT := aidd
VERSION := $(shell date +%Y%m%d-%H%M%S)

help: ## 显示帮助信息
	@echo "$(BLUE)AIDD (AI Document Detector) 构建工具$(RESET)"
	@echo ""
	@echo "$(YELLOW)快速开始:$(RESET)"
	@echo "  make quick     # 🚀 一键部署（最简单）"
	@echo "  make deploy    # 🏗️  完整构建和部署"
	@echo ""
	@echo "$(YELLOW)可用命令:$(RESET)"
	@awk 'BEGIN {FS = ":.*##"}; /^[a-zA-Z_-]+:.*##/ { printf "  $(GREEN)%-12s$(RESET) %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(YELLOW)环境变量:$(RESET)"
	@echo "  VERSION        指定版本号 (default: $(VERSION))"
	@echo "  ENVIRONMENT    环境类型 (dev/prod)"
	@echo ""
	@echo "$(YELLOW)示例:$(RESET)"
	@echo "  make quick                    # 快速部署"
	@echo "  make deploy                   # 完整部署"
	@echo "  VERSION=v1.0.0 make build     # 指定版本构建"
	@echo "  ENVIRONMENT=prod make deploy  # 生产环境部署"

quick: ## 🚀 快速部署（推荐）
	@echo "$(BLUE)启动快速部署...$(RESET)"
	@./quick-deploy.sh

quick-mysql: ## 🚀 快速部署 (MySQL)
	@echo "$(BLUE)启动快速部署 (MySQL数据库)...$(RESET)"
	@DATABASE_TYPE=mysql ./quick-deploy.sh

quick-postgres: ## 🚀 快速部署 (PostgreSQL)  
	@echo "$(BLUE)启动快速部署 (PostgreSQL数据库)...$(RESET)"
	@DATABASE_TYPE=postgresql ./quick-deploy.sh

deploy: ## 🏗️ 完整构建和部署
	@echo "$(BLUE)启动完整构建和部署...$(RESET)"
	@./local-build.sh deploy

deploy-mysql: ## 🏗️ 完整部署 (MySQL)
	@echo "$(BLUE)启动完整构建和部署 (MySQL数据库)...$(RESET)"
	@DATABASE_TYPE=mysql ./local-build.sh deploy

deploy-postgres: ## 🏗️ 完整部署 (PostgreSQL)
	@echo "$(BLUE)启动完整构建和部署 (PostgreSQL数据库)...$(RESET)"
	@DATABASE_TYPE=postgresql ./local-build.sh deploy

build: ## 🔨 仅构建镜像
	@echo "$(BLUE)构建Docker镜像...$(RESET)"
	@./local-build.sh build

build-test: ## 🔨🧪 构建镜像并测试
	@echo "$(BLUE)构建镜像并运行测试...$(RESET)"
	@./local-build.sh -t build

build-clean: ## 🔨🧹 清理后重新构建
	@echo "$(BLUE)清理后重新构建...$(RESET)"
	@./local-build.sh -c build

start: ## ▶️ 启动服务
	@echo "$(BLUE)启动AIDD服务...$(RESET)"
	@./local-build.sh start

stop: ## ⏹️ 停止服务
	@echo "$(YELLOW)停止AIDD服务...$(RESET)"
	@./local-build.sh stop

restart: ## 🔄 重启服务
	@echo "$(BLUE)重启AIDD服务...$(RESET)"
	@./local-build.sh restart

clean: ## 🧹 清理所有资源
	@echo "$(RED)清理所有资源...$(RESET)"
	@./local-build.sh clean
	@docker compose -f docker-compose.quick.yml down -v 2>/dev/null || true
	@rm -f .env.quick docker-compose.quick.yml

test: ## 🧪 运行镜像测试
	@echo "$(BLUE)运行镜像测试...$(RESET)"
	@./local-build.sh test

logs: ## 📄 查看服务日志
	@echo "$(BLUE)显示服务日志...$(RESET)"
	@./local-build.sh logs

status: ## 📊 查看服务状态
	@echo "$(BLUE)检查服务状态...$(RESET)"
	@./local-build.sh status

# 开发相关命令
dev-quick: ## 💻 开发环境快速启动
	@echo "$(BLUE)启动开发环境...$(RESET)"
	@ENVIRONMENT=development ./quick-deploy.sh

dev-logs: ## 💻 开发环境日志
	@docker compose -f docker-compose.quick.yml logs -f 2>/dev/null || \
	 ./local-build.sh logs 2>/dev/null || \
	 echo "$(YELLOW)未找到运行中的服务$(RESET)"

dev-shell-backend: ## 💻 进入后端容器Shell
	@docker exec -it aidd-backend-quick bash 2>/dev/null || \
	 docker exec -it aidd-backend bash 2>/dev/null || \
	 echo "$(RED)后端容器未运行$(RESET)"

dev-shell-frontend: ## 💻 进入前端容器Shell
	@docker exec -it aidd-frontend-quick sh 2>/dev/null || \
	 docker exec -it aidd-frontend sh 2>/dev/null || \
	 echo "$(RED)前端容器未运行$(RESET)"

# 生产环境命令
prod-deploy: ## 🏭 生产环境部署
	@echo "$(BLUE)部署到生产环境...$(RESET)"
	@ENVIRONMENT=production ./local-build.sh -p deploy

prod-status: ## 🏭 生产环境状态
	@echo "$(BLUE)检查生产环境状态...$(RESET)"
	@./local-build.sh status

# 维护命令
backup: ## 💾 备份数据
	@echo "$(BLUE)备份数据...$(RESET)"
	@mkdir -p backups/$(VERSION)
	@docker cp aidd-backend:/app/data backups/$(VERSION)/ 2>/dev/null || \
	 docker cp aidd-backend-quick:/app/data backups/$(VERSION)/ 2>/dev/null || \
	 echo "$(YELLOW)未找到运行中的后端容器$(RESET)"
	@echo "$(GREEN)备份完成: backups/$(VERSION)/$(RESET)"

health-check: ## 🏥 健康检查
	@echo "$(BLUE)运行健康检查...$(RESET)"
	@echo "检查后端服务..."
	@curl -f http://localhost:8080/health >/dev/null 2>&1 && \
	 echo "$(GREEN)✓ 后端服务正常$(RESET)" || \
	 echo "$(RED)✗ 后端服务异常$(RESET)"
	@echo "检查前端服务..."
	@curl -f http://localhost:3000/ >/dev/null 2>&1 && \
	 echo "$(GREEN)✓ 前端服务正常$(RESET)" || \
	 echo "$(RED)✗ 前端服务异常$(RESET)"

ps: ## 📋 显示容器状态
	@echo "$(BLUE)容器运行状态:$(RESET)"
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(NAME|aidd)" || \
	 echo "$(YELLOW)未找到AIDD相关容器$(RESET)"

images: ## 🖼️ 显示镜像列表
	@echo "$(BLUE)AIDD相关镜像:$(RESET)"
	@docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | grep -E "(REPOSITORY|aidd)" || \
	 echo "$(YELLOW)未找到AIDD相关镜像$(RESET)"

# 实用工具
open: ## 🌐 打开浏览器访问应用
	@echo "$(BLUE)在浏览器中打开AIDD...$(RESET)"
	@command -v open >/dev/null && open http://localhost:3000 || \
	 command -v xdg-open >/dev/null && xdg-open http://localhost:3000 || \
	 echo "$(YELLOW)请手动访问: http://localhost:3000$(RESET)"

env: ## ⚙️ 显示环境信息
	@echo "$(BLUE)环境信息:$(RESET)"
	@echo "Docker版本: $(shell docker --version)"
	@echo "Compose版本: $(shell docker compose version 2>/dev/null || docker-compose --version)"
	@echo "系统: $(shell uname -s)"
	@echo "内存: $(shell free -h 2>/dev/null | awk '/^Mem:/ {print $$2}' || echo '未知')"
	@echo "磁盘: $(shell df -h . | awk 'NR==2 {print $$4}')"

setup: ## 🛠️ 初始化环境（安装依赖）
	@echo "$(BLUE)检查并安装依赖...$(RESET)"
	@command -v docker >/dev/null || (echo "$(RED)请先安装Docker$(RESET)" && exit 1)
	@command -v curl >/dev/null || (echo "$(YELLOW)建议安装curl用于健康检查$(RESET)")
	@echo "$(GREEN)环境检查完成$(RESET)"

# 清理命令变体
clean-containers: ## 🧹 仅清理容器
	@echo "$(YELLOW)清理AIDD容器...$(RESET)"
	@docker ps -a --format "{{.Names}}" | grep aidd | xargs -r docker rm -f

clean-images: ## 🧹 仅清理镜像
	@echo "$(YELLOW)清理AIDD镜像...$(RESET)"
	@docker images --format "{{.Repository}}:{{.Tag}}" | grep aidd | xargs -r docker rmi -f

clean-volumes: ## 🧹 仅清理卷（危险：会删除数据）
	@echo "$(RED)清理AIDD数据卷...$(RESET)"
	@read -p "这将删除所有数据，确认吗？(y/N): " confirm && \
	 [ "$$confirm" = "y" ] && docker volume ls -q | grep aidd | xargs -r docker volume rm || \
	 echo "$(YELLOW)操作已取消$(RESET)"

# 快捷访问信息
info: ## ℹ️ 显示访问信息
	@echo "$(BLUE)AIDD 访问信息:$(RESET)"
	@echo "🌐 前端界面: http://localhost:3000"
	@echo "🔧 后端API:  http://localhost:8080"  
	@echo "📚 API文档:  http://localhost:8080/docs"
	@echo "💊 健康检查: http://localhost:8080/health"
	@echo ""
	@echo "$(YELLOW)常用命令:$(RESET)"
	@echo "  make logs      # 查看日志"
	@echo "  make status    # 查看状态"  
	@echo "  make restart   # 重启服务"
	@echo "  make clean     # 清理资源"