import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Form, Input, Card, message, Tabs, Space, Segmented, Progress, Alert } from 'antd';
import { 
  UserOutlined, 
  LockOutlined, 
  RobotOutlined, 
  FileTextOutlined, 
  ThunderboltOutlined, 
  SafetyOutlined,
  CheckCircleOutlined,
  BgColorsOutlined,
  CloudOutlined,
  StarOutlined,
  HeartOutlined,
  SunOutlined
} from '@ant-design/icons';
import { loginWithThirdParty, loginWithThirdPartyLegacy, loginWithSystem } from '../services/authService';
import config from '../config';
import { useTheme } from '../hooks/useTheme';
import './LoginPage.css';

const { TabPane } = Tabs;

const LoginPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const { currentTheme, setTheme, themes } = useTheme();
  const navigate = useNavigate();

  // 防止重复处理的标志
  const [hasProcessedCode, setHasProcessedCode] = useState(false);
  // 第三方登录过程状态
  const [thirdPartyLoginState, setThirdPartyLoginState] = useState<'idle' | 'processing' | 'success' | 'error'>('idle');
  const [thirdPartyError, setThirdPartyError] = useState<string>('');
  // 系统登录过程状态（保持原有逻辑）
  const [loginStep, setLoginStep] = useState<'idle' | 'exchanging' | 'logging' | 'success' | 'error'>('idle');
  const [loginError, setLoginError] = useState<string>('');
  
  // 监听第三方登录事件
  useEffect(() => {
    // 监听第三方登录开始事件
    const handleThirdPartyLoginStart = () => {
      console.log('📥 LoginPage收到第三方登录开始事件');
      setThirdPartyLoginState('processing');
      setThirdPartyError('');
    };

    // 监听第三方登录成功事件
    const handleThirdPartyLoginSuccess = () => {
      console.log('📥 LoginPage收到第三方登录成功事件');
      setThirdPartyLoginState('success');
    };

    // 监听第三方登录失败事件
    const handleThirdPartyLoginError = (event: CustomEvent) => {
      console.log('📥 LoginPage收到第三方登录失败事件', event.detail);
      setThirdPartyLoginState('error');
      setThirdPartyError(event.detail.error || '登录失败');
    };

    // 添加事件监听器
    window.addEventListener('thirdPartyLoginStart', handleThirdPartyLoginStart);
    window.addEventListener('thirdPartyLoginSuccess', handleThirdPartyLoginSuccess);
    window.addEventListener('thirdPartyLoginError', handleThirdPartyLoginError as EventListener);

    return () => {
      // 清理事件监听器
      window.removeEventListener('thirdPartyLoginStart', handleThirdPartyLoginStart);
      window.removeEventListener('thirdPartyLoginSuccess', handleThirdPartyLoginSuccess);
      window.removeEventListener('thirdPartyLoginError', handleThirdPartyLoginError as EventListener);
    };
  }, []);

  // 检查URL中是否有第三方登录回调的code参数
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    
    if (code && !hasProcessedCode) {
      // 标记为已处理，防止重复执行
      setHasProcessedCode(true);
      
      console.log('🔄 LoginPage检测到第三方登录回调，重定向到专用处理器');
      
      // 立即重定向到CallbackHandler，让专用组件处理
      const currentUrl = new URL(window.location.href);
      const callbackUrl = `/third-login/callback${currentUrl.search}`;
      window.location.replace(callbackUrl);
      return;
    }
  }, [hasProcessedCode]);

  const handleThirdPartyCallback = async (code: string) => {
    // 检查是否已经在处理中，防止重复请求
    if (loading) {
      console.log('🔄 登录请求正在处理中，跳过重复请求');
      return;
    }
    
    // 检查是否已经处理过相同的授权码
    const processedCode = sessionStorage.getItem('processed_auth_code');
    if (processedCode === code) {
      console.log('🔄 相同授权码已处理，跳过重复请求');
      return;
    }
    
    setLoading(true);
    setLoginStep('exchanging');
    setLoginError('');
    
    // 立即标记授权码为已处理
    sessionStorage.setItem('processed_auth_code', code);
    
    try {
      console.log('🔐 开始第三方登录回调处理');
      
      // 尝试使用新架构登录
      let result = await loginWithThirdParty(code);
      
      // 如果新架构失败，尝试使用legacy接口作为回退
      if (!result.success) {
        console.log('🔄 新架构登录失败，尝试Legacy模式', result.message);
        message.warning('正在尝试兼容模式登录...');
        setLoginStep('logging');
        
        result = await loginWithThirdPartyLegacy(code);
        
        if (result.success) {
          console.log('✅ Legacy模式登录成功');
        }
      } else {
        setLoginStep('success');
      }
      
      if (result.success) {
        message.success('登录成功');
        localStorage.setItem('user', JSON.stringify(result.user));
        localStorage.setItem('token', result.access_token || '');
        
        // 清除URL中的code参数
        window.history.replaceState({}, document.title, window.location.pathname);
        // 清除已处理的授权码标记
        sessionStorage.removeItem('processed_auth_code');
        
        setLoginStep('success');
        
        // 触发自定义事件，通知App组件立即更新状态
        window.dispatchEvent(new CustomEvent('userLogin', { 
          detail: { user: result.user, token: result.access_token } 
        }));
        
        // 稍等一下再跳转，让用户看到成功提示和状态更新
        setTimeout(() => {
          navigate('/');
        }, 500);
      } else {
        // 如果登录失败，清除标记以允许重试
        sessionStorage.removeItem('processed_auth_code');
        setLoginStep('error');
        setLoginError(result.message || '登录失败');
        message.error(result.message || '登录失败');
      }
    } catch (error: any) {
      // 如果发生异常，清除标记以允许重试
      sessionStorage.removeItem('processed_auth_code');
      setLoginStep('error');
      const errorMessage = error?.message || '登录过程中发生错误';
      setLoginError(errorMessage);
      console.error('❌ 第三方登录异常:', error);
      message.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleThirdPartyLogin = async () => {
    setLoading(true);
    setThirdPartyLoginState('idle'); // 重置第三方登录状态
    setThirdPartyError('');
    
    try {
      // 1. 获取第三方认证URL
      const response = await fetch(`${config.apiBaseUrl}/auth/thirdparty/url`);
      const { auth_url } = await response.json();
      
      // 2. 检查是否强制使用真实认证（通过查询参数或环境变量）
      const urlParams = new URLSearchParams(window.location.search);
      const forceRealAuth = urlParams.get('real_auth') === 'true' || 
                           localStorage.getItem('force_real_auth') === 'true' ||
                           import.meta.env.VITE_FORCE_REAL_AUTH === 'true';
      
      // 3. 检查是否是开发/测试环境且未强制使用真实认证
      const isDevelopment = process.env.NODE_ENV === 'development' || window.location.hostname === 'localhost';
      
      if (isDevelopment && !forceRealAuth) {
        // 开发/测试环境：模拟第三方认证流程
        setThirdPartyLoginState('processing');
        
        // 生成模拟的authorization code
        const mockCode = `mock_auth_code_${Date.now()}`;
        
        // 直接使用模拟code进行登录（业务流程与生产环境完全一致）
        const result = await loginWithThirdParty(mockCode);
        
        if (result.success) {
          message.success('登录成功');
          localStorage.setItem('user', JSON.stringify(result.user));
          localStorage.setItem('token', result.access_token || '');
          setThirdPartyLoginState('success');
          
          // 触发用户登录事件，通知App组件更新状态
          window.dispatchEvent(new CustomEvent('userLogin', { 
            detail: { user: result.user, token: result.access_token } 
          }));
          
          setTimeout(() => {
            navigate('/');
          }, 500);
        } else {
          setThirdPartyLoginState('error');
          setThirdPartyError(result.message || '登录失败');
          message.error(result.message || '登录失败');
        }
      } else {
        // 生产环境或强制使用真实认证：跳转到真实的第三方认证页面
        // 保存当前页面状态，以便认证后返回
        sessionStorage.setItem('preLoginLocation', window.location.pathname);
        
        // 跳转到第三方认证页面
        window.location.href = auth_url;
      }
    } catch (error) {
      console.error('第三方登录错误:', error);
      setThirdPartyLoginState('error');
      setThirdPartyError('登录过程中发生错误');
      message.error('登录过程中发生错误');
    } finally {
      setLoading(false);
    }
  };

  const handleSystemLogin = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      const result = await loginWithSystem(values.username, values.password);
      
      if (result.success) {
        message.success('登录成功');
        // 保存用户信息和token到localStorage
        localStorage.setItem('user', JSON.stringify(result.user));
        localStorage.setItem('token', result.access_token || '');
        
        // 触发自定义事件，通知App组件立即更新状态
        window.dispatchEvent(new CustomEvent('userLogin', { 
          detail: { user: result.user, token: result.access_token } 
        }));
        
        // 等待系统登录状态更新后跳转
        console.log('⏳ 系统登录等待App组件确认状态更新完成...');
        
        let navigationTimeout: NodeJS.Timeout;
        let stateUpdateConfirmed = false;
        
        // 监听App组件发出的状态更新确认事件
        const handleStateUpdated = (event: CustomEvent) => {
          if (stateUpdateConfirmed) return; // 防止重复处理
          
          stateUpdateConfirmed = true;
          console.log('✅ 系统登录收到App组件状态更新确认，执行跳转');
          
          // 清除超时定时器
          if (navigationTimeout) {
            clearTimeout(navigationTimeout);
          }
          
          // 移除事件监听器
          window.removeEventListener('userStateUpdated', handleStateUpdated as EventListener);
          
          // 执行跳转
          navigate('/', { replace: true });
        };
        
        // 添加事件监听器
        window.addEventListener('userStateUpdated', handleStateUpdated as EventListener);
        
        // 减少超时时间，但保持可靠性
        navigationTimeout = setTimeout(() => {
          if (!stateUpdateConfirmed) {
            console.log('⚠️ 系统登录等待状态更新确认超时(1000ms)，强制跳转');
            window.removeEventListener('userStateUpdated', handleStateUpdated as EventListener);
            navigate('/', { replace: true });
          }
        }, 1000); // 1秒超时
      } else {
        message.error(result.message || '登录失败');
      }
    } catch (error) {
      message.error('登录过程中发生错误');
    } finally {
      setLoading(false);
    }
  };

  const { themeConfig } = useTheme();

  // 获取第三方登录状态显示文本
  const getThirdPartyLoginText = () => {
    switch (thirdPartyLoginState) {
      case 'processing':
        return '🔐 正在验证身份信息...';
      case 'success':
        return '✅ 登录成功，即将跳转...';
      case 'error':
        return '❌ 登录失败';
      default:
        return '';
    }
  };

  // 获取第三方登录进度百分比
  const getThirdPartyLoginProgress = () => {
    switch (thirdPartyLoginState) {
      case 'processing':
        return 50;
      case 'success':
        return 100;
      case 'error':
        return 0;
      default:
        return 0;
    }
  };

  // 获取系统登录步骤显示文本
  const getLoginStepText = () => {
    switch (loginStep) {
      case 'exchanging':
        return '正在兑换第三方令牌...';
      case 'logging':
        return '正在进行用户登录...';
      case 'success':
        return '登录成功，即将跳转...';
      case 'error':
        return '登录失败';
      default:
        return '';
    }
  };

  // 获取系统登录进度百分比
  const getLoginProgress = () => {
    switch (loginStep) {
      case 'exchanging':
        return 30;
      case 'logging':
        return 70;
      case 'success':
        return 100;
      case 'error':
        return 0;
      default:
        return 0;
    }
  };

  return (
    <div className="login-container" style={{ background: themeConfig.background }}>
      {/* 主题切换器 */}
      <div className="theme-switcher">
        <div className="theme-switcher-title">
          <BgColorsOutlined /> 选择主题
        </div>
        <div className="theme-options">
          {Object.entries(themes).map(([key, themeConfig]) => (
            <div
              key={key}
              className={`theme-option ${currentTheme === key ? 'active' : ''}`}
              onClick={() => setTheme(key as keyof typeof themes)}
              title={themeConfig.description}
            >
              {themeConfig.icon}
              <span>{themeConfig.name}</span>
            </div>
          ))}
        </div>
      </div>

      {/* 浮动装饰元素 */}
      <div className="floating-elements">
        <div className="floating-circle"></div>
        <div className="floating-circle"></div>
        <div className="floating-circle"></div>
        <div className="floating-circle"></div>
      </div>

      {/* 主要内容区域 */}
      <div className="login-main-content">
        {/* 左侧介绍 */}
        <div className="login-left-section">
          <div className="brand-container">
            <div className="login-logo">
              <span className="logo-ai">AI</span>
              <span className="logo-docs">Docs</span>
              <span className="logo-pro">Pro</span>
            </div>
            <div className="login-subtitle">
              智能文档质量评估专家
            </div>
            <div className="login-tagline">
              让每一份文档都达到专业标准
            </div>
          </div>
          
          <div className="value-proposition">
            <div className="value-item">
              <div className="value-icon">
                <RobotOutlined />
              </div>
              <div className="value-content">
                <div className="value-title">AI深度分析</div>
                <div className="value-desc">基于大语言模型的智能文档质量评估</div>
              </div>
            </div>
            
            <div className="value-item">
              <div className="value-icon">
                <FileTextOutlined />
              </div>
              <div className="value-content">
                <div className="value-title">全格式兼容</div>
                <div className="value-desc">支持PDF、Word、Markdown等主流格式</div>
              </div>
            </div>
            
            <div className="value-item">
              <div className="value-icon">
                <CheckCircleOutlined />
              </div>
              <div className="value-content">
                <div className="value-title">专业报告</div>
                <div className="value-desc">生成结构化质量评估报告和改进建议</div>
              </div>
            </div>
          </div>
          
          <div className="trust-indicators">
            <div className="trust-item">
              <ThunderboltOutlined className="trust-icon" />
              <span>毫秒级响应</span>
            </div>
            <div className="trust-item">
              <SafetyOutlined className="trust-icon" />
              <span>企业级安全</span>
            </div>
            <div className="trust-item">
              <StarOutlined className="trust-icon" />
              <span>专业可靠</span>
            </div>
          </div>
        </div>

        {/* 右侧登录 */}
        <div className="login-right-section">
          <Card className="login-card" title="登录系统" bordered={false}>
          <Tabs defaultActiveKey="1" className="login-tabs">
            <TabPane tab="第三方登录" key="1">
              <Space direction="vertical" style={{ width: '100%' }}>
                {/* 第三方登录进度显示 */}
                {thirdPartyLoginState !== 'idle' && (
                  <div style={{ marginBottom: '16px' }}>
                    <div style={{ marginBottom: '8px', fontSize: '14px', color: themeConfig.colors.primary }}>
                      {getThirdPartyLoginText()}
                    </div>
                    <Progress 
                      percent={getThirdPartyLoginProgress()} 
                      status={thirdPartyLoginState === 'error' ? 'exception' : thirdPartyLoginState === 'success' ? 'success' : 'active'}
                      strokeColor={thirdPartyLoginState === 'success' ? '#52c41a' : themeConfig.colors.primary}
                    />
                  </div>
                )}
                
                {/* 第三方登录错误信息显示 */}
                {thirdPartyError && (
                  <Alert
                    message="🤔 登录遇到小问题"
                    description={
                      <div>
                        <div style={{ marginBottom: '4px' }}>{thirdPartyError}</div>
                        <div style={{ fontSize: '12px', opacity: 0.8 }}>
                          💡 请检查网络连接或稍后重试
                        </div>
                      </div>
                    }
                    type="warning"
                    showIcon
                    closable
                    onClose={() => {
                      setThirdPartyError('');
                      setThirdPartyLoginState('idle');
                    }}
                    style={{ 
                      marginBottom: '16px',
                      borderRadius: '8px',
                      border: '1px solid #faad14'
                    }}
                  />
                )}
                
                <Button 
                  type="primary" 
                  onClick={handleThirdPartyLogin}
                  loading={loading || thirdPartyLoginState === 'processing'}
                  disabled={thirdPartyLoginState === 'processing' || thirdPartyLoginState === 'success'}
                  className="login-button"
                  style={{ 
                    width: '100%',
                    background: `linear-gradient(135deg, ${themeConfig.colors.primary} 0%, ${themeConfig.colors.secondary} 100%)`,
                    boxShadow: `0 4px 15px ${themeConfig.colors.primary}40`
                  }}
                  icon={<UserOutlined />}
                >
                  {thirdPartyLoginState === 'processing' ? '登录中...' : 
                   thirdPartyLoginState === 'success' ? '登录成功' :
                   loading ? '处理中...' : '第三方登录'}
                </Button>
                <div className="login-tips">
                  🔗 点击后将跳转到第三方认证页面
                </div>
              </Space>
            </TabPane>
            <TabPane tab="系统登录" key="2">
              <Form
                name="system_login"
                onFinish={handleSystemLogin}
                autoComplete="off"
                layout="vertical"
              >
                <Form.Item
                  name="username"
                  rules={[{ required: true, message: '请输入用户名!' }]}
                  className="login-form-item"
                >
                  <Input 
                    prefix={<UserOutlined />} 
                    placeholder="请输入用户名"
                    className="login-input"
                  />
                </Form.Item>

                <Form.Item
                  name="password"
                  rules={[{ required: true, message: '请输入密码!' }]}
                  className="login-form-item"
                >
                  <Input
                    prefix={<LockOutlined />}
                    type="password"
                    placeholder="请输入密码"
                    className="login-input"
                  />
                </Form.Item>

                <Form.Item>
                  <Button 
                    type="primary" 
                    htmlType="submit" 
                    loading={loading}
                    className="login-button"
                    style={{ 
                      width: '100%',
                      background: `linear-gradient(135deg, ${themeConfig.colors.primary} 0%, ${themeConfig.colors.secondary} 100%)`,
                      boxShadow: `0 4px 15px ${themeConfig.colors.primary}40`
                    }}
                  >
                    立即登录
                  </Button>
                </Form.Item>
                
                <div className="login-tips">
                  🔑 请使用管理员账号登录系统
                </div>
              </Form>
            </TabPane>
          </Tabs>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;