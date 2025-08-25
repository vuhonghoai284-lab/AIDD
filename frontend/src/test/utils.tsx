import React from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '../components/ThemeProvider'

// 创建测试用的QueryClient
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

// 自定义渲染器，包含常用的Provider
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  initialEntries?: string[]
  user?: any
}

export const renderWithProviders = (
  ui: React.ReactElement,
  options: CustomRenderOptions = {}
) => {
  const { initialEntries = ['/'], user, ...renderOptions } = options
  
  const queryClient = createTestQueryClient()
  
  const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ThemeProvider>
          {children}
        </ThemeProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )

  // 如果提供了用户信息，设置localStorage
  if (user) {
    localStorage.setItem('user', JSON.stringify(user))
    localStorage.setItem('token', 'test-token')
  }

  return {
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
    queryClient,
  }
}

// 路由测试工具
export const renderWithRouter = (
  ui: React.ReactElement,
  { route = '/' } = {}
) => {
  window.history.pushState({}, 'Test page', route)
  
  return render(
    <BrowserRouter>
      <ThemeProvider>
        {ui}
      </ThemeProvider>
    </BrowserRouter>
  )
}

// 等待异步操作完成的工具函数
export const waitForLoadingToFinish = () =>
  new Promise(resolve => setTimeout(resolve, 0))

// 模拟用户登录状态
export const mockUserLogin = (user: any) => {
  localStorage.setItem('user', JSON.stringify(user))
  localStorage.setItem('token', 'mock-token')
}

// 清理用户登录状态
export const mockUserLogout = () => {
  localStorage.removeItem('user')
  localStorage.removeItem('token')
}

// 模拟文件拖拽事件
export const createDragEvent = (type: string, files: File[]) => {
  const event = new Event(type, { bubbles: true })
  Object.defineProperty(event, 'dataTransfer', {
    value: {
      files,
      types: ['Files'],
    },
  })
  return event
}

// 等待元素出现
export const waitForElement = async (selector: string, timeout = 5000) => {
  return new Promise((resolve, reject) => {
    const startTime = Date.now()
    
    const checkElement = () => {
      const element = document.querySelector(selector)
      if (element) {
        resolve(element)
      } else if (Date.now() - startTime > timeout) {
        reject(new Error(`Element ${selector} not found within ${timeout}ms`))
      } else {
        setTimeout(checkElement, 100)
      }
    }
    
    checkElement()
  })
}

// 测试环境检查
export const isTestEnvironment = () => process.env.NODE_ENV === 'test'

// 控制台静默工具
export const silenceConsole = () => {
  const originalConsole = { ...console }
  // 在测试环境中使用mock函数，否则使用空函数
  if (typeof vi !== 'undefined') {
    console.log = vi.fn()
    console.warn = vi.fn()
    console.error = vi.fn()
  } else {
    console.log = () => {}
    console.warn = () => {}
    console.error = () => {}
  }
  
  return () => {
    Object.assign(console, originalConsole)
  }
}