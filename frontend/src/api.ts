// API服务封装
import axios from 'axios';
import { Task, TaskDetail, AIOutput, AnalyticsData, UserStats, TaskStats, SystemStats, IssueStats, ErrorStats } from './types';
import config from './config';

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

  // 下载报告
  downloadReport: async (taskId: number) => {
    const response = await api.get(`/tasks/${taskId}/report`, {
      responseType: 'blob',
    });
    
    // 创建下载链接
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `report_${taskId}.xlsx`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
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