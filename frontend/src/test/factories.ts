import { User, Task } from '../types'

// 用户工厂函数
export const userFactory = {
  admin: (): User => ({
    id: 1,
    uid: 'admin',
    display_name: '管理员',
    is_admin: true,
    is_system_admin: true,
    avatar_url: undefined,
    created_at: '2024-01-01T00:00:00Z'
  }),
  
  regular: (): User => ({
    id: 2,
    uid: 'user001',
    display_name: '普通用户',
    is_admin: false,
    is_system_admin: false,
    avatar_url: undefined,
    created_at: '2024-01-01T00:00:00Z'
  }),
  
  custom: (overrides: Partial<User> = {}): User => ({
    id: 99,
    uid: 'testuser',
    display_name: '测试用户',
    is_admin: false,
    is_system_admin: false,
    avatar_url: undefined,
    created_at: '2024-01-01T00:00:00Z',
    ...overrides
  })
}

// 任务工厂函数
export const taskFactory = {
  pending: (): Task => ({
    id: 1,
    title: '待处理任务',
    file_name: 'pending.md',
    status: 'pending',
    progress: 0,
    created_at: '2024-01-01T00:00:00Z',
  }),
  
  processing: (): Task => ({
    id: 2,
    title: '处理中任务',
    file_name: 'processing.pdf',
    status: 'processing',
    progress: 50,
    created_at: '2024-01-01T00:00:00Z',
  }),
  
  completed: (): Task => ({
    id: 3,
    title: '已完成任务',
    file_name: 'completed.docx',
    status: 'completed',
    progress: 100,
    created_at: '2024-01-01T00:00:00Z',
  }),
  
  failed: (): Task => ({
    id: 4,
    title: '失败任务',
    file_name: 'failed.md',
    status: 'failed',
    progress: 0,
    created_at: '2024-01-01T00:00:00Z',
  }),
  
  custom: (overrides: Partial<Task> = {}): Task => ({
    id: 99,
    title: '自定义测试任务',
    file_name: 'custom.md',
    status: 'pending',
    progress: 0,
    created_at: '2024-01-01T00:00:00Z',
    ...overrides
  })
}

// 文件对象工厂函数
export const fileFactory = {
  pdf: (name = 'test.pdf'): File => 
    new File(['test pdf content'], name, { type: 'application/pdf' }),
    
  docx: (name = 'test.docx'): File =>
    new File(['test docx content'], name, { 
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' 
    }),
    
  markdown: (name = 'test.md'): File =>
    new File(['# Test Markdown'], name, { type: 'text/markdown' }),
    
  txt: (name = 'test.txt'): File =>
    new File(['test text content'], name, { type: 'text/plain' }),
    
  invalid: (name = 'test.exe'): File =>
    new File(['invalid content'], name, { type: 'application/exe' }),
    
  large: (name = 'large.pdf'): File => {
    const largeContent = 'x'.repeat(11 * 1024 * 1024) // 11MB
    return new File([largeContent], name, { type: 'application/pdf' })
  }
}