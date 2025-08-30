# 🚀 AI Document Testing System - 构建脚本目录

此目录包含本地开发环境的构建、部署脚本和相关配置文件。

## 📁 目录结构

```
build/
├── build-local.sh              # 本地构建脚本
├── deploy-local.sh             # 本地部署脚本
├── setup-local.sh              # 完整环境设置脚本
├── start-local.sh              # 一键启动脚本
├── LOCAL_DEPLOYMENT_GUIDE.md   # 详细部署指南
├── .env.template               # 环境变量模板
├── config.local.yaml           # 本地配置模板
├── docker-compose.local.yml    # Docker本地开发环境
└── README.md                   # 本说明文件
```

## 🎯 快速开始

### 从项目根目录启动（推荐）

```bash
# 在项目根目录运行
./start-local.sh
```

### 从build目录启动

```bash
# 进入build目录
cd build

# 运行启动脚本
./start-local.sh
```

## 📋 主要脚本说明

### 1. `start-local.sh` - 一键启动脚本
最简单的启动方式，自动选择最佳启动路径。

```bash
./start-local.sh
```

### 2. `setup-local.sh` - 完整环境设置脚本
交互式环境配置和部署脚本，适合首次使用。

```bash
# 完整交互式设置
./setup-local.sh

# 快速自动设置
./setup-local.sh --quick

# 使用Docker设置
./setup-local.sh --docker
```

### 3. `build-local.sh` - 构建脚本
专门用于构建前端和后端应用。

```bash
# 开发环境构建
./build-local.sh

# 生产环境构建
./build-local.sh --type production

# 快速构建（跳过测试）
./build-local.sh --skip-tests
```

### 4. `deploy-local.sh` - 部署脚本
部署应用到本地环境。

```bash
# 开发模式部署
./deploy-local.sh

# 生产模式部署
./deploy-local.sh --mode prod

# Docker部署
./deploy-local.sh --docker
```

## 📚 配置文件说明

### `.env.template`
环境变量模板，复制为 `.env` 并根据需要修改：

```bash
cp build/.env.template .env
```

### `config.local.yaml`
后端本地配置模板，会自动复制到 `backend/config.local.yaml`。

### `docker-compose.local.yml`
Docker本地开发环境配置，包含前端、后端、Redis等服务。

## 🔧 服务管理

```bash
# 查看服务状态
./build/deploy-local.sh status

# 停止所有服务
./build/deploy-local.sh stop

# 重启服务
./build/deploy-local.sh restart

# 查看日志
./build/deploy-local.sh logs
```

## 🌐 默认访问地址

- **前端应用**: http://localhost:3000
- **后端API**: http://localhost:8080
- **API文档**: http://localhost:8080/docs

## 📖 详细文档

查看 [`LOCAL_DEPLOYMENT_GUIDE.md`](LOCAL_DEPLOYMENT_GUIDE.md) 获取：
- 详细的安装和配置指南
- 故障排除方法
- 开发和测试流程
- 性能优化建议

## 🆘 获取帮助

```bash
# 查看各脚本的帮助信息
./build/build-local.sh --help
./build/deploy-local.sh --help
./build/setup-local.sh --help
```

## 📝 注意事项

1. **权限设置**: 脚本会自动设置执行权限
2. **路径问题**: 从项目根目录运行脚本以避免路径问题
3. **首次运行**: 建议使用 `setup-local.sh` 进行完整设置
4. **依赖检查**: 脚本会自动检查系统依赖
5. **日志查看**: 遇到问题时查看 `logs/` 目录下的日志文件

---

🎉 **祝开发愉快！** 如有问题，请查看详细文档或提交Issue。