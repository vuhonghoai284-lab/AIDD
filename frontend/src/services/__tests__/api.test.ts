import { describe, it, expect, vi, beforeEach } from 'vitest'
import { taskAPI } from '../../api'

// Mock fetch
global.fetch = vi.fn()

describe('taskAPI', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    localStorage.setItem('token', 'test-token')
  })

  describe('getTasks', () => {
    it('should fetch tasks successfully', async () => {
      const mockTasks = [
        {
          id: 1,
          title: '测试任务',
          status: 'completed',
          progress: 100
        }
      ]

      ;(fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockTasks
      })

      const tasks = await taskAPI.getTasks()

      expect(tasks).toEqual(mockTasks)
      expect(fetch).toHaveBeenCalledWith('/api/tasks', {
        method: 'GET',
        headers: {
          'Authorization': 'Bearer test-token',
          'Content-Type': 'application/json'
        }
      })
    })

    it('should handle fetch error', async () => {
      ;(fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 500
      })

      await expect(taskAPI.getTasks()).rejects.toThrow('Failed to fetch')
    })

    it('should handle network error', async () => {
      ;(fetch as any).mockRejectedValueOnce(new Error('Network error'))

      await expect(taskAPI.getTasks()).rejects.toThrow('Network error')
    })
  })

  describe('getTaskDetail', () => {
    it('should fetch task detail successfully', async () => {
      const mockTask = {
        id: 1,
        title: '测试任务',
        status: 'completed',
        issues: []
      }

      ;(fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockTask
      })

      const task = await taskAPI.getTaskDetail(1)

      expect(task).toEqual(mockTask)
      expect(fetch).toHaveBeenCalledWith('/api/tasks/1', {
        method: 'GET',
        headers: {
          'Authorization': 'Bearer test-token',
          'Content-Type': 'application/json'
        }
      })
    })

    it('should handle 404 error', async () => {
      ;(fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 404
      })

      await expect(taskAPI.getTaskDetail(999)).rejects.toThrow('Failed to fetch')
    })
  })

  describe('createTask', () => {
    it('should create task successfully', async () => {
      const mockFile = new File(['test'], 'test.pdf', { type: 'application/pdf' })
      const mockResponse = {
        id: 1,
        title: '新任务',
        status: 'pending'
      }

      ;(fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })

      const task = await taskAPI.createTask(mockFile, '测试任务', 0)

      expect(task).toEqual(mockResponse)
      expect(fetch).toHaveBeenCalledWith('/api/tasks', {
        method: 'POST',
        headers: {
          'Authorization': 'Bearer test-token'
        },
        body: expect.any(FormData)
      })
    })

    it('should handle file upload error', async () => {
      const mockFile = new File(['test'], 'test.pdf', { type: 'application/pdf' })
      
      ;(fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: '文件格式不支持' })
      })

      await expect(taskAPI.createTask(mockFile, '测试任务', 0))
        .rejects.toThrow('文件格式不支持')
    })

    it('should handle large file upload', async () => {
      const largeContent = 'x'.repeat(11 * 1024 * 1024) // 11MB
      const mockFile = new File([largeContent], 'large.pdf', { type: 'application/pdf' })
      
      ;(fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 413,
        json: async () => ({ detail: '文件过大' })
      })

      await expect(taskAPI.createTask(mockFile, '大文件测试', 0))
        .rejects.toThrow('文件过大')
    })
  })

  describe('deleteTask', () => {
    it('should delete task successfully', async () => {
      ;(fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true })
      })

      await taskAPI.deleteTask(1)

      expect(fetch).toHaveBeenCalledWith('/api/tasks/1', {
        method: 'DELETE',
        headers: {
          'Authorization': 'Bearer test-token',
          'Content-Type': 'application/json'
        }
      })
    })

    it('should handle delete error', async () => {
      ;(fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 403
      })

      await expect(taskAPI.deleteTask(1)).rejects.toThrow('Failed to fetch')
    })
  })

  describe('downloadReport', () => {
    it('should download report successfully', async () => {
      const mockBlob = new Blob(['report content'], { type: 'application/xlsx' })
      
      ;(fetch as any).mockResolvedValueOnce({
        ok: true,
        blob: async () => mockBlob
      })

      // Mock URL.createObjectURL
      const mockUrl = 'blob:http://localhost/test'
      global.URL.createObjectURL = vi.fn().mockReturnValue(mockUrl)
      
      // Mock createElement and click
      const mockLink = {
        href: '',
        download: '',
        click: vi.fn()
      }
      document.createElement = vi.fn().mockReturnValue(mockLink)
      document.body.appendChild = vi.fn()
      document.body.removeChild = vi.fn()

      await taskAPI.downloadReport(1)

      expect(fetch).toHaveBeenCalledWith('/api/tasks/1/report', {
        method: 'GET',
        headers: {
          'Authorization': 'Bearer test-token'
        }
      })
      
      expect(mockLink.click).toHaveBeenCalled()
      expect(global.URL.createObjectURL).toHaveBeenCalledWith(mockBlob)
    })
  })
})