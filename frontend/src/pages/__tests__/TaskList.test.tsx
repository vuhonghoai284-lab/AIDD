import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import TaskList from '../TaskList'
import { renderWithProviders } from '../../test/utils'
import { taskFactory, userFactory } from '../../test/factories'

// Mock useNavigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

// Mock fetch
global.fetch = vi.fn()

describe('TaskList', () => {
  const mockTasks = [
    taskFactory.completed(),
    taskFactory.processing(),
    taskFactory.pending(),
    taskFactory.failed()
  ]

  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    mockNavigate.mockClear()
    
    // Set up authenticated user
    localStorage.setItem('token', 'test-token')
    localStorage.setItem('user', JSON.stringify(userFactory.regular()))
  })

  it('should render task list with data', async () => {
    ;(fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockTasks
    })

    renderWithProviders(<TaskList />)
    
    // 等待数据加载
    await waitFor(() => {
      expect(screen.getByText('已完成任务')).toBeInTheDocument()
      expect(screen.getByText('处理中任务')).toBeInTheDocument()
      expect(screen.getByText('待处理任务')).toBeInTheDocument()
      expect(screen.getByText('失败任务')).toBeInTheDocument()
    })
  })

  it('should render empty state when no tasks', async () => {
    ;(fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => []
    })

    renderWithProviders(<TaskList />)
    
    await waitFor(() => {
      expect(screen.getByText('暂无任务数据')).toBeInTheDocument()
    })
  })

  it('should handle API error', async () => {
    ;(fetch as any).mockRejectedValueOnce(new Error('API Error'))

    renderWithProviders(<TaskList />)
    
    await waitFor(() => {
      expect(screen.getByText('加载任务列表失败')).toBeInTheDocument()
    })
  })

  it('should filter tasks by status', async () => {
    ;(fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockTasks
    })

    const user = userEvent.setup()
    renderWithProviders(<TaskList />)
    
    // 等待任务列表加载
    await waitFor(() => {
      expect(screen.getByText('已完成任务')).toBeInTheDocument()
    })
    
    // 点击状态筛选 - 只显示已完成的任务
    const statusFilter = screen.getByText('全部')
    await user.click(statusFilter)
    await user.click(screen.getByText('已完成'))
    
    // 验证筛选结果
    await waitFor(() => {
      expect(screen.getByText('已完成任务')).toBeInTheDocument()
      expect(screen.queryByText('处理中任务')).not.toBeInTheDocument()
    })
  })

  it('should search tasks by title and filename', async () => {
    ;(fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockTasks
    })

    const user = userEvent.setup()
    renderWithProviders(<TaskList />)
    
    // 等待任务列表加载
    await waitFor(() => {
      expect(screen.getByText('已完成任务')).toBeInTheDocument()
    })
    
    // 搜索任务
    const searchInput = screen.getByPlaceholderText('搜索任务标题或文件名')
    await user.type(searchInput, '已完成')
    
    // 验证搜索结果
    await waitFor(() => {
      expect(screen.getByText('已完成任务')).toBeInTheDocument()
      expect(screen.queryByText('处理中任务')).not.toBeInTheDocument()
    })
  })

  it('should refresh task list', async () => {
    ;(fetch as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockTasks
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [...mockTasks, taskFactory.custom({ id: 5, title: '新任务' })]
      })

    const user = userEvent.setup()
    renderWithProviders(<TaskList />)
    
    // 等待初始数据加载
    await waitFor(() => {
      expect(screen.getByText('已完成任务')).toBeInTheDocument()
    })
    
    // 点击刷新按钮
    await user.click(screen.getByRole('button', { name: /刷新/i }))
    
    // 验证API调用
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it('should navigate to task detail when clicking task title', async () => {
    ;(fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockTasks
    })

    const user = userEvent.setup()
    renderWithProviders(<TaskList />)
    
    // 等待任务列表加载
    await waitFor(() => {
      expect(screen.getByText('已完成任务')).toBeInTheDocument()
    })
    
    // 点击任务标题
    await user.click(screen.getByText('已完成任务'))
    
    // 验证导航到详情页
    expect(mockNavigate).toHaveBeenCalledWith('/task/3')
  })

  it('should delete task', async () => {
    ;(fetch as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockTasks
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockTasks.filter(task => task.id !== 3)
      })

    const user = userEvent.setup()
    renderWithProviders(<TaskList />)
    
    // 等待任务列表加载
    await waitFor(() => {
      expect(screen.getByText('已完成任务')).toBeInTheDocument()
    })
    
    // 找到删除按钮并点击
    const deleteButtons = screen.getAllByRole('button', { name: /删除/i })
    await user.click(deleteButtons[0])
    
    // 确认删除
    const confirmButton = screen.getByText('确定')
    await user.click(confirmButton)
    
    // 验证删除API调用
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith('/api/tasks/3', {
        method: 'DELETE',
        headers: {
          'Authorization': 'Bearer test-token',
          'Content-Type': 'application/json'
        }
      })
    })
  })

  it('should handle delete task error', async () => {
    ;(fetch as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockTasks
      })
      .mockRejectedValueOnce(new Error('Delete failed'))

    const user = userEvent.setup()
    renderWithProviders(<TaskList />)
    
    // 等待任务列表加载
    await waitFor(() => {
      expect(screen.getByText('已完成任务')).toBeInTheDocument()
    })
    
    // 点击删除按钮
    const deleteButtons = screen.getAllByRole('button', { name: /删除/i })
    await user.click(deleteButtons[0])
    
    // 确认删除
    const confirmButton = screen.getByText('确定')
    await user.click(confirmButton)
    
    // 验证错误消息
    await waitFor(() => {
      expect(screen.getByText('删除任务失败')).toBeInTheDocument()
    })
  })

  it('should switch between table and card view modes', async () => {
    ;(fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockTasks
    })

    const user = userEvent.setup()
    renderWithProviders(<TaskList />)
    
    // 等待任务列表加载
    await waitFor(() => {
      expect(screen.getByText('已完成任务')).toBeInTheDocument()
    })
    
    // 切换到卡片视图
    await user.click(screen.getByText('卡片'))
    
    // 验证视图模式改变
    expect(screen.getByText('已完成任务')).toBeInTheDocument() // 任务仍然显示
    
    // 切换回表格视图
    await user.click(screen.getByText('表格'))
    
    // 验证表格视图
    expect(screen.getByText('已完成任务')).toBeInTheDocument()
  })

  it('should show task statistics', async () => {
    ;(fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockTasks
    })

    renderWithProviders(<TaskList />)
    
    // 等待任务列表加载
    await waitFor(() => {
      expect(screen.getByText('总任务数')).toBeInTheDocument()
      expect(screen.getByText('4')).toBeInTheDocument() // 4个任务
      expect(screen.getByText('已完成')).toBeInTheDocument()
      expect(screen.getByText('1')).toBeInTheDocument() // 1个已完成
      expect(screen.getByText('处理中')).toBeInTheDocument()
      expect(screen.getByText('1')).toBeInTheDocument() // 1个处理中
    })
  })

  it('should auto-refresh processing tasks', async () => {
    vi.useFakeTimers()

    ;(fetch as any)
      .mockResolvedValue({
        ok: true,
        json: async () => mockTasks
      })

    renderWithProviders(<TaskList />)
    
    // 等待初始数据加载
    await waitFor(() => {
      expect(screen.getByText('处理中任务')).toBeInTheDocument()
    })
    
    // 快进时间，触发自动刷新
    vi.advanceTimersByTime(5000)
    
    // 验证自动刷新调用
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledTimes(2) // 初始加载 + 自动刷新
    })

    vi.useRealTimers()
  })
})