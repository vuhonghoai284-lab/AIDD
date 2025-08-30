// API服务封装
import axios from 'axios';
import { Task, TaskDetail, AIOutput, AnalyticsData, UserStats, TaskStats, SystemStats, IssueStats, ErrorStats, Issue, PaginationParams, PaginatedResponse } from './types';
import config from './config/index';

const API_BASE = config.apiBaseUrl;

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 添加请求拦截器，自动添加认证头
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 添加响应拦截器，处理认证错误
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // 认证失败，清除本地存储并跳转到登录页
      localStorage.removeItem('user');
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const taskAPI = {
  // 创建任务
  createTask: async (file: File, title?: string, modelIndex?: number) => {
    const formData = new FormData();
    formData.append('file', file);
    if (title) {
      formData.append('title', title);
    }
    if (modelIndex !== undefined) {
      formData.append('model_index', modelIndex.toString());
    }
    
    const response = await api.post<Task>('/tasks/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // 批量创建任务
  batchCreateTasks: async (files: File[], modelIndex?: number) => {
    const formData = new FormData();
    
    // 添加所有文件
    files.forEach(file => {
      formData.append('files', file);
    });
    
    // 添加模型索引
    if (modelIndex !== undefined) {
      formData.append('model_index', modelIndex.toString());
    }
    
    const response = await api.post<Task[]>('/tasks/batch', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // 获取任务列表（兼容性接口）
  getTasks: async () => {
    const response = await api.get<Task[]>('/tasks/');
    return response.data;
  },
  
  // 分页获取任务列表
  getTasksPaginated: async (params: PaginationParams) => {
    const queryParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        queryParams.append(key, value.toString());
      }
    });
    
    const response = await api.get<PaginatedResponse<Task>>(`/tasks/paginated?${queryParams.toString()}`);
    return response.data;
  },

  // 获取任务统计数据
  getTaskStatistics: async () => {
    const response = await api.get<{
      total: number;
      pending: number;
      processing: number;
      completed: number;
      failed: number;
    }>('/tasks/statistics');
    return response.data;
  },

  // 获取任务详情
  getTaskDetail: async (taskId: number) => {
    const response = await api.get<TaskDetail>(`/tasks/${taskId}`);
    return response.data;
  },

  // 分页获取任务问题列表
  getTaskIssues: async (taskId: number, params: PaginationParams) => {
    const queryParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        queryParams.append(key, value.toString());
      }
    });
    
    const response = await api.get<PaginatedResponse<Issue>>(`/tasks/${taskId}/issues?${queryParams.toString()}`);
    return response.data;
  },

  // 获取任务AI输出列表
  getTaskAIOutputs: async (taskId: number, params?: PaginationParams) => {
    if (params) {
      const queryParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          queryParams.append(key, value.toString());
        }
      });
      
      const response = await api.get<PaginatedResponse<AIOutput>>(`/tasks/${taskId}/ai-outputs?${queryParams.toString()}`);
      return response.data;
    } else {
      // 兼容性接口，返回所有数据
      const response = await api.get<AIOutput[]>(`/tasks/${taskId}/ai-outputs`);
      return response.data;
    }
  },

  // 删除任务
  deleteTask: async (taskId: number) => {
    const response = await api.delete(`/tasks/${taskId}`);
    return response.data;
  },

  // 提交问题反馈
  submitFeedback: async (issueId: number, feedbackType: string, comment?: string) => {
    const response = await api.put(`/issues/${issueId}/feedback`, {
      feedback_type: feedbackType,
      comment,
    });
    return response.data;
  },

  // 提交满意度评分
  submitSatisfactionRating: async (issueId: number, rating: number) => {
    const response = await api.put(`/issues/${issueId}/satisfaction`, {
      satisfaction_rating: rating,
    });
    return response.data;
  },

  // 只更新评论，不改变反馈状态
  updateCommentOnly: async (issueId: number, comment?: string) => {
    const response = await api.put(`/issues/${issueId}/comment`, {
      comment,
    });
    return response.data;
  },

  // 检查报告下载权限
  checkReportPermission: async (taskId: number) => {
    const response = await api.get(`/tasks/${taskId}/report/check`);
    return response.data;
  },

  // 下载报告
  downloadReport: async (taskId: number) => {
    try {
      const response = await api.get(`/tasks/${taskId}/report`, {
        responseType: 'blob',
      });
      
      // 从响应头获取文件名
      const contentDisposition = response.headers['content-disposition'];
      let filename = `report_${taskId}.xlsx`;
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="(.+)"/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }
      
      // 创建下载链接
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      return { success: true, filename };
    } catch (error) {
      // 抛出错误让调用方处理
      throw error;
    }
  },

  // 分页获取任务的AI输出记录（新方法名避免冲突）
  getTaskAIOutputsPaginated: async (taskId: number, params: PaginationParams) => {
    const queryParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        queryParams.append(key, value.toString());
      }
    });
    
    const response = await api.get<PaginatedResponse<AIOutput>>(`/tasks/${taskId}/ai-outputs/paginated?${queryParams.toString()}`);
    return response.data;
  },

  // 获取单个AI输出详情
  getAIOutputDetail: async (outputId: number) => {
    const response = await api.get<AIOutput>(`/ai-outputs/${outputId}`);
    return response.data;
  },

  // 重试任务
  retryTask: async (taskId: number) => {
    const response = await api.post(`/tasks/${taskId}/retry`);
    return response.data;
  },

  // 下载任务原文件 - 增强安全版本
  downloadTaskFile: async (taskId: number) => {
    try {
      console.log('🚀 开始下载任务文件:', taskId);
      
      // 输入验证
      if (!taskId || taskId <= 0) {
        throw new Error('无效的任务ID');
      }

      const response = await api.get(`/tasks/${taskId}/file`, {
        responseType: 'blob',
        timeout: 30000, // 30秒超时
        headers: {
          'Accept': 'application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/markdown,text/plain,application/octet-stream'
        }
      });
      
      console.log('📡 响应接收完成:', {
        status: response.status,
        statusText: response.statusText,
        headers: response.headers,
        dataType: typeof response.data,
        isBlob: response.data instanceof Blob,
        size: response.data?.size
      });
      
      // 增强的响应验证
      if (!response.data) {
        throw new Error('服务器返回了空响应');
      }
      
      if (!(response.data instanceof Blob)) {
        console.error('❌ 响应数据不是Blob类型:', typeof response.data);
        throw new Error('服务器返回了非二进制数据');
      }
      
      // 文件大小安全检查（限制100MB）
      const maxFileSize = 100 * 1024 * 1024; // 100MB
      if (response.data.size > maxFileSize) {
        throw new Error(`文件过大 (${Math.round(response.data.size / 1024 / 1024)}MB)，超出100MB限制`);
      }
      
      if (response.data.size === 0) {
        throw new Error('文件为空，无法下载');
      }
      
      // 从响应头获取文件名，支持UTF-8编码的文件名
      // Axios会将所有响应头转换为小写，所以我们统一使用小写
      const contentDisposition = response.headers['content-disposition'];
      let filename = `task_${taskId}_file`;
      
      console.log('🔍 所有响应头:', response.headers);
      console.log('📋 Content-Disposition:', contentDisposition);
      
      if (contentDisposition) {
        // 优先尝试解析 filename*=UTF-8''encoded_name 格式（RFC 5987）
        const utf8FilenameMatch = contentDisposition.match(/filename\*=UTF-8''([^;,\n]*)/);
        if (utf8FilenameMatch) {
          try {
            filename = decodeURIComponent(utf8FilenameMatch[1]);
            console.log('✅ UTF-8文件名解析成功:', filename);
          } catch (decodeError) {
            console.warn('UTF-8文件名解码失败:', decodeError);
            filename = `task_${taskId}_file`; // 使用安全的默认名称
          }
        } else {
          // 降级处理普通的 filename="name" 格式
          const filenameMatch = contentDisposition.match(/filename="([^"]+)"/);
          if (filenameMatch) {
            filename = filenameMatch[1];
            console.log('✅ 标准文件名解析成功:', filename);
          } else {
            // 最后尝试没有引号的filename格式
            const simpleMatch = contentDisposition.match(/filename=([^;,\n]*)/);
            if (simpleMatch) {
              filename = simpleMatch[1].trim();
              console.log('✅ 简单文件名解析成功:', filename);
            } else {
              console.warn('❌ 无法解析文件名，使用默认名称');
            }
          }
        }
      } else {
        console.warn('❌ 响应中没有Content-Disposition头');
      }
      
      // 文件名安全检查和清理
      filename = filename.replace(/[<>:"/\\|?*]/g, '_'); // 替换危险字符
      filename = filename.substring(0, 255); // 限制文件名长度
      
      if (!filename.trim()) {
        filename = `task_${taskId}_file`; // 确保有有效的文件名
      }
      
      // 获取响应的MIME类型并进行安全检查
      let contentType = response.headers['content-type'] || 'application/octet-stream';
      
      // 定义安全的文件类型白名单
      const allowedMimeTypes = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword',
        'text/plain',
        'text/markdown',
        'application/octet-stream'
      ];
      
      // 根据文件扩展名验证和纠正MIME类型
      const fileExtension = filename.toLowerCase().split('.').pop() || '';
      const allowedExtensions = ['pdf', 'docx', 'doc', 'txt', 'md', 'markdown'];
      
      // 扩展名安全检查
      if (!allowedExtensions.includes(fileExtension)) {
        throw new Error(`不支持的文件类型: .${fileExtension}。仅支持: ${allowedExtensions.join(', ')}`);
      }
      
      const mimeTypeMap: { [key: string]: string } = {
        'pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'doc': 'application/msword',
        'txt': 'text/plain',
        'md': 'text/markdown',
        'markdown': 'text/markdown'
      };
      
      if (fileExtension && mimeTypeMap[fileExtension]) {
        const expectedMimeType = mimeTypeMap[fileExtension];
        if (contentType !== expectedMimeType) {
          console.log(`🔧 MIME类型纠正: ${contentType} -> ${expectedMimeType}`);
          contentType = expectedMimeType;
        }
      }
      
      // MIME类型安全检查
      if (!allowedMimeTypes.includes(contentType)) {
        throw new Error(`不安全的文件类型: ${contentType}`);
      }
      
      console.log('📄 文件信息:', { filename, contentType, size: response.data.size });
      
      // 增强的文件内容验证
      try {
        const fileHeader = response.data.slice(0, 16); // 读取前16字节
        const arrayBuffer = await fileHeader.arrayBuffer();
        const header = new Uint8Array(arrayBuffer);
        
        // 根据文件类型进行魔数验证
        switch (fileExtension) {
          case 'pdf':
            const pdfHeader = String.fromCharCode(...header.slice(0, 4));
            if (!pdfHeader.startsWith('%PDF')) {
              throw new Error('PDF文件头验证失败，文件可能已损坏或不是有效的PDF文件');
            }
            console.log('✅ PDF文件头验证通过');
            break;
            
          case 'docx':
            // DOCX文件是ZIP格式，检查ZIP头
            if (header[0] !== 0x50 || header[1] !== 0x4B) {
              throw new Error('DOCX文件头验证失败，文件可能已损坏');
            }
            console.log('✅ DOCX文件头验证通过');
            break;
            
          case 'doc':
            // DOC文件头检查（简化版）
            if (header.length >= 8) {
              const signature = header.slice(0, 8);
              // DOC文件有特定的OLE复合文档签名
              console.log('✅ DOC文件基本检查通过');
            }
            break;
            
          default:
            console.log('ℹ️ 文本文件，跳过二进制头验证');
        }
      } catch (validationError) {
        console.error('文件内容验证失败:', validationError);
        throw new Error(`文件验证失败: ${validationError.message}`);
      }
      
      // 创建下载链接，强制使用正确的MIME类型
      const blob = new Blob([response.data], { type: contentType });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      
      // 为不同文件类型设置特定属性
      if (contentType === 'application/pdf') {
        link.type = 'application/pdf';
      }
      
      console.log('🔗 下载链接创建:', {
        href: link.href,
        download: link.download,
        type: link.type,
        blob_type: blob.type,
        blob_size: blob.size,
        final_mime_type: contentType
      });
      
      // 执行下载 - 使用更可靠的方法
      document.body.appendChild(link);
      
      // 触发点击事件
      const clickEvent = new MouseEvent('click', {
        view: window,
        bubbles: true,
        cancelable: false
      });
      link.dispatchEvent(clickEvent);
      
      // 清理DOM
      setTimeout(() => {
        document.body.removeChild(link);
      }, 100);
      
      // 延迟释放URL，确保下载完成
      setTimeout(() => {
        window.URL.revokeObjectURL(url);
        console.log('🗑️ URL资源已释放');
      }, 2000);
      
      return { success: true, filename, contentType };
    } catch (error) {
      console.error('❌ 文件下载失败:', error);
      throw error;
    }
  },
};

// 运营数据统计API
export const analyticsAPI = {
  // 获取综合运营数据概览
  getOverview: async (days: number = 30): Promise<AnalyticsData> => {
    const response = await api.get<AnalyticsData>(`/analytics/overview?days=${days}`);
    return response.data;
  },

  // 获取用户统计数据
  getUserStats: async (days: number = 30): Promise<UserStats> => {
    const response = await api.get<UserStats>(`/analytics/users?days=${days}`);
    return response.data;
  },

  // 获取任务统计数据
  getTaskStats: async (days: number = 30): Promise<TaskStats> => {
    const response = await api.get<TaskStats>(`/analytics/tasks?days=${days}`);
    return response.data;
  },

  // 获取系统资源统计数据
  getSystemStats: async (days: number = 30): Promise<SystemStats> => {
    const response = await api.get<SystemStats>(`/analytics/system?days=${days}`);
    return response.data;
  },

  // 获取问题统计数据
  getIssueStats: async (days: number = 30): Promise<IssueStats> => {
    const response = await api.get<IssueStats>(`/analytics/issues?days=${days}`);
    return response.data;
  },

  // 获取错误统计数据
  getErrorStats: async (days: number = 30): Promise<ErrorStats> => {
    const response = await api.get<ErrorStats>(`/analytics/errors?days=${days}`);
    return response.data;
  },
};

// 任务分享API
export const taskShareAPI = {
  // 分享任务给其他用户
  shareTask: async (taskId: number, shareData: {
    shared_user_ids: number[];
    permission_level: string;
    share_comment?: string;
  }) => {
    const response = await api.post(`/task-share/${taskId}/share`, shareData);
    return response.data;
  },

  // 获取任务的分享列表
  getTaskShares: async (taskId: number, includeInactive: boolean = false) => {
    const response = await api.get(`/task-share/${taskId}/shares?include_inactive=${includeInactive}`);
    return response.data;
  },

  // 更新分享权限
  updateSharePermission: async (shareId: number, updateData: {
    permission_level: string;
    share_comment?: string;
  }) => {
    const response = await api.put(`/task-share/shares/${shareId}`, updateData);
    return response.data;
  },

  // 撤销任务分享
  revokeTaskShare: async (shareId: number, permanently: boolean = false) => {
    const response = await api.delete(`/task-share/shares/${shareId}?permanently=${permanently}`);
    return response.data;
  },

  // 获取分享给我的任务列表
  getSharedTasks: async (includeInactive: boolean = false) => {
    const response = await api.get(`/task-share/shared-with-me?include_inactive=${includeInactive}`);
    return response.data;
  },

  // 搜索用户
  searchUsers: async (query: string, limit: number = 20) => {
    const response = await api.get(`/task-share/users/search?q=${encodeURIComponent(query)}&limit=${limit}`);
    return response.data;
  },

  // 获取分享统计信息
  getShareStats: async () => {
    const response = await api.get('/task-share/stats');
    return response.data;
  },
};