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

  // 下载任务原文件
  downloadTaskFile: async (taskId: number) => {
    try {
      const response = await api.get(`/tasks/${taskId}/file`, {
        responseType: 'blob',
      });
      
      // 从响应头获取文件名，支持UTF-8编码的文件名
      const contentDisposition = response.headers['content-disposition'];
      let filename = `task_${taskId}_file`;
      if (contentDisposition) {
        // 优先尝试解析 filename*=UTF-8''encoded_name 格式（RFC 5987）
        const utf8FilenameMatch = contentDisposition.match(/filename\*=UTF-8''([^;,\n]*)/);
        if (utf8FilenameMatch) {
          filename = decodeURIComponent(utf8FilenameMatch[1]);
        } else {
          // 降级处理普通的 filename="name" 格式
          const filenameMatch = contentDisposition.match(/filename="([^"]+)"/);
          if (filenameMatch) {
            filename = filenameMatch[1];
          }
        }
      }
      
      // 获取响应的MIME类型
      const contentType = response.headers['content-type'] || 'application/octet-stream';
      
      // 创建下载链接，保持原始MIME类型
      const url = window.URL.createObjectURL(new Blob([response.data], { type: contentType }));
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