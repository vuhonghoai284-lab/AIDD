# API测试目录结构说明

本目录按照资源URL层级组织了所有API接口测试，实现了用户请求的测试重构目标。

## 目录结构

```
tests/api/
├── system/                 # 系统相关API测试
│   ├── test_root.py       # GET / 根路径测试
│   ├── test_config.py     # GET /api/config 配置测试
│   └── test_models.py     # GET /api/models 模型列表测试
├── auth/                   # 认证相关API测试
│   ├── test_authentication.py  # 通用认证和权限测试
│   ├── test_system_login.py     # POST /api/auth/system/login 系统登录
│   ├── test_thirdparty.py       # 第三方OAuth认证流程
│   └── test_token_exchange.py   # POST /api/auth/thirdparty/exchange-token
├── users/                  # 用户相关API测试
│   ├── test_me.py         # GET /api/users/me 当前用户信息
│   └── test_list.py       # GET /api/users/ 用户列表
├── tasks/                  # 任务相关API测试
│   ├── test_crud.py       # 任务CRUD操作 (GET/POST/DELETE /api/tasks/)
│   ├── test_retry.py      # POST /api/tasks/{id}/retry 重试任务
│   ├── test_report.py     # GET /api/tasks/{id}/report 下载报告
│   ├── test_batch.py      # POST /api/tasks/batch 批量创建
│   ├── test_pagination.py # GET /api/tasks/paginated 分页查询
│   ├── test_statistics.py # GET /api/tasks/statistics 统计信息
│   └── test_files.py      # GET /api/tasks/{id}/file 文件下载
├── ai_outputs/             # AI输出相关API测试
│   ├── test_task_outputs.py    # GET /api/tasks/{id}/ai-outputs
│   └── test_single_output.py   # GET /api/ai-outputs/{id}
├── issues/                 # 问题相关API测试
│   ├── test_feedback.py   # PUT /api/issues/{id}/feedback
│   └── test_satisfaction.py    # PUT /api/issues/{id}/satisfaction
├── task_logs/              # 任务日志API测试
│   └── test_history.py    # GET /api/tasks/{id}/logs/history
├── task_shares/            # 任务分享API测试
│   ├── test_sharing.py    # 通用分享功能测试
│   ├── test_create.py     # POST /api/task-shares/ 创建分享
│   ├── test_management.py # 分享管理操作
│   └── test_access.py     # 分享访问控制
└── analytics/              # 数据分析API测试
    ├── test_overview.py   # GET /api/analytics/overview 概览统计
    ├── test_users.py      # GET /api/analytics/users 用户统计
    └── test_tasks.py      # GET /api/analytics/tasks 任务统计
```

## 测试覆盖范围

### HTTP方法覆盖
- ✅ GET - 所有查询接口
- ✅ POST - 创建和登录接口
- ✅ PUT - 更新操作
- ✅ DELETE - 删除操作

### 测试类型覆盖
- ✅ 成功响应测试
- ✅ 权限和认证测试
- ✅ 数据验证测试
- ✅ 性能测试
- ✅ 错误处理测试
- ✅ 并发访问测试

### 业务场景覆盖
- ✅ 用户认证和权限控制
- ✅ 任务生命周期管理
- ✅ 文件上传和下载
- ✅ AI输出和问题反馈
- ✅ 数据统计和分析
- ✅ 系统配置和健康检查

## 运行测试

### 运行所有API测试
```bash
python -m pytest tests/api/ -v
```

### 按模块运行测试
```bash
# 系统API测试
python -m pytest tests/api/system/ -v

# 用户API测试  
python -m pytest tests/api/users/ -v

# 认证API测试
python -m pytest tests/api/auth/ -v

# 任务API测试
python -m pytest tests/api/tasks/ -v

# 分析API测试
python -m pytest tests/api/analytics/ -v
```

### 按HTTP方法运行测试
```bash
# 只运行GET方法测试
python -m pytest tests/api/ -k "get_" -v

# 只运行POST方法测试
python -m pytest tests/api/ -k "post_" -v
```

## 测试标记

使用pytest标记系统组织测试：

- `@pytest.mark.unit` - 单元测试
- `@pytest.mark.integration` - 集成测试  
- `@pytest.mark.e2e` - 端到端测试
- `@pytest.mark.performance` - 性能测试
- `@pytest.mark.security` - 安全测试

## 注意事项

1. **文件命名规范**: 所有测试文件以 `test_` 开头，按API资源命名
2. **测试类命名**: 使用 `Test{Resource}{Operation}API` 格式
3. **测试方法命名**: 使用 `test_{operation}_{scenario}` 格式
4. **测试ID**: 重要测试案例包含ID标识，如 `USER-001`, `SYS-002`
5. **最小粒度**: 每个测试文件对应一个API资源URL
6. **Mock使用**: 适当使用mock避免外部依赖问题

## 迁移说明

原有的测试文件已成功迁移到新结构：
- ✅ `test_system_api.py` → `tests/api/system/`
- ✅ `test_user_api.py` → `tests/api/users/`
- ✅ `test_ai_output_api.py` → `tests/api/ai_outputs/`
- ✅ `test_analytics_api.py` → `tests/api/analytics/`
- ✅ `test_api.py` → `tests/api/tasks/` (部分内容)

所有原始测试文件已删除，避免重复和混乱。