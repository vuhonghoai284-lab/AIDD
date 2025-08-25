@echo off
REM Windows专用：在4000端口启动前端开发服务器（修复版）

echo =======================================
echo    启动前端开发服务器 (端口: 4000) 
echo =======================================

REM 临时重命名.env文件，避免冲突
if exist .env (
    ren .env .env.backup
    echo 已备份原有.env文件
)

REM 创建临时环境配置
echo # 临时配置文件 > .env.temp
echo VITE_PORT=4000 >> .env.temp
echo VITE_HOST=0.0.0.0 >> .env.temp
echo VITE_API_BASE_URL=http://localhost:8080/api >> .env.temp
echo VITE_WS_BASE_URL=ws://localhost:8080 >> .env.temp

REM 使用临时配置
ren .env.temp .env

REM 显示当前配置
echo 前端地址: http://localhost:4000
echo 监听地址: 0.0.0.0:4000
echo API地址: http://localhost:8080/api
echo =======================================

REM 设置额外的环境变量
set VITE_PORT=4000
set VITE_HOST=0.0.0.0

echo 正在启动开发服务器...
npm run dev

REM 清理和恢复
echo.
echo 正在清理临时文件...
if exist .env del .env
if exist .env.backup (
    ren .env.backup .env
    echo 已恢复原有.env文件
)

pause