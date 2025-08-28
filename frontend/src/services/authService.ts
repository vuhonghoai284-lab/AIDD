// 认证服务
import axios from 'axios';
import { User } from '../types';
import config from '../config/index';

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

export interface LoginResult {
  success: boolean;
  user?: User;
  access_token?: string;
  message?: string;
}

// 第三方登录相关接口
export interface ThirdPartyTokenResponse {
  access_token: string;
  refresh_token?: string;
  scope: string;
  expires_in: number;
}

export const exchangeThirdPartyToken = async (code: string): Promise<{ success: boolean; token?: ThirdPartyTokenResponse; message?: string }> => {
  try {
    const response = await api.post('/auth/thirdparty/exchange-token', { code });
    return {
      success: true,
      token: response.data
    };
  } catch (error: any) {
    return {
      success: false,
      message: error.response?.data?.detail || 'Token兑换失败'
    };
  }
};

export const loginWithThirdPartyToken = async (accessToken: string): Promise<LoginResult> => {
  try {
    const response = await api.post('/auth/thirdparty/login', { access_token: accessToken });
    return {
      success: true,
      user: response.data.user,
      access_token: response.data.access_token
    };
  } catch (error: any) {
    return {
      success: false,
      message: error.response?.data?.detail || '用户登录失败'
    };
  }
};

export const loginWithThirdParty = async (code: string): Promise<LoginResult> => {
  try {
    // 第一步：使用授权码兑换Access Token
    // console.log('🔄 步骤1: 兑换第三方Access Token');
    const tokenResult = await exchangeThirdPartyToken(code);
    
    if (!tokenResult.success || !tokenResult.token) {
      return {
        success: false,
        message: tokenResult.message || 'Token兑换失败'
      };
    }
    
    // console.log('✅ Token兑换成功，开始用户登录');
    
    // 第二步：使用Access Token进行用户登录
    // console.log('🔄 步骤2: 使用Token进行用户登录');
    const loginResult = await loginWithThirdPartyToken(tokenResult.token.access_token);
    
    if (loginResult.success) {
      // console.log('✅ 第三方登录完成');
    }
    
    return loginResult;
  } catch (error: any) {
    console.error('❌ 第三方登录过程异常:', error);
    return {
      success: false,
      message: '登录过程中发生异常，请重试'
    };
  }
};

// 兼容旧版本的登录方法（使用legacy接口）
export const loginWithThirdPartyLegacy = async (code: string): Promise<LoginResult> => {
  try {
    // console.log('🔄 使用Legacy接口登录（兼容模式）');
    const response = await api.post('/auth/thirdparty/login-legacy', { code });
    return {
      success: true,
      user: response.data.user,
      access_token: response.data.access_token
    };
  } catch (error: any) {
    return {
      success: false,
      message: error.response?.data?.detail || '登录失败'
    };
  }
};

export const loginWithSystem = async (username: string, password: string): Promise<LoginResult> => {
  try {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    
    const response = await api.post('/auth/system/login', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    return {
      success: true,
      user: response.data.user,
      access_token: response.data.access_token
    };
  } catch (error: any) {
    return {
      success: false,
      message: error.response?.data?.detail || '登录失败'
    };
  }
};

// 用户信息缓存机制，避免频繁请求
let userCache: { user: User | null; timestamp: number } = { user: null, timestamp: 0 };
const CACHE_DURATION = 30000; // 30秒缓存

export const getCurrentUser = async (): Promise<User | null> => {
  try {
    // 检查缓存是否有效
    const now = Date.now();
    if (userCache.user && (now - userCache.timestamp) < CACHE_DURATION) {
      console.log('🟢 使用缓存的用户信息');
      return userCache.user;
    }
    
    console.log('🔄 从API获取用户信息');
    const response = await api.get('/users/me');
    const user = response.data;
    
    // 更新缓存
    userCache = { user, timestamp: now };
    
    return user;
  } catch (error) {
    // 清除缓存
    userCache = { user: null, timestamp: 0 };
    return null;
  }
};

// 清除用户缓存的方法
export const clearUserCache = () => {
  userCache = { user: null, timestamp: 0 };
};

export const logout = () => {
  localStorage.removeItem('user');
  localStorage.removeItem('token');
  clearUserCache(); // 清除用户缓存
};

export default api;