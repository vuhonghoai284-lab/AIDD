import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TaskCreate from '../TaskCreate'
import { renderWithProviders } from '../../test/utils'
import { fileFactory, userFactory } from '../../test/factories'

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

describe('TaskCreate', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    mockNavigate.mockClear()
    
    // Set up authenticated user
    localStorage.setItem('token', 'test-token')
    localStorage.setItem('user', JSON.stringify(userFactory.regular()))

    // Mock models API
    ;(fetch as any).mockResolvedValue({
      ok: true,
      json: async () => ({
        models: [
          {
            index: 0,
            label: 'GPT-4o Mini (快速)',
            description: '适用于快速处理的模型',
            provider: 'openai',
            is_default: true
          }
        ],
        default_index: 0
      })
    })
  })

  it('should render task creation form', async () => {
    renderWithProviders(<TaskCreate />)
    
    await waitFor(() => {
      expect(screen.getByText('创建新任务')).toBeInTheDocument()
      expect(screen.getByPlaceholderText('请输入任务标题')).toBeInTheDocument()
      expect(screen.getByText('上传文档')).toBeInTheDocument()
      expect(screen.getByText('AI模型选择')).toBeInTheDocument()
    })
  })

  it('should load and display available models', async () => {
    renderWithProviders(<TaskCreate />)
    
    await waitFor(() => {
      expect(screen.getByText('GPT-4o Mini (快速)')).toBeInTheDocument()
    })
    
    expect(fetch).toHaveBeenCalledWith('/api/models')
  })

  it('should handle file upload', async () => {
    const user = userEvent.setup()
    renderWithProviders(<TaskCreate />)
    
    await waitFor(() => {
      expect(screen.getByText('上传文档')).toBeInTheDocument()
    })
    
    const file = fileFactory.pdf('test.pdf')
    const fileInput = screen.getByLabelText('上传文档')
    
    await user.upload(fileInput, file)
    
    await waitFor(() => {
      expect(screen.getByText('test.pdf')).toBeInTheDocument()
      expect(screen.getByText('已添加 1 个文件')).toBeInTheDocument()
    })
  })

  it('should handle multiple file upload', async () => {
    const user = userEvent.setup()
    renderWithProviders(<TaskCreate />)
    
    await waitFor(() => {
      expect(screen.getByText('上传文档')).toBeInTheDocument()
    })
    
    const files = [
      fileFactory.pdf('test1.pdf'),
      fileFactory.docx('test2.docx'),
      fileFactory.markdown('test3.md')
    ]
    
    const fileInput = screen.getByLabelText('上传文档')
    
    await user.upload(fileInput, files)
    
    await waitFor(() => {
      expect(screen.getByText('test1.pdf')).toBeInTheDocument()
      expect(screen.getByText('test2.docx')).toBeInTheDocument()
      expect(screen.getByText('test3.md')).toBeInTheDocument()
      expect(screen.getByText('已添加 3 个文件')).toBeInTheDocument()
    })
  })

  it('should prevent duplicate file upload', async () => {
    const user = userEvent.setup()
    renderWithProviders(<TaskCreate />)
    
    await waitFor(() => {
      expect(screen.getByText('上传文档')).toBeInTheDocument()
    })
    
    const file = fileFactory.pdf('test.pdf')
    const fileInput = screen.getByLabelText('上传文档')
    
    // 上传第一次
    await user.upload(fileInput, file)
    await waitFor(() => {
      expect(screen.getByText('test.pdf')).toBeInTheDocument()
    })
    
    // 尝试上传相同文件
    await user.upload(fileInput, file)
    
    await waitFor(() => {
      expect(screen.getByText('文件 test.pdf 已经添加')).toBeInTheDocument()
    })
  })

  it('should remove uploaded file', async () => {
    const user = userEvent.setup()
    renderWithProviders(<TaskCreate />)
    
    await waitFor(() => {
      expect(screen.getByText('上传文档')).toBeInTheDocument()
    })
    
    const file = fileFactory.pdf('test.pdf')
    const fileInput = screen.getByLabelText('上传文档')
    
    await user.upload(fileInput, file)
    await waitFor(() => {
      expect(screen.getByText('test.pdf')).toBeInTheDocument()
    })
    
    // 点击删除按钮
    const removeButton = screen.getByRole('button', { name: /删除/i })
    await user.click(removeButton)
    
    await waitFor(() => {
      expect(screen.queryByText('test.pdf')).not.toBeInTheDocument()
    })
  })

  it('should validate file types', async () => {
    const user = userEvent.setup()
    renderWithProviders(<TaskCreate />)
    
    await waitFor(() => {
      expect(screen.getByText('上传文档')).toBeInTheDocument()
    })
    
    const invalidFile = fileFactory.invalid('test.exe')
    const fileInput = screen.getByLabelText('上传文档')
    
    // 模拟文件类型验证失败
    Object.defineProperty(invalidFile, 'type', {
      value: 'application/exe',
      writable: false
    })
    
    await user.upload(fileInput, invalidFile)
    
    // 在真实的组件中，应该显示文件类型错误
    // 这里我们验证文件没有被添加到列表中
    expect(screen.queryByText('test.exe')).not.toBeInTheDocument()
  })

  it('should create task successfully', async () => {
    const user = userEvent.setup()
    
    // Mock task creation API
    ;(fetch as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          models: [
            {
              index: 0,
              label: 'GPT-4o Mini',
              provider: 'openai',
              is_default: true
            }
          ],
          default_index: 0
        })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          id: 1,
          title: '测试任务',
          status: 'pending'
        })
      })

    renderWithProviders(<TaskCreate />)
    
    await waitFor(() => {
      expect(screen.getByText('上传文档')).toBeInTheDocument()
    })
    
    // 上传文件
    const file = fileFactory.pdf('test.pdf')
    const fileInput = screen.getByLabelText('上传文档')
    await user.upload(fileInput, file)
    
    await waitFor(() => {
      expect(screen.getByText('test.pdf')).toBeInTheDocument()
    })
    
    // 点击创建任务按钮
    const createButton = screen.getByRole('button', { name: /创建任务/i })
    await user.click(createButton)
    
    // 验证API调用
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith('/api/tasks', expect.objectContaining({
        method: 'POST',
        headers: {
          'Authorization': 'Bearer test-token'
        },
        body: expect.any(FormData)
      }))
    })
    
    // 验证成功消息
    await waitFor(() => {
      expect(screen.getByText('test.pdf 创建任务成功')).toBeInTheDocument()
    })
  })

  it('should handle task creation failure', async () => {
    const user = userEvent.setup()
    
    // Mock models API
    ;(fetch as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          models: [{ index: 0, label: 'Test Model', is_default: true }],
          default_index: 0
        })
      })
      .mockRejectedValueOnce(new Error('Creation failed'))

    renderWithProviders(<TaskCreate />)
    
    await waitFor(() => {
      expect(screen.getByText('上传文档')).toBeInTheDocument()
    })
    
    // 上传文件
    const file = fileFactory.pdf('test.pdf')
    const fileInput = screen.getByLabelText('上传文档')
    await user.upload(fileInput, file)
    
    await waitFor(() => {
      expect(screen.getByText('test.pdf')).toBeInTheDocument()
    })
    
    // 点击创建任务按钮
    const createButton = screen.getByRole('button', { name: /创建任务/i })
    await user.click(createButton)
    
    // 验证错误处理
    await waitFor(() => {
      expect(screen.getByText('创建任务失败')).toBeInTheDocument()
    })
  })

  it('should show loading state during task creation', async () => {
    const user = userEvent.setup()
    
    // Mock delayed response
    ;(fetch as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          models: [{ index: 0, label: 'Test Model', is_default: true }],
          default_index: 0
        })
      })
      .mockImplementation(() =>
        new Promise(resolve => {
          setTimeout(() => {
            resolve({
              ok: true,
              json: async () => ({ id: 1, title: 'Test', status: 'pending' })
            })
          }, 100)
        })
      )

    renderWithProviders(<TaskCreate />)
    
    await waitFor(() => {
      expect(screen.getByText('上传文档')).toBeInTheDocument()
    })
    
    const file = fileFactory.pdf('test.pdf')
    const fileInput = screen.getByLabelText('上传文档')
    await user.upload(fileInput, file)
    
    const createButton = screen.getByRole('button', { name: /创建任务/i })
    await user.click(createButton)
    
    // 验证loading状态
    expect(screen.getByText('创建中...')).toBeInTheDocument()
  })

  it('should handle no files selected', async () => {
    const user = userEvent.setup()
    
    renderWithProviders(<TaskCreate />)
    
    await waitFor(() => {
      expect(screen.getByText('上传文档')).toBeInTheDocument()
    })
    
    // 直接点击创建任务按钮，没有上传文件
    const createButton = screen.getByRole('button', { name: /创建任务/i })
    await user.click(createButton)
    
    // 验证警告消息
    await waitFor(() => {
      expect(screen.getByText('没有需要处理的文件')).toBeInTheDocument()
    })
  })

  it('should change AI model selection', async () => {
    const user = userEvent.setup()
    
    // Mock multiple models
    ;(fetch as any).mockResolvedValue({
      ok: true,
      json: async () => ({
        models: [
          {
            index: 0,
            label: 'GPT-4o Mini',
            provider: 'openai',
            is_default: true
          },
          {
            index: 1,
            label: 'GPT-4o',
            provider: 'openai',
            is_default: false
          }
        ],
        default_index: 0
      })
    })

    renderWithProviders(<TaskCreate />)
    
    await waitFor(() => {
      expect(screen.getByText('GPT-4o Mini')).toBeInTheDocument()
      expect(screen.getByText('GPT-4o')).toBeInTheDocument()
    })
    
    // 选择不同的模型
    const modelSelect = screen.getByRole('combobox')
    await user.click(modelSelect)
    await user.click(screen.getByText('GPT-4o'))
    
    // 验证模型选择变化
    expect(screen.getByDisplayValue('GPT-4o')).toBeInTheDocument()
  })
})