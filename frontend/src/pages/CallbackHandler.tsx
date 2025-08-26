import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { message, Spin, Card, Progress } from 'antd';
import { LoadingOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { loginWithThirdParty } from '../services/authService';

/**
 * 第三方登录回调处理组件
 * 优化版：显示登录进度，提供更好的用户体验
 */
const CallbackHandler: React.FC = () => {
  const navigate = useNavigate();
  const [isProcessing, setIsProcessing] = useState(false);
  const [loginStatus, setLoginStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [loginMessage, setLoginMessage] = useState('正在处理登录信息...');
  const [progress, setProgress] = useState(10);

  useEffect(() => {
    // 防止React StrictMode导致的重复执行
    if (!isProcessing) {
      setIsProcessing(true);
      handleCallback();
    }
  }, [isProcessing]);

  // 全局锁机制：防止多个组件同时处理相同的授权码
  const acquireLock = (code: string): boolean => {
    const lockKey = `auth_processing_${code}`;
    const now = Date.now();
    const existingLock = sessionStorage.getItem(lockKey);
    
    if (existingLock) {
      const lockTime = parseInt(existingLock);
      // 如果锁存在且未过期（5分钟），返回false
      if (now - lockTime < 5 * 60 * 1000) {
        console.log('🔒 授权码正在被其他组件处理中，跳过');
        return false;
      }
    }
    
    // 获取锁
    sessionStorage.setItem(lockKey, now.toString());
    console.log('🔓 获取授权码处理锁成功');
    return true;
  };

  const releaseLock = (code: string) => {
    const lockKey = `auth_processing_${code}`;
    sessionStorage.removeItem(lockKey);
    console.log('🔓 释放授权码处理锁');
  };

  const handleCallback = async () => {
    try {
      // 1. 从URL中获取授权码
      const urlParams = new URLSearchParams(window.location.search);
      const code = urlParams.get('code');
      const error = urlParams.get('error');
      const state = urlParams.get('state');

      // 2. 检查是否有错误参数
      if (error) {
        console.error('第三方认证失败:', error);
        // 触发登录失败事件，让LoginPage处理UI显示
        window.dispatchEvent(new CustomEvent('thirdPartyLoginError', { 
          detail: { error: `第三方认证失败: ${error}` } 
        }));
        navigate('/login', { replace: true });
        return;
      }

      // 3. 检查是否有授权码
      if (!code) {
        console.error('未收到有效的授权码');
        // 触发登录失败事件，让LoginPage处理UI显示
        window.dispatchEvent(new CustomEvent('thirdPartyLoginError', { 
          detail: { error: '未收到有效的授权码，请重新登录' } 
        }));
        navigate('/login', { replace: true });
        return;
      }

      console.log('收到第三方认证回调:', { code, state });

      // 4. 检查并获取处理锁
      if (!acquireLock(code)) {
        console.log('授权码正在处理中，跳过重复处理');
        navigate('/login', { replace: true });
        return;
      }

      // 更新进度：获取授权码成功
      setProgress(30);
      setLoginMessage('正在验证授权码...');

      // 触发登录开始事件，让LoginPage显示进度
      window.dispatchEvent(new CustomEvent('thirdPartyLoginStart'));

      // 5. 使用授权码进行登录
      setProgress(60);
      setLoginMessage('正在登录系统...');
      
      const result = await loginWithThirdParty(code);

      if (result.success) {
        // 6. 登录成功，保存用户信息
        setProgress(85);
        setLoginMessage('登录成功，正在初始化...');
        setLoginStatus('success');
        
        localStorage.setItem('user', JSON.stringify(result.user));
        localStorage.setItem('token', result.access_token || '');
        
        // 7. 显示成功消息
        message.success('第三方登录成功！');
        
        // 8. 释放锁
        releaseLock(code);
        
        // 9. 触发用户登录事件，通知App组件更新状态
        console.log('🚀 触发userLogin事件，通知App组件更新状态');
        window.dispatchEvent(new CustomEvent('userLogin', { 
          detail: { user: result.user, token: result.access_token } 
        }));
        
        // 10. 触发登录成功事件，让LoginPage显示成功状态
        window.dispatchEvent(new CustomEvent('thirdPartyLoginSuccess'));
        
        // 11. 等待React状态更新完成后再跳转
        console.log('⏳ 等待App组件确认状态更新完成...');
        
        let navigationTimeout: NodeJS.Timeout;
        let stateUpdateConfirmed = false;
        
        // 监听App组件发出的状态更新确认事件
        const handleStateUpdated = (event: CustomEvent) => {
          if (stateUpdateConfirmed) return; // 防止重复处理
          
          stateUpdateConfirmed = true;
          console.log('✅ 收到App组件状态更新确认，执行跳转');
          
          // 更新进度到100%
          setProgress(100);
          setLoginMessage('跳转中...');
          
          // 清除超时定时器
          if (navigationTimeout) {
            clearTimeout(navigationTimeout);
          }
          
          // 移除事件监听器
          window.removeEventListener('userStateUpdated', handleStateUpdated as EventListener);
          
          // 稍微延迟跳转，让用户看到完成状态
          setTimeout(() => {
            const preLoginLocation = sessionStorage.getItem('preLoginLocation');
            sessionStorage.removeItem('preLoginLocation');
            navigate(preLoginLocation || '/', { replace: true });
          }, 200);
        };
        
        // 添加事件监听器
        window.addEventListener('userStateUpdated', handleStateUpdated as EventListener);
        
        // 进一步优化：减少超时时间，提升响应速度
        navigationTimeout = setTimeout(() => {
          if (!stateUpdateConfirmed) {
            console.log('⚠️ 等待状态更新确认超时(300ms)，强制跳转');
            setProgress(100);
            setLoginMessage('跳转中...');
            window.removeEventListener('userStateUpdated', handleStateUpdated as EventListener);
            
            // 稍微延迟跳转，让用户看到完成状态
            setTimeout(() => {
              navigate('/', { replace: true });
            }, 100);
          }
        }, 300); // 300ms超时，更快的响应

      } else {
        setLoginStatus('error');
        setLoginMessage('登录失败');
        setProgress(0);
        
        releaseLock(code);
        // 触发登录失败事件，让LoginPage处理UI显示
        window.dispatchEvent(new CustomEvent('thirdPartyLoginError', { 
          detail: { error: result.message || '登录失败' } 
        }));
        
        // 显示错误状态1秒后跳转
        setTimeout(() => {
          navigate('/login', { replace: true });
        }, 1500);
      }

    } catch (error) {
      console.error('第三方登录回调处理失败:', error);
      
      setLoginStatus('error');
      setLoginMessage('登录过程中发生错误');
      setProgress(0);
      
      // 发生异常时释放锁
      const urlParams = new URLSearchParams(window.location.search);
      const code = urlParams.get('code');
      if (code) releaseLock(code);
      
      // 触发登录失败事件，让LoginPage处理UI显示
      window.dispatchEvent(new CustomEvent('thirdPartyLoginError', { 
        detail: { error: '登录过程中发生错误，请稍后重试' } 
      }));
      
      // 显示错误状态1.5秒后跳转
      setTimeout(() => {
        navigate('/login', { replace: true });
      }, 1500);
    }
  };

  // 显示登录进度界面，提供更好的用户体验
  return (
    <div style={{ 
      display: 'flex', 
      justifyContent: 'center', 
      alignItems: 'center', 
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      padding: '20px'
    }}>
      <Card 
        style={{ 
          width: '400px', 
          textAlign: 'center',
          borderRadius: '12px',
          boxShadow: '0 8px 24px rgba(0,0,0,0.1)'
        }}
        bordered={false}
      >
        <div style={{ padding: '20px' }}>
          {/* 登录图标 */}
          <div style={{ marginBottom: '20px' }}>
            {loginStatus === 'success' ? (
              <CheckCircleOutlined 
                style={{ 
                  fontSize: '48px', 
                  color: '#52c41a',
                  animation: loginStatus === 'success' ? 'fadeIn 0.5s ease-in' : 'none'
                }} 
              />
            ) : loginStatus === 'error' ? (
              <div style={{ 
                fontSize: '48px', 
                color: '#ff4d4f'
              }}>
                ❌
              </div>
            ) : (
              <Spin 
                indicator={<LoadingOutlined style={{ fontSize: '48px', color: '#1890ff' }} spin />} 
              />
            )}
          </div>
          
          {/* 登录状态文字 */}
          <div style={{ 
            fontSize: '18px', 
            fontWeight: '500',
            color: loginStatus === 'error' ? '#ff4d4f' : loginStatus === 'success' ? '#52c41a' : '#1890ff',
            marginBottom: '20px'
          }}>
            {loginMessage}
          </div>
          
          {/* 进度条 */}
          {loginStatus !== 'error' && (
            <Progress 
              percent={progress} 
              status={loginStatus === 'success' ? 'success' : 'active'}
              strokeColor={loginStatus === 'success' ? '#52c41a' : '#1890ff'}
              trailColor="#f0f0f0"
              showInfo={false}
              style={{ marginBottom: '10px' }}
            />
          )}
          
          {/* 提示文字 */}
          <div style={{ 
            fontSize: '14px', 
            color: '#666',
            opacity: 0.8
          }}>
            {loginStatus === 'processing' && '请稍候，正在为您登录...'}
            {loginStatus === 'success' && '登录成功！正在跳转到主页面...'}
            {loginStatus === 'error' && '请检查网络连接后重试'}
          </div>
        </div>
      </Card>
    </div>
  );
};

export default CallbackHandler;