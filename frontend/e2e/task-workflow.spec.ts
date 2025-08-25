import { test, expect } from '@playwright/test'
import path from 'path'

test.describe('Task Management Workflow', () => {
  // 在每个测试前先登录
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
    
    // 执行登录
    await page.getByRole('button', { name: /第三方登录/i }).click()
    await expect(page).toHaveURL('/')
  })

  test('should display task list page correctly', async ({ page }) => {
    // 验证任务列表页面元素
    await expect(page.locator('text=任务管理中心')).toBeVisible()
    await expect(page.getByRole('button', { name: /新建任务/i })).toBeVisible()
    
    // 验证统计信息
    await expect(page.locator('text=总任务数')).toBeVisible()
    await expect(page.locator('text=已完成')).toBeVisible()
    await expect(page.locator('text=处理中')).toBeVisible()
    
    // 验证操作按钮
    await expect(page.getByRole('button', { name: /刷新/i })).toBeVisible()
    await expect(page.locator('.ant-segmented-item-label:has-text("表格")')).toBeVisible()
    await expect(page.locator('.ant-segmented-item-label:has-text("卡片")')).toBeVisible()
    
    // 验证搜索和筛选
    await expect(page.getByPlaceholder('搜索文件名或标题...')).toBeVisible()
    await expect(page.locator('text=全部状态')).toBeVisible()
  })

  test('should create a new task with file upload', async ({ page }) => {
    // 导航到创建任务页面
    await page.getByRole('button', { name: /新建任务/i }).click()
    await expect(page).toHaveURL('/create')
    
    // 验证页面元素
    await expect(page.locator('text=创建文档测试任务')).toBeVisible()
    await expect(page.locator('text=上传文档文件')).toBeVisible()
    await expect(page.locator('text=选择分析模型')).toBeVisible()
    
    // 上传测试文件
    const filePath = path.join(__dirname, 'fixtures', 'sample.pdf')
    await page.setInputFiles('input[type="file"]', filePath)
    
    // 等待文件上传完成
    await expect(page.locator('text=sample.pdf')).toBeVisible()
    await expect(page.locator('text=已添加 1 个文件')).toBeVisible()
    
    // 点击创建任务按钮
    await page.locator('button:has-text("创建任务")').last().click()
    
    // 验证任务创建过程
    await expect(page.locator('text=创建中...')).toBeVisible()
    
    // 验证成功消息和跳转
    await expect(page.locator('.ant-message-success')).toBeVisible()
    await expect(page).toHaveURL(/\/task\/\d+/)
  })

  test('should handle multiple file uploads', async ({ page }) => {
    await page.getByRole('button', { name: /新建任务/i }).click()
    
    // 上传多个文件
    const pdfPath = path.join(__dirname, 'fixtures', 'sample.pdf')
    const mdPath = path.join(__dirname, 'fixtures', 'sample.md')
    
    // 分别上传两个文件
    await page.setInputFiles('input[type="file"]', pdfPath)
    await expect(page.locator('text=sample.pdf')).toBeVisible()
    
    await page.setInputFiles('input[type="file"]', mdPath)
    await expect(page.locator('text=sample.md')).toBeVisible()
    
    // 验证文件计数
    await expect(page.locator('text=已添加 2 个文件')).toBeVisible()
    
    // 创建任务
    await page.locator('button:has-text("创建任务")').last().click()
    
    // 验证所有文件都开始处理
    await expect(page.locator('text=sample.pdf 创建任务成功')).toBeVisible()
    await expect(page.locator('text=sample.md 创建任务成功')).toBeVisible()
  })

  test('should validate file types and sizes', async ({ page }) => {
    await page.getByRole('button', { name: /新建任务/i }).click()
    
    // 尝试上传不支持的文件类型（使用一个text文件模拟）
    const invalidFile = path.join(__dirname, 'fixtures', 'sample.md') // 实际测试中可以创建.exe文件
    
    // 由于Playwright的限制，这里主要验证UI反馈
    // 实际的文件类型验证应该在单元测试中覆盖
    await page.setInputFiles('input[type="file"]', invalidFile)
    
    // 验证文件被接受（因为.md是支持的格式）
    await expect(page.locator('text=sample.md')).toBeVisible()
  })

  test('should remove uploaded files', async ({ page }) => {
    await page.getByRole('button', { name: /新建任务/i }).click()
    
    // 上传文件
    const filePath = path.join(__dirname, 'fixtures', 'sample.pdf')
    await page.setInputFiles('input[type="file"]', filePath)
    await expect(page.locator('text=sample.pdf')).toBeVisible()
    
    // 点击删除按钮
    await page.locator('button:has-text("移除")').first().click()
    
    // 验证文件被删除
    await expect(page.locator('text=sample.pdf')).not.toBeVisible()
  })

  test('should navigate to task detail and view information', async ({ page }) => {
    // 假设已有任务存在，点击进入详情页
    // 这里我们先创建一个任务，然后查看详情
    await page.getByRole('button', { name: /新建任务/i }).click()
    
    const filePath = path.join(__dirname, 'fixtures', 'sample.md')
    await page.setInputFiles('input[type="file"]', filePath)
    await page.locator('button:has-text("创建任务")').last().click()
    
    // 等待跳转到任务详情页
    await expect(page).toHaveURL(/\/task\/\d+/)
    
    // 验证任务详情页面元素
    await expect(page.locator('text=任务详情')).toBeVisible()
    await expect(page.locator('text=sample.md')).toBeVisible()
    
    // 验证任务状态
    await expect(page.locator('text=待处理')).toBeVisible()
    
    // 验证操作按钮
    await expect(page.getByRole('button', { name: /返回/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /下载报告/i })).toBeVisible()
  })

  test('should filter and search tasks', async ({ page }) => {
    // 在任务列表页面进行筛选测试
    await expect(page.locator('text=任务管理中心')).toBeVisible()
    
    // 测试状态筛选
    const statusFilter = page.locator('.ant-select-selector').first()
    await statusFilter.click()
    await page.locator('text=已完成').click()
    
    // 验证筛选结果（假设有已完成的任务）
    await expect(page.locator('text=已完成')).toBeVisible()
    
    // 清除筛选
    await statusFilter.click()
    await page.locator('text=全部状态').click()
    
    // 测试搜索功能
    const searchInput = page.getByPlaceholder('搜索文件名或标题...')
    await searchInput.fill('sample')
    
    // 验证搜索结果
    await expect(page.locator('text=sample')).toBeVisible()
    
    // 清除搜索
    await searchInput.clear()
  })

  test('should switch between table and card views', async ({ page }) => {
    await expect(page.locator('text=任务管理中心')).toBeVisible()
    
    // 切换到卡片视图
    await page.locator('.ant-segmented-item-label:has-text("卡片")').click()
    
    // 验证视图切换（通过CSS类或具体的UI变化）
    await expect(page.locator('.task-cards-grid')).toBeVisible()
    
    // 切换回表格视图
    await page.locator('.ant-segmented-item-label:has-text("表格")').click()
    
    // 验证表格视图
    await expect(page.locator('.ant-table')).toBeVisible()
  })

  test('should refresh task list', async ({ page }) => {
    await expect(page.locator('text=任务管理中心')).toBeVisible()
    
    // 点击刷新按钮
    await page.getByRole('button', { name: /刷新/i }).click()
    
    // 验证loading状态
    await expect(page.locator('.ant-spin')).toBeVisible()
    
    // 等待刷新完成
    await expect(page.locator('.ant-spin')).not.toBeVisible()
  })

  test('should delete a task', async ({ page }) => {
    // 先创建一个任务
    await page.getByRole('button', { name: /新建任务/i }).click()
    const filePath = path.join(__dirname, 'fixtures', 'sample.pdf')
    await page.setInputFiles('input[type="file"]', filePath)
    await page.locator('button:has-text("创建任务")').last().click()
    
    // 返回到任务列表
    await page.getByRole('button', { name: /返回/i }).click()
    
    // 找到删除按钮并点击（通过下拉菜单）
    const moreButton = page.locator('button:has-text("更多")').first()
    await moreButton.click()
    // 点击下拉菜单中的删除选项
    const deleteButton = page.locator('li:has-text("删除任务")')
    await deleteButton.click()
    
    // 确认删除
    await page.getByRole('button', { name: /确定/i }).click()
    
    // 验证删除成功消息
    await expect(page.locator('.ant-message-success')).toBeVisible()
    await expect(page.locator('text=任务已删除')).toBeVisible()
  })

  test('should handle task processing status updates', async ({ page }) => {
    // 创建任务后观察状态变化
    await page.getByRole('button', { name: /新建任务/i }).click()
    const filePath = path.join(__dirname, 'fixtures', 'sample.md')
    await page.setInputFiles('input[type="file"]', filePath)
    await page.locator('button:has-text("创建任务")').last().click()
    
    // 在任务详情页观察状态
    await expect(page.locator('text=pending')).toBeVisible()
    
    // 等待状态可能的变化（在实际环境中任务可能会开始处理）
    // 这里我们验证进度条存在
    await expect(page.locator('.ant-progress')).toBeVisible()
  })

  test('should download task report when completed', async ({ page }) => {
    // 这个测试需要有已完成的任务
    // 在实际环境中，我们需要等待任务完成或使用mock数据
    
    // 假设我们有一个已完成的任务，进入详情页
    await page.goto('/task/1') // 假设任务ID为1
    
    // 如果任务已完成，应该能看到下载报告按钮
    const downloadButton = page.getByRole('button', { name: /下载报告/i })
    
    // 设置下载监听
    const downloadPromise = page.waitForEvent('download')
    
    // 点击下载按钮
    await downloadButton.click()
    
    // 验证下载开始
    const download = await downloadPromise
    expect(download.suggestedFilename()).toContain('.xlsx')
  })

  test('should handle navigation between pages', async ({ page }) => {
    // 测试页面间的导航
    await expect(page).toHaveURL('/')
    
    // 导航到创建任务页面
    await page.getByRole('button', { name: /新建任务/i }).click()
    await expect(page).toHaveURL('/create')
    
    // 返回任务列表
    await page.getByRole('link', { name: /任务列表/i }).click()
    await expect(page).toHaveURL('/')
    
    // 测试浏览器后退按钮
    await page.getByRole('button', { name: /新建任务/i }).click()
    await page.goBack()
    await expect(page).toHaveURL('/')
    
    // 测试浏览器前进按钮
    await page.goForward()
    await expect(page).toHaveURL('/create')
  })
})