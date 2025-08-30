# 后端 Dockerfile
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建数据和配置目录
RUN mkdir -p /app/data/uploads /app/data/reports /app/config

# 设置权限
RUN chmod +x /app/data /app/config

# 创建非root用户
RUN useradd -m -u 1001 appuser && chown -R appuser:appuser /app
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 启动命令 - 支持外部配置文件
CMD ["sh", "-c", "CONFIG_FILE=${CONFIG_FILE:-config.yaml} python app/main.py"]