#!/bin/bash

# AIDD 数据库选择部署脚本
# 交互式选择数据库类型并部署

set -e

# 颜色定义
BLUE='\033[34m'
GREEN='\033[32m'
YELLOW='\033[33m'
RED='\033[31m'
RESET='\033[0m'

echo -e "${BLUE}"
cat << "EOF"
╔══════════════════════════════════════════╗
║           AIDD 数据库选择部署             ║
║        AI Document Detector v2.0         ║
╚══════════════════════════════════════════╝
EOF
echo -e "${RESET}"

# 显示数据库选项
echo -e "${YELLOW}请选择数据库类型:${RESET}"
echo ""
echo "1) SQLite    - 轻量级，无需配置 (推荐用于开发和小规模使用)"
echo "2) MySQL     - 高性能，适合生产环境"  
echo "3) PostgreSQL- 功能强大，适合复杂查询"
echo ""

# 获取用户选择
while true; do
    read -p "请输入选择 (1-3): " choice
    case $choice in
        1)
            DATABASE_TYPE="sqlite"
            DB_NAME="SQLite"
            break
            ;;
        2)
            DATABASE_TYPE="mysql"
            DB_NAME="MySQL"
            break
            ;;
        3)
            DATABASE_TYPE="postgresql"
            DB_NAME="PostgreSQL"
            break
            ;;
        *)
            echo -e "${RED}无效选择，请输入 1、2 或 3${RESET}"
            ;;
    esac
done

echo ""
echo -e "${GREEN}✓ 已选择: $DB_NAME${RESET}"

# 显示部署选项
echo ""
echo -e "${YELLOW}请选择部署方式:${RESET}"
echo ""
echo "1) 快速部署  - 简单快捷，一键启动"
echo "2) 完整部署  - 完整构建流程，更多控制选项"
echo ""

while true; do
    read -p "请输入选择 (1-2): " deploy_choice
    case $deploy_choice in
        1)
            DEPLOY_METHOD="quick"
            DEPLOY_NAME="快速部署"
            break
            ;;
        2)
            DEPLOY_METHOD="full"
            DEPLOY_NAME="完整部署"
            break
            ;;
        *)
            echo -e "${RED}无效选择，请输入 1 或 2${RESET}"
            ;;
    esac
done

echo ""
echo -e "${GREEN}✓ 已选择: $DEPLOY_NAME${RESET}"

# 显示配置摘要
echo ""
echo -e "${BLUE}部署配置摘要:${RESET}"
echo "  数据库类型: $DB_NAME"
echo "  部署方式:   $DEPLOY_NAME"
echo ""

# 确认部署
read -p "确认开始部署吗? (y/N): " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo -e "${YELLOW}部署已取消${RESET}"
    exit 0
fi

echo ""
echo -e "${BLUE}🚀 开始部署...${RESET}"

# 执行部署
case $DEPLOY_METHOD in
    quick)
        echo -e "${GREEN}使用快速部署方式...${RESET}"
        DATABASE_TYPE=$DATABASE_TYPE ./quick-deploy.sh
        ;;
    full)
        echo -e "${GREEN}使用完整部署方式...${RESET}"
        DATABASE_TYPE=$DATABASE_TYPE ./local-build.sh deploy
        ;;
esac

# 显示部署完成信息
echo ""
echo -e "${GREEN}🎉 AIDD 部署完成！${RESET}"
echo ""
echo -e "${YELLOW}数据库信息:${RESET}"
case $DATABASE_TYPE in
    sqlite)
        echo "  类型: SQLite"
        echo "  文件: ./data/app.db"
        echo "  无需外部连接配置"
        ;;
    mysql)
        echo "  类型: MySQL 8.0"
        echo "  端口: 3306"
        echo "  用户: aidd"
        echo "  数据库: aidd_db"
        echo "  连接: 查看 .env.quick 获取密码"
        ;;
    postgresql)
        echo "  类型: PostgreSQL 15"
        echo "  端口: 5432"
        echo "  用户: aidd"
        echo "  数据库: aidd_db"
        echo "  连接: 查看 .env.quick 获取密码"
        ;;
esac

echo ""
echo -e "${YELLOW}访问地址:${RESET}"
echo "  🌐 前端界面: http://localhost:3000"
echo "  🔧 后端API:  http://localhost:8080"
echo "  📚 API文档:  http://localhost:8080/docs"

echo ""
echo -e "${YELLOW}管理命令:${RESET}"
if [[ "$DEPLOY_METHOD" == "quick" ]]; then
    echo "  查看日志: docker compose -f docker-compose.quick.yml logs -f"
    echo "  停止服务: docker compose -f docker-compose.quick.yml down"
    echo "  重启服务: docker compose -f docker-compose.quick.yml restart"
else
    echo "  查看状态: ./local-build.sh status"
    echo "  查看日志: ./local-build.sh logs"
    echo "  停止服务: ./local-build.sh stop"
    echo "  重启服务: ./local-build.sh restart"
fi

echo ""
echo -e "${GREEN}✨ 开始使用AIDD吧！${RESET}"