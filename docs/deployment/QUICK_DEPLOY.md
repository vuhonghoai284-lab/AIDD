# 快速部署指南

## 🚀 一键部署命令

### 1. 部署前检查
```bash
# 检查环境是否满足部署条件
./pre_deploy_check.sh
```

### 2. 标准部署
```bash
# 完整自动化部署（推荐）
./deploy_update.sh
```

### 3. 快速部署选项
```bash
# 跳过备份（仅在测试环境使用）
./deploy_update.sh --skip-backup

# 跳过依赖安装（如果依赖已是最新）
./deploy_update.sh --skip-deps

# 仅验证环境，不实际部署
./deploy_update.sh --dry-run
```

### 4. 紧急回滚
```bash
# 如果部署出现问题，立即回滚
./deploy_update.sh --rollback
```

---

## 📋 手动部署步骤

如果自动化脚本无法使用，可按以下步骤手动部署：

### 第1步：备份（🚨 必须）
```bash
# 数据库备份
mysqldump -u root -p --single-transaction ai_doc_test > backup_$(date +%Y%m%d_%H%M%S).sql

# 代码备份
git stash push -m "Auto-backup before deployment"
```

### 第2步：更新代码
```bash
git fetch origin
git checkout main
git pull origin main
```

### 第3步：数据库迁移
```bash
cd backend

# 并发限制字段迁移
python3 migrate_user_concurrency.py

# 外键约束问题修复
python3 fix_foreign_key_constraints.py --verify
# 如果有问题：
# python3 fix_foreign_key_constraints.py --force
```

### 第4步：安装依赖
```bash
# 后端依赖
cd backend
pip3 install -r requirements.txt

# 前端依赖
cd ../frontend
npm install
npm run build
```

### 第5步：重启服务
```bash
# 重启后端
sudo systemctl restart ai-doc-backend

# 重启前端
sudo systemctl restart nginx
```

### 第6步：验证部署
```bash
# 检查服务状态
systemctl status ai-doc-backend
systemctl status nginx

# 测试API
curl http://localhost:8080/health
```

---

## ⚡ 核心更新内容

### 新增功能
- **并发任务限制**: 每用户默认10个并发任务，系统级100个
- **外键约束修复**: 解决生产环境数据完整性问题
- **大文档支持**: TEXT字段升级为LONGTEXT

### API变化
- 新增 `GET /api/tasks/concurrency-status` - 获取并发状态
- 新增 `PUT /api/tasks/user/{user_id}/concurrency-limit` - 更新用户限制
- 任务创建API现在会检查并发限制（可能返回HTTP 429）

### 数据库变化
- `users`表新增`max_concurrent_tasks`字段
- `ai_outputs`表字段升级为LONGTEXT
- 自动清理孤儿记录

---

## 🔍 部署验证清单

部署完成后，请确认：

- [ ] 所有服务正常运行
- [ ] 数据库连接正常
- [ ] 可以正常创建任务
- [ ] 并发限制功能工作
- [ ] 文件上传下载正常
- [ ] 用户登录功能正常
- [ ] 前端页面加载正常

---

## 🆘 故障处理

### 服务启动失败
```bash
# 查看服务日志
sudo journalctl -u ai-doc-backend -f

# 手动启动测试
cd backend
python3 app/main.py
```

### 数据库问题
```bash
# 检查数据库状态
sudo systemctl status mysql

# 测试连接
mysql -u root -p -e "SELECT 1"

# 检查表结构
mysql -u root -p ai_doc_test -e "DESCRIBE users"
```

### 前端加载问题
```bash
# 检查nginx状态
sudo systemctl status nginx

# 重新构建前端
cd frontend
npm run build
```

### 回滚操作
```bash
# 停止服务
sudo systemctl stop ai-doc-backend

# 恢复数据库
mysql -u root -p ai_doc_test < backup_YYYYMMDD_HHMMSS.sql

# 恢复代码
git reset --hard HEAD~2

# 重启服务
sudo systemctl start ai-doc-backend
```

---

## 📞 技术支持

如果遇到问题：

1. **查看日志**: 检查 `deployment.log` 文件
2. **验证环境**: 运行 `./pre_deploy_check.sh`
3. **检查状态**: 使用系统命令验证服务状态
4. **回滚**: 如有需要，立即执行回滚操作

---

**重要提醒：**
- 🔴 生产环境部署前务必备份
- 🟡 建议在业务低峰期执行
- 🟢 部署后持续监控系统状态