// API服务封装
import axios from 'axios';
import { Task, TaskDetail, AIOutput, AnalyticsData, UserStats, TaskStats, SystemStats, IssueStats, ErrorStats } from './types';
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

  // 获取任务列表
  getTasks: async () => {
    const response = await api.get<Task[]>('/tasks/');
    return response.data;
  },

  // 获取任务详情
  getTaskDetail: async (taskId: number) => {
    const response = await api.get<TaskDetail>(`/tasks/${taskId}`);
    return response.data;
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

  // 获取任务的AI输出记录
  getTaskAIOutputs: async (taskId: number, operationType?: string) => {
    const params = operationType ? { operation_type: operationType } : {};
    const response = await api.get<AIOutput[]>(`/tasks/${taskId}/ai-outputs`, { params });
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

  // 下载任务原文件
  downloadTaskFile: async (taskId: number) => {
    try {
      console.log('🚀 开始下载任务文件:', taskId);
      
      const response = await api.get(`/tasks/${taskId}/file`, {
        responseType: 'blob',
        headers: {
          'Accept': 'application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/markdown,application/octet-stream,*/*'
        }
      });
      
      console.log('📡 响应接收完成:', {
        status: response.status,
        statusText: response.statusText,
        headers: response.headers,
        dataType: typeof response.data,
        isBlob: response.data instanceof Blob,
        size: response.data.size
      });
      
      // 验证响应数据是Blob
      if (!(response.data instanceof Blob)) {
        console.error('❌ 响应数据不是Blob类型:', typeof response.data);
        throw new Error('服务器返回了非二进制数据');
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
          filename = decodeURIComponent(utf8FilenameMatch[1]);
          console.log('✅ UTF-8文件名解析成功:', filename);
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
      
      // 获取响应的MIME类型
      let contentType = response.headers['content-type'] || 'application/octet-stream';
      
      // 根据文件扩展名纠正MIME类型（防止服务器MIME类型不准确）
      const fileExtension = filename.toLowerCase().split('.').pop();
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
      
      console.log('📄 文件信息:', { filename, contentType, size: response.data.size });
      
      // 验证PDF文件内容（如果是PDF）
      if (contentType === 'application/pdf') {
        try {
          const slice = response.data.slice(0, 10);
          const arrayBuffer = await slice.arrayBuffer();
          const header = new Uint8Array(arrayBuffer);
          const headerStr = String.fromCharCode(...header);
          const isPdfValid = headerStr.startsWith('%PDF');
          console.log('🔍 PDF文件头验证:', isPdfValid ? '✅ 正确' : '❌ 错误', '内容:', headerStr);
          
          if (!isPdfValid) {
            console.warn('⚠️ PDF文件头验证失败，可能不是有效的PDF文件');
          }
        } catch (e) {
          console.warn('⚠️ PDF文件头验证失败:', e);
        }
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