# 前端自动化测试指南

## 概述

本项目采用了完整的自动化测试方案，包括单元测试、集成测试和端到端(E2E)测试。

## 测试框架

- **Vitest**: 单元测试和集成测试框架
- **React Testing Library**: React组件测试工具
- **Playwright**: 端到端测试框架
- **MSW**: API请求Mock工具

## 安装依赖

```bash
npm install
```

## 运行测试

### 单元测试和集成测试

```bash
# 运行所有测试
npm run test

# 运行测试并生成覆盖率报告
npm run test:coverage

# 运行测试UI界面
npm run test:ui

# 仅运行单元测试
npm run test:unit

# 仅运行集成测试
npm run test:integration
```

### E2E测试

```bash
# 安装Playwright浏览器
npx playwright install

# 运行E2E测试
npm run test:e2e

# 运行E2E测试UI界面
npm run test:e2e:ui

# 调试E2E测试
npm run test:e2e:debug
```

## 测试文件结构

```
src/
├── test/                    # 测试配置和工具
│   ├── setup.ts            # 测试环境设置
│   ├── factories.ts         # 测试数据工厂
│   ├── utils.tsx           # 测试工具函数
│   └── mocks/              # API Mock配置
│       ├── server.ts        # MSW服务器配置
│       └── handlers.ts      # API请求处理器
├── services/__tests__/      # 服务层测试
├── pages/__tests__/         # 页面组件测试
└── components/__tests__/    # 组件测试

e2e/                        # E2E测试
├── fixtures/               # 测试夹具文件
├── login.spec.ts           # 登录流程测试
└── task-workflow.spec.ts   # 任务管理流程测试
```

## 测试覆盖率目标

- 总体覆盖率: ≥ 80%
- 函数覆盖率: ≥ 85%
- 分支覆盖率: ≥ 75%
- 行覆盖率: ≥ 80%

## 编写测试

### 单元测试示例

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import MyComponent from '../MyComponent'

describe('MyComponent', () => {
  it('should render correctly', () => {
    render(<MyComponent />)
    expect(screen.getByText('Hello World')).toBeInTheDocument()
  })

  it('should handle user interaction', async () => {
    const user = userEvent.setup()
    const onClickMock = vi.fn()
    
    render(<MyComponent onClick={onClickMock} />)
    
    await user.click(screen.getByRole('button'))
    
    expect(onClickMock).toHaveBeenCalledTimes(1)
  })
})
```

### E2E测试示例

```typescript
import { test, expect } from '@playwright/test'

test('should complete user workflow', async ({ page }) => {
  await page.goto('/login')
  
  await page.getByRole('button', { name: /第三方登录/i }).click()
  await expect(page).toHaveURL('/')
  
  await page.getByRole('link', { name: /创建任务/i }).click()
  await page.setInputFiles('input[type="file"]', 'path/to/test-file.pdf')
  await page.getByRole('button', { name: /创建任务/i }).click()
  
  await expect(page.locator('text=任务创建成功')).toBeVisible()
})
```

## Mock数据

### API Mock

使用MSW来Mock API请求，配置在 `src/test/mocks/handlers.ts`:

```typescript
import { http, HttpResponse } from 'msw'

export const handlers = [
  http.get('/api/tasks', () => {
    return HttpResponse.json([
      { id: 1, title: '测试任务', status: 'completed' }
    ])
  }),
  
  http.post('/api/auth/login', () => {
    return HttpResponse.json({
      success: true,
      user: { id: 1, name: '测试用户' },
      token: 'mock-token'
    })
  })
]
```

### 测试数据工厂

使用工厂函数创建测试数据:

```typescript
import { userFactory, taskFactory } from '../test/factories'

// 创建不同类型的用户
const adminUser = userFactory.admin()
const regularUser = userFactory.regular()
const customUser = userFactory.custom({ name: '自定义用户' })

// 创建不同状态的任务
const pendingTask = taskFactory.pending()
const completedTask = taskFactory.completed()
```

## 调试测试

### 调试单元测试

1. 在测试代码中添加 `console.log` 或使用 `screen.debug()`
2. 运行特定测试: `npm test -- --grep "测试名称"`
3. 使用测试UI界面: `npm run test:ui`

### 调试E2E测试

1. 使用调试模式: `npm run test:e2e:debug`
2. 在浏览器中观察测试执行
3. 查看测试录制的视频和截图

## CI/CD集成

项目配置了GitHub Actions自动化流水线，包括：

- 单元测试和集成测试
- E2E测试
- 代码覆盖率检查
- 代码质量检查
- 安全扫描

## 最佳实践

### 测试命名

- 使用描述性的测试名称
- 遵循 "should do something when condition" 格式
- 使用中文描述业务场景

### 测试结构

- 使用 AAA 模式 (Arrange, Act, Assert)
- 每个测试只验证一个行为
- 保持测试简单和独立

### Mock策略

- 只Mock外部依赖
- 避免过度Mock
- 使用真实数据结构

### 异步测试

- 使用 `waitFor` 等待异步操作
- 避免使用固定的延时
- 正确处理Promise和async/await

## 故障排除

### 常见问题

1. **测试超时**: 增加timeout配置或优化异步操作
2. **Mock不生效**: 检查MSW服务器配置和handler
3. **DOM操作失败**: 确保元素已渲染并可见
4. **类型错误**: 更新TypeScript配置和类型定义

### 获取帮助

- 查看测试框架官方文档
- 检查测试输出和错误信息
- 使用调试工具定位问题
- 参考项目中的测试示例

## 更新测试

随着功能开发，请及时更新相关测试：

1. 新增功能时编写对应测试
2. 修改功能时更新现有测试
3. 重构代码时确保测试仍然有效
4. 定期审查和优化测试套件