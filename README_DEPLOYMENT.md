# AI文档测试系统 - 部署指南

## 前端网络访问配置

前端已配置为监听 `0.0.0.0`，允许其他用户通过网络访问。

### 开发环境启动

```bash
# 进入前端目录
cd frontend

# 安装依赖（如果还没安装）
npm install

# 启动开发服务器（监听0.0.0.0:3000）
npm run dev
```

启动后，系统将在以下地址可用：
- 本地访问：http://localhost:3000
- 局域网访问：http://[你的IP地址]:3000

### 查看本机IP地址

**Windows:**
```bash
ipconfig
# 查看 IPv4 地址，通常是 192.168.x.x
```

**Linux/Mac:**
```bash
ifconfig
# 或
ip addr show
```

### 生产环境部署

1. **构建前端**
```bash
cd frontend
npm run build
# 生成的文件在 dist 目录
```

2. **使用静态服务器部署**

使用 `serve` 包：
```bash
# 全局安装serve
npm install -g serve

# 在dist目录启动服务
serve -s dist -l 0.0.0.0:3000
```

使用 Nginx：
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    root /path/to/frontend/dist;
    index index.html;
    
    # 处理前端路由
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # 代理API请求到后端
    location /api {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 防火墙配置

确保防火墙允许相应端口的访问：

**Windows防火墙:**
```bash
# 允许端口3000
netsh advfirewall firewall add rule name="Frontend Port 3000" dir=in action=allow protocol=TCP localport=3000
```

**Linux (Ubuntu/Debian):**
```bash
# 使用ufw
sudo ufw allow 3000/tcp
sudo ufw allow 8080/tcp  # 后端API端口
```

**Linux (CentOS/RHEL):**
```bash
# 使用firewall-cmd
sudo firewall-cmd --permanent --add-port=3000/tcp
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload
```

### Docker部署（推荐）

创建 `docker-compose.yml`:
```yaml
version: '3.8'

services:
  frontend:
    build: ./frontend
    ports:
      - "0.0.0.0:3000:3000"
    environment:
      - VITE_API_BASE_URL=http://backend:8080
    depends_on:
      - backend
    networks:
      - app-network

  backend:
    build: ./backend
    ports:
      - "0.0.0.0:8080:8080"
    volumes:
      - ./backend/data:/app/data
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    networks:
      - app-network

networks:
  app-network:
    driver: bridge
```

前端 Dockerfile:
```dockerfile
# frontend/Dockerfile
FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
```

### 安全建议

1. **生产环境使用HTTPS**
   - 使用Let's Encrypt获取免费SSL证书
   - 配置Nginx强制HTTPS

2. **访问控制**
   - 考虑添加身份验证
   - 限制IP访问范围（如仅允许公司内网）

3. **端口安全**
   - 生产环境不要暴露后端端口（8080）
   - 所有请求通过前端代理

4. **环境变量**
   - 敏感信息（API密钥等）使用环境变量
   - 不要将 `.env` 文件提交到版本控制

### 常见问题

**Q: 其他用户无法访问？**
A: 检查：
1. 防火墙是否开放端口
2. 服务是否监听0.0.0.0而非localhost
3. 网络是否互通（同一局域网）

**Q: API请求失败？**
A: 确保：
1. 后端服务正在运行
2. 代理配置正确
3. CORS设置允许前端域名

**Q: 端口被占用？**
A: 修改 `vite.config.ts` 中的端口配置，或使用环境变量：
```bash
VITE_PORT=3001 npm run dev
```