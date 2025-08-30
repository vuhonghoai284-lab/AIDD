# GitHub Actions 工作流程

本项目使用 GitHub Actions 实现完整的 CI/CD 流程，包含代码质量检查、构建、测试、Docker 镜像构建和部署。

## 🏗️ 工作流程架构

### 1. 持续集成 (CI) - `ci.yml`
**触发条件**: 推送到 main/develop 分支或创建 Pull Request  
**功能**:
- 智能变更检测（仅构建有变化的模块）
- 前端构建和测试 (Node.js 20)
- 后端测试和健康检查 (Python 3.11)
- 安全扫描
- 构建产物上传

**工作流程**:
```
变更检测 → 前端CI/后端CI → 安全扫描 → 状态汇总
    ↓           ↓              ↓         ↓
  路径过滤   构建+测试      审计检查   结果报告
```

### 2. Docker 构建 - `docker-build.yml`
**触发条件**: 推送到 main 分支，创建版本标签，或手动触发  
**功能**:
- 多平台构建 (linux/amd64, linux/arm64)
- 智能缓存策略
- 安全漏洞扫描
- 镜像发布到 GHCR
- 自动版本标记

**镜像标记策略**:
- `main` 分支 → `latest`
- Git 标签 → 版本号 (如 `v1.0.0`)
- 提交哈希 → `main-abc123`

### 3. 代码质量检查 - `code-quality.yml`
**触发条件**: Pull Request 或每周定时执行  
**功能**:
- 代码格式化检查 (Prettier, Black)
- 静态分析 (ESLint, Flake8, MyPy)
- 安全扫描 (Bandit)
- 秘钥泄露检查
- 质量报告生成

### 4. 部署流程 - `deploy.yml`
**触发条件**: CI/Docker 构建成功后或手动触发  
**功能**:
- 分环境部署 (Staging/Production)
- 健康检查
- 回滚机制
- 部署状态通知

## 🚀 使用方法

### 自动触发
- **开发流程**: 提交代码到 `develop` → CI 检查 → 合并到 `main` → 完整构建和部署
- **发版流程**: 创建 `v*.*.*` 标签 → Docker 构建 → 自动发布

### 手动触发
```bash
# 手动触发 Docker 构建
gh workflow run docker-build.yml

# 手动部署到 staging
gh workflow run deploy.yml -f environment=staging

# 手动部署到生产环境
gh workflow run deploy.yml -f environment=production
```

## 📊 工作流程状态

| 工作流程 | 状态 | 描述 |
|---------|------|------|
| CI | ![CI](https://github.com/vuhonghoai284-lab/AIDD/actions/workflows/ci.yml/badge.svg) | 持续集成 |
| Docker Build | ![Docker](https://github.com/vuhonghoai284-lab/AIDD/actions/workflows/docker-build.yml/badge.svg) | Docker 镜像构建 |
| Code Quality | ![Quality](https://github.com/vuhonghoai284-lab/AIDD/actions/workflows/code-quality.yml/badge.svg) | 代码质量检查 |
| Deploy | ![Deploy](https://github.com/vuhonghoai284-lab/AIDD/actions/workflows/deploy.yml/badge.svg) | 应用部署 |

## ⚙️ 配置说明

### 环境变量
- `NODE_VERSION`: Node.js 版本 (默认: 20)
- `PYTHON_VERSION`: Python 版本 (默认: 3.11)
- `REGISTRY`: Docker 镜像仓库 (默认: ghcr.io)

### Secrets 配置
确保在仓库设置中配置以下 secrets:
- `GITHUB_TOKEN`: GitHub 访问令牌 (自动提供)

### 环境保护
- `staging`: 需要审批的 staging 环境
- `production`: 需要审批的生产环境

## 🔧 维护指南

### 添加新的检查项
1. 修改 `ci.yml` 中的相应步骤
2. 更新 `code-quality.yml` 中的质量检查
3. 测试工作流程是否正常运行

### 修改部署流程
1. 编辑 `deploy.yml` 中的部署步骤
2. 更新环境配置
3. 测试部署流程

### 优化构建性能
- 使用缓存策略减少依赖安装时间
- 并行执行独立的构建步骤
- 优化 Docker 层缓存

## 📝 最佳实践

1. **分支保护**: main 分支需要通过 CI 检查才能合并
2. **并行构建**: 前端和后端构建并行执行
3. **智能触发**: 只在相关文件变更时触发构建
4. **安全优先**: 每次构建都包含安全扫描
5. **快速反馈**: 关键检查在 15 分钟内完成