@echo off
echo AI文档测试系统启动脚本
echo ========================

REM 检查Python环境
echo 检查Python环境...
python --version

REM 创建虚拟环境（如果不存在）
if not exist "backend\venv" (
    echo 创建Python虚拟环境...
    cd backend
    python -m venv venv
    cd ..
)

REM 激活虚拟环境并安装后端依赖
echo 安装后端依赖...
cd backend
call venv\Scripts\activate.bat
pip install -r requirements.txt

REM 启动后端服务
echo 启动后端服务...
start /B python main.py
cd ..

REM 安装前端依赖
echo 安装前端依赖...
cd frontend
if not exist "node_modules" (
    echo 使用华为云镜像源安装npm包...
    npm config set registry https://mirrors.huaweicloud.com/repository/npm/
    npm install
)

REM 启动前端服务
echo 启动前端服务...
start npm start
cd ..

echo ========================
echo 系统启动完成！
echo 后端服务: http://localhost:8080
echo 前端服务: http://localhost:3000
echo API文档: http://localhost:8080/docs
echo ========================
pause