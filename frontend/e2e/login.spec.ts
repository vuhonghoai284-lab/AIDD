import { test, expect } from '@playwright/test'

test.describe('User Login', () => {
  test.beforeEach(async ({ page }) => {
    // 清除存储 - 使用更安全的方式
    await page.context().clearCookies()
    
    // 先导航到页面，再清除存储
    await page.goto('/login')
    
    try {
      await page.evaluate(() => {
        if (typeof Storage !== 'undefined') {
          localStorage.clear()
          sessionStorage.clear()
        }
      })
    } catch (error) {
      // 如果localStorage不可用，忽略错误
      console.warn('Could not clear localStorage:', error)
    }
  })

  test('should display login page correctly', async ({ page }) => {
    // 页面已在beforeEach中导航，这里不需要重复
    
    // 验证页面基本元素
    await expect(page.locator('.login-container')).toBeVisible()
    
    // 验证品牌标识 - 使用实际的页面结构
    await expect(page.locator('.brand-container')).toBeVisible()
    await expect(page.locator('text=AIDocsPro')).toBeVisible()
    await expect(page.locator('text=智能文档质量评估专家')).toBeVisible()
    
    // 验证登录选项
    await expect(page.getByRole('button', { name: /第三方登录/i })).toBeVisible()
    await expect(page.locator('[role="tab"]:has-text("系统登录")')).toBeVisible()
    
    // 验证功能亮点
    await expect(page.locator('text=AI深度分析')).toBeVisible()
    await expect(page.locator('text=全格式兼容')).toBeVisible()
    await expect(page.locator('text=专业报告')).toBeVisible()
    
    // 验证主题切换器
    await expect(page.locator('text=选择主题')).toBeVisible()
  })

  test('should handle third party login in development mode', async ({ page }) => {
    // 页面已在beforeEach中导航
    
    // 验证开发模式提示
    await expect(page.locator('text=💡 开发模式：将模拟第三方登录流程')).toBeVisible()
    
    // 点击第三方登录按钮
    await page.getByRole('button', { name: /第三方登录/i }).click()
    
    // 等待登录处理
    await expect(page.locator('text=处理中...')).toBeVisible()
    
    // 验证登录成功并跳转到主页
    await expect(page).toHaveURL('/')
    await expect(page.locator('text=任务列表')).toBeVisible()
    
    // 验证用户信息显示
    await expect(page.locator('.ant-avatar')).toBeVisible()
  })

  test('should handle system login successfully', async ({ page }) => {
    // 页面已在beforeEach中导航
    
    // 切换到系统登录标签
    await page.locator('div[role="tab"]:has-text("系统登录")').click()
    
    // 填写登录表单
    await page.getByPlaceholder('请输入用户名').fill('admin')
    await page.getByPlaceholder('请输入密码').fill('admin123')
    
    // 提交表单
    await page.getByRole('button', { name: /立即登录/i }).click()
    
    // 验证登录成功
    await expect(page.locator('.ant-message-success')).toBeVisible()
    await expect(page).toHaveURL('/')
    await expect(page.locator('text=任务列表')).toBeVisible()
    
    // 验证管理员权限
    await expect(page.locator('text=运营统计')).toBeVisible()
    await expect(page.locator('text=(管理员)')).toBeVisible()
  })

  test('should handle system login validation', async ({ page }) => {
    // 页面已在beforeEach中导航
    
    // 切换到系统登录标签
    await page.locator('div[role="tab"]:has-text("系统登录")').click()
    
    // 直接点击登录按钮，不填写表单
    await page.getByRole('button', { name: /立即登录/i }).click()
    
    // 验证表单验证错误
    await expect(page.locator('text=请输入用户名!')).toBeVisible()
    await expect(page.locator('text=请输入密码!')).toBeVisible()
  })

  test('should handle invalid login credentials', async ({ page }) => {
    // 页面已在beforeEach中导航
    
    // 切换到系统登录
    await page.locator('div[role="tab"]:has-text("系统登录")').click()
    
    // 输入错误凭据
    await page.getByPlaceholder('请输入用户名').fill('wronguser')
    await page.getByPlaceholder('请输入密码').fill('wrongpass')
    
    await page.getByRole('button', { name: /立即登录/i }).click()
    
    // 验证错误提示
    await expect(page.locator('.ant-message-error')).toBeVisible()
  })

  test('should switch themes correctly', async ({ page }) => {
    // 页面已在beforeEach中导航
    
    // 测试主题切换
    await page.locator('.theme-option:has-text("商务黑")').click()
    
    // 验证主题变化（通过背景色验证）
    const loginContainer = page.locator('.login-container')
    await expect(loginContainer).toHaveCSS('background', /linear-gradient/)
    
    // 切换回科技蓝主题
    await page.locator('.theme-option:has-text("科技蓝")').click()
    
    // 验证主题恢复
    await expect(loginContainer).toHaveCSS('background', /linear-gradient/)
  })

  test('should handle auth code from URL parameters', async ({ page }) => {
    // 直接访问带有auth code的URL
    await page.goto('/login?code=test-auth-code-123')
    
    // 验证自动处理auth code
    await expect(page.locator('text=正在兑换第三方令牌...')).toBeVisible()
    
    // 等待处理完成并跳转
    await expect(page).toHaveURL('/')
    await expect(page.locator('text=任务列表')).toBeVisible()
  })

  test('should show loading state during authentication', async ({ page }) => {
    // 页面已在beforeEach中导航
    
    // 点击第三方登录
    await page.getByRole('button', { name: /第三方登录/i }).click()
    
    // 验证loading状态
    await expect(page.getByRole('button', { name: /处理中/i })).toBeVisible()
    
    // 验证进度显示
    await expect(page.locator('.ant-progress')).toBeVisible()
  })

  test('should persist login state across page refresh', async ({ page }) => {
    // 页面已在beforeEach中导航
    
    // 执行登录
    await page.getByRole('button', { name: /第三方登录/i }).click()
    await expect(page).toHaveURL('/')
    
    // 刷新页面
    await page.reload()
    
    // 验证仍然保持登录状态
    await expect(page).toHaveURL('/')
    await expect(page.locator('.ant-avatar')).toBeVisible()
  })

  test('should logout successfully', async ({ page }) => {
    // 先登录（页面已在beforeEach中导航）
    await page.getByRole('button', { name: /第三方登录/i }).click()
    await expect(page).toHaveURL('/')
    
    // 点击用户头像打开下拉菜单
    await page.locator('.ant-avatar').click()
    
    // 点击退出登录
    await page.locator('text=退出登录').click()
    
    // 验证跳转回登录页
    await expect(page).toHaveURL('/login')
    await expect(page.locator('text=AI文档测试系统')).toBeVisible()
  })

  test('should prevent access to protected routes when not logged in', async ({ page }) => {
    // 尝试直接访问受保护的路由
    await page.goto('/')
    
    // 应该被重定向到登录页
    await expect(page).toHaveURL('/login')
    await expect(page.locator('text=AI文档测试系统')).toBeVisible()
    
    // 尝试访问任务创建页
    await page.goto('/create')
    await expect(page).toHaveURL('/login')
    
    // 尝试访问任务详情页
    await page.goto('/task/1')
    await expect(page).toHaveURL('/login')
  })

  test('should handle network error during login', async ({ page }) => {
    // 由于开发模式会跳过真实API调用，我们需要拦截实际被调用的登录端点
    // 根据LoginPage.tsx，在开发模式下会调用 loginWithThirdParty(mockCode)
    await page.route('**/api/auth/thirdparty/login', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Network connection failed' })
      })
    })
    
    // 页面已在beforeEach中导航
    await page.getByRole('button', { name: /第三方登录/i }).click()
    
    // 等待错误处理
    await page.waitForTimeout(2000)
    
    // 检查是否有错误消息显示
    // 由于登录失败，应该看到错误消息而不是成功跳转
    await expect(page).toHaveURL('/login')  // 应该还在登录页面
    
    // 检查是否有错误相关的UI反馈
    const hasErrorFeedback = await page.locator('.ant-message-error').count() > 0 ||
                            await page.locator('.ant-message:has-text("登录失败")').count() > 0 ||
                            await page.locator('.ant-message:has-text("登录过程中发生错误")').count() > 0 ||
                            await page.locator('.ant-alert-error').count() > 0
    
    expect(hasErrorFeedback).toBeTruthy()
  })
})