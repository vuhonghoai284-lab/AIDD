// 前端配置
const config = {
  // API基础URL，确保包含正确的前缀避免重定向
  // 在Vite中，环境变量需要以VITE_开头
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080/api',
  
  // 其他配置
  appName: 'AI文档测试系统',
  version: '1.0.0'
};

export default config;