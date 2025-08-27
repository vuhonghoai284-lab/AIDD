@echo off
REM Windows环境变量诊断工具
REM 帮助诊断.env文件加载问题

echo =======================================
echo   Windows环境变量诊断工具
echo =======================================

echo.
echo 1. 检查.env文件是否存在...
if exist .env (
    echo ✓ .env文件存在
) else (
    echo ✗ .env文件不存在
    goto :end
)

echo.
echo 2. 检查.env文件内容...
type .env

echo.
echo 3. 检查.env.development文件...
if exist .env.development (
    echo ✓ .env.development文件存在
    type .env.development
) else (
    echo ✗ .env.development文件不存在
)

echo.
echo 4. 检查package.json中的scripts配置...
findstr /C:"\"dev\"" package.json

echo.
echo 5. 检查vite.config.ts配置...
if exist vite.config.ts (
    echo ✓ vite.config.ts存在
) else (
    echo ✗ vite.config.ts不存在
)

echo.
echo 6. 尝试设置环境变量并启动...
echo 建议使用以下方法之一：
echo.
echo 方法1: 使用start-dev-windows.bat
echo   start-dev-windows.bat
echo.
echo 方法2: 手动设置环境变量
echo   set VITE_API_BASE_URL=http://localhost:8080/api
echo   set VITE_WS_BASE_URL=ws://localhost:8080
echo   npm run dev
echo.
echo 方法3: 使用cross-env (需要安装)
echo   npm install --save-dev cross-env
echo   npx cross-env VITE_API_BASE_URL=http://localhost:8080/api npm run dev

:end
echo.
echo =======================================
echo 诊断完成。如果仍有问题，请检查：
echo 1. .env文件是否使用UTF-8编码
echo 2. .env文件是否在项目根目录
echo 3. 变量名是否以VITE_开头
echo 4. 是否安装了所有依赖: npm install
echo =======================================
pause