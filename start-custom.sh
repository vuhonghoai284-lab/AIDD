#!/bin/bash
# 自定义IP和端口启动脚本 (Linux/Mac)
# 使用方法：./start-custom.sh [前端IP] [前端端口] [后端IP] [后端端口]

# 设置默认值
FRONTEND_HOST=${1:-"0.0.0.0"}
FRONTEND_PORT=${2:-"3000"}
BACKEND_HOST=${3:-"0.0.0.0"}
BACKEND_PORT=${4:-"8080"}

echo "================================"
echo "    AI文档测试系统自定义启动"
echo "================================"
echo "前端地址: http://$FRONTEND_HOST:$FRONTEND_PORT"
echo "后端地址: http://$BACKEND_HOST:$BACKEND_PORT"
echo "================================"

# 启动后端
echo "[1/2] 启动后端服务..."
cd backend
export SERVER_HOST=$BACKEND_HOST
export SERVER_PORT=$BACKEND_PORT
python app/main.py &
BACKEND_PID=$!

# 等待后端启动
echo "等待后端启动..."
sleep 3

# 启动前端
echo "[2/2] 启动前端服务..."
cd ../frontend

# 设置前端环境变量
export VITE_HOST=$FRONTEND_HOST
export VITE_PORT=$FRONTEND_PORT
export VITE_API_BASE_URL=http://$BACKEND_HOST:$BACKEND_PORT/api
export VITE_WS_BASE_URL=ws://$BACKEND_HOST:$BACKEND_PORT
export VITE_BACKEND_PORT=$BACKEND_PORT

# 启动前端
npm run dev &
FRONTEND_PID=$!

echo "启动完成！"
echo "前端访问地址: http://$FRONTEND_HOST:$FRONTEND_PORT"
echo "后端API地址: http://$BACKEND_HOST:$BACKEND_PORT/api"
echo ""
echo "按 Ctrl+C 停止服务"

# 等待中断信号
trap "echo '正在关闭服务...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait