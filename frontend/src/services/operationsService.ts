import axios from 'axios';
import config from '../config/index';

// 创建专用的API客户端
const apiClient = axios.create({
  baseURL: config.apiBaseUrl,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 添加请求拦截器，自动添加认证头
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 添加响应拦截器，处理认证错误
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('user');
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
import type { OperationsOverview, OperationsRequest } from '../types/operations';

export const operationsService = {
  /**
   * 获取运营总览数据 (GET方式)
   */
  async getOperationsOverview(params: {
    time_range_type?: string;
    start_date?: string;
    end_date?: string;
    include_trends?: boolean;
    include_critical_issues?: boolean;
    max_critical_issues?: number;
  }): Promise<OperationsOverview> {
    const response = await apiClient.get('/operations/overview', {
      params: {
        time_range_type: params.time_range_type || '30days',
        start_date: params.start_date,
        end_date: params.end_date,
        include_trends: params.include_trends !== false,
        include_critical_issues: params.include_critical_issues !== false,
        max_critical_issues: params.max_critical_issues || 20,
      },
    });
    return response.data;
  },

  /**
   * 获取运营总览数据 (POST方式)
   */
  async getOperationsOverviewByRequest(request: OperationsRequest): Promise<OperationsOverview> {
    const response = await apiClient.post('/operations/overview', request);
    return response.data;
  },

  /**
   * 获取运营总览数据 - 缓存版本
   */
  async getOperationsOverviewCached(params: {
    time_range_type?: string;
    start_date?: string;
    end_date?: string;
    include_trends?: boolean;
    include_critical_issues?: boolean;
    max_critical_issues?: number;
  }): Promise<OperationsOverview> {
    const cacheKey = `operations_overview_${JSON.stringify(params)}`;
    const cached = sessionStorage.getItem(cacheKey);
    
    // 检查缓存 (5分钟有效期)
    if (cached) {
      const { data, timestamp } = JSON.parse(cached);
      const now = Date.now();
      if (now - timestamp < 5 * 60 * 1000) { // 5分钟缓存
        return data;
      }
    }

    // 获取新数据并缓存
    const data = await this.getOperationsOverview(params);
    sessionStorage.setItem(cacheKey, JSON.stringify({
      data,
      timestamp: Date.now(),
    }));
    
    return data;
  },

  /**
   * 清除运营数据缓存
   */
  clearCache(): void {
    // 清除所有运营数据相关的缓存
    for (let i = 0; i < sessionStorage.length; i++) {
      const key = sessionStorage.key(i);
      if (key?.startsWith('operations_overview_')) {
        sessionStorage.removeItem(key);
      }
    }
  },
};