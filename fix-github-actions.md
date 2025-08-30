# GitHub Actions 故障排除指南

## 🔍 检查构建状态

访问GitHub仓库的Actions页面查看构建状态：
```
https://github.com/vuhonghoai284-lab/AIDD/actions
```

## 🚨 可能遇到的问题

### 1. 权限问题

**问题**: `Error: permission denied while trying to connect to the Docker daemon socket`

**解决方案**: 需要启用GitHub仓库的Package权限

1. 进入GitHub仓库设置
2. Settings → Actions → General
3. Workflow permissions → 选择 "Read and write permissions"
4. 保存设置

### 2. 多平台构建失败

**问题**: ARM64构建失败或超时

**解决方案**: 修改构建配置，先只构建AMD64平台

```yaml
# 在 .github/workflows/build.yml 中修改
platforms: linux/amd64  # 暂时移除 ,linux/arm64
```

### 3. 测试阶段失败

**问题**: 集成测试无法访问服务

**解决方案**: 修改测试配置

```yaml
# 修改端口映射和健康检查
- name: Run integration tests
  run: |
    # 启动测试环境
    docker compose --env-file .env.test up -d
    
    # 等待更长时间
    sleep 60
    
    # 检查容器状态
    docker compose --env-file .env.test ps
    
    # 查看日志
    docker compose --env-file .env.test logs
    
    # 健康检查 - 使用容器内部端口
    curl -f http://localhost:8000/health || exit 1
```

### 4. 包推送失败

**问题**: `Error: failed to push to registry`

**解决方案**: 检查GitHub Package Registry设置

1. 确保仓库是公开的，或者配置了正确的访问权限
2. 验证GITHUB_TOKEN权限
3. 检查包名是否符合规范

## 🛠️ 立即修复方案

如果构建失败，可以使用以下简化版本：