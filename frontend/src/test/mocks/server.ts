import { setupServer } from 'msw/node'
import { handlers } from './handlers'

// 创建mock服务器
export const server = setupServer(...handlers)