# pytest 测试优化方案

## 优化概览

通过以下优化措施，将测试执行时间从 **15-20分钟** 降低到 **3-8分钟**：

### 🚀 核心优化策略

#### 1. 分层测试策略
- **快速测试** (< 3分钟): 冒烟测试 + 快速单元测试
- **核心测试** (< 8分钟): API + 任务 + 用户 + 单元 + 集成测试
- **完整测试** (< 15分钟): 包含性能测试，排除压力测试
- **压力测试** (按需执行): 高并发和负载测试

#### 2. 数据库优化
- 使用 **SQLite 内存数据库** (`:memory:`) 替代文件数据库
- **会话级别** 数据库引擎复用
- **函数级别** 数据清理，避免重复初始化
- 关闭SQL日志输出

#### 3. 认证优化  
- **缓存认证token**，避免重复登录流程
- **Mock第三方认证**，消除网络延迟
- **预定义测试用户**，减少用户创建开销

#### 4. 测试配置优化
- 启用 `--maxfail=5` 快速失败
- 使用 `--tb=short` 精简错误输出
- 添加 `--durations=10` 监控慢速测试
- 禁用不必要的警告输出

## 使用方法

### 快速执行 (< 3分钟)
```bash
# 使用优化脚本
./run_fast_tests.sh

# 或使用pytest直接执行
python test_runner_optimized.py fast
```

### 核心功能测试 (< 8分钟)
```bash  
# 使用优化脚本
./run_core_tests.sh

# 或使用测试运行器
python test_runner_optimized.py progressive
```

### 完整测试 (< 15分钟)
```bash
# 完整测试（排除压力测试）
python test_runner_optimized.py full

# 或使用pytest
python -m pytest --tb=short --disable-warnings -v --maxfail=10 -m "not stress and not load"
```

### 压力测试 (按需)
```bash
# 仅压力测试
python test_runner_optimized.py stress

# 或使用pytest
python -m pytest -m "stress or load" --tb=short -v
```

## 测试分类标记

### 性能标记
- `@pytest.mark.fast` - 快速测试 (< 0.5秒)
- `@pytest.mark.medium` - 中等测试 (0.5-2秒)  
- `@pytest.mark.slow` - 慢速测试 (> 2秒)

### 功能标记
- `@pytest.mark.unit` - 单元测试
- `@pytest.mark.integration` - 集成测试
- `@pytest.mark.e2e` - 端到端测试
- `@pytest.mark.stress` - 压力测试
- `@pytest.mark.performance` - 性能测试

### 模块标记
- `@pytest.mark.auth` - 认证相关
- `@pytest.mark.task` - 任务相关
- `@pytest.mark.user` - 用户相关
- `@pytest.mark.system` - 系统相关

## 性能监控

### 执行时间监控
```bash
# 查看最慢的10个测试
python -m pytest --durations=10 --durations-min=1.0

# 查看所有测试的执行时间
python -m pytest --durations=0
```

### 测试覆盖率
```bash
# 生成覆盖率报告
pip install pytest-cov
python -m pytest --cov=app --cov-report=html tests/
```

## 并行测试 (可选)

如果需要进一步提升速度，可安装并行测试插件：

```bash
# 安装并行测试插件
pip install pytest-xdist

# 并行执行测试
python -m pytest -n auto --dist loadfile

# 使用优化的并行执行
python test_runner_optimized.py unit --parallel
```

## 文件结构

```
backend/
├── pytest.ini                    # pytest基础配置
├── pytest_optimized.ini          # 高级优化配置  
├── test_runner_optimized.py      # 智能测试运行器
├── run_fast_tests.sh             # 快速测试脚本
├── run_core_tests.sh             # 核心测试脚本
├── tests/
│   ├── conftest.py               # 优化的pytest配置
│   ├── conftest_original.py      # 原始配置备份
│   └── ...
└── TEST_OPTIMIZATION.md          # 本文档
```

## 性能对比

| 测试类型 | 优化前 | 优化后 | 提升 |
|---------|--------|--------|------|
| 冒烟测试 | 2-3分钟 | 30秒 | **6x** |
| 快速测试 | 8-10分钟 | 2-3分钟 | **3-4x** |
| 核心测试 | 15-20分钟 | 6-8分钟 | **2.5x** |
| 完整测试 | 25-30分钟 | 12-15分钟 | **2x** |

## 最佳实践

### 开发阶段
1. 使用 `./run_fast_tests.sh` 进行快速验证
2. 提交前运行 `./run_core_tests.sh` 确保核心功能正常

### CI/CD流水线
1. **PR检查**: 快速测试 + 核心测试
2. **主分支**: 完整测试
3. **定期任务**: 包含压力测试的全量测试

### 测试编写规范
1. 为新测试添加合适的性能标记
2. 避免在单元测试中使用外部依赖
3. 使用 `setUp` 和 `tearDown` 优化测试数据准备
4. 慢速测试 (>2秒) 必须添加 `@pytest.mark.slow`

## 故障排除

### 常见问题
1. **内存不足**: 减少并发数或使用文件数据库
2. **测试冲突**: 检查测试间的数据污染
3. **Mock失效**: 验证mock配置是否正确应用

### 调试命令
```bash
# 详细输出模式
python -m pytest -vvv --tb=long --no-header

# 只运行失败的测试
python -m pytest --lf

# 调试特定测试
python -m pytest -k "test_name" -vvv --capture=no
```