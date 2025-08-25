import { describe, it, expect, vi, beforeEach } from 'vitest'
import { loginWithThirdParty, loginWithSystem, getCurrentUser, logout } from '../authService'

// Mock fetch
global.fetch = vi.fn()

describe('AuthService', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    vi.clearAllMocks()
  })

  describe('loginWithThirdParty', () => {
    it('should handle successful third party login', async () => {
      const mockResponse = {
        success: true,
        user: {
          id: 1,
          uid: 'testuser',
          display_name: '测试用户',
          is_admin: false
        },
        access_token: 'token123'
      }

      ;(fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })

      const result = await loginWithThirdParty('auth-code')

      expect(result.success).toBe(true)
      expect(result.user?.uid).toBe('testuser')
      expect(result.access_token).toBe('token123')
      expect(fetch).toHaveBeenCalledWith('/api/auth/thirdparty/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code: 'auth-code' })
      })
    })

    it('should handle login failure', async () => {
      const mockResponse = {
        success: false,
        message: '认证失败'
      }

      ;(fetch as any).mockResolvedValueOnce({
        ok: false,
        json: async () => mockResponse
      })

      const result = await loginWithThirdParty('invalid-code')

      expect(result.success).toBe(false)
      expect(result.message).toBe('认证失败')
    })

    it('should handle network errors', async () => {
      ;(fetch as any).mockRejectedValueOnce(new Error('Network error'))

      const result = await loginWithThirdParty('auth-code')

      expect(result.success).toBe(false)
      expect(result.message).toContain('请求失败')
    })
  })

  describe('loginWithSystem', () => {
    it('should handle successful system login', async () => {
      const mockResponse = {
        success: true,
        user: {
          id: 1,
          uid: 'admin',
          display_name: '管理员',
          is_admin: true
        },
        access_token: 'admin-token'
      }

      ;(fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })

      const result = await loginWithSystem('admin', 'admin123')

      expect(result.success).toBe(true)
      expect(result.user?.uid).toBe('admin')
      expect(result.user?.is_admin).toBe(true)
      expect(fetch).toHaveBeenCalledWith('/api/auth/system/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: 'admin',
          password: 'admin123'
        })
      })
    })

    it('should handle invalid credentials', async () => {
      ;(fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ message: '用户名或密码错误' })
      })

      const result = await loginWithSystem('wrong', 'wrong')

      expect(result.success).toBe(false)
      expect(result.message).toBe('用户名或密码错误')
    })
  })

  describe('getCurrentUser', () => {
    it('should get current user with valid token', async () => {
      const mockUser = {
        id: 1,
        uid: 'testuser',
        display_name: '测试用户',
        is_admin: false
      }

      localStorage.setItem('token', 'valid-token')
      ;(fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockUser
      })

      const user = await getCurrentUser()

      expect(user).toEqual(mockUser)
      expect(fetch).toHaveBeenCalledWith('/api/auth/user', {
        method: 'GET',
        headers: {
          'Authorization': 'Bearer valid-token',
        }
      })
    })

    it('should throw error when no token', async () => {
      localStorage.removeItem('token')

      await expect(getCurrentUser()).rejects.toThrow('No token found')
    })

    it('should throw error when token is invalid', async () => {
      localStorage.setItem('token', 'invalid-token')
      ;(fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 401
      })

      await expect(getCurrentUser()).rejects.toThrow()
    })
  })

  describe('logout', () => {
    it('should clear local storage on logout', () => {
      localStorage.setItem('token', 'test-token')
      localStorage.setItem('user', '{"id":1}')

      logout()

      expect(localStorage.getItem('token')).toBeNull()
      expect(localStorage.getItem('user')).toBeNull()
    })

    it('should clear session storage on logout', () => {
      sessionStorage.setItem('processed_auth_code', 'test-code')

      logout()

      expect(sessionStorage.getItem('processed_auth_code')).toBeNull()
    })
  })
})