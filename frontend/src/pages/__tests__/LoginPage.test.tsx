import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import LoginPage from '../LoginPage'
import { renderWithProviders } from '../../test/utils'

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

describe('LoginPage', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    vi.clearAllMocks()
    mockNavigate.mockClear()
  })

  it('should render login page with all elements', () => {
    renderWithProviders(<LoginPage />)
    
    expect(screen.getByText('AI文档测试系统')).toBeInTheDocument()
    expect(screen.getByText('智能文档质量评估专家')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /第三方登录/i })).toBeInTheDocument()
    expect(screen.getByText('系统登录')).toBeInTheDocument()
  })

  it('should render theme switcher', () => {
    renderWithProviders(<LoginPage />)
    
    expect(screen.getByText('选择主题')).toBeInTheDocument()
    expect(screen.getByText('科技蓝')).toBeInTheDocument()
    expect(screen.getByText('商务黑')).toBeInTheDocument()
  })

  it('should handle third party login in development mode', async () => {
    const user = userEvent.setup()
    
    // Mock development environment
    Object.defineProperty(window, 'location', {
      value: { hostname: 'localhost' },
      writable: true
    })

    ;(fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        user: { id: 1, uid: 'testuser', display_name: '测试用户' },
        access_token: 'test-token'
      })
    })

    renderWithProviders(<LoginPage />)
    
    await user.click(screen.getByRole('button', { name: /第三方登录/i }))
    
    await waitFor(() => {
      expect(localStorage.setItem).toHaveBeenCalledWith('user', expect.any(String))
      expect(localStorage.setItem).toHaveBeenCalledWith('token', 'test-token')
      expect(mockNavigate).toHaveBeenCalledWith('/')
    })
  })

  it('should handle system login form submission', async () => {
    const user = userEvent.setup()
    
    ;(fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        user: { id: 1, uid: 'admin', display_name: '管理员', is_admin: true },
        access_token: 'admin-token'
      })
    })

    renderWithProviders(<LoginPage />)
    
    // 切换到系统登录标签
    await user.click(screen.getByText('系统登录'))
    
    // 填写表单
    await user.type(screen.getByPlaceholderText('请输入用户名'), 'admin')
    await user.type(screen.getByPlaceholderText('请输入密码'), 'admin123')
    
    // 提交表单
    await user.click(screen.getByRole('button', { name: /立即登录/i }))
    
    await waitFor(() => {
      expect(localStorage.setItem).toHaveBeenCalledWith('user', expect.any(String))
      expect(localStorage.setItem).toHaveBeenCalledWith('token', 'admin-token')
    })
  })

  it('should show form validation errors', async () => {
    const user = userEvent.setup()
    
    renderWithProviders(<LoginPage />)
    
    // 切换到系统登录标签
    await user.click(screen.getByText('系统登录'))
    
    // 直接点击登录按钮，不填写表单
    await user.click(screen.getByRole('button', { name: /立即登录/i }))
    
    await waitFor(() => {
      expect(screen.getByText('请输入用户名!')).toBeInTheDocument()
      expect(screen.getByText('请输入密码!')).toBeInTheDocument()
    })
  })

  it('should handle login failure', async () => {
    const user = userEvent.setup()
    
    ;(fetch as any).mockResolvedValueOnce({
      ok: false,
      json: async () => ({
        success: false,
        message: '用户名或密码错误'
      })
    })

    renderWithProviders(<LoginPage />)
    
    await user.click(screen.getByText('系统登录'))
    await user.type(screen.getByPlaceholderText('请输入用户名'), 'wronguser')
    await user.type(screen.getByPlaceholderText('请输入密码'), 'wrongpass')
    await user.click(screen.getByRole('button', { name: /立即登录/i }))
    
    await waitFor(() => {
      expect(screen.getByText('用户名或密码错误')).toBeInTheDocument()
    })
  })

  it('should show loading state during login', async () => {
    const user = userEvent.setup()
    
    // Mock a delayed response
    ;(fetch as any).mockImplementation(() =>
      new Promise(resolve => {
        setTimeout(() => {
          resolve({
            ok: true,
            json: async () => ({
              success: true,
              user: { id: 1 },
              access_token: 'token'
            })
          })
        }, 100)
      })
    )

    renderWithProviders(<LoginPage />)
    
    await user.click(screen.getByRole('button', { name: /第三方登录/i }))
    
    expect(screen.getByRole('button', { name: /处理中/i })).toBeInTheDocument()
  })

  it('should process auth code from URL parameters', async () => {
    // Mock URL with auth code
    delete (window as any).location
    ;(window as any).location = {
      ...window.location,
      search: '?code=auth-code-123'
    }

    ;(fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        user: { id: 1, uid: 'testuser' },
        access_token: 'token'
      })
    })

    renderWithProviders(<LoginPage />)
    
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith('/api/auth/thirdparty/login', expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ code: 'auth-code-123' })
      }))
    })
  })

  it('should handle auth code processing error', async () => {
    // Mock URL with auth code
    delete (window as any).location
    ;(window as any).location = {
      ...window.location,
      search: '?code=invalid-code'
    }

    ;(fetch as any).mockResolvedValueOnce({
      ok: false,
      json: async () => ({
        success: false,
        message: '授权码无效'
      })
    })

    renderWithProviders(<LoginPage />)
    
    await waitFor(() => {
      expect(screen.getByText('授权码无效')).toBeInTheDocument()
    })
  })

  it('should show development mode tips', () => {
    // Mock development environment
    Object.defineProperty(window, 'location', {
      value: { hostname: 'localhost' },
      writable: true
    })

    renderWithProviders(<LoginPage />)
    
    expect(screen.getByText('💡 开发模式：将模拟第三方登录流程')).toBeInTheDocument()
  })

  it('should display admin credentials hint', () => {
    renderWithProviders(<LoginPage />)
    
    expect(screen.getByText('🔑 系统管理员账号: admin / admin123')).toBeInTheDocument()
  })
})