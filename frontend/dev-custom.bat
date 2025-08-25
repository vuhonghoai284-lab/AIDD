@echo off
REM Windows专用：自定义端口启动前端开发服务器
REM 用法: dev-custom.bat [端口号]

REM 获取端口参数，默认为4000
set PORT=%1
if "%PORT%"=="" set PORT=4000

echo =======================================
echo    启动前端开发服务器 (端口: %PORT%)
echo =======================================

REM 设置环境变量
set VITE_PORT=%PORT%
set VITE_HOST=0.0.0.0

REM 显示配置信息
echo 前端地址: http://localhost:%PORT%
echo 监听地址: 0.0.0.0:%PORT%
echo =======================================

REM 启动开发服务器
npm run dev

pause