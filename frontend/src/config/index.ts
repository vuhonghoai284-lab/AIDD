/**
 * 应用配置管理
 */

interface AppConfig {
  apiBaseUrl: string;
  wsBaseUrl: string;
  appTitle: string;
  appVersion: string;
  isDev: boolean;
  isProd: boolean;
}

// 从环境变量获取配置
const getDefaultApiUrl = () => {
  // 优先使用环境变量，其次使用当前域名 + 默认端口
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL;
  }
  
  // 在生产环境使用相对路径
  if (import.meta.env.PROD) {
    return `${window.location.protocol}//${window.location.host}/api`;
  }
  
  // 开发环境默认配置 - 支持环境变量指定后端端口
  const backendPort = import.meta.env.VITE_BACKEND_PORT || '8080';
  return `${window.location.protocol}//${window.location.hostname}:${backendPort}/api`;
};

const getDefaultWsUrl = () => {
  // 优先使用环境变量
  if (import.meta.env.VITE_WS_BASE_URL) {
    return import.meta.env.VITE_WS_BASE_URL;
  }
  
  // 在生产环境使用相对路径
  if (import.meta.env.PROD) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}`;
  }
  
  // 开发环境默认配置 - 支持环境变量指定后端端口
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const backendPort = import.meta.env.VITE_BACKEND_PORT || '8080';
  return `${protocol}//${window.location.hostname}:${backendPort}`;
};

const config: AppConfig = {
  apiBaseUrl: getDefaultApiUrl(),
  wsBaseUrl: getDefaultWsUrl(),
  appTitle: import.meta.env.VITE_APP_TITLE || 'AI文档测试系统',
  appVersion: import.meta.env.VITE_APP_VERSION || '2.0.0',
  isDev: import.meta.env.DEV,
  isProd: import.meta.env.PROD,
};

// 验证必要的配置
if (!config.apiBaseUrl) {
  throw new Error('VITE_API_BASE_URL is required');
}

if (!config.wsBaseUrl) {
  throw new Error('VITE_WS_BASE_URL is required');
}

// 日志配置信息（仅开发环境）
if (config.isDev) {
  console.log('应用配置:', {
    apiBaseUrl: config.apiBaseUrl,
    wsBaseUrl: config.wsBaseUrl,
    appTitle: config.appTitle,
    appVersion: config.appVersion,
    environment: config.isDev ? '开发环境' : '生产环境',
    environmentVariables: {
      VITE_API_BASE_URL: import.meta.env.VITE_API_BASE_URL,
      VITE_WS_BASE_URL: import.meta.env.VITE_WS_BASE_URL,
      VITE_BACKEND_PORT: import.meta.env.VITE_BACKEND_PORT,
    },
  });
}

export default config;