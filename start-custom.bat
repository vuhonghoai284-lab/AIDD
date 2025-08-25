@echo off
REM 自定义IP和端口启动脚本 (Windows)
REM 使用方法：start-custom.bat [前端IP] [前端端口] [后端IP] [后端端口]

REM 设置默认值
set FRONTEND_HOST=%1
set FRONTEND_PORT=%2  
set BACKEND_HOST=%3
set BACKEND_PORT=%4

REM 如果没有提供参数，使用默认值
if "%FRONTEND_HOST%"=="" set FRONTEND_HOST=0.0.0.0
if "%FRONTEND_PORT%"=="" set FRONTEND_PORT=3000
if "%BACKEND_HOST%"=="" set BACKEND_HOST=0.0.0.0  
if "%BACKEND_PORT%"=="" set BACKEND_PORT=8080

echo ================================
echo    AI文档测试系统自定义启动
echo ================================
echo 前端地址: http://%FRONTEND_HOST%:%FRONTEND_PORT%
echo 后端地址: http://%BACKEND_HOST%:%BACKEND_PORT%
echo ================================

REM 启动后端
echo [1/2] 启动后端服务...
cd backend
set SERVER_HOST=%BACKEND_HOST%
set SERVER_PORT=%BACKEND_PORT%
start cmd /c "python app/main.py"

REM 等待后端启动
timeout /t 3 /nobreak

REM 启动前端
echo [2/2] 启动前端服务...
cd ..\frontend

REM 设置前端环境变量
set VITE_HOST=%FRONTEND_HOST%
set VITE_PORT=%FRONTEND_PORT%
set VITE_API_BASE_URL=http://%BACKEND_HOST%:%BACKEND_PORT%/api
set VITE_WS_BASE_URL=ws://%BACKEND_HOST%:%BACKEND_PORT%
set VITE_BACKEND_PORT=%BACKEND_PORT%

npm run dev

echo 启动完成！
pause