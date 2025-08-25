import { http, HttpResponse } from 'msw'
import { User, Task } from '../../types'

// 模拟用户数据
const mockUsers: User[] = [
  {
    id: 1,
    uid: 'admin',
    display_name: '管理员',
    is_admin: true,
    is_system_admin: true,
    avatar_url: undefined,
    created_at: '2024-01-01T00:00:00Z'
  },
  {
    id: 2,
    uid: 'user001',
    display_name: '普通用户',
    is_admin: false,
    is_system_admin: false,
    avatar_url: undefined,
    created_at: '2024-01-01T00:00:00Z'
  }
]

// 模拟任务数据
const mockTasks: Task[] = [
  {
    id: 1,
    title: '测试任务1',
    file_name: 'test1.md',
    status: 'completed',
    progress: 100,
    created_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 2,
    title: '测试任务2',
    file_name: 'test2.pdf',
    status: 'processing',
    progress: 50,
    created_at: '2024-01-02T00:00:00Z',
  }
]

export const handlers = [
  // 登录接口
  http.post('/api/auth/thirdparty/login', () => {
    return HttpResponse.json({
      success: true,
      user: mockUsers[1],
      access_token: 'mock-token-12345'
    })
  }),

  http.post('/api/auth/system/login', () => {
    return HttpResponse.json({
      success: true,
      user: mockUsers[0],
      access_token: 'mock-admin-token-67890'
    })
  }),

  // 获取当前用户
  http.get('/api/auth/user', () => {
    return HttpResponse.json(mockUsers[1])
  }),

  // 退出登录
  http.post('/api/auth/logout', () => {
    return HttpResponse.json({ success: true })
  }),

  // 获取任务列表
  http.get('/api/tasks', () => {
    return HttpResponse.json(mockTasks)
  }),

  // 获取任务详情
  http.get('/api/tasks/:id', ({ params }) => {
    const taskId = parseInt(params.id as string)
    const task = mockTasks.find(t => t.id === taskId)
    if (task) {
      return HttpResponse.json(task)
    }
    return new HttpResponse(null, { status: 404 })
  }),

  // 创建任务
  http.post('/api/tasks', () => {
    const newTask: Task = {
      id: 3,
      title: '新创建的任务',
      file_name: 'new_task.md',
      status: 'pending',
      progress: 0,
      created_at: new Date().toISOString(),
    }
    return HttpResponse.json(newTask)
  }),

  // 删除任务
  http.delete('/api/tasks/:id', ({ params }) => {
    return HttpResponse.json({ success: true })
  }),

  // 获取模型列表
  http.get('/api/models', () => {
    return HttpResponse.json({
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
]