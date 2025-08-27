@echo off
REM Windows专用：解决.env环境变量不生效问题
REM 手动设置所有环境变量然后启动Vite开发服务器

echo =======================================
echo   AI文档测试系统 - Windows开发环境
echo =======================================

REM 从.env文件手动设置环境变量
set VITE_PORT=3000
set VITE_HOST=0.0.0.0
set VITE_API_BASE_URL=http://localhost:8080/api
set VITE_WS_BASE_URL=ws://localhost:8080
set VITE_BACKEND_PORT=8080
set VITE_APP_TITLE=AI文档测试系统
set VITE_APP_VERSION=2.0.0

REM 从.env.development文件额外设置的变量
set VITE_BACKEND_HOST=localhost
set VITE_BACKEND_PROTOCOL=http

echo 环境变量设置完成:
echo   VITE_PORT=%VITE_PORT%
echo   VITE_HOST=%VITE_HOST%
echo   VITE_API_BASE_URL=%VITE_API_BASE_URL%
echo   VITE_WS_BASE_URL=%VITE_WS_BASE_URL%
echo   VITE_APP_TITLE=%VITE_APP_TITLE%
echo   VITE_APP_VERSION=%VITE_APP_VERSION%
echo =======================================

REM 启动开发服务器
echo 启动Vite开发服务器...
npm run dev

pause