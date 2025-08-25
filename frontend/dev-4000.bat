@echo off
REM Windows专用：在4000端口启动前端开发服务器

echo =======================================
echo    启动前端开发服务器 (端口: 4000)
echo =======================================

REM 设置环境变量
set VITE_PORT=4000
set VITE_HOST=0.0.0.0

REM 显示配置信息
echo 前端地址: http://localhost:4000
echo 监听地址: 0.0.0.0:4000
echo =======================================

REM 启动开发服务器
npm run dev

pause