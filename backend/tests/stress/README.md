# 高并发压力测试

本目录包含了系统的高并发和压力测试用例，用于验证系统在高负载情况下的性能表现和稳定性。

## 测试文件说明

### 1. `test_concurrent_task_execution.py`
**并发任务执行测试**
- 测试多用户同时创建任务的并发安全性
- 测试任务执行的并发处理能力
- 测试任务状态查询的高并发访问
- 测试混合操作（创建、执行、查询）的并发场景
- 测试数据库连接池在负载下的性能

**主要测试场景**：
- 10个并发用户同时创建任务
- 5个任务同时执行处理
- 大量并发状态查询
- 混合操作负载测试
- 数据库连接池压力测试

### 2. `test_performance_benchmarks.py`
**性能基准测试**
- 建立系统性能基线指标
- 测试不同负载条件下的响应时间
- 测试系统吞吐量（RPS - Requests Per Second）
- 测试大文件处理性能
- 提供性能回归检测

**性能指标**：
- 平均响应时间
- P95/P99响应时间
- 每秒请求数（RPS）
- 成功率
- 系统资源使用

### 3. `test_resource_contention.py`
**资源竞争和并发安全测试**
- 测试任务ID生成的唯一性
- 测试用户会话的并发管理
- 测试数据库事务的一致性
- 测试文件上传的资源竞争
- 验证并发操作的数据完整性

**关键测试点**：
- ID生成不会产生重复
- 多用户并发操作互不干扰
- 数据库事务保持一致性
- 文件上传处理并发安全

## 运行测试

### 快速运行
```bash
# 运行所有压力测试
python run_stress_tests.py

# 只运行并发测试
python run_stress_tests.py --concurrent

# 只运行性能基准测试
python run_stress_tests.py --performance

# 只运行资源竞争测试
python run_stress_tests.py --resource

# 快速模式（减少测试时间和并发数）
python run_stress_tests.py --quick

# 生成详细报告
python run_stress_tests.py --report
```

### 使用pytest直接运行
```bash
# 运行所有压力测试
pytest tests/stress/ -m stress -v

# 运行特定测试文件
pytest tests/stress/test_concurrent_task_execution.py -v

# 运行特定测试用例
pytest tests/stress/test_performance_benchmarks.py::TestPerformanceBenchmarks::test_task_creation_benchmark -v
```

## 性能基准指标

### 任务创建性能
- **目标成功率**: ≥ 90%
- **平均响应时间**: ≤ 2.0秒
- **P95响应时间**: ≤ 5.0秒
- **最小RPS**: ≥ 20次/秒

### 任务查询性能
- **目标成功率**: ≥ 95%
- **平均响应时间**: ≤ 1.0秒
- **P95响应时间**: ≤ 2.0秒
- **最小RPS**: ≥ 50次/秒

### 混合操作性能
- **目标成功率**: ≥ 85%
- **平均响应时间**: ≤ 3.0秒
- **最小RPS**: ≥ 15次/秒

### 大文件处理性能
- **目标成功率**: ≥ 80%
- **平均响应时间**: ≤ 10.0秒
- **P95响应时间**: ≤ 20.0秒

## 测试环境要求

### 系统资源
- **最小内存**: 512MB
- **CPU**: 至少2核心
- **数据库连接**: 支持至少50个并发连接
- **磁盘空间**: 至少1GB可用空间

### 依赖条件
- 所有常规测试通过
- 数据库正常运行
- API服务正常启动
- 测试用户认证配置正确

## 故障排除

### 常见问题

1. **数据库连接超时**
   - 检查数据库连接池配置
   - 确保数据库可以处理并发连接
   - 调整 `pool_size` 和 `max_overflow` 参数

2. **响应时间过长**
   - 检查AI服务是否可用
   - 验证网络连接稳定性
   - 监控系统资源使用情况

3. **并发测试失败**
   - 检查系统内存是否充足
   - 验证数据库事务隔离级别
   - 确认没有死锁或资源竞争

4. **ID重复问题**
   - 检查数据库自增ID配置
   - 验证事务提交顺序
   - 确认数据库并发处理正确

### 调试技巧

1. **启用详细日志**
   ```bash
   pytest tests/stress/ -v -s --log-cli-level=INFO
   ```

2. **单独运行失败的测试**
   ```bash
   pytest tests/stress/test_concurrent_task_execution.py::TestConcurrentTaskExecution::test_concurrent_task_creation -v -s
   ```

3. **使用资源监控**
   - 监控CPU、内存使用
   - 查看数据库连接数
   - 检查磁盘I/O情况

## 测试报告

运行带 `--report` 参数的测试会生成详细的Markdown报告，包含：
- 测试执行概述
- 性能指标汇总
- 失败测试的错误信息
- 成功率统计
- 建议和改进点

报告文件名格式：`stress_test_report_YYYYMMDD_HHMMSS.md`

## 持续集成

这些压力测试可以集成到CI/CD流水线中：

```yaml
# GitHub Actions 示例
- name: Run Stress Tests
  run: |
    python run_stress_tests.py --quick --report
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
```

## 贡献指南

添加新的压力测试时，请遵循以下规范：

1. **命名规范**: 测试方法以 `test_` 开头，包含 `@pytest.mark.stress` 装饰器
2. **文档说明**: 每个测试都应该有清晰的docstring说明
3. **断言标准**: 设置合理的性能阈值和成功率要求
4. **清理工作**: 确保测试后清理测试数据
5. **报告指标**: 输出关键性能指标用于分析