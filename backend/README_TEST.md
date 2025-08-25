# 测试模式使用说明

## 概述

测试模式允许您在不调用真实AI API的情况下运行和调试系统，使用模拟数据来测试所有功能。

## 快速启动

### 方法1: 使用测试启动脚本
```bash
python run_test.py
```

### 方法2: 使用命令行参数
```bash
python run.py --mode test --reload
```

### 方法3: 使用环境变量
```bash
export APP_MODE=test
python run.py
```

## 测试模式特性

### 🤖 AI服务模拟
- 不调用真实的OpenAI/Anthropic API
- 使用本地生成的模拟数据
- 可配置响应延迟和问题类型

### 📊 数据隔离
- 使用独立的测试数据库 (`./data/test.db`)
- 文件上传到测试目录 (`./data/test/uploads`)
- 日志输出到测试目录 (`./data/test/logs`)

### ⚡ 快速响应
- 模拟的AI响应时间：0.5-2秒
- 可配置的处理延迟
- 确定性的测试结果（相同输入产生相同输出）

## 配置文件

测试模式使用 `config.test.yaml` 配置文件：

```yaml
# 测试模式标志
test_mode: true

# AI模型配置 - 使用mock provider
ai_models:
  models:
    - label: "测试模型 (快速响应)"
      provider: "mock"  # 关键：使用mock provider
      config:
        response_delay: 0.5  # 响应延迟
```

## 测试数据

### 文档内容
- 如果上传的文件不存在，系统会自动生成测试文档内容
- 包含多个章节和典型的技术文档结构

### 生成的问题类型
1. **语法错误** (30%概率)
   - 句子结构不完整
   - 标点符号使用不当
   - 中英文混用格式不统一

2. **逻辑问题** (40%概率)  
   - 前后描述存在矛盾
   - 因果关系不明确
   - 论述缺乏支撑依据

3. **完整性问题** (30%概率)
   - 缺少必要的背景介绍
   - 示例代码不完整
   - 缺少结论或总结

### 问题数量
- 每个文档生成3-10个问题
- 问题严重程度：致命/严重/一般/提示
- 置信度：0.7-0.95

## API测试

### 检查服务状态
```bash
curl http://localhost:8080/
```

响应示例：
```json
{
  "message": "AI文档测试系统后端API v2.0",
  "mode": "测试模式",
  "test_mode": true
}
```

### 获取模型列表
```bash
curl http://localhost:8080/api/models
```

### 创建测试任务
```bash
curl -X POST "http://localhost:8080/api/tasks" \
  -H "Content-Type: multipart/form-data" \
  -F "title=测试文档" \
  -F "model_index=0" \
  -F "file=@test.md"
```

## 开发调试

### 日志查看
测试模式使用DEBUG级别日志：
```bash
tail -f ./data/test/logs/app.log
```

### 数据库检查
```bash
# 连接测试数据库
sqlite3 ./data/test.db

# 查看任务
SELECT * FROM tasks;

# 查看问题
SELECT * FROM issues;

# 查看AI输出
SELECT * FROM ai_outputs;
```

### 重置测试数据
```bash
# 删除测试数据库和文件
rm -rf ./data/test/
```

## 前端配置

确保前端连接到正确的后端地址：
```javascript
// 开发环境
const API_BASE_URL = 'http://localhost:8080';
```

## 常见问题

### Q: 如何切换回生产模式？
A: 使用 `python run.py --mode production` 或删除 `APP_MODE` 环境变量

### Q: 测试模式下可以上传真实文件吗？
A: 可以，系统会正常处理上传的文件，但AI分析使用模拟数据

### Q: 模拟数据是否一致？
A: 是的，相同的文档内容会产生相同的模拟问题（基于内容hash）

### Q: 如何修改模拟的问题类型？
A: 编辑 `app/services/mock_ai_service.py` 中的问题模板

## 下一步

- 使用前端界面测试完整流程
- 验证AI输出显示功能
- 测试问题反馈功能
- 检查实时日志显示