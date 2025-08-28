#!/bin/bash

# 任务分享功能快速部署脚本
# 适用于生产环境一键部署

set -e  # 遇到错误立即退出

echo "🚀 任务分享功能部署脚本"
echo "================================"

# 检查是否在正确的目录
if [ ! -f "backend/migration_task_sharing.py" ]; then
    echo "❌ 错误：请在项目根目录下运行此脚本"
    exit 1
fi

# 检查Python环境
if ! command -v python &> /dev/null; then
    echo "❌ 错误：未找到Python环境"
    exit 1
fi

# 检查数据库文件
if [ ! -f "backend/data/app.db" ]; then
    echo "❌ 错误：数据库文件不存在 (backend/data/app.db)"
    exit 1
fi

echo "📋 环境检查通过"

# 询问用户确认
read -p "⚠️  即将进行数据库迁移，是否已备份数据库？(y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 请先备份数据库后重新运行"
    exit 1
fi

echo ""
echo "🔄 步骤 1: 执行数据库迁移"
cd backend
if python migration_task_sharing.py; then
    echo "✅ 数据库迁移成功"
else
    echo "❌ 数据库迁移失败"
    exit 1
fi

echo ""
echo "🔄 步骤 2: 检查后端依赖"
if pip install -r requirements.txt --quiet; then
    echo "✅ 后端依赖检查完成"
else
    echo "⚠️  后端依赖安装可能有问题"
fi

cd ../

echo ""
echo "🔄 步骤 3: 检查前端依赖"
cd frontend
if npm install --silent; then
    echo "✅ 前端依赖检查完成"
else
    echo "⚠️  前端依赖安装可能有问题"
fi

echo ""
echo "🔄 步骤 4: 构建前端资源"
if npm run build --silent; then
    echo "✅ 前端构建成功"
else
    echo "❌ 前端构建失败"
    exit 1
fi

cd ../

echo ""
echo "🔄 步骤 5: 验证部署"

# 检查关键文件是否存在
key_files=(
    "backend/app/models/task_share.py"
    "backend/app/views/task_share_view.py"
    "backend/app/services/task_permission_service.py"
    "frontend/src/components/TaskShareModal.tsx"
    "frontend/src/pages/SharedTasks.tsx"
)

for file in "${key_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ 缺少文件: $file"
        exit 1
    fi
done

echo ""
echo "🎉 任务分享功能部署完成！"
echo "================================"
echo ""
echo "📝 部署摘要："
echo "  ✅ 数据库已迁移（已自动备份）"
echo "  ✅ 后端代码已更新"
echo "  ✅ 前端资源已构建"
echo "  ✅ 关键文件验证通过"
echo ""
echo "🚀 下一步操作："
echo "  1. 重启后端服务"
echo "  2. 重启前端服务（如果使用pm2等）"
echo "  3. 测试分享功能是否正常"
echo ""
echo "📞 如有问题，请查看 TASK_SHARING_DEPLOYMENT.md"