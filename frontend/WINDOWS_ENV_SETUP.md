# Windows下前端环境变量配置指南

## 问题描述

在Windows环境下执行 `npm run dev` 时，`.env` 文件中的环境变量可能不生效，导致前端应用无法正确连接到后端API。

## 常见原因

1. **文件编码问题**：Windows默认编码与Vite预期不符
2. **文件位置问题**：`.env` 文件不在正确位置
3. **变量命名问题**：环境变量名称不符合Vite要求
4. **Windows路径解析问题**：路径分隔符导致的问题

## 解决方案

### 方案1：使用专用Windows启动脚本（推荐）

直接运行项目提供的Windows启动脚本：

```bash
# 在frontend目录下执行
start-dev-windows.bat
```

这个脚本会：
- 手动设置所有必要的环境变量
- 显示当前配置
- 启动Vite开发服务器

### 方案2：使用诊断工具

如果遇到问题，先运行诊断工具：

```bash
diagnose-env-windows.bat
```

诊断工具会检查：
- `.env` 文件是否存在
- 文件内容是否正确
- Vite配置是否正确
- 提供解决建议

### 方案3：手动设置环境变量

在命令行中手动设置环境变量后启动：

```cmd
set VITE_API_BASE_URL=http://localhost:8080/api
set VITE_WS_BASE_URL=ws://localhost:8080
set VITE_BACKEND_PORT=8080
set VITE_APP_TITLE=AI文档测试系统
set VITE_APP_VERSION=2.0.0
npm run dev
```

### 方案4：使用cross-env（需要额外安装）

安装cross-env包：
```bash
npm install --save-dev cross-env
```

修改package.json的scripts：
```json
{
  "scripts": {
    "dev": "cross-env VITE_API_BASE_URL=http://localhost:8080/api vite --host 0.0.0.0"
  }
}
```

### 方案5：修改PowerShell执行策略（高级用户）

如果使用PowerShell，可能需要修改执行策略：

```powershell
# 以管理员身份运行PowerShell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 然后使用PowerShell脚本设置环境变量
$env:VITE_API_BASE_URL="http://localhost:8080/api"
$env:VITE_WS_BASE_URL="ws://localhost:8080"
npm run dev
```

## 验证配置是否生效

启动开发服务器后，打开浏览器控制台，查看是否有类似以下的日志：

```
应用配置: {
  apiBaseUrl: "http://localhost:8080/api",
  wsBaseUrl: "ws://localhost:8080", 
  appTitle: "AI文档测试系统",
  appVersion: "2.0.0",
  environment: "开发环境",
  environmentVariables: {
    VITE_API_BASE_URL: "http://localhost:8080/api",
    VITE_WS_BASE_URL: "ws://localhost:8080",
    VITE_BACKEND_PORT: "8080"
  }
}
```

如果环境变量显示为 `undefined`，说明环境变量没有正确加载。

## 文件检查清单

确保以下文件存在且内容正确：

### `.env` 文件（项目根目录）
```env
# 前端服务配置
VITE_PORT=3000
VITE_HOST=0.0.0.0

# 后端API配置  
VITE_API_BASE_URL=http://localhost:8080/api
VITE_WS_BASE_URL=ws://localhost:8080
VITE_BACKEND_PORT=8080

# 应用配置
VITE_APP_TITLE=AI文档测试系统  
VITE_APP_VERSION=2.0.0
```

### `.env.development` 文件（可选）
```env
# 开发环境特定配置
VITE_API_BASE_URL=http://localhost:8080/api
VITE_WS_BASE_URL=ws://localhost:8080
VITE_APP_TITLE=AI文档测试系统
VITE_APP_VERSION=2.0.0
VITE_BACKEND_HOST=localhost
VITE_BACKEND_PORT=8080
VITE_BACKEND_PROTOCOL=http
```

## 注意事项

1. **变量前缀**：Vite只会加载以 `VITE_` 开头的环境变量
2. **文件编码**：确保 `.env` 文件使用UTF-8编码保存
3. **重启服务**：修改环境变量后需要重启开发服务器
4. **缓存清理**：如果仍有问题，可以删除 `node_modules` 重新安装依赖

## 故障排除

### 问题1：API请求失败
**现象**：前端无法连接后端API
**解决**：
1. 确认后端服务已启动（端口8080）
2. 检查 `VITE_API_BASE_URL` 是否正确
3. 确认防火墙没有阻止连接

### 问题2：WebSocket连接失败  
**现象**：实时功能不工作
**解决**：
1. 检查 `VITE_WS_BASE_URL` 配置
2. 确认后端WebSocket服务正常

### 问题3：环境变量显示undefined
**现象**：控制台显示环境变量为undefined
**解决**：
1. 使用 `start-dev-windows.bat` 启动
2. 检查 `.env` 文件编码和位置
3. 运行 `diagnose-env-windows.bat` 诊断

## 联系支持

如果以上方案都无法解决问题，请提供以下信息：
1. Windows版本和PowerShell版本
2. Node.js和npm版本
3. `diagnose-env-windows.bat` 的输出结果
4. 浏览器控制台的错误信息