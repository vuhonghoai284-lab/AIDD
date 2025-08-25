#!/bin/bash

echo "AI文档测试系统启动脚本"
echo "========================"

# 检查Python环境
echo "检查Python环境..."
python3 --version || python --version

# 创建虚拟环境（如果不存在）
if [ ! -d "backend/venv" ]; then
    echo "创建Python虚拟环境..."
    cd backend
    python3 -m venv venv || python -m venv venv
    cd ..
fi

# 激活虚拟环境并安装后端依赖
echo "安装后端依赖..."
cd backend
source venv/bin/activate 2>/dev/null || venv\\Scripts\\activate
pip install -r requirements.txt

# 启动后端服务
echo "启动后端服务..."
python main.py &
BACKEND_PID=$!
cd ..

# 安装前端依赖
echo "安装前端依赖..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "使用华为云镜像源安装npm包..."
    npm config set registry https://mirrors.huaweicloud.com/repository/npm/
    npm install
fi

# 启动前端服务
echo "启动前端服务..."
npm run &
FRONTEND_PID=$!
cd ..

echo "========================"
echo "系统启动完成！"
echo "后端服务: http://localhost:8080"
echo "前端服务: http://localhost:3000"
echo "API文档: http://localhost:8080/docs"
echo ""
echo "按 Ctrl+C 停止所有服务"
echo "========================"

# 等待用户中断
wait $BACKEND_PID $FRONTEND_PID